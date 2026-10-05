#!/usr/bin/env python3
"""Sync maintained Claude domains into AI.list and regenerate AIMerged.list."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import ipaddress
import os
from pathlib import Path
import re
import tempfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ACL_SOURCES = tuple(
    f"https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/{name}.list"
    for name in ("AI", "ClaudeAI", "Gemini", "OpenAi")
)
CLAUDE_SOURCE = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/anthropic.list"
START = "# --- Claude START (auto) ---"
END = "# --- Claude END (auto) ---"
# Only these previously added community entries migrate out of the manual area.
LEGACY_CORE_RULES = {
    "DOMAIN,servd-anthropic-website.b-cdn.net",
    *(f"DOMAIN-SUFFIX,{value}" for value in (
        "anthropic.com", "clau.de", "claude.ai", "claude.com", "claude.dev",
        "claudemcpclient.com", "claudemcpcontent.com", "claudeusercontent.com",
    )),
}


def domain(value: str) -> str:
    value = value.lower()
    labels = value.split(".")
    if len(value) > 253 or len(labels) < 2 or not all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in labels
    ) or not re.search(r"[a-z]", labels[-1]):
        raise ValueError(f"Invalid domain: {value!r}")
    return value


def parse_rules(text: str, *, geosite: bool = False) -> list[str]:
    rules = set()
    for line in text.lstrip("\ufeff").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if geosite:
            suffix = line.startswith("+.")
            rule = f"{'DOMAIN-SUFFIX' if suffix else 'DOMAIN'},{domain(line[2:] if suffix else line)}"
        else:
            parts = [part.strip() for part in line.split(",")]
            kind = parts[0]
            if kind in ("URL-REGEX", "USER-AGENT"):
                continue  # Preserve the original merged feed's exclusions.
            if kind in ("DOMAIN", "DOMAIN-SUFFIX") and len(parts) == 2:
                rule = f"{kind},{domain(parts[1])}"
            elif kind == "DOMAIN-KEYWORD" and len(parts) == 2 and re.fullmatch(r"[a-zA-Z0-9_.-]+", parts[1]):
                rule = f"{kind},{parts[1]}"
            elif kind in ("IP-CIDR", "IP-CIDR6") and (
                len(parts) == 2 or (len(parts) == 3 and parts[2] == "no-resolve")
            ):
                if "/" not in parts[1]:
                    raise ValueError("IP rule must include a CIDR mask")
                network = ipaddress.ip_network(parts[1], strict=True)
                if (
                    network.version != (4 if kind == "IP-CIDR" else 6)
                    or not network.is_global
                    or not network.network_address.is_global
                    or not network.broadcast_address.is_global
                ):
                    raise ValueError("IP rule must match its family and be public")
                rule = f"{kind},{network}" + (",no-resolve" if len(parts) == 3 else "")
            else:
                raise ValueError(f"Invalid or unsupported rule: {line!r}")
        rules.add(rule)
    if not rules:
        raise ValueError("Upstream feed contains no valid rules")
    if geosite and not {"DOMAIN-SUFFIX,claude.ai", "DOMAIN-SUFFIX,anthropic.com"} <= rules:
        raise ValueError("Anthropic feed is missing its two core domains")
    return sorted(rules)


def render_ai(current: str, rules: list[str]) -> str:
    newline = "\r\n" if "\r\n" in current else "\n"
    lines = current.splitlines()
    if lines.count(START) != lines.count(END) or lines.count(START) > 1:
        raise ValueError("Malformed or duplicate Claude block markers")
    if START in lines:
        pattern = re.compile(
            rf"^{re.escape(START)}\r?\n.*?^{re.escape(END)}(?=\r?$)",
            re.MULTILINE | re.DOTALL,
        )
        outside, count = pattern.subn("", current)
        if count != 1:
            raise ValueError("Claude block markers are out of order")
    else:
        # Initial migration leaves auxiliary hosts, IPs, Gemini and Voice intact.
        lines = [line for line in lines if line not in LEGACY_CORE_RULES]
        current = newline.join(lines) + (newline if current.endswith("\n") else "")
        outside = current
    manual = {line.strip() for line in outside.splitlines() if not line.startswith("#")}
    block = newline.join([START, f"# Source: {CLAUDE_SOURCE}",
                          *(rule for rule in rules if rule not in manual), END])
    if START in current.splitlines():
        return pattern.sub(lambda _: block, current, count=1)
    anchor = "# 内容：Claude"
    if anchor in lines:
        position = lines.index(anchor) + 1
        lines[position:position] = block.splitlines()
        return newline.join(lines) + newline
    if current and not current.endswith("\n"):
        current += newline
    return current + block + newline


def render_merged(current: str, rules: list[str], sources: tuple[str, ...]) -> str:
    source_lines = [f"# 来源{i}：{url}" for i, url in enumerate(sources, 1)]
    previous_rules = [line for line in current.splitlines() if line and not line.startswith("#")]
    previous_sources = [line for line in current.splitlines() if line.startswith("# 来源")]
    if previous_rules == rules and previous_sources == source_lines:
        return current  # Don't create daily commits just to change a timestamp.
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    return "\n".join([f"# 更新时间：{stamp}", f"# 数量：{len(rules)}条",
                       *source_lines, "# 作者：mmm1h", *rules, ""])


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "clashconfig-ai-rules/1.0"})
    with urlopen(request, timeout=30) as response:
        payload = response.read(2 * 1024 * 1024 + 1)
    if len(payload) > 2 * 1024 * 1024:
        raise ValueError("Upstream feed exceeds size limit")
    return payload.decode("utf-8-sig")


def update_files(ai_output: Path, merged_output: Path) -> tuple[int, list[str]]:
    if ai_output.resolve() == merged_output.resolve():
        raise ValueError("AI and merged outputs must be different files")
    sources = (*ACL_SOURCES, CLAUDE_SOURCE)
    # All downloads, parsers and block validation finish before either file is written.
    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        contents = list(pool.map(fetch, sources))
    claude_rules = parse_rules(contents[-1], geosite=True)
    merged_rules = sorted(set(claude_rules).union(
        *(parse_rules(text) for text in contents[:-1])
    ))
    originals = {ai_output: ai_output.read_bytes(), merged_output: merged_output.read_bytes()}
    updates = {
        ai_output: render_ai(originals[ai_output].decode("utf-8"), claude_rules).encode("utf-8"),
        merged_output: render_merged(originals[merged_output].decode("utf-8"), merged_rules, sources).encode("utf-8"),
    }
    changed = [path for path in updates if updates[path] != originals[path]]
    staged = {}
    replaced = []
    try:
        for path in changed:
            fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            staged[path] = temporary
            with os.fdopen(fd, "wb") as handle:
                handle.write(updates[path])
        for path in changed:
            os.replace(staged[path], path)
            replaced.append(path)
    except OSError:
        for path in replaced:
            path.write_bytes(originals[path])
        raise
    finally:
        for temporary in staged.values():
            if os.path.exists(temporary):
                os.unlink(temporary)
    return len(claude_rules), [path.name for path in changed]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai-output", type=Path, default=ROOT / "rules" / "AI.list")
    parser.add_argument("--merged-output", type=Path, default=ROOT / "AIMerged.list")
    args = parser.parse_args()
    try:
        count, changed = update_files(args.ai_output, args.merged_output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"AI sync failed; existing rules retained: {exc}\n")
    print(f"Claude community rules: {count}; updated: {', '.join(changed) or 'none'}")


if __name__ == "__main__":
    main()
