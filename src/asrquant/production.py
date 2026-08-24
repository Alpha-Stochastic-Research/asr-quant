"""Production-readiness gates and cryptographic live-trading authorization.

The module deliberately separates *software capability* from *deployment approval*.
A live-capital session is allowed only when a signed, time-limited deployment
certificate matches the package version, broker, account, risk policy, and
maximum authorized capital.
"""
from __future__ import annotations

from .version import __version__
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import hmac
import json
from pathlib import Path
import platform
import secrets
from typing import Any, Iterable


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def canonical_json(payload: Any) -> str:
    """Return deterministic JSON suitable for hashes and signatures."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def account_fingerprint(account_id: str, *, salt: str) -> str:
    """Hash a broker account identifier without retaining the clear-text value."""
    if not account_id or not salt:
        raise ValueError("account_id and salt are required")
    return hashlib.sha256(f"{salt}:{account_id}".encode("utf-8")).hexdigest()


class CheckLevel(str, Enum):
    REQUIRED = "required"
    ADVISORY = "advisory"


class CheckState(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass(frozen=True)
class ReadinessCheck:
    code: str
    state: CheckState
    level: CheckLevel
    message: str
    evidence: Any = None

    @property
    def passed(self) -> bool:
        return self.state == CheckState.PASS


@dataclass
class ProductionReadinessReport:
    checks: list[ReadinessCheck]
    generated_at: str = field(default_factory=lambda: _iso(_utcnow()))

    @property
    def ready(self) -> bool:
        return all(check.passed for check in self.checks if check.level == CheckLevel.REQUIRED)

    @property
    def failed_required(self) -> list[ReadinessCheck]:
        return [
            check
            for check in self.checks
            if check.level == CheckLevel.REQUIRED and not check.passed
        ]

    @property
    def warnings(self) -> list[ReadinessCheck]:
        return [check for check in self.checks if check.state == CheckState.WARN]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "generated_at": self.generated_at,
            "checks": [
                {
                    **asdict(check),
                    "state": check.state.value,
                    "level": check.level.value,
                }
                for check in self.checks
            ],
        }

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return output


@dataclass(frozen=True)
class DeploymentEvidence:
    """Evidence required before a deployment certificate can be issued.

    The defaults are intentionally failing. A deployment operator must provide
    concrete evidence from CI, security scans, broker paper testing, operations,
    compliance, and recovery exercises.
    """

    release_version: str
    ci_passed: bool = False
    test_count: int = 0
    coverage_percent: float = 0.0
    static_analysis_passed: bool = False
    dependency_scan_passed: bool = False
    secrets_scan_passed: bool = False
    sbom_present: bool = False
    artifacts_signed: bool = False
    reproducible_build_verified: bool = False
    disaster_recovery_tested: bool = False
    rollback_tested: bool = False
    monitoring_enabled: bool = False
    alerting_enabled: bool = False
    durable_audit_log_enabled: bool = False
    time_synchronization_verified: bool = False
    broker_paper_days: int = 0
    broker_paper_orders: int = 0
    reconciliation_mismatches: int = 1
    unresolved_critical_incidents: int = 1
    operator_approved: bool = False
    legal_compliance_reviewed: bool = False
    data_licenses_reviewed: bool = False
    strategy_owner_approved: bool = False
    model_validation_approved: bool = False
    change_ticket: str = ""
    notes: dict[str, Any] = field(default_factory=dict)


class ProductionReadinessGate:
    """Evaluate a strict, auditable go-live checklist."""

    def __init__(
        self,
        *,
        minimum_tests: int = 100,
        minimum_coverage: float = 90.0,
        minimum_paper_days: int = 30,
        minimum_paper_orders: int = 500,
    ) -> None:
        self.minimum_tests = int(minimum_tests)
        self.minimum_coverage = float(minimum_coverage)
        self.minimum_paper_days = int(minimum_paper_days)
        self.minimum_paper_orders = int(minimum_paper_orders)

    @staticmethod
    def _boolean(code: str, value: bool, message: str) -> ReadinessCheck:
        return ReadinessCheck(
            code=code,
            state=CheckState.PASS if value else CheckState.FAIL,
            level=CheckLevel.REQUIRED,
            message=message,
            evidence=bool(value),
        )

    @staticmethod
    def _threshold(
        code: str,
        value: float,
        minimum: float,
        message: str,
    ) -> ReadinessCheck:
        return ReadinessCheck(
            code=code,
            state=CheckState.PASS if value >= minimum else CheckState.FAIL,
            level=CheckLevel.REQUIRED,
            message=message,
            evidence={"actual": value, "minimum": minimum},
        )

    def evaluate(self, evidence: DeploymentEvidence) -> ProductionReadinessReport:
        checks: list[ReadinessCheck] = [
            ReadinessCheck(
                "release_version",
                CheckState.PASS if evidence.release_version == __version__ else CheckState.FAIL,
                CheckLevel.REQUIRED,
                f"The deployment release must exactly match installed ASRQuant {__version__}.",
                evidence.release_version,
            ),
            self._boolean("ci", evidence.ci_passed, "All required CI jobs passed on the release commit."),
            self._threshold(
                "tests",
                evidence.test_count,
                self.minimum_tests,
                "The release has the minimum automated test count.",
            ),
            self._threshold(
                "coverage",
                evidence.coverage_percent,
                self.minimum_coverage,
                "The release meets the minimum line-coverage threshold.",
            ),
            self._boolean(
                "static_analysis",
                evidence.static_analysis_passed,
                "Static analysis and type checks passed.",
            ),
            self._boolean(
                "dependency_scan",
                evidence.dependency_scan_passed,
                "Dependency vulnerability scanning passed with no unresolved critical finding.",
            ),
            self._boolean(
                "secrets_scan",
                evidence.secrets_scan_passed,
                "Repository and build artifacts passed secret scanning.",
            ),
            self._boolean("sbom", evidence.sbom_present, "A software bill of materials is attached."),
            self._boolean(
                "artifact_signing",
                evidence.artifacts_signed,
                "Release artifacts have provenance attestations or signatures.",
            ),
            self._boolean(
                "reproducible_build",
                evidence.reproducible_build_verified,
                "A second clean build produced equivalent release contents.",
            ),
            self._boolean(
                "disaster_recovery",
                evidence.disaster_recovery_tested,
                "Disaster recovery and state restoration were tested.",
            ),
            self._boolean("rollback", evidence.rollback_tested, "Deployment rollback was tested."),
            self._boolean(
                "monitoring",
                evidence.monitoring_enabled,
                "Runtime health, latency, order, fill, risk, and reconciliation monitoring is enabled.",
            ),
            self._boolean("alerting", evidence.alerting_enabled, "Operational alerting is enabled and tested."),
            self._boolean(
                "audit_log",
                evidence.durable_audit_log_enabled,
                "A durable, tamper-evident audit log is enabled.",
            ),
            self._boolean(
                "time_sync",
                evidence.time_synchronization_verified,
                "Host and broker clock synchronization was verified.",
            ),
            self._threshold(
                "paper_days",
                evidence.broker_paper_days,
                self.minimum_paper_days,
                "The strategy completed the minimum broker-paper observation period.",
            ),
            self._threshold(
                "paper_orders",
                evidence.broker_paper_orders,
                self.minimum_paper_orders,
                "The strategy completed the minimum number of broker-paper orders.",
            ),
            ReadinessCheck(
                "reconciliation",
                CheckState.PASS if evidence.reconciliation_mismatches == 0 else CheckState.FAIL,
                CheckLevel.REQUIRED,
                "There are no unresolved broker/account reconciliation mismatches.",
                evidence.reconciliation_mismatches,
            ),
            ReadinessCheck(
                "critical_incidents",
                CheckState.PASS if evidence.unresolved_critical_incidents == 0 else CheckState.FAIL,
                CheckLevel.REQUIRED,
                "There are no unresolved critical incidents.",
                evidence.unresolved_critical_incidents,
            ),
            self._boolean(
                "operator_approval",
                evidence.operator_approved,
                "An accountable operator approved the deployment.",
            ),
            self._boolean(
                "legal_compliance",
                evidence.legal_compliance_reviewed,
                "Applicable legal, broker, venue, and regulatory obligations were reviewed.",
            ),
            self._boolean(
                "data_licenses",
                evidence.data_licenses_reviewed,
                "Market-data and research-data licenses were reviewed.",
            ),
            self._boolean(
                "strategy_owner",
                evidence.strategy_owner_approved,
                "The strategy owner approved limits, instruments, and capital allocation.",
            ),
            self._boolean(
                "model_validation",
                evidence.model_validation_approved,
                "Independent model validation approved the strategy and controls.",
            ),
            ReadinessCheck(
                "change_ticket",
                CheckState.PASS if bool(evidence.change_ticket.strip()) else CheckState.FAIL,
                CheckLevel.REQUIRED,
                "A change-control ticket identifies the exact release and deployment.",
                evidence.change_ticket,
            ),
        ]
        return ProductionReadinessReport(checks)


@dataclass
class DeploymentCertificate:
    """Signed authorization required to construct a live-capital session."""

    certificate_id: str
    issued_at: str
    expires_at: str
    release_version: str
    broker: str
    account_hash: str
    risk_policy_hash: str
    evidence_hash: str
    max_live_capital: float
    approved_by: tuple[str, ...]
    environment_fingerprint: str
    change_ticket: str
    signature: str = ""

    @classmethod
    def issue(
        cls,
        *,
        report: ProductionReadinessReport,
        evidence: DeploymentEvidence,
        secret_key: str | bytes,
        release_version: str,
        broker: str,
        account_id: str,
        account_salt: str,
        risk_policy: Any,
        max_live_capital: float,
        approved_by: Iterable[str],
        validity_hours: int = 24,
        environment_fingerprint: str | None = None,
    ) -> "DeploymentCertificate":
        if not report.ready:
            failures = ", ".join(check.code for check in report.failed_required)
            raise PermissionError(f"production readiness gate failed: {failures}")
        if max_live_capital <= 0:
            raise ValueError("max_live_capital must be positive")
        approvers = tuple(str(item).strip() for item in approved_by if str(item).strip())
        if len(approvers) < 2:
            raise ValueError("at least two named approvers are required")
        now = _utcnow()
        environment = environment_fingerprint or stable_hash(
            {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "machine": platform.machine(),
            }
        )
        certificate = cls(
            certificate_id=secrets.token_hex(16),
            issued_at=_iso(now),
            expires_at=_iso(now + timedelta(hours=int(validity_hours))),
            release_version=release_version,
            broker=broker.lower().strip(),
            account_hash=account_fingerprint(account_id, salt=account_salt),
            risk_policy_hash=stable_hash(asdict(risk_policy) if hasattr(risk_policy, "__dataclass_fields__") else risk_policy),
            evidence_hash=stable_hash({"evidence": asdict(evidence), "report": report.to_dict()}),
            max_live_capital=float(max_live_capital),
            approved_by=approvers,
            environment_fingerprint=environment,
            change_ticket=evidence.change_ticket,
        )
        certificate.signature = certificate._sign(secret_key)
        return certificate

    def _unsigned_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("signature", None)
        payload["approved_by"] = list(self.approved_by)
        return payload

    def _sign(self, secret_key: str | bytes) -> str:
        key = secret_key.encode("utf-8") if isinstance(secret_key, str) else secret_key
        if len(key) < 32:
            raise ValueError("secret_key must contain at least 32 bytes")
        return hmac.new(key, canonical_json(self._unsigned_payload()).encode("utf-8"), hashlib.sha256).hexdigest()

    def verify(
        self,
        *,
        secret_key: str | bytes,
        release_version: str,
        broker: str,
        account_id: str,
        account_salt: str,
        risk_policy: Any,
        requested_capital: float,
        environment_fingerprint: str | None = None,
        now: datetime | None = None,
    ) -> None:
        expected = self._sign(secret_key)
        if not hmac.compare_digest(expected, self.signature):
            raise PermissionError("deployment certificate signature is invalid")
        current_time = now or _utcnow()
        if current_time < _parse_time(self.issued_at) - timedelta(minutes=5):
            raise PermissionError("deployment certificate is not yet valid")
        if current_time >= _parse_time(self.expires_at):
            raise PermissionError("deployment certificate has expired")
        if self.release_version != release_version:
            raise PermissionError("deployment certificate release version mismatch")
        if self.broker != broker.lower().strip():
            raise PermissionError("deployment certificate broker mismatch")
        if self.account_hash != account_fingerprint(account_id, salt=account_salt):
            raise PermissionError("deployment certificate account mismatch")
        current_policy_hash = stable_hash(
            asdict(risk_policy) if hasattr(risk_policy, "__dataclass_fields__") else risk_policy
        )
        if self.risk_policy_hash != current_policy_hash:
            raise PermissionError("deployment certificate risk-policy mismatch")
        if requested_capital <= 0 or requested_capital > self.max_live_capital:
            raise PermissionError("requested live capital exceeds certificate authorization")
        if environment_fingerprint is not None and self.environment_fingerprint != environment_fingerprint:
            raise PermissionError("deployment certificate environment mismatch")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["approved_by"] = list(self.approved_by)
        return payload

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return output

    @classmethod
    def load(cls, path: str | Path) -> "DeploymentCertificate":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        payload["approved_by"] = tuple(payload.get("approved_by", ()))
        return cls(**payload)


__all__ = [
    "CheckLevel",
    "CheckState",
    "ReadinessCheck",
    "ProductionReadinessReport",
    "DeploymentEvidence",
    "ProductionReadinessGate",
    "DeploymentCertificate",
    "canonical_json",
    "stable_hash",
    "account_fingerprint",
]
