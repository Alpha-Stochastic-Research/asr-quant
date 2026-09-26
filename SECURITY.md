# Security policy

## Supported versions

| Version | Security support |
|---|---|
| 1.0.x stable | Yes |
| 0.5.x and earlier | No live-execution support; critical disclosure review only |

## Reporting a vulnerability

Report suspected vulnerabilities privately to `research@asr-lab.online`.

Include:

- affected version and commit;
- operating system and Python version;
- minimal reproduction;
- expected and observed behavior;
- impact assessment;
- whether broker credentials, order routing or capital may be affected.

Do not publish exploit details, credentials, deployment certificates, broker account identifiers or live endpoints before coordinated review.

## Credential rules

ASRQuant does not intentionally persist broker credentials. Production credentials must be provided by a secret manager or protected environment variables. Never store them in source code, notebooks, `.env` files committed to Git, reports, audit payloads or support tickets.

The deployment certificate signing key must be separate from broker credentials and contain at least 32 bytes of entropy. It must not be stored beside the certificate.

## Live-trading security model

Live mode requires all of the following:

1. a signed and unexpired `DeploymentCertificate`;
2. matching package version, broker, account fingerprint, risk-policy hash and capital limit;
3. at least two named approvers in the certificate;
4. `ASRQUANT_LIVE_TRADING=ENABLED` in the controlled deployment environment;
5. broker credentials;
6. a persistent kill switch;
7. a durable audit store;
8. pre-trade risk approval.

Direct live-adapter construction is rejected.

## Supply-chain controls

The release workflows are designed to include:

- protected source review;
- multi-platform tests;
- static analysis;
- dependency vulnerability scanning;
- secret scanning;
- CodeQL;
- SBOM generation;
- Trusted Publishing to PyPI;
- GitHub artifact provenance attestations.

Users should verify release provenance before deploying live-capable artifacts.

## Incident handling

For any suspected compromise involving live execution:

1. activate the persistent kill switch;
2. cancel open orders through the broker interface;
3. verify positions and cash directly with the broker;
4. revoke broker credentials and certificate keys as appropriate;
5. preserve audit, broker and market-data evidence;
6. open an incident record;
7. do not resume until reconciliation, root-cause analysis and fresh approval are complete.

See `docs/operations_runbook.md` and `THREAT_MODEL.md`.
