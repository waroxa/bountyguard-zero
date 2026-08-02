# Payout Watch

## Steps

1. **Scan finalized activity** — Run the fixed, read-only payout scanner.
   - tools: bountyguard__scan_finalized_payouts
   - allow-tools: bountyguard__scan_finalized_payouts
   - on_failure: retry:1
   - next: 2

2. **Verify evidence boundary** — Confirm the report names an allowlisted mint or SOL, finalized signature, explorer URL, and report receipt.
   - tools: sop_advance
   - allow-tools: sop_advance
   - next: 3

3. **Human earnings checkpoint** — Require an operator to review the payout evidence before it is counted as earned.
   - kind: checkpoint
   - requires_confirmation: true
   - next: 4

4. **Record verified payout** — Store the operator-approved result in the SOP audit trail and notify the originating channel.
   - tools: memory_store, sop_advance
   - allow-tools: memory_store, sop_advance

