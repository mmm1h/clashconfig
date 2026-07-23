#!/usr/bin/env python3
"""Analyze Quantumult X HAR files without exposing captured secrets."""

from __future__ import annotations

import argparse
import base64
import hashlib
import ipaddress
import json
import os
import re
import secrets
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit


MAX_BODY_CHARS = 4 * 1024 * 1024
MAX_FORM_CHARS = 512 * 1024
HOST_REDACTION_KEY = secrets.token_bytes(32)

AD_HOST_LABELS = {
    "ad",
    "adbs",
    "ads",
    "adse",
    "adse-v2",
    "adsebs",
    "adsehera",
    "adbehavior",
    "adsmind",
    "adweb",
    "impdsp",
    "pangolin",
    "pgdt",
    "sdkreport",
    "tmead",
    "voiceads",
    "xdcs-collector",
}
AD_HOSTS = {
    "sdkquic.e.qq.com",
    "us.l.qq.com",
    "v2mi.gdt.qq.com",
}
AD_PATH_SEGMENTS = {
    "ad",
    "adx",
    "advertisement",
    "advertising",
    "exapp",
    "gdt_mview",
    "gdt_mview.fcg",
    "getad",
    "getpbcompressad",
    "impress",
    "splash",
}
AD_PATH_PAIRS = {
    ("api", "ad"),
    ("ting", "loading"),
    ("ting", "preload"),
}
REPORT_PATH_SEGMENTS = {
    "click",
    "event",
    "impress",
    "report",
    "show",
    "statistics",
}
JSON_SIGNAL_MARKERS = {
    "ad-id": ("adid", "aduniqid"),
    "ad-type": ("adtype", "adtypes", "thirdadtype"),
    "bid-slot": ("bidslot",),
    "creative": ("creative",),
    "exposure": ("exposure", "impression", "thirdshowstat"),
    "loading": ("loadingshowtime",),
    "material": ("material",),
    "splash": ("splash",),
    "visual": ("cover", "showstyle", "videourl"),
}
MEDIA_KEY_MARKERS = (
    "cover",
    "downloadlink",
    "image",
    "material",
    "pic",
    "video",
)
MEDIA_EXTENSIONS = (
    ".avif",
    ".gif",
    ".jpeg",
    ".jpg",
    ".m3u8",
    ".mov",
    ".mp4",
    ".png",
    ".webp",
)

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
LONG_NUMBER_RE = re.compile(r"^\d{7,}(?:\.\d+)?$")
EMAIL_RE = re.compile(r"^[^/@\s]+@[^/@\s]+$")
SAFE_PACKAGE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
SAFE_NAME_RE = re.compile(
    r"^(?:loading|splash)(?:[_-]v?\d{1,4})?$",
    re.IGNORECASE,
)
SAFE_SOURCE_RE = re.compile(r"^HAR (?:[A-Z]+|\d+)$")
SAFE_PUBLIC_HOSTS = AD_HOSTS | {
    "ad.ximalaya.com",
    "adbehavior.wsa.ximalaya.com",
    "adbehavior.ximalaya.com",
    "adbs.ximalaya.com",
    "adse-v2.ximalaya.com",
    "adse.wsa.ximalaya.com",
    "adse.ximalaya.com",
    "adsebs.ximalaya.com",
    "adsehera.ximalaya.com",
    "adweb.ximalaya.com",
    "example.com",
    "imagev2.xmcdn.com",
    "xdcs-collector.ximalaya.com",
}
SAFE_PUBLIC_PACKAGES = {"com.gemd.iting"}
SAFE_METHODS = {
    "CONNECT",
    "DELETE",
    "GET",
    "HEAD",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
    "TRACE",
}
SAFE_MIME_TYPES = {
    "application/json",
    "application/octet-stream",
    "application/protobuf",
    "application/x-protobuf",
    "application/xml",
    "text/css",
    "text/html",
    "text/javascript",
    "text/plain",
    "text/xml",
}
SAFE_PATH_SEGMENTS = {
    "ad",
    "adx",
    "api",
    "click",
    "event",
    "exapp",
    "feed",
    "gdt_mview.fcg",
    "getad",
    "getpbcompressad",
    "home",
    "impress",
    "launch",
    "loading",
    "preload",
    "report",
    "show",
    "splash",
    "statistics",
    "storages",
    "ting",
}
PUBLIC_REPORT_FIELDS = (
    "source",
    "summary",
    "top_hosts",
    "candidate_endpoints",
    "timeline",
    "linked_media",
    "ad_reports",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze one or more Quantumult X HAR files. Reports are always "
            "redacted: headers, cookies, query values, and raw bodies are omitted."
        )
    )
    parser.add_argument("har", nargs="+", type=Path, help="HAR file(s) to analyze")
    parser.add_argument(
        "--app-package",
        help="Boost candidates whose safe form metadata matches this package",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=30,
        help="Maximum rows per report section (default: 30)",
    )
    parser.add_argument(
        "--window",
        type=float,
        default=8.0,
        help="Seconds used to associate ad metadata with media downloads (default: 8)",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=5,
        help="Minimum candidate score (default: 5)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
    )
    parser.add_argument(
        "--show-hosts",
        action="store_true",
        help="Show all hostnames; may expose account or device identifiers",
    )
    parser.add_argument("--output", type=Path, help="Write the report to this file")
    args = parser.parse_args(argv)

    if args.top < 1:
        parser.error("--top must be at least 1")
    if args.window < 0:
        parser.error("--window cannot be negative")
    if args.min_score < 0:
        parser.error("--min-score cannot be negative")
    if args.app_package and not SAFE_PACKAGE_RE.fullmatch(args.app_package):
        parser.error("--app-package has an invalid format")

    return args


