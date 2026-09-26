# Operations runbook

## Before market open

1. Verify the deployed package hash and artifact attestation.
2. Verify the deployment certificate signature, expiry, broker, account, policy and capital.
3. Confirm the kill switch is inactive.
4. Confirm broker authentication and account reachability.
5. Confirm the correct paper or live endpoint.
6. Confirm market-data freshness and secondary-feed agreement.
7. Verify host time synchronization.
8. Verify audit database writeability and hash-chain integrity.
9. Run reconciliation against the broker.
10. Verify monitoring and alert delivery.
11. Confirm the daily change ticket and named operators.

## During the session

Monitor at least:

- process heartbeat;
- broker latency and request failures;
- market-data age;
- signal age;
- order-entry rate;
- open orders;
- rejects and cancellations;
- fills and partial fills;
- positions and leverage;
- cash and buying power;
- realized and unrealized PnL;
- daily loss and drawdown;
- reconciliation status;
- audit-chain validity.

## Automatic stop conditions

- daily loss limit;
- drawdown limit;
- repeated broker failures;
- reconciliation mismatch;
- stale or invalid market data;
- account block;
- unauthorized symbol;
- price-collar violation;
- invalid certificate or expired certificate;
- corrupted kill-switch or audit state.

## Manual stop procedure

1. Call `engine.emergency_stop(reason, operator=...)`.
2. Confirm open-order cancellation results.
3. Verify broker positions directly in the broker interface.
4. Flatten positions manually only under the documented emergency policy.
5. Snapshot and back up the audit database.
6. Open an incident ticket.
7. Preserve logs and market-data evidence.
8. Do not clear the kill switch until root-cause analysis and approval are complete.

## Restart procedure

1. Keep the kill switch active.
2. Restore the latest verified audit backup if necessary.
3. Verify the hash chain.
4. Query broker account, positions and open orders.
5. Reconcile expected and actual state.
6. Resolve every mismatch.
7. Repeat readiness checks affected by the incident.
8. Issue a new deployment certificate if release, environment, risk policy, account or capital changed.
9. Clear the kill switch with an accountable operator.
10. Resume first in shadow or paper mode when practical.

## End of day

1. Reconcile positions, cash, orders and fills.
2. Verify the audit hash chain.
3. Create an immutable backup.
4. Generate daily risk and execution reports.
5. Record incidents, rejects and limit events.
6. Revoke or allow the short-lived certificate to expire.
7. Review whether capital limits remain appropriate.
