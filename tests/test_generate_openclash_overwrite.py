from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts import generate_openclash_overwrite as generator


TEMPLATE = (generator.ROOT / "openclash/overwrite.template.conf").read_text()
SOURCE = """
secret: must-not-publish
proxy-providers:
  private:
    url: https://private.example/subscription?token=must-not-publish
dns:
  respect-rules: true
  fake-ip-range: 198.18.0.0/15
  nameserver-policy:
    rule-set:Custom_AI: ['https://1.1.1.1/dns-query#🤖 AI节点']
sniffer:
  enable: true
  override-destination: false
  skip-domain: ['+.push.apple.com']
tun:
  dns-hijack: ['any:53', 'tcp://any:53']
  route-exclude-address: ['17.249.0.0/16', '192.168.0.0/16']
"""


class OpenClashGenerationTests(unittest.TestCase):
    def patch_data(self, module):
        return yaml.safe_load(module.split("[YAML]\n", 1)[1])

    def test_only_adaptation_fields_are_distributed(self):
        module, bypass = generator.render(SOURCE, TEMPLATE, "224.0.0.0/4\n")
        self.assertNotIn("must-not-publish", module + bypass)
        self.assertNotIn("private.example", module + bypass)
        self.assertEqual(self.patch_data(module)["dns"]["nameserver-policy!"],
                         yaml.safe_load(SOURCE)["dns"]["nameserver-policy"])
        self.assertNotIn("listen!", self.patch_data(module)["dns"])
        self.assertNotIn("[Overwrite]", module)
        self.assertIn("force=false", module)
        self.assertIn("ENABLE_RESPECT_RULES = 1", module)

    def test_source_changes_propagate_without_manual_copies(self):
        config = yaml.safe_load(SOURCE)
        config["sniffer"]["skip-domain"].append("+.new.example")
        config["tun"]["route-exclude-address"].append("17.252.0.0/16")
        config["dns"]["respect-rules"] = False
        module, bypass = generator.render(yaml.safe_dump(config), TEMPLATE, "")
        data = self.patch_data(module)
        self.assertEqual(data["sniffer!"], config["sniffer"])
        self.assertEqual(data["dns"]["respect-rules!"], False)
        self.assertIn("ENABLE_RESPECT_RULES = 0", module)
        self.assertIn("17.252.0.0/16\n", bypass)
        self.assertEqual(data["tun"]["dns-hijack"],
                         ["127.0.0.1:53", "any:53", "tcp://any:53"])

    def test_legacy_proxy_dns_policy_cannot_override_source(self):
        module, _ = generator.render(SOURCE, TEMPLATE, "")
        self.assertIn("proxy-server-nameserver-policy", self.patch_data(module)["dns-"])
        config = yaml.safe_load(SOURCE)
        policy = {"+.example.com": ["https://223.5.5.5/dns-query#DIRECT"]}
        config["dns"]["proxy-server-nameserver-policy"] = policy
        module, _ = generator.render(yaml.safe_dump(config), TEMPLATE, "")
        self.assertNotIn("proxy-server-nameserver-policy", self.patch_data(module)["dns-"])
        self.assertEqual(self.patch_data(module)["dns"]["proxy-server-nameserver-policy!"], policy)

    def test_fake_ip_overlap_and_invalid_ranges_rejected(self):
        for extra in ["198.18.0.0/16", "0.0.0.0/0", "invalid", "999.1.1.1/24", "::/0"]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                generator.render(SOURCE, TEMPLATE, extra)
        with self.assertRaises(ValueError):
            generator.render(SOURCE.replace("17.249.0.0/16", "198.18.1.0/24"), TEMPLATE, "")

    def test_native_parser_environment_expansion_is_not_silent(self):
        with self.assertRaisesRegex(ValueError, "expands"):
            generator.render(SOURCE.replace("+.push.apple.com", "^example$"), TEMPLATE, "")

    def fixture(self, root):
        directory = root / "openclash"
        directory.mkdir()
        (root / "mihomo.yaml").write_text(SOURCE)
        (directory / "overwrite.template.conf").write_text(TEMPLATE)
        (directory / "bypass_extra_ipv4.list").write_text("224.0.0.0/4\n")

    def test_check_mode_and_repeated_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            with self.assertRaisesRegex(ValueError, "stale"):
                generator.generate(root, check=True)
            self.assertEqual(len(generator.generate(root)), 2)
            before = {p: p.stat().st_mtime_ns for p in (root / "openclash").iterdir()}
            self.assertEqual(generator.generate(root), [])
            self.assertEqual(generator.generate(root, check=True), [])
            self.assertEqual(before, {p: p.stat().st_mtime_ns for p in before})

    def test_validation_and_write_failure_preserve_previous_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            generator.generate(root)
            paths = [root / "openclash" / name for name in ("overwrite.conf", "bypass_ipv4.list")]
            original = [p.read_bytes() for p in paths]
            (root / "openclash/bypass_extra_ipv4.list").write_text("198.18.0.0/16\n")
            with self.assertRaises(ValueError):
                generator.generate(root)
            self.assertEqual(original, [p.read_bytes() for p in paths])
            (root / "openclash/bypass_extra_ipv4.list").write_text("240.0.0.0/4\n")
            (root / "mihomo.yaml").write_text(SOURCE.replace("+.push.apple.com", "+.new.example"))
            replace = generator.os.replace
            count = 0

            def fail_second(source, destination):
                nonlocal count
                count += 1
                if count == 2:
                    raise OSError("simulated disk error")
                replace(source, destination)

            with patch.object(generator.os, "replace", side_effect=fail_second):
                with self.assertRaises(OSError):
                    generator.generate(root)
            self.assertEqual(original, [p.read_bytes() for p in paths])
            self.assertFalse(list((root / "openclash").glob(".openclash-*")))


if __name__ == "__main__":
    unittest.main()
