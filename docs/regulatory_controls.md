# Regulatory and supervisory control mapping

This document is an engineering mapping, not legal advice. Applicability depends on the firm, account, instruments, venue and jurisdiction.

## United States market access

SEC Rule 15c3-5 requires relevant broker-dealers with market access to maintain documented controls designed to limit financial exposure and prevent erroneous or non-compliant orders. ASRQuant provides software primitives that may support, but do not independently satisfy, these obligations:

| Control objective | ASRQuant mechanism |
|---|---|
| Pre-set capital or credit scope | deployment certificate maximum capital; `max_capital`; buying-power check |
| Erroneous size control | `max_order_notional`; `max_position_notional`; position-weight and leverage limits |
| Erroneous price control | `max_price_deviation_bps` price collar |
| Duplicate-order prevention | client-order ID tracking and broker lookup |
| Restricted instruments | symbol allowlist and denylist |
| Authorized access | signed certificate, environment arm, broker credentials |
| Immediate execution records | broker receipts and tamper-evident audit events |
| Regular review | readiness evidence, short-lived certificate and change ticket |

The broker-dealer remains responsible for its legal obligations and the effectiveness of controls.

## European algorithmic trading

MiFID II Article 17 requires investment firms engaged in algorithmic trading to have resilient systems, capacity, thresholds and limits, erroneous-order prevention, monitoring, testing and business-continuity arrangements. ASRQuant contributes:

- deterministic pre-trade thresholds;
- fail-closed broker health checks;
- persistent kill switch;
- durable audit trail;
- recovery and rollback evidence gates;
- broker-paper testing evidence;
- reconciliation;
- monitoring and alerting requirements.

A deployed system must also address the full applicable MiFID II, RTS 6, DORA, market-abuse and venue-rule obligations with qualified legal and compliance professionals.

## Supervisory practices

FINRA guidance emphasizes holistic risk assessment, controlled software development, testing, system validation, surveillance and supervision. The ASRQuant readiness gate requires these practices to be evidenced before live authorization.

## Non-goals

ASRQuant does not provide:

- regulatory registration;
- legal opinions;
- broker-dealer supervision;
- market-abuse surveillance across all venues;
- best-execution determination;
- transaction reporting;
- books-and-records compliance certification;
- exchange certification;
- HFT co-location or deterministic low-latency guarantees.
