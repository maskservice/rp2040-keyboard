"""Regression tests for the pinned Docs and Report adapter."""

import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "docs_report_adapter", ROOT / "standards/docs_report.py"
)
adapter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(adapter)


class DocumentationAdapterTests(unittest.TestCase):
    """Keep immutable pins and real local Report bytes under test."""

    repository = "maskservice/" + ROOT.name

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(ROOT / ".governance/wellmanifest/docs", self.root / ".governance/wellmanifest/docs")
        shutil.copytree(ROOT / "standards/report", self.root / "standards/report")
        lock = json.loads((ROOT / "standards/standards-lock.json").read_text())
        self.entries = {entry["id"]: entry for entry in lock["standards"]}

    def test_published_artifacts_match_the_lock(self):
        adapter.verify(self.root, self.entries)

    def test_untrusted_pin_is_rejected(self):
        entries = copy.deepcopy(self.entries)
        entries["wellmanifest/docs"]["sourceRevision"] = "main"
        with self.assertRaises(RuntimeError):
            adapter.verify(self.root, entries)

    def test_incomplete_report_inventory_is_rejected(self):
        entries = copy.deepcopy(self.entries)
        entries["wellmanifest/report"]["artifacts"].pop()
        with self.assertRaises(RuntimeError):
            adapter.verify(self.root, entries)

    def test_report_validation_reads_actual_document_bytes(self):
        schema = json.loads(
            (self.root / "standards/report/models/report-manifest.schema.json").read_text()
        )
        manifest = copy.deepcopy(schema["examples"][0])
        manifest["owner"] = self.repository
        manifest["scope"]["repositories"] = [self.repository]
        manifest["scope"]["subjects"][0]["repository"] = self.repository

        document_path = self.root / manifest["document"]["path"]
        document_path.parent.mkdir(parents=True)
        document_path.write_text("# Synthetic report fixture\n")
        manifest["document"]["sha256"] = hashlib.sha256(
            document_path.read_bytes()
        ).hexdigest()
        sidecar = self.root / Path(manifest["document"]["path"]).with_suffix(
            ".report.json"
        )
        sidecar.write_text(json.dumps(manifest))
        index = self.root / manifest["document"]["index_path"]
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_text("[Report](analysis/example-report.md)\n")

        for command in (
            ("git", "init", "-q"),
            ("git", "config", "user.name", "Docs tests"),
            ("git", "config", "user.email", "docs-tests@example.invalid"),
            ("git", "remote", "add", "origin", "https://github.com/" + self.repository + ".git"),
            ("git", "add", "."),
            ("git", "commit", "-qm", "fixture"),
        ):
            subprocess.run(command, cwd=self.root, check=True)

        result = adapter.run_json(
            self.root,
            "standards/report/operations/conformance.py",
            str(sidecar),
            "--root",
            str(self.root),
        )
        self.assertTrue(result["local_artifacts_verified"])

        document_path.write_text("# Tampered report\n")
        with self.assertRaises(RuntimeError):
            adapter.run_json(
                self.root,
                "standards/report/operations/conformance.py",
                str(sidecar),
                "--root",
                str(self.root),
            )


class ManagedCopyInventoryTests(unittest.TestCase):
    """Standard-managed .governance/docs copies are declared, not documents."""

    def run_check(self, inventory):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / ".governance").mkdir()
            if inventory is not None:
                (root / ".governance/managed-copies.json").write_text(json.dumps(inventory))
            (root / "README.md").write_text("x\n")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
                           cwd=root, check=True)
            base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            seen = []

            def run_json(_root, script, *args):
                seen.append(json.loads(Path(args[args.index("--managed-copies") + 1]).read_text()))
                return {"ok": True}

            original = (adapter.verify, adapter.run_json)
            adapter.verify, adapter.run_json = (lambda *_: None), run_json
            try:
                adapter.check(root, {}, base)
            finally:
                adapter.verify, adapter.run_json = original
            return seen[-1]

    def test_tracked_inventory_is_passed_to_the_docs_checker(self):
        inventory = {".governance/docs/SNAPSHOT_MIGRATION.md": "0" * 64}
        self.assertEqual(self.run_check(inventory), inventory)

    def test_missing_inventory_passes_an_empty_map(self):
        self.assertEqual(self.run_check(None), {})


if __name__ == "__main__":
    unittest.main()
