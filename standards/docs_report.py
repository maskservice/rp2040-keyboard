"""Documentation adapter: verify published copies before invoking upstream validators."""

import json
import importlib.util
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

DOCS_REVISION = "6f475fb223e7a259d514b5483fb0d62f0e80a46e"
REPORT_REVISION = "3eafc9c212bbfd4060fe15b63eb97e4614725234"
ARTIFACTS = {
    "docs": {
        "docs/standard/" + name
        for name in (
            "check.py",
            "policy.json",
            "change_contract.py",
            "policy-dsl.lock.json",
        )
    },
    "report": {
        "operations/conformance.py",
        "models/report-manifest.schema.json",
        "models/acceptance.schema.json",
    },
}


def verify(root, entries):
    import hashlib

    for name, revision in [("docs", DOCS_REVISION), ("report", REPORT_REVISION)]:
        entry = entries["wellmanifest/" + name]
        if (
            entry.get("sourceRevision") != revision
            or entry.get("status") != "published"
            or entry.get("sourceRepository")
            != "https://github.com/wellmanifest/" + name
        ):
            raise RuntimeError("Untrusted published pin: " + name)
        artifacts = entry.get("artifacts", [])
        if (
            len(artifacts) != len(ARTIFACTS[name])
            or {a.get("sourcePath") for a in artifacts} != ARTIFACTS[name]
        ):
            raise RuntimeError("Incomplete artifact inventory: " + name)
        for item in artifacts:
            relative = (
                ".governance/wellmanifest/docs/"
                if name == "docs"
                else "standards/report/"
            ) + item["sourcePath"]
            if item.get("targetPath") != relative:
                raise RuntimeError("Unexpected artifact target")
            current = root
            for part in Path(relative).parts:
                current /= part
                if current.is_symlink():
                    raise RuntimeError("Symlinked standard artifact")
            if hashlib.sha256(current.read_bytes()).hexdigest() != item.get("sha256"):
                raise RuntimeError("Standard artifact digest mismatch")


def checker_environment(root):
    environment = os.environ.copy()
    identity = environment.get("ONEDEV_PR_REPOSITORY")
    if identity is None:
        return environment
    base = environment.get("ONEDEV_PR_MAIN_SHA", "")
    if identity != "maskservice/displaynet" or not re.fullmatch("[0-9a-f]{40}", base):
        raise RuntimeError(
            "Docs requires the exact authenticated OneDev job identity and base"
        )
    subprocess.run(["git", "cat-file", "-e", base + "^{commit}"], cwd=root, check=True)
    mirror = subprocess.check_output(
        ["git", "remote", "get-url", "origin"], cwd=root, text=True
    ).strip()
    if not mirror:
        raise RuntimeError("OneDev mirror origin is missing")
    count = int(environment.get("GIT_CONFIG_COUNT", "0"))
    if not 0 <= count <= 256:
        raise RuntimeError("Invalid inherited Git configuration")
    # Same read-only URL mapping as OneDev's protected documentation adapter.
    # The authenticated job supplies identity; do not rewrite the candidate Git config.
    environment["GIT_CONFIG_COUNT"] = str(count + 1)
    environment[f"GIT_CONFIG_KEY_{count}"] = (
        "url.https://github.com/" + identity + ".git.insteadOf"
    )
    environment[f"GIT_CONFIG_VALUE_{count}"] = mirror
    return environment


def run_json(root, script, *args):
    environment = checker_environment(root)
    interpreter = sys.executable
    if (
        script == "standards/report/operations/conformance.py"
        and importlib.util.find_spec("jsonschema") is None
    ):
        # Report validation is an infrastructure check, not an application
        # dependency. Use the trusted system runtime when the product runtime
        # does not provide the schema library (as in the protected OneDev job).
        if Path("/usr/local/bin/python").is_file():
            interpreter = "/usr/local/bin/python"
        else:
            raise RuntimeError("Trusted schema runtime is unavailable")
    result = subprocess.run(
        [interpreter, str(root / script), *args],
        cwd=root,
        capture_output=True,
        text=True,
        env=environment,
    )
    if result.returncode:
        raise RuntimeError(result.stdout or "Upstream validator failed: " + script)
    return json.loads(result.stdout)


