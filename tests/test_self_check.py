from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SELF_CHECK = ROOT / "scripts/self_check.py"


class SelfCheckTests(unittest.TestCase):
    def test_self_check_json_reports_required_and_optional_checks(self):
        with tempfile.TemporaryDirectory() as temporary:
            binary_directory = Path(temporary)
            codex = binary_directory / "codex"
            codex.write_text(
                "#!/bin/sh\nprintf '%s\\n' 'codex-cli 0.144.6'\n",
                encoding="utf-8",
            )
            codex.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = (
                str(binary_directory)
                + os.pathsep
                + environment.get("PATH", "")
            )
            result = subprocess.run(
                [sys.executable, str(SELF_CHECK), "--json", "--project-root", str(ROOT)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=20,
                env=environment,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        checks = json.loads(result.stdout)["checks"]
        by_name = {item["name"]: item for item in checks}
        self.assertEqual(by_name["plugin"]["status"], "pass")
        self.assertEqual(by_name["templates"]["status"], "pass")
        self.assertIn("optional:latexmk", by_name)
        self.assertFalse(any(item["status"] == "error" for item in checks))

    def test_schema_rejects_unknown_fields_and_invalid_versions(self):
        schema = json.loads((ROOT / "schemas/plugin.schema.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        invalid = dict(manifest, unknown=True, version="v0.5.0")
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(invalid))
        self.assertGreaterEqual(len(errors), 2)


if __name__ == "__main__":
    unittest.main()
