import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyze_qx_har as analyzer


class AnalyzeQxHarTests(unittest.TestCase):
    @staticmethod
    def make_entry(url, *, status=200, body=None, method="GET"):
        content = {"mimeType": "application/json", "size": 0}
        if body is not None:
            content["text"] = json.dumps(body)
        return {
            "startedDateTime": "2026-07-23T07:07:47.000Z",
            "request": {"method": method, "url": url},
            "response": {
                "status": status,
                "bodySize": 0,
                "content": content,
            },
        }

    def make_har(self, secret="CANARY_SECRET_0123456789ABCDEF"):
        ad_url = (
            "https://adse.ximalaya.com/ting/loading/ts-1784790466691"
            f"?token={secret}"
        )
        media_url = (
            "https://imagev2.xmcdn.com/storages/"
            f"{secret}/GAqhJLsOGUf1AAIAhgSveaw6.jpg?auth={secret}"
        )
        return {
            "log": {
                "entries": [
                    {
                        "startedDateTime": "2026-07-23T07:07:47.000Z",
                        "request": {
                            "method": "POST",
                            "url": ad_url,
                            "headers": [
                                {"name": "Authorization", "value": secret},
                                {"name": "Cookie", "value": secret},
                            ],
                            "cookies": [{"name": "session", "value": secret}],
                            "postData": {
                                "mimeType": "application/json",
                                "text": json.dumps(
                                    {
                                        "name": "loading_v2",
                                        "positionId": 1,
                                        "secret": secret,
                                    }
                                ),
                            },
                        },
                        "response": {
                            "status": 200,
                            "bodySize": -1,
                            "content": {
                                "mimeType": "application/json",
                                "size": 1024,
                                "text": json.dumps(
                                    {
                                        "ret": 0,
                                        "data": [
                                            {
                                                "adUniqId": secret,
                                                "loadingShowTime": 3000,
                                                "cover": media_url,
                                            }
                                        ],
                                        "adTypes": [0],
                                        "bidSlotList": {"8": [secret]},
                                    }
                                ),
                            },
                        },
                    },
                    {
                        "startedDateTime": "2026-07-23T07:07:48.000Z",
                        "request": {
                            "method": "GET",
                            "url": media_url,
                            "headers": [{"name": "Cookie", "value": secret}],
                        },
                        "response": {
                            "status": 200,
                            "bodySize": 131206,
                            "content": {
                                "mimeType": "image/jpeg",
                                "size": 131206,
                            },
                        },
                    },
                ]
            }
        }

    def test_report_never_contains_captured_secrets(self):
        secret = "CANARY_SECRET_0123456789ABCDEF"
        report = analyzer.build_report(
            self.make_har(secret),
            "fixture.har",
            app_package="com.gemd.iting",
        )
        rendered = json.dumps(report, ensure_ascii=False)

        self.assertNotIn(secret, rendered)
        self.assertNotIn("Authorization", rendered)
        self.assertNotIn("Cookie", rendered)
        self.assertEqual(report["timeline"][0]["safe_fields"]["name"], "loading_v2")
        self.assertEqual(report["timeline"][0]["safe_fields"]["position_id"], "1")
        self.assertEqual(len(report["linked_media"]), 1)

    def test_form_allowlist_extracts_only_known_fields(self):
        request = {
            "postData": {
                "mimeType": "application/x-www-form-urlencoded",
                "text": (
                    "posid=7341520759123916"
                    "&ext=%7B%22req%22%3A%7B%22c_pkgname%22%3A"
                    "%22com.gemd.iting%22%2C%22placement_type%22%3A4%2C"
                    "%22token%22%3A%22SECRET%22%7D%7D"
                    "&token=SECRET"
                ),
            }
        }

        fields = analyzer.extract_safe_request_fields(request)

        self.assertEqual(
            fields,
            {
                "position_id": "7341520759123916",
                "package": "com.gemd.iting",
                "placement_type": "4",
            },
        )

    def test_normalized_url_drops_query_and_dynamic_segments(self):
        host, path = analyzer.normalize_url(
            "https://example.com/api/1784790466691/"
            "GAqhJLsOGUf1AAIAhgSveaw6.jpg?token=SECRET"
        )

        self.assertEqual(host, "example.com")
        self.assertEqual(path, "/api/<id>/<asset>.jpg")

    def test_report_redacts_source_unknown_host_path_and_name(self):
        har_data = {
            "log": {
                "entries": [
                    {
                        "startedDateTime": "2026-07-23T07:07:47.000Z",
                        "request": {
                            "method": "SECRET_METHOD",
                            "url": "https://adam.smith/private/alice",
                            "postData": {
                                "mimeType": "application/json",
                                "text": json.dumps({"name": "adam.smith"}),
                            },
                        },
                        "response": {
                            "status": 200,
                            "bodySize": 0,
                            "content": {
                                "mimeType": "application/SECRET_MIME",
                                "size": 0,
                                "text": json.dumps(
                                    {
                                        "data": [
                                            {
                                                "loadingShowTime": 1,
                                                "splashShake": 1,
                                            }
                                        ]
                                    }
                                ),
                            },
                        },
                    }
                ]
            }
        }

        report = analyzer.build_report(har_data, "SECRET_CAPTURE.har")
        rendered = json.dumps(report)

        for secret in (
            "SECRET_CAPTURE",
            "SECRET_METHOD",
            "SECRET_MIME",
            "adam",
            "smith",
            "private",
            "alice",
        ):
            self.assertNotIn(secret, rendered)
        self.assertEqual(report["source"], "HAR")
        self.assertRegex(report["top_hosts"][0]["host"], r"^<host-[0-9a-f]{12}>$")
        self.assertEqual(report["timeline"][0]["mime"], "<mime>")
        self.assertEqual(
            analyzer.normalize_url(
                "https://adam.smith/private/alice",
                show_hosts=True,
            )[0],
            "adam.smith",
        )

    def test_ad_classifiers_require_complete_dns_and_path_tokens(self):
        for host in (
            "admin.example.com",
            "address.example.com",
            "adobe.example.com",
        ):
            self.assertFalse(analyzer.is_ad_host(host))
        self.assertTrue(analyzer.is_ad_host("adse.ximalaya.com"))
        self.assertTrue(analyzer.is_ad_host("adbehavior.ximalaya.com"))

        for path in ("/showcase", "/launcher", "/shadow", "/api/address"):
            self.assertFalse(analyzer.is_ad_path(path))
        self.assertTrue(analyzer.is_ad_path("/ting/loading/ts-123"))
        self.assertTrue(analyzer.is_ad_path("/api/ad/request"))
        self.assertTrue(analyzer.is_ad_path("/gdt_mview.fcg"))

    def test_url_fingerprint_includes_scheme_port_and_query(self):
        baseline = analyzer.url_fingerprint(
            "https://example.com:443/asset.jpg?token=one"
        )

        self.assertEqual(
            baseline,
            analyzer.url_fingerprint(
                "https://example.com/asset.jpg?token=one"
            ),
        )
        self.assertNotEqual(
            baseline,
            analyzer.url_fingerprint(
                "http://example.com:443/asset.jpg?token=one"
            ),
        )
        self.assertNotEqual(
            baseline,
            analyzer.url_fingerprint(
                "https://example.com:8443/asset.jpg?token=one"
            ),
        )
        self.assertNotEqual(
            baseline,
            analyzer.url_fingerprint(
                "https://example.com:443/asset.jpg?token=two"
            ),
        )

    def test_media_with_different_query_is_not_linked(self):
        source_url = "https://example.com/asset.jpg?token=one"
        requested_url = "https://example.com/asset.jpg?token=two"
        har_data = {
            "log": {
                "entries": [
                    self.make_entry(
                        "https://adse.ximalaya.com/ting/loading/ts-1",
                        method="POST",
                        body={
                            "data": [{"cover": source_url, "loadingShowTime": 3}],
                            "adTypes": [0],
                        },
                    ),
                    {
                        **self.make_entry(requested_url),
                        "startedDateTime": "2026-07-23T07:07:48.000Z",
                        "response": {
                            "status": 200,
                            "bodySize": 10,
                            "content": {"mimeType": "image/jpeg", "size": 10},
                        },
                    },
                ]
            }
        }

        report = analyzer.build_report(har_data, "HAR A")

        self.assertEqual(report["linked_media"], [])

    def test_comparison_reports_new_candidate_endpoint(self):
        old_har = {"log": {"entries": []}}
        new_har = self.make_har()
        first = analyzer.build_report(
            old_har,
            "old.har",
        )
        second = analyzer.build_report(
            new_har,
            "new.har",
        )

        comparison = analyzer.compare_reports(
            first,
            second,
            30,
            old_har,
            new_har,
        )

        self.assertEqual(comparison["identical_prefix_entries"], 0)
        self.assertTrue(
            any(
                row["endpoint"].startswith(
                    "adse.ximalaya.com/ting/loading/ts-*"
                )
                for row in comparison["added"]
            )
        )

    def test_common_prefix_detects_cumulative_export(self):
        old_har = self.make_har()
        new_har = self.make_har()
        new_har["log"]["entries"].append(
            {
                "startedDateTime": "2026-07-23T07:07:49.000Z",
                "request": {
                    "method": "GET",
                    "url": "https://example.com/after-prefix",
                },
                "response": {
                    "status": 204,
                    "bodySize": 0,
                    "content": {"size": 0, "mimeType": "text/plain"},
                },
            }
        )

        self.assertEqual(analyzer.common_prefix_entries(old_har, new_har), 2)

    def test_comparison_keeps_http_status_dimension(self):
        old_har = {
            "log": {
                "entries": [
                    self.make_entry(
                        "https://adse.ximalaya.com/ting/loading/ts-1",
                        status=200,
                    )
                ]
            }
        }
        new_har = {
            "log": {
                "entries": [
                    self.make_entry(
                        "https://adse.ximalaya.com/ting/loading/ts-1",
                        status=204,
                    )
                ]
            }
        }
        old_report = analyzer.build_report(old_har, "HAR A")
        new_report = analyzer.build_report(new_har, "HAR B")

        comparison = analyzer.compare_reports(old_report, new_report, 30)

        self.assertEqual([row["status"] for row in comparison["removed"]], [200])
        self.assertEqual([row["status"] for row in comparison["added"]], [204])

    def test_comparison_uses_candidates_beyond_display_top(self):
        first_entry = self.make_entry(
            "https://adse.ximalaya.com/ting/loading/ts-1"
        )
        second_entry = self.make_entry(
            "https://v2mi.gdt.qq.com/gdt_mview.fcg"
        )
        old_report = analyzer.build_report(
            {"log": {"entries": [first_entry]}},
            "HAR A",
            top=1,
        )
        new_report = analyzer.build_report(
            {"log": {"entries": [first_entry, second_entry]}},
            "HAR B",
            top=1,
        )

        comparison = analyzer.compare_reports(old_report, new_report, 30)

        self.assertEqual(len(new_report["candidate_endpoints"]), 1)
        self.assertTrue(
            any("v2mi.gdt.qq.com" in row["endpoint"] for row in comparison["added"])
        )

    def test_cli_redacts_input_filename_and_writes_atomically(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            input_path = directory / "SECRET_CAPTURE.har"
            output_path = directory / "report.json"
            input_path.write_text(
                json.dumps(self.make_har()),
                encoding="utf-8",
            )

            result = analyzer.main(
                [
                    str(input_path),
                    "--format",
                    "json",
                    "--output",
                    str(output_path),
                ]
            )
            rendered = output_path.read_text(encoding="utf-8")

            self.assertEqual(result, 0)
            self.assertNotIn("SECRET_CAPTURE", rendered)
            self.assertEqual(json.loads(rendered)["reports"][0]["source"], "HAR A")
            self.assertEqual(list(directory.glob(f".{output_path.name}.*.tmp")), [])

    def test_output_cannot_overwrite_input_har(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "capture.har"
            original = json.dumps(self.make_har()).encode("utf-8")
            input_path.write_bytes(original)

            with contextlib.redirect_stderr(io.StringIO()):
                result = analyzer.main(
                    [str(input_path), "--output", str(input_path)]
                )

            self.assertEqual(result, 2)
            self.assertEqual(input_path.read_bytes(), original)

    def test_failed_atomic_replace_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            input_path = directory / "capture.har"
            output_path = directory / "report.txt"
            input_path.write_text(json.dumps(self.make_har()), encoding="utf-8")
            output_path.write_text("existing report", encoding="utf-8")

            with (
                mock.patch.object(
                    analyzer.os,
                    "replace",
                    side_effect=OSError("replace failed"),
                ),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                result = analyzer.main(
                    [str(input_path), "--output", str(output_path)]
                )

            self.assertEqual(result, 2)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "existing report",
            )
            self.assertEqual(list(directory.glob(f".{output_path.name}.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
