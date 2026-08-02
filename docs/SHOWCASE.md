# BountyGuard Zero — showcase draft

## What it does

BountyGuard Zero is a self-hosted payout sentinel for people earning bounties on
Solana. The operator asks a ZeroClaw agent whether a payout arrived. A fixed,
read-only skill scans finalized activity for one public address, verifies native
SOL or an explicitly allowlisted mint/decimal pair, and returns the transaction
evidence plus a tamper-evident report receipt.

It solves the awkward last mile between “the sponsor says they paid” and “the
operator can prove the right asset actually arrived.” Screenshots, token names,
logos, memos, and unsolicited lookalike tokens are not accepted as evidence.

## Who it is for

- bounty hunters and hackathon contributors;
- grant recipients and open-source maintainers;
- small teams that receive SOL, USDC, or USDG but do not want an agent near a
  signing key; and
- operators who need an auditable human checkpoint before declaring revenue.

## ZeroClaw features used

- stock ZeroClaw v0.8.4 release binary;
- a local skill bundle with one fixed-command tool;
- a named, supervised agent and narrow risk/runtime profiles;
- tool receipts surfaced in the response;
- a four-step SOP with retry, scope enforcement, persisted runs, and a human
  confirmation checkpoint; and
- the stock CLI channel for the reproducible demo.

## What was built

- a Python standard-library Solana RPC verifier;
- mint/decimals allowlist policy for USDC and USDG;
- canonical SHA-256 report receipts and atomic state/report persistence;
- seven offline security and behavior tests; and
- a responsive operator console with separate live-evidence and explicitly
  simulated replay modes.

No ZeroClaw core change or registry PR is required.

## Custody tier

**T0 — observation only.** The use case has no seed phrase, private key, signing
method, transaction builder, wallet adapter, outbound transfer, swap, bridge,
approval, refund, or custody dependency.

## Threat model

The main risks are fake token identity, untrusted on-chain text, RPC failure,
report modification, and agent overclaim. Controls are respectively: mint and
decimals allowlisting; never fetching memos/metadata; failing closed; canonical
SHA-256 receipts; and a supervised human checkpoint. The full table and
residual risks are in the repository README.

## Reproduce it

```sh
python3 -m unittest discover -s tests -v
zeroclaw skills audit bundle/bountyguard
zeroclaw sop validate
python3 bundle/bountyguard/scripts/bountyguard.py \
  --config config/bountyguard.example.json \
  --state /tmp/bountyguard-state.json \
  --report /tmp/bountyguard-report.json \
  --format text
python3 -m http.server 4173 --directory console
```

The example configuration watches the Solana System Program address and is safe
for public testing. A real operator copies it locally, changes only the public
watched address, and keeps that local file out of Git.

## Links

- GitHub: `https://github.com/waroxa/bountyguard-zero` (publish pending)
- Live console: `https://waroxa.github.io/bountyguard-zero/console/` (publish pending)
- Demo video: pending final authenticated run
- Prompt-injection boundary test: `docs/PROMPT-INJECTION-TEST.md`