def parse_timestamp(value: Any) -> float | None:
    if not isinstance(value, str) or not value:
        return None

    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return None


def safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    return default


def sanitize_method(value: Any) -> str:
    method = value.upper() if isinstance(value, str) else ""
    return method if method in SAFE_METHODS else "<method>"


def sanitize_mime(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    base_type = value.split(";", 1)[0].strip().lower()
    for media_prefix in ("audio/", "image/", "video/"):
        if base_type.startswith(media_prefix):
            return media_prefix + "*"
    return base_type if base_type in SAFE_MIME_TYPES else "<mime>"


def sanitize_segment(segment: str) -> str:
    decoded = unquote(segment)
    if "!" in decoded:
        decoded = decoded.split("!", 1)[0]

    if not decoded:
        return ""
    if "=" in decoded or "&" in decoded:
        return "<params>"
    if UUID_RE.fullmatch(decoded) or LONG_NUMBER_RE.fullmatch(decoded):
        return "<id>"
    if EMAIL_RE.fullmatch(decoded):
        return "<id>"
    if re.fullmatch(r"ts-\d+(?:\.\d+)?", decoded, re.IGNORECASE):
        return "ts-*"

    extension_match = re.search(r"(\.[A-Za-z0-9]{2,5})$", decoded)
    suffix = extension_match.group(1).lower() if extension_match else ""
    if decoded.lower() in SAFE_PATH_SEGMENTS:
        return decoded.lower()
    if suffix:
        return "<asset>" + suffix
    return "<segment>"


def sanitize_host(host: str, *, show_hosts: bool = False) -> str:
    lowered = host.lower().rstrip(".")
    if show_hosts:
        return lowered
    if lowered in SAFE_PUBLIC_HOSTS:
        return lowered
    try:
        ipaddress.ip_address(lowered)
        alias_type = "ip"
    except ValueError:
        alias_type = "host"
    digest = hashlib.blake2s(
        lowered.encode("utf-8"),
        key=HOST_REDACTION_KEY,
        digest_size=6,
    ).hexdigest()
    return f"<{alias_type}-{digest}>"


def normalize_url(
    raw_url: Any,
    *,
    show_hosts: bool = False,
) -> tuple[str, str]:
    if not isinstance(raw_url, str):
        return "<invalid-host>", "/<invalid-path>"

    try:
        parsed = urlsplit(raw_url)
        raw_host = (parsed.hostname or "<invalid-host>").lower()
        host = sanitize_host(raw_host, show_hosts=show_hosts)
        segments = [sanitize_segment(segment) for segment in parsed.path.split("/")]
        path = "/".join(segments)
        if not path.startswith("/"):
            path = "/" + path
        return host, path or "/"
    except ValueError:
        return "<invalid-host>", "/<invalid-path>"


def url_fingerprint(raw_url: Any) -> str | None:
    if not isinstance(raw_url, str):
        return None

    try:
        parsed = urlsplit(raw_url)
        if not parsed.hostname:
            return None
        scheme = parsed.scheme.lower()
        host = parsed.hostname.lower()
        port = parsed.port
        if port is None:
            port = {"http": 80, "https": 443}.get(scheme)
        canonical = (
            f"{scheme}://{host}:{port or ''}{parsed.path}"
            f"?{parsed.query}"
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    except ValueError:
        return None


def response_size(response: dict[str, Any]) -> int:
    body_size = safe_int(response.get("bodySize"), -1)
    if body_size >= 0:
        return body_size

    content = response.get("content")
    if isinstance(content, dict):
        content_size = safe_int(content.get("size"), -1)
        if content_size >= 0:
            return content_size
    return 0


def decoded_content_text(content: Any) -> str | None:
    if not isinstance(content, dict):
        return None

    text = content.get("text")
    if not isinstance(text, str) or len(text) > MAX_BODY_CHARS:
        return None

    if content.get("encoding") != "base64":
        return text

    try:
        decoded = base64.b64decode(text, validate=False)
        if len(decoded) > MAX_BODY_CHARS:
            return None
        return decoded.decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def first_value(values: dict[str, list[str]], key: str) -> str | None:
    candidates = values.get(key)
    if not candidates:
        return None
    return candidates[0]


def add_safe_request_json_fields(payload: Any, fields: dict[str, str]) -> None:
    if not isinstance(payload, dict):
        return

    request_info = payload.get("req")
    if isinstance(request_info, dict):
        package = request_info.get("c_pkgname")
        placement = request_info.get("placement_type")
        if isinstance(package, str) and SAFE_PACKAGE_RE.fullmatch(package):
            fields["package"] = package
        if str(placement).isdigit() and len(str(placement)) <= 6:
            fields["placement_type"] = str(placement)

    position_id = payload.get("positionId")
    if str(position_id).isdigit() and len(str(position_id)) <= 20:
        fields["position_id"] = str(position_id)

    name = payload.get("name")
    if isinstance(name, str) and SAFE_NAME_RE.fullmatch(name):
        fields["name"] = name


def extract_safe_request_fields(request: dict[str, Any]) -> dict[str, str]:
    post_data = request.get("postData")
    if not isinstance(post_data, dict) or post_data.get("encoding") == "base64":
        return {}

    text = post_data.get("text")
    if not isinstance(text, str) or len(text) > MAX_FORM_CHARS:
        return {}

    fields: dict[str, str] = {}
    mime_type = str(post_data.get("mimeType", "")).lower()

    if "application/x-www-form-urlencoded" in mime_type:
        try:
            values = parse_qs(
                text,
                keep_blank_values=True,
                strict_parsing=False,
                max_num_fields=200,
            )
        except (ValueError, UnicodeDecodeError):
            values = {}

        position_id = first_value(values, "posid")
        if position_id and position_id.isdigit() and len(position_id) <= 20:
            fields["position_id"] = position_id

        extension = first_value(values, "ext")
        if extension and len(extension) <= MAX_FORM_CHARS:
            try:
                add_safe_request_json_fields(json.loads(extension), fields)
            except (json.JSONDecodeError, TypeError):
                pass

    if "json" in mime_type or text.lstrip().startswith(("{", "[")):
        try:
            add_safe_request_json_fields(json.loads(text), fields)
        except (json.JSONDecodeError, TypeError):
            pass

    return fields


def json_signal_name(key: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    for signal_name, markers in JSON_SIGNAL_MARKERS.items():
        if any(marker in normalized for marker in markers):
            return signal_name
    return None


def looks_like_media_url(value: str) -> bool:
    try:
        path = urlsplit(value).path.lower()
    except ValueError:
        return False
    return any(extension in path for extension in MEDIA_EXTENSIONS)


def analyze_response_json(
    response: dict[str, Any],
) -> tuple[dict[str, Any], set[str]]:
    content = response.get("content")
    text = decoded_content_text(content)
    if text is None:
        return {}, set()

    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}, set()

    signals: Counter[str] = Counter()
    media_fingerprints: set[str] = set()

    def walk(value: Any, parent_key: str = "", depth: int = 0) -> None:
        if depth > 10:
            return
        if isinstance(value, dict):
            for key, nested in value.items():
                key_text = str(key)
                signal = json_signal_name(key_text)
                if signal:
                    signals[signal] += 1
                walk(nested, key_text, depth + 1)
        elif isinstance(value, list):
            for nested in value[:100]:
                walk(nested, parent_key, depth + 1)
        elif isinstance(value, str):
            normalized_key = re.sub(r"[^a-z0-9]", "", parent_key.lower())
            is_media_key = any(marker in normalized_key for marker in MEDIA_KEY_MARKERS)
            if is_media_key and looks_like_media_url(value):
                fingerprint = url_fingerprint(value)
                if fingerprint:
                    media_fingerprints.add(fingerprint)

    walk(payload)

    summary: dict[str, Any] = {}
    if signals:
        summary["signals"] = sorted(signals)
        summary["signal_count"] = sum(signals.values())
    if isinstance(payload, dict):
        data = payload.get("data")
        ad_types = payload.get("adTypes")
        bid_slots = payload.get("bidSlotList")
        if isinstance(data, list):
            summary["data_items"] = len(data)
        elif isinstance(data, dict):
            summary["data_items"] = len(data)
        if isinstance(ad_types, list):
            summary["ad_type_items"] = len(ad_types)
        if isinstance(bid_slots, dict):
            summary["bid_slots"] = len(bid_slots)

    return summary, media_fingerprints


def is_ad_host(host: str) -> bool:
    if host in AD_HOSTS:
        return True
    labels = host.split(".")
    return any(
        label in AD_HOST_LABELS
        or re.fullmatch(r"(?:adse|adbehavior)[-_]?\d+", label) is not None
        for label in labels
    )


def is_ad_path(path: str) -> bool:
    segments = [
        unquote(segment).lower()
        for segment in path.split("/")
        if segment
    ]
    if any(segment in AD_PATH_SEGMENTS for segment in segments):
        return True
    return any(
        (first, second) in AD_PATH_PAIRS
        for first, second in zip(segments, segments[1:])
    )


def is_report_path(path: str) -> bool:
    segments = {
        unquote(segment).lower()
        for segment in path.split("/")
        if segment
    }
    return bool(segments & REPORT_PATH_SEGMENTS)


def is_media_response(mime_type: str, path: str) -> bool:
    lowered_mime = mime_type.lower()
    lowered_path = path.lower()
    return (
        lowered_mime.startswith(("image/", "video/"))
        or any(extension in lowered_path for extension in MEDIA_EXTENSIONS)
    )


def build_entry_view(
    entry: dict[str, Any],
    index: int,
    base_time: float | None,
    app_package: str | None,
    show_hosts: bool,
) -> dict[str, Any]:
    request = entry.get("request")
    response = entry.get("response")
    if not isinstance(request, dict):
        request = {}
    if not isinstance(response, dict):
        response = {}

    raw_url = request.get("url")
    host, path = normalize_url(raw_url, show_hosts=show_hosts)
    try:
        parsed_url = urlsplit(raw_url) if isinstance(raw_url, str) else None
        raw_host = (
            (parsed_url.hostname or "<invalid-host>").lower()
            if parsed_url is not None
            else "<invalid-host>"
        )
        raw_path = parsed_url.path if parsed_url is not None else ""
    except ValueError:
        raw_host = "<invalid-host>"
        raw_path = ""
    timestamp = parse_timestamp(entry.get("startedDateTime"))
    relative_time = (
        round(timestamp - base_time, 3)
        if timestamp is not None and base_time is not None
        else None
    )
    content = response.get("content")
    mime_type = (
        sanitize_mime(content.get("mimeType", ""))
        if isinstance(content, dict)
        else ""
    )
    safe_fields = extract_safe_request_fields(request)
    package = safe_fields.get("package")
    allowed_packages = SAFE_PUBLIC_PACKAGES | ({app_package} if app_package else set())
    if package and package not in allowed_packages:
        del safe_fields["package"]
    json_summary, media_references = analyze_response_json(response)

    evidence: list[str] = []
    score = 0

    if is_ad_host(raw_host):
        evidence.append("ad-host")
        score += 4
    if is_ad_path(raw_path):
        evidence.append("ad-path")
        score += 3
    if "position_id" in safe_fields:
        evidence.append("ad-position")
        score += 3
    if "package" in safe_fields:
        evidence.append("package")
        score += 1
        if app_package and safe_fields["package"] == app_package:
            evidence.append("target-package")
            score += 3
    signals = json_summary.get("signals", [])
    if len(signals) >= 2:
        evidence.append("json-ad-signals")
        score += 4
    if json_summary.get("data_items", 0) > 0 and signals:
        evidence.append("ad-items")
        score += 2
    if any(signal in signals for signal in ("loading", "splash")):
        evidence.append("splash-signals")
        score += 4
    if is_media_response(mime_type, raw_path) and is_ad_host(raw_host):
        evidence.append("ad-media")
        score += 2
    if is_report_path(raw_path) and (
        is_ad_host(raw_host) or is_ad_path(raw_path)
    ):
        evidence.append("ad-report")
        score += 1

    return {
        "index": index,
        "time": relative_time,
        "timestamp": timestamp,
        "method": sanitize_method(request.get("method")),
        "host": host,
        "path": path,
        "endpoint": host + path,
        "status": safe_int(response.get("status")),
        "size": response_size(response),
        "mime": mime_type,
        "score": score,
        "evidence": evidence,
        "safe_fields": safe_fields,
        "json": json_summary,
        "_is_ad_host": is_ad_host(raw_host),
        "_is_ad_path": is_ad_path(raw_path),
        "_is_report_path": is_report_path(raw_path),
        "_is_media": is_media_response(mime_type, raw_path),
        "_media_references": media_references,
        "_request_fingerprint": url_fingerprint(raw_url),
    }


def public_entry(view: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in view.items()
        if not key.startswith("_") and key not in ("timestamp", "host", "path")
    }


def aggregate_candidate_endpoints(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    aggregated: dict[tuple[str, str, int], dict[str, Any]] = {}
    for view in candidates:
        key = (view["method"], view["endpoint"], view["status"])
        item = aggregated.setdefault(
            key,
            {
                "method": view["method"],
                "endpoint": view["endpoint"],
                "status": view["status"],
                "count": 0,
                "bytes": 0,
                "max_score": 0,
                "evidence": set(),
            },
        )
        item["count"] += 1
        item["bytes"] += view["size"]
        item["max_score"] = max(item["max_score"], view["score"])
        item["evidence"].update(view["evidence"])

    rows = []
    for item in aggregated.values():
        item["evidence"] = sorted(item["evidence"])
        rows.append(item)
    rows.sort(key=lambda item: (-item["max_score"], -item["count"], item["endpoint"]))
    return rows


def build_report(
    har_data: dict[str, Any],
    source_label: str,
    *,
    app_package: str | None = None,
    top: int = 30,
    window: float = 8.0,
    min_score: int = 5,
    show_hosts: bool = False,
) -> dict[str, Any]:
    log = har_data.get("log")
    if not isinstance(log, dict) or not isinstance(log.get("entries"), list):
        raise ValueError("HAR does not contain log.entries")

    entries = [entry for entry in log["entries"] if isinstance(entry, dict)]
    timestamps = [
        timestamp
        for timestamp in (
            parse_timestamp(entry.get("startedDateTime")) for entry in entries
        )
        if timestamp is not None
    ]
    base_time = min(timestamps) if timestamps else None
    end_time = max(timestamps) if timestamps else None

    views = [
        build_entry_view(
            entry,
            index,
            base_time,
            app_package,
            show_hosts,
        )
        for index, entry in enumerate(entries)
    ]

    requests_by_fingerprint: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for view in views:
        fingerprint = view["_request_fingerprint"]
        if fingerprint:
            requests_by_fingerprint[fingerprint].append(view)

    linked_media: list[dict[str, Any]] = []
    linked_keys: set[tuple[int, int]] = set()
    for source in views:
        if not source["_media_references"]:
            continue
        for fingerprint in source["_media_references"]:
            for media in requests_by_fingerprint.get(fingerprint, []):
                if source["timestamp"] is None or media["timestamp"] is None:
                    continue
                delta = media["timestamp"] - source["timestamp"]
                relation_key = (source["index"], media["index"])
                if (
                    delta < 0
                    or delta > window
                    or relation_key in linked_keys
                    or not media["_is_media"]
                ):
                    continue
                linked_keys.add(relation_key)
                linked_media.append(
                    {
                        "time": media["time"],
                        "delta": round(delta, 3),
                        "source": source["endpoint"],
                        "media": media["endpoint"],
                        "status": media["status"],
                        "size": media["size"],
                        "mime": media["mime"],
                    }
                )
                if "linked-media" not in source["evidence"]:
                    source["evidence"].append("linked-media")
                    source["score"] += 2

    candidates = [view for view in views if view["score"] >= min_score]
    selected_timeline = sorted(
        sorted(
            candidates,
            key=lambda view: (-view["score"], view["time"] is None, view["time"], view["index"]),
        )[:top],
        key=lambda view: (view["time"] is None, view["time"], view["index"]),
    )
    reports = [
        public_entry(view)
        for view in views
        if view["_is_report_path"]
        and (view["_is_ad_host"] or view["_is_ad_path"])
    ][:top]

    host_counts = Counter(view["host"] for view in views)
    top_hosts = [
        {"host": host, "count": count}
        for host, count in host_counts.most_common(top)
    ]

    candidate_endpoints = aggregate_candidate_endpoints(candidates)
    safe_source = source_label if SAFE_SOURCE_RE.fullmatch(source_label) else "HAR"

    return {
        "source": safe_source,
        "summary": {
            "entries": len(entries),
            "hosts": len(host_counts),
            "duration_seconds": (
                round(end_time - base_time, 3)
                if base_time is not None and end_time is not None
                else None
            ),
            "response_bytes": sum(view["size"] for view in views),
            "invalid_timestamps": len(entries) - len(timestamps),
        },
        "top_hosts": top_hosts,
        "candidate_endpoints": candidate_endpoints[:top],
        "timeline": [public_entry(view) for view in selected_timeline],
        "linked_media": sorted(
            linked_media,
            key=lambda item: (item["time"] is None, item["time"], item["media"]),
        )[:top],
        "ad_reports": reports,
        "_candidate_endpoints_all": candidate_endpoints,
    }


def compare_reports(
    previous: dict[str, Any],
    current: dict[str, Any],
    top: int,
    previous_har: dict[str, Any] | None = None,
    current_har: dict[str, Any] | None = None,
) -> dict[str, Any]:
    def endpoint_counts(report: dict[str, Any]) -> dict[tuple[str, str, int], int]:
        rows = report.get(
            "_candidate_endpoints_all",
            report["candidate_endpoints"],
        )
        return {
            (row["method"], row["endpoint"], row["status"]): row["count"]
            for row in rows
        }

    old_counts = endpoint_counts(previous)
    new_counts = endpoint_counts(current)
    old_keys = set(old_counts)
    new_keys = set(new_counts)

    added = [
        {
            "method": method,
            "endpoint": endpoint,
            "status": status,
            "count": new_counts[(method, endpoint, status)],
        }
        for method, endpoint, status in sorted(new_keys - old_keys)
    ]
    removed = [
        {
            "method": method,
            "endpoint": endpoint,
            "status": status,
            "count": old_counts[(method, endpoint, status)],
        }
        for method, endpoint, status in sorted(old_keys - new_keys)
    ]
    changed = [
        {
            "method": method,
            "endpoint": endpoint,
            "status": status,
            "before": old_counts[(method, endpoint, status)],
            "after": new_counts[(method, endpoint, status)],
        }
        for method, endpoint, status in sorted(old_keys & new_keys)
        if old_counts[(method, endpoint, status)]
        != new_counts[(method, endpoint, status)]
    ]
    changed.sort(key=lambda row: -abs(row["after"] - row["before"]))

    comparison = {
        "from": previous["source"],
        "to": current["source"],
        "added": added[:top],
        "removed": removed[:top],
        "changed": changed[:top],
    }
    if previous_har is not None and current_har is not None:
        comparison["identical_prefix_entries"] = common_prefix_entries(
            previous_har,
            current_har,
        )
    return comparison


def common_prefix_entries(
    previous_har: dict[str, Any],
    current_har: dict[str, Any],
) -> int:
    previous_entries = previous_har.get("log", {}).get("entries", [])
    current_entries = current_har.get("log", {}).get("entries", [])
    if not isinstance(previous_entries, list) or not isinstance(current_entries, list):
        return 0

    identical = 0
    for previous_entry, current_entry in zip(previous_entries, current_entries):
        if previous_entry != current_entry:
            break
        identical += 1
    return identical


def format_time(value: Any) -> str:
    return f"{value:9.3f}s" if isinstance(value, (int, float)) else "   index?"


def format_text(result: dict[str, Any]) -> str:
    lines: list[str] = []
    for report in result["reports"]:
        summary = report["summary"]
        lines.extend(
            [
                report["source"],
                (
                    "  entries={entries} hosts={hosts} duration={duration_seconds}s "
                    "response_bytes={response_bytes} invalid_timestamps={invalid_timestamps}"
                ).format(**summary),
                "  Top hosts:",
            ]
        )
        for row in report["top_hosts"]:
            lines.append(f"    {row['count']:5d}  {row['host']}")

        lines.append("  Candidate endpoints:")
        for row in report["candidate_endpoints"]:
            evidence = ",".join(row["evidence"])
            lines.append(
                f"    score={row['max_score']:2d} count={row['count']:3d} "
                f"status={row['status']:3d} bytes={row['bytes']:8d} "
                f"{row['method']} {row['endpoint']} [{evidence}]"
            )

        lines.append("  Candidate timeline:")
        for row in report["timeline"]:
            fields = ",".join(
                f"{key}={value}" for key, value in row["safe_fields"].items()
            )
            evidence = ",".join(row["evidence"])
            suffix = f" {{{fields}}}" if fields else ""
            lines.append(
                f"    {format_time(row['time'])} score={row['score']:2d} "
                f"{row['status']:3d} {row['size']:8d}B {row['method']} "
                f"{row['endpoint']} [{evidence}]{suffix}"
            )

        lines.append("  Linked media:")
        for row in report["linked_media"]:
            lines.append(
                f"    {format_time(row['time'])} +{row['delta']:.3f}s "
                f"{row['status']:3d} {row['size']:8d}B "
                f"{row['source']} -> {row['media']}"
            )

        lines.append("  Ad reports:")
        for row in report["ad_reports"]:
            lines.append(
                f"    {format_time(row['time'])} {row['status']:3d} "
                f"{row['method']} {row['endpoint']}"
            )
        lines.append("")

    for comparison in result["comparisons"]:
        lines.append(f"COMPARE {comparison['from']} -> {comparison['to']}")
        if "identical_prefix_entries" in comparison:
            lines.append(
                "  identical_prefix_entries="
                f"{comparison['identical_prefix_entries']}"
            )
        for label in ("added", "removed", "changed"):
            lines.append(f"  {label}:")
            for row in comparison[label]:
                if label == "changed":
                    lines.append(
                        f"    {row['before']:3d} -> {row['after']:3d} "
                        f"status={row['status']:3d} "
                        f"{row['method']} {row['endpoint']}"
                    )
                else:
                    lines.append(
                        f"    {row['count']:3d} status={row['status']:3d} "
                        f"{row['method']} {row['endpoint']}"
                    )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def load_har(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("HAR root must be a JSON object")
    return payload


def har_source_label(index: int) -> str:
    value = index + 1
    letters = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return f"HAR {letters}"


def paths_refer_to_same_file(first: Path, second: Path) -> bool:
    first_resolved = os.path.normcase(str(first.resolve(strict=False)))
    second_resolved = os.path.normcase(str(second.resolve(strict=False)))
    if first_resolved == second_resolved:
        return True
    try:
        return first.exists() and second.exists() and os.path.samefile(first, second)
    except OSError:
        return False


def write_text_atomic(path: Path, text: str) -> None:
    parent = path.resolve(strict=False).parent
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=parent,
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink()
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.output and any(
        paths_refer_to_same_file(args.output, input_path)
        for input_path in args.har
    ):
        print("error: --output must not overwrite an input HAR", file=sys.stderr)
        return 2

    try:
        har_payloads = [load_har(path) for path in args.har]
        reports = [
            build_report(
                har_payload,
                har_source_label(index),
                app_package=args.app_package,
                top=args.top,
                window=args.window,
                min_score=args.min_score,
                show_hosts=args.show_hosts,
            )
            for index, har_payload in enumerate(har_payloads)
        ]
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    result = {
        "reports": [
            {
                key: report[key]
                for key in PUBLIC_REPORT_FIELDS
            }
            for report in reports
        ],
        "comparisons": [
            compare_reports(
                reports[index - 1],
                reports[index],
                args.top,
                har_payloads[index - 1],
                har_payloads[index],
            )
            for index in range(1, len(reports))
        ],
    }
    rendered = (
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output_format == "json"
        else format_text(result)
    )

    try:
        if args.output:
            write_text_atomic(args.output, rendered)
        else:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
            sys.stdout.write(rendered)
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
