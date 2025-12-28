# Agent Guide

## Project summary
- This repo stores Clash/Mihomo configuration, custom rule lists, and generated merged lists.
- It also includes PaoPaoDNS force-TTL rules and helper scripts, plus archived ACL4SSR data and ImmortalWrt build notes.

## Key files
- mihomo.yaml: primary Mihomo/Clash config (providers, DNS, proxy groups, rule providers, rules).
- mihomo.js: JS config generator; group/rule names must match mihomo.yaml.
- rules/*.list: custom rule lists in Clash classical text format.
- *Merged.list: generated/merged rule lists with source headers.
- force_ttl_rules.txt: generated PaoPaoDNS rules.
- scripts/update_dns.py: regenerate force_ttl_rules.txt (requires network + python requests).
- scripts/update_dns_rules.sh: server-side updater for PaoPaoDNS.
- ImmortalWrt build notes folder (Chinese-named directory, see its README).
- ACL4SSR archive folder (Chinese-named directory): upstream snapshot; treat as vendor data.

## Editing guidelines
- Keep proxy group names and rule targets identical across mihomo.yaml and mihomo.js.
- Rule lists are one rule per line; use Clash keywords (DOMAIN, DOMAIN-SUFFIX, DOMAIN-KEYWORD, IP-CIDR, IP-CIDR6) with optional ,no-resolve.
- Preserve headers and metadata in merged lists; avoid manual edits unless regenerating from sources.
- Keep placeholders like __MEIYING_URL__ and __YUNDONG_URL__ intact unless updating subscription URLs.

## Update flows
- Custom rules: edit the relevant file in rules/ and ensure it is referenced in mihomo.yaml or mihomo.js.
- PaoPaoDNS rules: run `python scripts/update_dns.py` to refresh force_ttl_rules.txt.
- Merged lists: regenerate using the sources listed in each file header; keep the header consistent.

## Validation
- No automated tests.
- Quick checks: YAML syntax for mihomo.yaml, JS syntax for mihomo.js, and rule line formatting.
