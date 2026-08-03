# Authenticated ZeroClaw run

This is the redacted evidence from the first real agent run. ZeroClaw v0.8.4
used an encrypted, local OpenAI Codex subscription profile and the supervised
`bountyguard` agent. No API key, OAuth token, wallet key, or seed phrase is
stored in this repository.

## Command

```sh
zeroclaw agent --agent bountyguard \
  --message "Run payout-watch and tell me whether a verified bounty payment arrived."
```

## Agent result

```text
No verified bounty payment arrived.

- Status: baseline created
- Checked: 2026-08-02 23:59:53Z
- Address: 7y9K2b…5WNCsS
- Counted assets: SOL=0, USDC=0, USDG=0
- Historical activity was not counted as a new payout

Receipt: sha256:f4f89dd171e2c47be243de8e1f7232f21f45c3c1926a55d34a6269b453785848
```

This zero result is intentional evidence of the product boundary: the agent
ran the real read-only scanner against finalized Solana mainnet state and did
not invent a payout. The separate `$500` replay in the operator console remains
explicitly labeled as simulated and is never counted as earnings.
