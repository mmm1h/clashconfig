import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import update_chatgpt_voice as updater


class VoiceRulesTests(unittest.TestCase):
    def test_sort_deduplicate_and_support_ipv6(self):
        data = {"prefixes": [
            {"ipv6Prefix": "2606:4700::/32"},
            {"ipv4Prefix": "20.184.36.134/32"},
            {"ipv4Prefix": "4.197.172.116/32"},
            {"ipv4Prefix": "20.184.36.134/32"},
        ]}
        self.assertEqual(updater.parse_prefixes(data), [
            "IP-CIDR,4.197.172.116/32,no-resolve",
            "IP-CIDR,20.184.36.134/32,no-resolve",
            "IP-CIDR6,2606:4700::/32,no-resolve",
        ])

    def test_invalid_feed_rejected(self):
        invalid = [None, {}, {"prefixes": []}, {"prefixes": [None]}]
        entries = [{}, {"ipv4Prefix": "bad"}, {"ipv4Prefix": "0.0.0.0/0"},
                   {"ipv4Prefix": "10.0.0.0/8"}, {"ipv4Prefix": "20.184.36.134"},
                   {"ipv4Prefix": "20.184.36.134/24"},
                   {"ipv4Prefix": "2606:4700::/32"},
                   {"ipv4Prefix": "4.197.172.116/32", "ipv6Prefix": "2606:4700::/32"}]
        invalid += [{"prefixes": [entry]} for entry in entries]
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ValueError):
                updater.parse_prefixes(data)

    def test_migration_preserves_manual_rules(self):
        for newline in ("\n", "\r\n"):
            before = "DOMAIN-SUFFIX,chat.openai.com" + newline
            after = newline + "# 手工规则" + newline + "DOMAIN-SUFFIX,claude.ai"
            current = before + newline.join(updater.LEGACY_BLOCK) + newline + after
            rules = ["IP-CIDR,4.197.172.116/32,no-resolve"]
            result = updater.render_rules(current, rules)
            self.assertTrue(result.startswith(before + after + newline))
            self.assertEqual(result.count(updater.START), 1)
            self.assertNotIn(updater.LEGACY_BLOCK[0], result)
            self.assertEqual(updater.render_rules(result, rules), result)

    def test_refresh_replaces_stale_addresses_only(self):
        before, after = "# prefix\n", "\n# suffix\nDOMAIN-SUFFIX,claude.ai"
        current = before + updater.START + "\nIP-CIDR,4.1.1.1/32,no-resolve\n" + updater.END + after
        result = updater.render_rules(current, ["IP-CIDR,4.2.2.2/32,no-resolve"])
        self.assertTrue(result.startswith(before))
        self.assertTrue(result.endswith(after))
        self.assertNotIn("4.1.1.1", result)
        self.assertIn("4.2.2.2", result)

    def test_malformed_markers_rejected(self):
        cases = [updater.START, updater.END,
                 updater.END + "\n" + updater.START,
                 (updater.START + "\n" + updater.END + "\n") * 2]
        for current in cases:
            with self.subTest(current=current), self.assertRaises(ValueError):
                updater.render_rules(current, ["IP-CIDR,4.2.2.2/32,no-resolve"])

    def test_idempotent_update_and_failed_replace_retains_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "AI.list"
            output.write_bytes(b"DOMAIN-SUFFIX,claude.ai\r\n")
            rules = ["IP-CIDR,4.2.2.2/32,no-resolve"]
            self.assertTrue(updater.update_file(output, rules))
            saved = output.read_bytes()
            self.assertFalse(updater.update_file(output, rules))
            with patch.object(updater.os, "replace", side_effect=OSError("test failure")):
                with self.assertRaises(OSError):
                    updater.update_file(output, ["IP-CIDR,4.3.3.3/32,no-resolve"])
            self.assertEqual(output.read_bytes(), saved)
            self.assertEqual(list(Path(directory).iterdir()), [output])

    def test_failed_download_retains_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "AI.list"
            saved = b"DOMAIN-SUFFIX,claude.ai\n"
            output.write_bytes(saved)
            for error in (OSError("network unavailable"), json.JSONDecodeError("bad", "", 0)):
                with self.subTest(error=error), patch("sys.argv", ["updater", "--output", str(output)]):
                    with patch.object(updater, "urlopen", side_effect=error):
                        with self.assertRaises(SystemExit) as caught:
                            updater.main()
                        self.assertEqual(caught.exception.code, 1)
                self.assertEqual(output.read_bytes(), saved)


if __name__ == "__main__":
    unittest.main()
