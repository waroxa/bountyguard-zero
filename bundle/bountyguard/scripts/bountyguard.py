#!/usr/bin/env python3
"""Read-only finalized payout verification for a configured Solana address."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
ALPHABET_INDEX = {character: index for index, character in enumerate(ALPHABET)}
ALLOWED_RPC_HOSTS = {"api.mainnet-beta.solana.com"}
LAMPORTS_PER_SOL = Decimal("1000000000")
TOKEN_PROGRAMS = (
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
)


class GuardError(RuntimeError):
    """An error that prevents a trustworthy verification result."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def base58_decode(value: str) -> bytes:
    if not value:
        raise ValueError("empty base58 value")
    number = 0
    for character in value:
        if character not in ALPHABET_INDEX:
            raise ValueError("invalid base58 character")
        number = number * 58 + ALPHABET_INDEX[character]
    decoded = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    leading_zeroes = len(value) - len(value.lstrip("1"))
    return b"\x00" * leading_zeroes + decoded


def validate_pubkey(value: str) -> str:
    if len(base58_decode(value)) != 32:
        raise ValueError("Solana public key must decode to 32 bytes")
    return value


def validate_rpc_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_RPC_HOSTS:
        raise ValueError("RPC must use HTTPS and an explicitly allowed host")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("RPC URL may not contain credentials or fragments")
    return value


def canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError as exc:
        raise GuardError(f"Required file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise GuardError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GuardError(f"Expected a JSON object in {path}")
    return value


@dataclass
class RpcClient:
    url: str
    timeout: int = 20
    request_id: int = 0

    def call(self, method: str, params: list[Any]) -> Any:
        self.request_id += 1
        body = json.dumps(
            {"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params},
            separators=(",", ":"),
        ).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "BountyGuard-Zero/0.1"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise GuardError(f"Solana RPC request failed for {method}: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("error"):
            raise GuardError(f"Solana RPC returned an error for {method}: {payload.get('error')}")
        if "result" not in payload:
            raise GuardError(f"Solana RPC response for {method} omitted result")
        return payload["result"]


def token_amount(entry: dict[str, Any]) -> tuple[int, int]:
    amount = entry.get("uiTokenAmount", {})
    return int(amount.get("amount", "0")), int(amount.get("decimals", 0))


def token_balances_for_owner(entries: list[dict[str, Any]], owner: str) -> dict[tuple[int, str], tuple[int, int]]:
    balances: dict[tuple[int, str], tuple[int, int]] = {}
    for entry in entries or []:
        if entry.get("owner") != owner:
            continue
        index = entry.get("accountIndex")
        mint = entry.get("mint")
        if isinstance(index, int) and isinstance(mint, str):
            balances[(index, mint)] = token_amount(entry)
    return balances


def account_keys(transaction: dict[str, Any]) -> list[str]:
    keys = transaction.get("transaction", {}).get("message", {}).get("accountKeys", [])
    normalized = []
    for key in keys:
        if isinstance(key, str):
            normalized.append(key)
        elif isinstance(key, dict) and isinstance(key.get("pubkey"), str):
            normalized.append(key["pubkey"])
    return normalized


def analyze_transaction(
    transaction: dict[str, Any],
    signature: str,
    owner: str,
    verified_mints: dict[str, dict[str, Any]],
    minimum_sol: Decimal,
) -> dict[str, Any]:
    meta = transaction.get("meta") or {}
    keys = account_keys(transaction)
    if owner not in keys:
        return {"signature": signature, "payouts": [], "unverified_assets": []}

    payouts: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    owner_index = keys.index(owner)
    pre_lamports = meta.get("preBalances", [])
    post_lamports = meta.get("postBalances", [])
    if owner_index < len(pre_lamports) and owner_index < len(post_lamports):
        delta_sol = Decimal(post_lamports[owner_index] - pre_lamports[owner_index]) / LAMPORTS_PER_SOL
        if delta_sol >= minimum_sol:
            payouts.append({"asset": "SOL", "amount": format(delta_sol, "f"), "mint": None})

    pre_tokens = token_balances_for_owner(meta.get("preTokenBalances", []), owner)
    post_tokens = token_balances_for_owner(meta.get("postTokenBalances", []), owner)
    for key in sorted(set(pre_tokens) | set(post_tokens), key=lambda item: (item[1], item[0])):
        mint = key[1]
        before_raw, before_decimals = pre_tokens.get(key, (0, 0))
        after_raw, after_decimals = post_tokens.get(key, (0, before_decimals))
        decimals = after_decimals or before_decimals
        delta_raw = after_raw - before_raw
        if delta_raw <= 0:
            continue
        amount = Decimal(delta_raw) / (Decimal(10) ** decimals)
        verified = verified_mints.get(mint)
        event = {"amount": format(amount, "f"), "mint": mint}
        if verified and int(verified.get("decimals", decimals)) == decimals:
            event["asset"] = str(verified.get("symbol", "VERIFIED"))
            payouts.append(event)
        else:
            event["reason"] = "mint_not_allowlisted_or_decimals_mismatch"
            unverified.append(event)

    return {
        "signature": signature,
        "slot": transaction.get("slot"),
        "block_time": transaction.get("blockTime"),
        "payouts": payouts,
        "unverified_assets": unverified,
    }


def current_balances(client: RpcClient, owner: str, verified_mints: dict[str, dict[str, Any]]) -> dict[str, str]:
    balance_result = client.call("getBalance", [owner, {"commitment": "finalized"}])
    balances = {"SOL": format(Decimal(balance_result.get("value", 0)) / LAMPORTS_PER_SOL, "f")}
    raw_by_mint: dict[str, tuple[int, int]] = {}
    for program in TOKEN_PROGRAMS:
        result = client.call(
            "getTokenAccountsByOwner",
            [owner, {"programId": program}, {"encoding": "jsonParsed", "commitment": "finalized"}],
        )
        for account in result.get("value", []):
            info = account.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
            mint = info.get("mint")
            amount_info = info.get("tokenAmount", {})
            if not isinstance(mint, str):
                continue
            raw, decimals = int(amount_info.get("amount", "0")), int(amount_info.get("decimals", 0))
            prior_raw, _ = raw_by_mint.get(mint, (0, decimals))
            raw_by_mint[mint] = (prior_raw + raw, decimals)
    for mint, details in verified_mints.items():
        raw, decimals = raw_by_mint.get(mint, (0, int(details.get("decimals", 0))))
        balances[str(details.get("symbol", mint))] = format(Decimal(raw) / (Decimal(10) ** decimals), "f")
    return balances


def new_signatures(client: RpcClient, owner: str, limit: int, last_seen: str | None) -> list[dict[str, Any]]:
    results = client.call(
        "getSignaturesForAddress",
        [owner, {"limit": limit, "commitment": "finalized"}],
    )
    pending = []
    for item in results:
        signature = item.get("signature")
        if signature == last_seen:
            break
        if item.get("err") is None and isinstance(signature, str):
            pending.append(item)
    return list(reversed(pending))


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "BountyGuard Zero — finalized Solana payout report",
        f"Status: {report['status']}",
        f"Checked: {report['checked_at']}",
        f"Address: {report['address_display']}",
    ]
    if report.get("message"):
        lines.append(str(report["message"]))
    for event in report.get("events", []):
        for payout in event.get("payouts", []):
            lines.extend(
                [
                    f"PAYOUT: {payout['amount']} {payout['asset']}",
                    f"Signature: {event['signature']}",
                    f"Explorer: https://solscan.io/tx/{event['signature']}",
                    "Finality: finalized",
                ]
            )
        for asset in event.get("unverified_assets", []):
            lines.append(f"UNVERIFIED ASSET: mint {asset['mint']} amount {asset['amount']}")
    if report.get("balances"):
        summary = ", ".join(f"{name}={amount}" for name, amount in report["balances"].items())
        lines.append("Balances: " + summary)
    lines.append("Report receipt: " + report["receipt"])
    return "\n".join(lines)


def scan(config_path: Path, state_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    try:
        rpc_url = validate_rpc_url(str(config["rpc_url"]))
        owner = validate_pubkey(str(config["watched_address"]))
        limit = max(1, min(int(config.get("signature_limit", 20)), 100))
        minimum_sol = Decimal(str(config.get("minimum_sol", "0.000001")))
    except (KeyError, ValueError, TypeError) as exc:
        raise GuardError(f"Invalid configuration: {exc}") from exc

    verified_mints = config.get("verified_mints", {})
    if not isinstance(verified_mints, dict):
        raise GuardError("verified_mints must be an object keyed by mint")
    for mint in verified_mints:
        try:
            validate_pubkey(mint)
        except ValueError as exc:
            raise GuardError(f"Invalid verified mint {mint}: {exc}") from exc

    state = load_json(state_path) if state_path.exists() else {}
    client = RpcClient(rpc_url)
    signatures = client.call(
        "getSignaturesForAddress",
        [owner, {"limit": limit, "commitment": "finalized"}],
    )
    newest_signature = signatures[0].get("signature") if signatures else None
    balances = current_balances(client, owner, verified_mints)
    checked_at = utc_now()
    address_display = owner[:6] + "…" + owner[-6:]

    if not state.get("initialized"):
        state = {
            "initialized": True,
            "last_seen_signature": newest_signature,
            "last_checked_at": checked_at,
            "balances": balances,
        }
        atomic_write_json(state_path, state)
        report = {
            "schema": "bountyguard.report.v1",
            "status": "baseline_created",
            "checked_at": checked_at,
            "address_display": address_display,
            "events": [],
            "balances": balances,
            "message": "Baseline recorded. No historical transaction is claimed as a new payout.",
        }
        report["receipt"] = canonical_hash(report)
        return report

    pending = new_signatures(client, owner, limit, state.get("last_seen_signature"))
    events = []
    for item in pending:
        signature = item["signature"]
        transaction = client.call(
            "getTransaction",
            [signature, {"encoding": "jsonParsed", "commitment": "finalized", "maxSupportedTransactionVersion": 0}],
        )
        if transaction:
            events.append(analyze_transaction(transaction, signature, owner, verified_mints, minimum_sol))

    payout_count = sum(len(event["payouts"]) for event in events)
    unknown_count = sum(len(event["unverified_assets"]) for event in events)
    status = "payout_detected" if payout_count else "attention" if unknown_count else "no_change"
    message = (
        f"Detected {payout_count} verified finalized payout event(s)."
        if payout_count
        else f"Detected {unknown_count} unverified incoming asset event(s); none count as earnings."
        if unknown_count
        else "No new finalized payout was detected."
    )

    state.update(
        {
            "initialized": True,
            "last_seen_signature": newest_signature or state.get("last_seen_signature"),
            "last_checked_at": checked_at,
            "balances": balances,
        }
    )
    atomic_write_json(state_path, state)
    report = {
        "schema": "bountyguard.report.v1",
        "status": status,
        "checked_at": checked_at,
        "address_display": address_display,
        "events": events,
        "balances": balances,
        "message": message,
    }
    report["receipt"] = canonical_hash(report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument(
        "--report",
        type=Path,
        help="Optionally persist the latest tamper-evident report for an operator console.",
    )
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = scan(args.config, args.state)
    except GuardError as exc:
        error_report = {
            "schema": "bountyguard.report.v1",
            "status": "verification_failed",
            "checked_at": utc_now(),
            "message": str(exc),
        }
        error_report["receipt"] = canonical_hash(error_report)
        if args.report:
            atomic_write_json(args.report, error_report)
        output = json.dumps(error_report, indent=2) if args.format == "json" else render_text({**error_report, "address_display": "unavailable", "events": []})
        print(output)
        return 1
    if args.report:
        atomic_write_json(args.report, report)
    print(json.dumps(report, indent=2) if args.format == "json" else render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
