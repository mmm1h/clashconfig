from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import update_ai_rules as updater
from scripts import update_chatgpt_voice as voice


COMMUNITY = "+.claude.ai\n+.anthropic.com\n+.new.claude.dev\ncdn.example.com\n"
CLASSICAL = "# test\nDOMAIN-SUFFIX,claude.ai\nDOMAIN-KEYWORD,openai\n"


def feed(url):
    return COMMUNITY if url == updater.CLAUDE_SOURCE else CLASSICAL


class AIRulesTests(unittest.TestCase):
    def test_geosite_conversion_and_deduplication(self):
        rules = updater.parse_rules("\ufeff" + COMMUNITY + "+.CLAUDE.AI # repeated\n", geosite=True)
        self.assertIn("DOMAIN,cdn.example.com", rules)
        self.assertIn("DOMAIN-SUFFIX,new.claude.dev", rules)
        self.assertEqual(len(rules), 4)
        self.assertEqual(rules, sorted(rules))

    def test_invalid_domain_feeds_rejected(self):
        for text in ("", "# only a comment", "<html>Service unavailable</html>",
                     "+.example.com", COMMUNITY + "*\n", COMMUNITY + "+.com\n",
                     COMMUNITY + "+.192.168.9.1\n", COMMUNITY + "-bad.example.com\n",
                     COMMUNITY + "claude.ai,DIRECT\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                updater.parse_rules(text, geosite=True)

    def test_classical_rules_and_original_exclusions(self):
        rules = updater.parse_rules(CLASSICAL +
            "DOMAIN-SUFFIX,CLAUDE.AI # duplicate\n"
            "IP-CIDR,160.79.104.0/23,no-resolve\n"
            "IP-CIDR6,2607:6bc0::/48,no-resolve\n"
            "URL-REGEX,^https://example.com/\nUSER-AGENT,SomeClient\n")
        self.assertEqual(len(rules), 4)
        self.assertIn("IP-CIDR6,2607:6bc0::/48,no-resolve", rules)

    def test_invalid_classical_rules_rejected(self):
        for line in ("MATCH,DIRECT", "DOMAIN,claude.ai,DIRECT", "DOMAIN-KEYWORD,",
                     "DOMAIN,192.168.9.1", "IP-CIDR,0.0.0.0/0", "IP-CIDR,10.0.0.0/8",
                     "IP-CIDR,2607:6bc0::/48", "IP-CIDR,160.79.104.10/23",
                     "IP-CIDR,160.79.104.10", "IP-CIDR,160.79.104.0/23,DIRECT"):
            with self.subTest(line=line), self.assertRaises(ValueError):
                updater.parse_rules(line)

    def test_initial_migration_preserves_manual_and_voice_rules(self):
        for newline in ("\n", "\r\n"):
            voice_block = newline.join([voice.START, "# Source: official",
                                       "IP-CIDR,4.1.1.1/32,no-resolve", voice.END])
            manual = newline.join(["# auxiliary", "DOMAIN,cdn.growthbook.io",
                                   "IP-CIDR,160.79.104.0/23,no-resolve",
                                   "DOMAIN-SUFFIX,gemini.google.com", voice_block]) + newline
            current = newline.join(["DOMAIN-SUFFIX,chat.openai.com", "# 内容：Claude",
                                    *sorted(updater.LEGACY_CORE_RULES), manual])
            result = updater.render_ai(current, updater.parse_rules(COMMUNITY, geosite=True))
            self.assertTrue(result.startswith("DOMAIN-SUFFIX,chat.openai.com" + newline))
            self.assertIn(manual, result)
            self.assertEqual(result.splitlines().count("DOMAIN-SUFFIX,claude.ai"), 1)
            self.assertNotIn("DOMAIN-SUFFIX,clau.de", result)
            self.assertEqual(updater.render_ai(result, updater.parse_rules(COMMUNITY, geosite=True)), result)

    def test_refresh_removes_stale_auto_rules_and_preserves_outside_bytes(self):
        before, after = "# before\r\nDOMAIN,manual.example.com\r\n", "\r\n# after\r\n"
        current = before + updater.START + "\r\nDOMAIN,old.example.com\r\n" + updater.END + after
        rules = updater.parse_rules(COMMUNITY, geosite=True)
        result = updater.render_ai(current, rules)
        self.assertTrue(result.startswith(before))
        self.assertTrue(result.endswith(after))
        self.assertNotIn("old.example.com", result)
        self.assertIn("new.claude.dev", result)

    def test_new_community_entry_does_not_duplicate_manual_rule(self):
        current = "DOMAIN,cdn.example.com\n" + updater.START + "\n" + updater.END + "\n"
        result = updater.render_ai(current, updater.parse_rules(COMMUNITY, geosite=True))
        self.assertEqual(result.splitlines().count("DOMAIN,cdn.example.com"), 1)

    def test_malformed_markers_rejected(self):
        for current in (updater.START, updater.END, updater.END + "\n" + updater.START,
                        (updater.START + "\n" + updater.END + "\n") * 2):
            with self.subTest(current=current), self.assertRaises(ValueError):
                updater.render_ai(current, ["DOMAIN-SUFFIX,claude.ai"])

    def test_voice_and_claude_updates_commute(self):
        current = "DOMAIN-SUFFIX,claude.ai\nDOMAIN-SUFFIX,gemini.google.com\n"
        claude_rules = updater.parse_rules(COMMUNITY, geosite=True)
        voice_rules = ["IP-CIDR,4.1.1.1/32,no-resolve"]
        first = updater.render_ai(voice.render_rules(current, voice_rules), claude_rules)
        second = voice.render_rules(updater.render_ai(current, claude_rules), voice_rules)
        # Initial appended block positions can differ; subsequent updates preserve both.
        self.assertEqual(set(first.splitlines()), set(second.splitlines()))
        self.assertEqual(updater.render_ai(first, claude_rules), first)
        self.assertEqual(voice.render_rules(first, voice_rules), first)

    def test_unchanged_merge_keeps_timestamp_and_updated_merge_lists_sources(self):
        rules = updater.parse_rules(CLASSICAL)
        sources = (*updater.ACL_SOURCES, updater.CLAUDE_SOURCE)
        first = updater.render_merged("", rules, sources)
        self.assertEqual(updater.render_merged(first, rules, sources), first)
        self.assertIn(f"# 来源5：{updater.CLAUDE_SOURCE}", first)
        updated = updater.render_merged(first, sorted([*rules, "DOMAIN,new.example.com"]), sources)
        self.assertIn("# 数量：3条", updated)

    def test_download_and_validation_failures_retain_both_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            ai, merged = Path(directory) / "AI.list", Path(directory) / "AIMerged.list"
            original_ai, original_merged = b"DOMAIN-SUFFIX,claude.ai\n", b"# previous merged\n"
            for kind in ("download", "html", "partial", "markers"):
                ai.write_bytes(original_ai if kind != "markers" else updater.START.encode())
                merged.write_bytes(original_merged)
                saved_ai = ai.read_bytes()

                def broken(url):
                    if url == updater.CLAUDE_SOURCE:
                        if kind == "download":
                            raise OSError("network unavailable")
                        if kind == "html":
                            return "<html>Bad Gateway</html>"
                    if kind == "partial" and url == updater.ACL_SOURCES[1]:
                        return "# empty upstream"
                    return feed(url)

                with self.subTest(kind=kind), patch.object(updater, "fetch", side_effect=broken):
                    with self.assertRaises((OSError, ValueError)):
                        updater.update_files(ai, merged)
                self.assertEqual(ai.read_bytes(), saved_ai)
                self.assertEqual(merged.read_bytes(), original_merged)

    def test_successful_update_is_idempotent_and_write_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            ai, merged = Path(directory) / "AI.list", Path(directory) / "AIMerged.list"
            ai.write_bytes(b"DOMAIN-SUFFIX,claude.ai\r\n")
            merged.write_bytes(b"# old\n")
            saved = (ai.read_bytes(), merged.read_bytes())
            original_replace = updater.os.replace
            count = 0

            def fail_second_replace(source, target):
                nonlocal count
                count += 1
                if count == 2:
                    raise OSError("second replace failed")
                original_replace(source, target)

            with patch.object(updater, "fetch", side_effect=feed):
                with patch.object(updater.os, "replace", side_effect=fail_second_replace):
                    with self.assertRaises(OSError):
                        updater.update_files(ai, merged)
                self.assertEqual((ai.read_bytes(), merged.read_bytes()), saved)
                self.assertEqual(set(Path(directory).iterdir()), {ai, merged})
                self.assertEqual(updater.update_files(ai, merged)[0], 4)
                self.assertEqual(updater.update_files(ai, merged), (4, []))

    def test_outputs_cannot_overlap(self):
        with self.assertRaises(ValueError):
            updater.update_files(Path("same.list"), Path("same.list"))


if __name__ == "__main__":
    unittest.main()
