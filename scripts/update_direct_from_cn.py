from pathlib import Path
from typing import List, Optional


CN_PATH = Path("rules/CN.txt")
DIRECT_PATH = Path("rules/Direct.list")
START_MARKER = "# --- CN.txt START (auto) ---"
END_MARKER = "# --- CN.txt END (auto) ---"


def _normalize_cn_line(line: str) -> Optional[str]:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("IP-CIDR,") or line.startswith("IP-CIDR6,"):
        if not line.endswith(",no-resolve"):
            return f"{line},no-resolve"
        return line
    return f"IP-CIDR,{line},no-resolve"


def _load_cn_rules(path: Path) -> List[str]:
    rules: List[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        normalized = _normalize_cn_line(raw_line)
        if normalized:
            rules.append(normalized)
    return rules


def _build_block(lines: List[str]) -> List[str]:
    return [START_MARKER, *lines, END_MARKER]


def _update_direct(direct_text: str, block: List[str]) -> str:
    lines = direct_text.splitlines()
    if START_MARKER in lines and END_MARKER in lines:
        start_index = lines.index(START_MARKER)
        end_index = lines.index(END_MARKER)
        if start_index > end_index:
            raise SystemExit("CN markers are in the wrong order in Direct.list.")
        updated = lines[:start_index] + block + lines[end_index + 1 :]
    else:
        updated = lines[:]
        if updated and updated[-1].strip():
            updated.append("")
        updated.extend(block)
    return "\n".join(updated) + "\n"


def main() -> None:
    cn_rules = _load_cn_rules(CN_PATH)
    block = _build_block(cn_rules)
    direct_text = DIRECT_PATH.read_text(encoding="utf-8")
    updated_text = _update_direct(direct_text, block)
    DIRECT_PATH.write_text(updated_text, encoding="utf-8")


if __name__ == "__main__":
    main()
