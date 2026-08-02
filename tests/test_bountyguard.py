import importlib.util
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "bundle" / "bountyguard" / "scripts" / "bountyguard.py"
SPEC = importlib.util.spec_from_file_location("bountyguard", SCRIPT)
bountyguard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = bountyguard
SPEC.loader.exec_module(bountyguard)


OWNER = "11111111111111111111111111111111"
MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


class BountyGuardTests(unittest.TestCase):
    def test_pubkey_validation(self):
        self.assertEqual(bountyguard.validate_pubkey(OWNER), OWNER)
        with self.assertRaises(ValueError):
            bountyguard.validate_pubkey("not-a-solana-address")

    def test_rpc_allowlist_fails_closed(self):
        self.assertEqual(
            bountyguard.validate_rpc_url("https://api.mainnet-beta.solana.com"),
            "https://api.mainnet-beta.solana.com",
        )
        with self.assertRaises(ValueError):
            bountyguard.validate_rpc_url("http://127.0.0.1:8899")

    def test_detects_finalized_sol_and_allowlisted_token_delta(self):
        transaction = {
            "slot": 123,
            "blockTime": 1700000000,
            "transaction": {
                "message": {
                    "accountKeys": [
                        {"pubkey": "Vote111111111111111111111111111111111111111"},
                        {"pubkey": OWNER},
                    ]
                }
            },
            "meta": {
                "preBalances": [100000, 0],
                "postBalances": [95000, 1000000000],
                "preTokenBalances": [],
                "postTokenBalances": [
                    {
                        "accountIndex": 1,
                        "mint": MINT,
                        "owner": OWNER,
                        "uiTokenAmount": {"amount": "500000000", "decimals": 6},
                    }
                ],
            },
        }
        result = bountyguard.analyze_transaction(
            transaction,
            "signature-one",
            OWNER,
            {MINT: {"symbol": "USDC", "decimals": 6}},
            Decimal("0.000001"),
        )
        self.assertEqual(result["payouts"][0]["asset"], "SOL")
        self.assertEqual(result["payouts"][0]["amount"], "1")
        self.assertEqual(result["payouts"][1]["asset"], "USDC")
        self.assertEqual(result["payouts"][1]["amount"], "500")

    def test_unknown_token_never_counts_as_earnings(self):
        unknown_mint = "So11111111111111111111111111111111111111112"
        transaction = {
            "transaction": {"message": {"accountKeys": [OWNER]}},
            "meta": {
                "preBalances": [0],
                "postBalances": [0],
                "preTokenBalances": [],
                "postTokenBalances": [
                    {
                        "accountIndex": 0,
                        "mint": unknown_mint,
                        "owner": OWNER,
                        "uiTokenAmount": {"amount": "999000000", "decimals": 6},
                    }
                ],
            },
        }
        result = bountyguard.analyze_transaction(
            transaction, "signature-two", OWNER, {}, Decimal("0.000001")
        )
        self.assertEqual(result["payouts"], [])
        self.assertEqual(result["unverified_assets"][0]["mint"], unknown_mint)

    def test_atomic_state_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            bountyguard.atomic_write_json(path, {"initialized": True, "count": 1})
            self.assertEqual(json.loads(path.read_text()), {"count": 1, "initialized": True})

    def test_canonical_hash_is_order_independent(self):
        left = bountyguard.canonical_hash({"a": 1, "b": 2})
        right = bountyguard.canonical_hash({"b": 2, "a": 1})
        self.assertEqual(left, right)

    def test_report_receipt_changes_when_evidence_changes(self):
        baseline = {
            "schema": "bountyguard.report.v1",
            "status": "no_change",
            "events": [],
        }
        changed = {**baseline, "status": "payout_detected"}
        self.assertNotEqual(
            bountyguard.canonical_hash(baseline),
            bountyguard.canonical_hash(changed),
        )


if __name__ == "__main__":
    unittest.main()
