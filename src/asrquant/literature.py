"""Scientific-paper ingestion and hypothesis discovery with source provenance.

The module is deliberately conservative: it extracts text and candidate claims from
PDFs, but never claims that a hypothesis is globally novel. ``corpus-novel`` means
only that no direct match was found in the supplied corpus.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Sequence

import pandas as pd


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_WHITESPACE = re.compile(r"\s+")

_HYPOTHESIS_PATTERNS = (
    r"\bwe hypothesi[sz]e\b",
    r"\bour hypothesis\b",
    r"\bwe predict\b",
    r"\bwe expect\b",
    r"\bwe test whether\b",
    r"\bwe examine whether\b",
    r"\bwe investigate whether\b",
    r"\bis associated with\b",
    r"\bpredicts?\b",
    r"\bleads? to\b",
    r"\baffects?\b",
    r"\bimpact of\b",
    r"\beffect of\b",
    r"\brelationship between\b",
)
_GAP_PATTERNS = (
    r"\bfuture research\b",
    r"\bfuture work\b",
    r"\bremains? unclear\b",
    r"\bremains? unknown\b",
    r"\bhas not been examined\b",
    r"\bhas not been tested\b",
    r"\bnot yet been\b",
    r"\blittle is known\b",
    r"\bunderexplored\b",
    r"\bopen question\b",
)
_TEST_PATTERNS = (
    r"\bwe test(?:ed)?\b",
    r"\bwe examine(?:d)?\b",
    r"\bwe investigate(?:d)?\b",
    r"\bwe estimate(?:d)?\b",
    r"\bempirical results?\b",
    r"\bwe find\b",
    r"\bour results?\b",
    r"\bthe evidence\b",
)

_POSITIVE = re.compile(r"\b(increase|increases|higher|positive|outperform|improve|rise|rises)\b", re.I)
_NEGATIVE = re.compile(r"\b(decrease|decreases|lower|negative|underperform|reduce|fall|falls)\b", re.I)


def _clean(text: str) -> str:
    return _WHITESPACE.sub(" ", text or "").strip()


def _clean_page(text: str) -> str:
    lines = [_WHITESPACE.sub(" ", line).strip() for line in (text or "").splitlines()]
    return "\n".join(line for line in lines if line)


def _sentences(text: str) -> list[str]:
    cleaned = _clean(text)
    if not cleaned:
        return []
    candidates = []
    for part in _SENTENCE_SPLIT.split(cleaned):
        sentence = part.strip()
        if not 35 <= len(sentence) <= 700:
            continue
        lower = sentence.lower()
        code_markers = sum(marker in lower for marker in ("import ", "print(", "def ", "lambda ", "project.", "asr.", "= asr"))
        if code_markers >= 2 or sentence.count("=") >= 4:
            continue
        letter_ratio = sum(character.isalpha() for character in sentence) / max(1, len(sentence))
        if letter_ratio < 0.55:
            continue
        candidates.append(sentence)
    return candidates


def _tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with", "is", "are",
        "we", "our", "that", "this", "be", "by", "as", "from", "at", "it", "its", "between",
    }
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2 and token not in stop}




def _topic_tokens(topic: str | None) -> set[str]:
    """Expand common quantitative-finance topic labels into useful search tokens."""
    tokens = _tokens(topic or "")
    key = (topic or "").lower().replace("-", "_").replace(" ", "_")
    if any(term in key for term in ("fixed_income", "interest_rate", "rates")):
        tokens.update({
            "rate", "rates", "yield", "curve", "forward", "bond", "bonds",
            "swap", "swaps", "swaption", "caplet", "ois", "duration", "dv01",
            "hedge", "hedging", "derivative", "derivatives",
        })
    if "equity" in key or "factor" in key:
        tokens.update({"equity", "stock", "stocks", "factor", "factors", "return", "returns", "alpha", "beta"})
    if "volatility" in key or "option" in key:
        tokens.update({"volatility", "option", "options", "implied", "smile", "skew", "variance"})
    return tokens

def _similarity(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _direction(text: str) -> str | None:
    positive = bool(_POSITIVE.search(text))
    negative = bool(_NEGATIVE.search(text))
    if positive and not negative:
        return "positive"
    if negative and not positive:
        return "negative"
    return None


@dataclass(frozen=True)
class SourceExcerpt:
    """One source-linked passage from a paper."""

    paper_id: str
    page: int
    text: str
    section: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperDocument:
    """Parsed paper text, metadata and page-level provenance."""

    paper_id: str
    title: str
    path: str | None
    pages: list[str]
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    abstract: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.pages)

    @property
    def fingerprint(self) -> str:
        return sha256(self.text.encode("utf-8", errors="ignore")).hexdigest()[:16]

    @classmethod
    def from_pdf(cls, path: str | Path) -> "PaperDocument":
        """Read a text-based PDF with page provenance.

        Scanned PDFs are not silently OCRed. Empty pages are retained and a warning
        asks the user to OCR the document before scientific extraction.
        """
        source = Path(path)
        if not source.exists() or source.suffix.lower() != ".pdf":
            raise ValueError(f"expected an existing PDF file, received {source}")
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - dependency declaration protects this
            raise ImportError("PDF ingestion requires pypdf; install ASRQuant with its standard dependencies") from exc

        reader = PdfReader(str(source))
        pages: list[str] = []
        warnings: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                pages.append(_clean_page(page.extract_text() or ""))
            except Exception as exc:  # malformed page should not lose the corpus
                pages.append("")
                warnings.append(f"page {index}: text extraction failed ({type(exc).__name__})")
        if not any(pages):
            warnings.append("no extractable text found; the PDF may be scanned and require OCR")

        raw_meta = dict(reader.metadata or {})
        inferred_title = cls._infer_title(pages, source.stem)
        metadata_title = _clean(str(raw_meta.get("/Title", "")))
        if metadata_title and inferred_title and _similarity(metadata_title, inferred_title) >= 0.45:
            title = metadata_title
        else:
            title = inferred_title or metadata_title
        author_line = _clean(str(raw_meta.get("/Author", "")))
        authors = [name.strip() for name in re.split(r"[,;]", author_line) if name.strip()]
        year = cls._infer_year(raw_meta, pages)
        abstract = cls._infer_abstract(pages)
        paper_id = sha256(f"{source.resolve()}:{title}".encode()).hexdigest()[:12]
        return cls(
            paper_id=paper_id,
            title=title,
            path=str(source),
            pages=pages,
            authors=authors,
            year=year,
            abstract=abstract,
            metadata={str(k).lstrip("/"): str(v) for k, v in raw_meta.items()},
            warnings=warnings,
        )

    @classmethod
    def from_text(
        cls,
        text: str,
        *,
        title: str = "Untitled paper",
        authors: Sequence[str] | None = None,
        year: int | None = None,
        paper_id: str | None = None,
    ) -> "PaperDocument":
        """Create a document from already extracted text, useful for APIs and tests."""
        cleaned = _clean(text)
        identifier = paper_id or sha256(f"{title}:{cleaned}".encode()).hexdigest()[:12]
        return cls(identifier, title, None, [cleaned], list(authors or []), year, cls._infer_abstract([cleaned]))

    @staticmethod
    def _infer_title(pages: Sequence[str], fallback: str) -> str:
        if pages:
            candidates = [line.strip() for line in re.split(r"[\n\r]", pages[0]) if 8 <= len(line.strip()) <= 240]
            if candidates:
                return candidates[0]
        return fallback.replace("_", " ").replace("-", " ").strip()

    @staticmethod
    def _infer_year(metadata: dict[str, Any], pages: Sequence[str]) -> int | None:
        # PDF dates commonly use D:YYYYMMDD. Prefer creation/modification metadata
        # over arbitrary years occurring in the title page or bibliography.
        for key in ("/CreationDate", "/ModDate", "CreationDate", "ModDate"):
            value = str(metadata.get(key, ""))
            match = re.search(r"(?:D:)?((?:19|20)\d{2})", value)
            if match:
                return int(match.group(1))
        first_page = pages[0][:3000] if pages else ""
        years = [int(value) for value in re.findall(r"\b(?:19|20)\d{2}\b", first_page)]
        return years[0] if years else None

    @staticmethod
    def _infer_abstract(pages: Sequence[str]) -> str | None:
        beginning = " ".join(pages[:2])[:12000]
        match = re.search(
            r"\babstract\b\s*[:.-]?\s*(.+?)(?=\b(?:keywords?|jel classification|1\.?\s+introduction|introduction)\b)",
            beginning,
            flags=re.I | re.S,
        )
        return _clean(match.group(1)) if match else None


@dataclass
class HypothesisCandidate:
    """A source-linked economic hypothesis or research gap."""

    hypothesis_id: str
    statement: str
    novelty_status: str
    confidence: float
    evidence: list[SourceExcerpt] = field(default_factory=list)
    expected_sign: str | None = None
    tags: list[str] = field(default_factory=list)
    rationale: str = ""
    evidence_status: str = "proposed"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def source_count(self) -> int:
        return len({item.paper_id for item in self.evidence})

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_count"] = self.source_count
        return payload


@dataclass
class HypothesisRegistry:
    """Searchable collection of candidate hypotheses."""

    hypotheses: list[HypothesisCandidate]
    corpus_fingerprint: str | None = None
    scope_note: str = (
        "Novelty labels are corpus-relative. 'corpus-novel' never means that a claim "
        "has never been tested anywhere in the global literature."
    )

    def __len__(self) -> int:
        return len(self.hypotheses)

    def __iter__(self):
        return iter(self.hypotheses)

    def select(self, identifier: str | int) -> HypothesisCandidate:
        if isinstance(identifier, int):
            return self.hypotheses[identifier]
        for hypothesis in self.hypotheses:
            if hypothesis.hypothesis_id == identifier:
                return hypothesis
        raise KeyError(f"unknown hypothesis {identifier!r}")

    def to_frame(self) -> pd.DataFrame:
        rows = []
        for item in self.hypotheses:
            rows.append(
                {
                    "hypothesis_id": item.hypothesis_id,
                    "statement": item.statement,
                    "novelty_status": item.novelty_status,
                    "confidence": item.confidence,
                    "expected_sign": item.expected_sign,
                    "source_count": item.source_count,
                    "evidence_status": item.evidence_status,
                    "pages": ", ".join(f"{e.paper_id}:p{e.page}" for e in item.evidence),
                    "rationale": item.rationale,
                }
            )
        return pd.DataFrame(rows)


@dataclass
class LiteratureCorpus:
    """A collection of parsed papers with conservative hypothesis discovery."""

    papers: list[PaperDocument]
    topic: str | None = None

    @classmethod
    def from_pdfs(
        cls,
        paths: str | Path | Sequence[str | Path],
        *,
        topic: str | None = None,
        recursive: bool = True,
    ) -> "LiteratureCorpus":
        source_paths: list[Path]
        if isinstance(paths, (str, Path)):
            root = Path(paths)
            if root.is_dir():
                source_paths = sorted(root.rglob("*.pdf") if recursive else root.glob("*.pdf"))
            else:
                source_paths = [root]
        else:
            source_paths = [Path(path) for path in paths]
        if not source_paths:
            raise ValueError("no PDF files were found")
        return cls([PaperDocument.from_pdf(path) for path in source_paths], topic=topic)

    @classmethod
    def from_texts(
        cls,
        documents: Sequence[str | tuple[str, str] | PaperDocument],
        *,
        topic: str | None = None,
    ) -> "LiteratureCorpus":
        papers: list[PaperDocument] = []
        for index, document in enumerate(documents, start=1):
            if isinstance(document, PaperDocument):
                papers.append(document)
            elif isinstance(document, tuple):
                papers.append(PaperDocument.from_text(document[1], title=document[0]))
            else:
                papers.append(PaperDocument.from_text(document, title=f"Document {index}"))
        return cls(papers, topic=topic)

    @property
    def fingerprint(self) -> str:
        payload = ":".join(sorted(paper.fingerprint for paper in self.papers))
        return sha256(payload.encode()).hexdigest()[:16]

    def search(self, query: str, *, top_k: int = 20) -> list[SourceExcerpt]:
        """Rank source sentences by transparent token overlap."""
        query_tokens = _tokens(query)
        scored: list[tuple[float, SourceExcerpt]] = []
        for paper in self.papers:
            for page_number, page in enumerate(paper.pages, start=1):
                for sentence in _sentences(page):
                    sentence_tokens = _tokens(sentence)
                    score = len(query_tokens & sentence_tokens) / max(1, len(query_tokens))
                    if score > 0:
                        scored.append((score, SourceExcerpt(paper.paper_id, page_number, sentence)))
        return [item for _, item in sorted(scored, key=lambda pair: pair[0], reverse=True)[:top_k]]

    def discover_hypotheses(
        self,
        *,
        topic: str | None = None,
        include_gaps: bool = True,
        similarity_threshold: float = 0.48,
        max_candidates: int = 100,
        extractor: Callable[[PaperDocument], Iterable[dict[str, Any] | HypothesisCandidate]] | None = None,
    ) -> HypothesisRegistry:
        """Extract and cluster hypothesis-like claims with page citations.

        A custom ``extractor`` may connect a local or remote language model while
        preserving the same provenance contract. Without one, deterministic
        heuristics are used.
        """
        active_topic = topic or self.topic
        topic_tokens = _topic_tokens(active_topic)
        raw: list[tuple[str, SourceExcerpt, bool, bool, float]] = []
        if extractor is not None:
            custom: list[HypothesisCandidate] = []
            for paper in self.papers:
                for item in extractor(paper):
                    if isinstance(item, HypothesisCandidate):
                        custom.append(item)
                    else:
                        statement = _clean(str(item["statement"]))
                        page = int(item.get("page", 1))
                        custom.append(
                            HypothesisCandidate(
                                hypothesis_id="",
                                statement=statement,
                                novelty_status=str(item.get("novelty_status", "underexplored")),
                                confidence=float(item.get("confidence", 0.7)),
                                evidence=[SourceExcerpt(paper.paper_id, page, str(item.get("source_text", statement)))],
                                expected_sign=item.get("expected_sign"),
                                tags=list(item.get("tags", [])),
                                rationale=str(item.get("rationale", "custom extractor")),
                                evidence_status=str(item.get("evidence_status", "proposed")),
                            )
                        )
            for index, item in enumerate(custom, start=1):
                item.hypothesis_id = f"H{index:03d}"
            return HypothesisRegistry(custom[:max_candidates], self.fingerprint)

        hypothesis_regex = re.compile("|".join(_HYPOTHESIS_PATTERNS), re.I)
        gap_regex = re.compile("|".join(_GAP_PATTERNS), re.I)
        test_regex = re.compile("|".join(_TEST_PATTERNS), re.I)
        for paper in self.papers:
            for page_number, page in enumerate(paper.pages, start=1):
                for sentence in _sentences(page):
                    is_gap = bool(gap_regex.search(sentence))
                    is_hypothesis = bool(hypothesis_regex.search(sentence))
                    is_tested = bool(test_regex.search(sentence))
                    if not is_hypothesis and not (include_gaps and is_gap):
                        continue
                    sentence_tokens = _tokens(sentence)
                    topic_score = (
                        len(topic_tokens & sentence_tokens) / max(1, len(topic_tokens)) if topic_tokens else 0.5
                    )
                    if topic_tokens and topic_score == 0:
                        continue
                    confidence = min(0.98, 0.55 + 0.25 * topic_score + (0.12 if is_hypothesis else 0.03))
                    raw.append((sentence, SourceExcerpt(paper.paper_id, page_number, sentence), is_gap, is_tested, confidence))

        clusters: list[dict[str, Any]] = []
        for sentence, evidence, is_gap, is_tested, confidence in raw:
            match = next(
                (cluster for cluster in clusters if _similarity(sentence, cluster["statement"]) >= similarity_threshold),
                None,
            )
            if match is None:
                clusters.append(
                    {
                        "statement": sentence,
                        "evidence": [evidence],
                        "gaps": int(is_gap),
                        "tested": int(is_tested),
                        "confidences": [confidence],
                        "directions": [_direction(sentence)],
                    }
                )
            else:
                match["evidence"].append(evidence)
                match["gaps"] += int(is_gap)
                match["tested"] += int(is_tested)
                match["confidences"].append(confidence)
                match["directions"].append(_direction(sentence))

        candidates: list[HypothesisCandidate] = []
        for index, cluster in enumerate(clusters[:max_candidates], start=1):
            evidence = cluster["evidence"]
            source_count = len({item.paper_id for item in evidence})
            non_null_directions = {value for value in cluster["directions"] if value is not None}
            if len(non_null_directions) > 1:
                novelty = "contradictory"
                rationale = "The corpus contains similar claims with opposing directional language."
            elif cluster["gaps"] and source_count == 1:
                novelty = "corpus-novel"
                rationale = "The claim is derived from a gap or limitation and no direct match was found elsewhere in the supplied corpus."
            elif source_count >= 3:
                novelty = "established"
                rationale = "Similar claims were found in at least three papers in the supplied corpus."
            elif source_count == 2:
                novelty = "replicated"
                rationale = "Similar claims were found in two papers in the supplied corpus."
            else:
                novelty = "underexplored"
                rationale = "Only one direct source was found in the supplied corpus."
            evidence_status = (
                "tested_in_corpus" if cluster["tested"] > 0
                else "not_directly_tested_in_corpus" if cluster["gaps"] > 0
                else "proposed_in_corpus"
            )
            candidates.append(
                HypothesisCandidate(
                    hypothesis_id=f"H{index:03d}",
                    statement=cluster["statement"],
                    novelty_status=novelty,
                    confidence=float(sum(cluster["confidences"]) / len(cluster["confidences"])),
                    evidence=evidence,
                    expected_sign=next(iter(non_null_directions), None),
                    tags=sorted(topic_tokens & _tokens(cluster["statement"]))[:10],
                    rationale=rationale,
                    evidence_status=evidence_status,
                    metadata={"corpus_fingerprint": self.fingerprint},
                )
            )
        return HypothesisRegistry(candidates, self.fingerprint)

    def paper_table(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "paper_id": paper.paper_id,
                    "title": paper.title,
                    "authors": "; ".join(paper.authors),
                    "year": paper.year,
                    "pages": len(paper.pages),
                    "fingerprint": paper.fingerprint,
                    "warnings": "; ".join(paper.warnings),
                    "path": paper.path,
                }
                for paper in self.papers
            ]
        )


__all__ = [
    "SourceExcerpt",
    "PaperDocument",
    "HypothesisCandidate",
    "HypothesisRegistry",
    "LiteratureCorpus",
]
