#!/usr/bin/env python3
"""Refresh only the managed ChatGPT Voice block in rules/AI.list."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.request import Request, urlopen


SOURCE_URL = "https://openai.com/chatgpt-voice.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "rules" / "AI.list"
START = "# --- ChatGPT Voice START (auto) ---"
END = "# --- ChatGPT Voice END (auto) ---"
LEGACY_BLOCK = (
    "# Observed ChatGPT dot voice media endpoints (2026-10-04)",
    "IP-CIDR,20.184.36.134/32,no-resolve",
    "IP-CIDR,4.197.172.116/32,no-resolve",
)


def parse_prefixes(data: object) -> list[str]:
    if not isinstance(data, dict):
        raise ValueError("Official feed must be a JSON object")
    prefixes = data.get("prefixes")
    if not isinstance(prefixes, list) or not prefixes:
        raise ValueError("Official feed must contain a non-empty prefixes list")
    networks = set()
    for entry in prefixes:
        if not isinstance(entry, dict):
            raise ValueError("Invalid prefix entry")
        keys = [key for key in ("ipv4Prefix", "ipv6Prefix") if key in entry]
        if len(keys) != 1 or not isinstance(entry[keys[0]], str):
            raise ValueError("Each entry must contain one IPv4 or IPv6 prefix")
        prefix = entry[keys[0]]
        if "/" not in prefix:
            raise ValueError("Prefix must include a CIDR mask")
        network = ipaddress.ip_network(prefix, strict=True)
        version = 4 if keys[0] == "ipv4Prefix" else 6
        if (
            network.version != version
            or not network.is_global
            or not network.network_address.is_global
            or not network.broadcast_address.is_global
        ):
            raise ValueError("Prefix must match its address family and be public")
        networks.add(network)
    return [
        f"{'IP-CIDR' if network.version == 4 else 'IP-CIDR6'},{network},no-resolve"
        for network in sorted(
            networks, key=lambda n: (n.version, int(n.network_address), n.prefixlen)
        )
    ]


def render_rules(current: str, rules: list[str]) -> str:
    newline = "\r\n" if "\r\n" in current else "\n"
    block = newline.join([START, f"# Source: {SOURCE_URL}", *rules, END])
    lines = current.splitlines()
    if lines.count(START) != lines.count(END) or lines.count(START) > 1:
        raise ValueError("Malformed or duplicate managed block markers")
    if START in lines:
        pattern = re.compile(
            rf"^{re.escape(START)}\r?\n.*?^{re.escape(END)}(?=\r?$)",
            re.MULTILINE | re.DOTALL,
        )
        result, count = pattern.subn(lambda _: block, current)
        if count != 1:
            raise ValueError("Managed block markers are out of order")
        return result
    # One-time migration removes only the exact temporary block from this incident.
    legacy_pattern = re.compile(
        r"^" + r"\r?\n".join(re.escape(line) for line in LEGACY_BLOCK)
        + r"(?:\r?\n|$)",
        re.MULTILINE,
    )
    current = legacy_pattern.sub("", current, count=1)
    if current and not current.endswith(("\n", "\r")):
        current += newline
    return current + block + newline


def update_file(output: Path, rules: list[str]) -> bool:
    original = output.read_bytes()
    updated = render_rules(original.decode("utf-8"), rules).encode("utf-8")
    if updated == original:
        return False
    # Replace only after parsing/rendering succeeds; interrupted downloads never write.
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(updated)
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    request = Request(SOURCE_URL, headers={"User-Agent": "clashconfig-voice-rules/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            data = json.load(response)
        rules = parse_prefixes(data)
        changed = update_file(args.output, rules)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"ChatGPT Voice update failed; existing rules retained: {exc}\n")
    print(f"{'Updated' if changed else 'Unchanged'}: {len(rules)} official voice rules")


if __name__ == "__main__":
    main()
