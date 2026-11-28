"""Tests for .claude/hooks/block-installer.py."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "block-installer.py"


class BlockInstallerTest(unittest.TestCase):
    def run_hook(self, payload):
        return subprocess.run(
            [sys.executable, "-I", str(HOOK)],
            input=payload,
            capture_output=True,
            text=True,
        )

    def check_command(self, command):
        return self.run_hook(json.dumps({"tool_input": {"command": command}}))

    def test_blocks_installer_runs(self):
        blocked = [
            "./install-macos.sh",
            "./install-macos.sh latest",
            "bash install-macos.sh",
            "sh ./install-macos.sh",
            "zsh install-macos.sh",
            ". ./install-macos.sh",
            "source install-macos.sh",
            "sudo ./install-macos.sh",
            "env -u FOO bash install-macos.sh",
            "bash install-macos.sh -n",
            "bash ./install-macos.sh -n",
            "bash -o nounset install-macos.sh",
            "bash -c './install-macos.sh'",
            "bash -lc './install-macos.sh'",
            "bash -c -- './install-macos.sh'",
            "sh -ec 'bash install-macos.sh'",
            "bash < install-macos.sh",
            "cat install-macos.sh | bash",
            "bash -s arg < install-macos.sh",
            'echo "$(./install-macos.sh)"',
            "eval ./install-macos.sh",
        ]
        for cmd in blocked:
            with self.subTest(cmd=cmd):
                res = self.check_command(cmd)
                self.assertEqual(res.returncode, 2, f"not blocked: {cmd}")
                self.assertIn("Blocked:", res.stderr)

    def test_allows_safe_commands(self):
        allowed = [
            "bash -n install-macos.sh",
            "sh -n ./install-macos.sh",
            "shellcheck install-macos.sh",
            "cat install-macos.sh",
            "git diff install-macos.sh",
            "python3 -I build.py examples/joe-hudson",
        ]
        for cmd in allowed:
            with self.subTest(cmd=cmd):
                res = self.check_command(cmd)
                self.assertEqual(res.returncode, 0, f"unexpectedly blocked: {cmd}: {res.stderr}")

    def test_malformed_input_fails_closed(self):
        res = self.run_hook("not json")
        self.assertEqual(res.returncode, 2)


if __name__ == "__main__":
    unittest.main()
