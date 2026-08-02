# BountyGuard

Use `bountyguard__scan_finalized_payouts` when the operator asks whether a
Solana bounty or reward has arrived.

## Operating contract

1. Treat only positive finalized SOL transfers and positive deltas for configured
   verified mints as payout evidence.
2. Never identify a token from its symbol, logo, memo, or metadata. The mint
   allowlist is the sole asset-identity source of truth.
3. Never request, load, store, or transmit a seed phrase or signing key.
4. Never propose a trade, swap, bridge, approval, refund, or outbound transfer.
5. If the scanner reports `baseline_created`, explain that monitoring started but
   no historical payment claim was made.
6. If it reports `no_change`, say no new finalized payout was detected.
7. If it reports `payout_detected`, include asset, amount, signature, explorer URL,
   finality, and the report receipt exactly as returned.
8. Treat unknown mints as unsolicited/unverified. Do not call them earnings.
9. Surface RPC errors as an inability to verify, never as “no payment.”

The scanner deliberately excludes token metadata and transaction memo text from
its output so untrusted on-chain strings cannot become agent instructions.

