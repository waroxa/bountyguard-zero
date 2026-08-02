# Three-minute demo runbook

Target length: 2:05–2:25. No slides.

1. **0:00–0:18 — operator console, live mode**
   - Show `LIVE EVIDENCE`, the masked address, finalized balances, and custody T0.
   - Say: “This is a real finalized baseline. No payment has arrived, so it says
     zero. BountyGuard never invents a win.”
2. **0:18–0:43 — ZeroClaw configuration**
   - Show stock release version, named agent, allowed tools, skill bundle, and
     supervised SOP graph.
3. **0:43–1:15 — real agent on the CLI channel**
   - Ask: “Run payout-watch and tell me whether a verified bounty payment
     arrived.”
   - Show the agent calling the fixed scanner and returning finality plus receipt.
4. **1:15–1:38 — evidence boundary**
   - Run the unknown-mint unit test and show that it does not count as earnings.
   - Point to the prompt-injection boundary document.
5. **1:38–1:58 — supervised SOP**
   - Show the human checkpoint; explain that earnings are recorded only after
     evidence review.
6. **1:58–2:18 — simulated replay**
   - Click the $500 replay and keep the amber `SIMULATED REPLAY — not an
     earnings claim` banner visible.
   - Return to live evidence before the video ends.
7. **2:18–2:25 — reproducibility**
   - End on the public repository's five-minute setup commands.

