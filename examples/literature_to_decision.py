"""End-to-end hypothesis-to-decision example using only ASRQuant's public facade."""
import asrquant as asr

# For a real corpus, replace from_texts with:
# project = asr.research.from_pdfs("papers/", topic="rates and equity styles")
corpus = asr.LiteratureCorpus.from_texts(
    [
        (
            "Rates and styles",
            "We hypothesize that rapid increases in long-term interest rates lead to value outperforming growth equities. "
            "Future research should examine whether the relationship changes across inflation regimes.",
        ),
        (
            "Replication",
            "We test whether higher Treasury yields predict relative value returns and find a positive relationship.",
        ),
    ],
    topic="interest rates value growth",
)
project = asr.ResearchProject("Rates and styles", topic=corpus.topic, corpus=corpus)
registry = project.discover_hypotheses()
print(registry.to_frame())