def check(
    root, entries, base, deliverable=None, prepared_plan=None, managed_copies=None
):
    verify(root, entries)
    if not re.fullmatch("[0-9a-f]{40}", base):
        raise RuntimeError("Trusted base must be a full commit SHA")

    def git_paths(*args):
        return set(
            subprocess.check_output(["git", *args, "-z"], cwd=root).decode().split("\0")
        ) - {""}

    tracked = git_paths("ls-files")
    changed = git_paths("diff", "--name-only", "--diff-filter=ACMR", base)
    reports = {p for p in tracked if p.endswith(".report.json")}
    for path in changed | ({deliverable} if deliverable else set()):
        if path.startswith("docs/analysis/") and path.endswith(".md"):
            if str(Path(path).with_suffix(".report.json")) not in reports:
                raise RuntimeError(
                    "Analysis requires a tracked Report sidecar: " + path
                )
    report_results = [
        run_json(
            root,
            "standards/report/operations/conformance.py",
            str(root / p),
            "--root",
            str(root),
        )
        for p in sorted(reports)
    ]
    args = ["--root", str(root), "--standard-revision", DOCS_REVISION, "--base", base]
    if deliverable:
        args += [
            "--complete",
            "--deliverable",
            deliverable,
            "--prepared-plan",
            str(prepared_plan.resolve()),
        ]
    import tempfile

    # The caller verifies the whole new-project adoption before supplying this map.
    # Keep the exact upstream inventory input in private local storage, not docs.
    receipts = root / ".subactor/receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="docs-check-", dir=receipts) as temporary:
        inventory = Path(temporary) / "managed-copies.json"
        if managed_copies is None:
            # Standard-managed .governance/docs copies are declared by the
            # tracked Wellmanifest inventory; they are not repository documents.
            inventory_path = root / ".governance" / "managed-copies.json"
            managed_copies = (
                json.loads(inventory_path.read_text()) if inventory_path.is_file() else {}
            )
        inventory.write_text(json.dumps(managed_copies))
        args += ["--managed-copies", str(inventory)]
        docs = run_json(
            root, ".governance/wellmanifest/docs/docs/standard/check.py", *args
        )
    return {
        "docs": docs,
        "reports": report_results,
        "publication_verified": False,
        "authority": "none",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    parser.add_argument("--complete", action="store_true")
    parser.add_argument("--deliverable")
    parser.add_argument("--prepared-plan", type=Path)
    args = parser.parse_args()
    if (
        args.complete != bool(args.deliverable and args.prepared_plan)
        or (not args.complete and (args.deliverable or args.prepared_plan))
        or (args.complete and not args.base)
    ):
        parser.error("--complete requires --base, --deliverable and --prepared-plan")
    root = Path(__file__).resolve().parents[1]
    try:
        lock = json.loads((root / "standards/standards-lock.json").read_text())
        entries = {entry["id"]: entry for entry in lock["standards"]}
        if (
            lock.get("schema") != "wellmanifest.documentation-pins/v1"
            or len(lock["standards"]) != 2
            or set(entries) != {"wellmanifest/docs", "wellmanifest/report"}
        ):
            raise RuntimeError("Unexpected documentation pin inventory")
        base = args.base or os.environ.get("WELLMANIFEST_BASE_SHA") or subprocess.check_output(
            ["git", "merge-base", "HEAD", "refs/remotes/origin/main"],
            cwd=root,
            text=True,
        ).strip()
        result = check(root, entries, base, args.deliverable, args.prepared_plan)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1
    print(json.dumps({"ok": True, **result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
