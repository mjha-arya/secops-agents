"""dspm.posture adapter over a real control-tool run (dbSAT slice 1, item 9).

The fixture run is produced once in setUpClass by `ctl.orchestrator.run_pipeline`
into a temp directory (%TEMP%, outside OneDrive). Needs CTL_ROOT pointing at
the control tool folder; without it every test errors, loudly, by design.

    CTL_ROOT="<controlTool abs path>" python -m unittest discover -s dspm/tests -v
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))    # myAgents root

from dspm.posture import adapter                                 # noqa: E402

ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"
BUCKETS = {"compliant", "deviation", "prerequisite-gap", "procedural", "unknown"}


def snapshot(root: Path) -> dict[str, tuple[int, int]]:
    return {str(p): (p.stat().st_size, p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


class PostureAdapter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ctl_root = adapter.load_ctl()
        from ctl import orchestrator, registry
        from ctl.collectors import FixtureBackend

        cls.registry_dir = cls.ctl_root / "registry"
        cls.reg = registry.load(cls.registry_dir)
        cls.tmp = Path(tempfile.mkdtemp(prefix="dspmPostureAdapter-"))
        backend = FixtureBackend.load(cls.ctl_root / "fixtures" / "demo")
        # not `cls.run`: that shadows TestCase.run and breaks collection
        cls.pipeline_run = orchestrator.run_pipeline(cls.tmp, cls.reg, backend, offline=True)
        cls.run_dir = cls.pipeline_run.dir
        cls.record = adapter.read_run(cls.run_dir, cls.registry_dir, account_id=ACCOUNT_ID)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def copy_run(self) -> Path:
        target = Path(tempfile.mkdtemp(prefix="dspmPostureAdapterCopy-")) / self.run_dir.name
        shutil.copytree(self.run_dir, target)
        self.addCleanup(shutil.rmtree, target.parent, True)
        return target

    def edit_findings(self, run_dir: Path, change) -> None:
        path = run_dir / "findings.json"
        findings = json.loads(path.read_text(encoding="utf-8"))
        change(findings)
        path.write_text(json.dumps(findings, indent=2), encoding="utf-8")

    # --- dbSat-1.7 ---------------------------------------------------

    def test_every_deviation_carries_its_evidence_fields(self):
        deviations = [r for r in self.record.findings if r.status == "deviation"]
        self.assertTrue(deviations)
        for r in deviations:
            with self.subTest(check=r.check_id, scope=r.scope_id):
                for name in ("check_id", "refs", "severity", "scope_id", "observed",
                             "desired", "method", "registry_version", "evidence_sha256"):
                    self.assertTrue(getattr(r, name), name)
                self.assertEqual(r.refs, (r.check_id,))
                if r.scope_type == "workspace":
                    self.assertTrue(r.workspace)

    # --- dbSat-1.8 (S5) ----------------------------------------------

    def test_per_account_checks_are_one_record_per_check_and_run(self):
        per_account = {c.id for c in self.reg for d in c.detect if d.scope == "per-account"}
        account_records = [r for r in self.record.findings if r.scope_type == "account"]
        self.assertTrue(account_records)
        for check in sorted({r.check_id for r in account_records}):
            with self.subTest(check=check):
                self.assertIn(check, per_account)
                mine = [r for r in account_records if r.check_id == check]
                self.assertEqual(len(mine), 1)
                self.assertEqual(mine[0].scope_id, ACCOUNT_ID)
                self.assertIsNone(mine[0].workspace)
        self.assertNotIn("account", {r.scope_id for r in self.record.findings})

    def test_scopes_map_to_ids_never_to_names(self):
        by_name = {w.name: w.workspace_id for w in self.reg.governed_workspaces()}
        for r in self.record.findings:
            with self.subTest(check=r.check_id, scope=r.scope_type):
                if r.scope_type == "workspace":
                    self.assertEqual(r.scope_id, by_name[r.workspace])
                elif r.scope_type == "metastore":
                    self.assertEqual(r.scope_id, "00000000-0000-0000-0000-00000000demo")
                else:
                    self.assertIn(r.scope_type, ("account", "estate"))
                    self.assertEqual(r.scope_id, ACCOUNT_ID)
                    self.assertIsNone(r.workspace)
                if r.scope_type == "estate":
                    self.assertIsNone(r.collected_at)
                else:
                    self.assertRegex(r.collected_at, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    # --- no loss, no percentage --------------------------------------

    def test_record_count_and_buckets_match_the_run(self):
        from ctl.models import Finding
        from ctl.stages.assess import summarise

        run_findings = self.pipeline_run.artifacts["findings"]
        self.assertEqual(len(self.record.findings), len(run_findings))
        as_findings = [Finding(control=r.check_id, title="", scope=f"{r.scope_type}:{r.scope_id}",
                               status=r.status) for r in self.record.findings]
        rolled = summarise(as_findings)["by_status"]
        self.assertEqual(rolled, summarise(run_findings)["by_status"])
        self.assertEqual(rolled, {"compliant": 16, "deviation": 7, "prerequisite-gap": 4,
                                  "procedural": 1, "unknown": 3})
        self.assertTrue({r.status for r in self.record.findings} <= BUCKETS)

    def test_no_percentage_field_anywhere(self):
        for cls in (adapter.FindingRecord, adapter.RunRecord):
            for f in dataclasses.fields(cls):
                for word in ("percent", "pct", "ratio", "coverage", "score"):
                    self.assertNotIn(word, f.name.lower(), f"{cls.__name__}.{f.name}")

    def test_run_record_header(self):
        self.assertEqual(self.record.run_id, self.pipeline_run.run_id)
        self.assertEqual(self.record.estate, "fixture")
        self.assertEqual(self.record.registry_version, self.reg.version)
        self.assertEqual(self.record.account_id, ACCOUNT_ID)

    # --- evidence hash ------------------------------------------------

    def test_every_record_verifies(self):
        for r in self.record.findings:
            self.assertTrue(adapter.verify_evidence(self.run_dir, r), r.check_id)

    def test_hash_matches_the_control_tools_own_evidence_pack(self):
        """Mirrored, not imported (the hash is inline in evidence_pack), so compare them."""
        from ctl.stages import report

        out = Path(tempfile.mkdtemp(prefix="dspmEvidencePack-"))
        self.addCleanup(shutil.rmtree, out, True)
        discovery = self.pipeline_run.artifacts["discovery"]
        report.evidence_pack(self.reg, self.pipeline_run.artifacts["findings"],
                             discovery.observations, out)
        stored = json.loads((out / "SEC-06.json").read_text(encoding="utf-8"))
        sha = stored.pop("sha256")
        self.assertEqual(adapter.evidence_hash(stored), sha)

    def test_flipped_byte_in_evidence_rejects_the_run(self):
        run_dir = self.copy_run()
        path = run_dir / "evidence" / "SEC-06.json"
        data = bytearray(path.read_bytes())
        at = data.index(b'"title": "') + len(b'"title": "')
        data[at] ^= 0x20                     # flip case: still valid JSON
        path.write_bytes(bytes(data))
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.read_run(run_dir, self.registry_dir, account_id=ACCOUNT_ID)
        self.assertIn("SEC-06", str(caught.exception))

    # --- whole-run rejection -----------------------------------------

    def test_unmapped_account_scope_rejects_the_run(self):
        env = {k: v for k, v in os.environ.items() if k != "DATABRICKS_ACCOUNT_ID"}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(adapter.AdapterError) as caught:
                adapter.read_run(self.run_dir, self.registry_dir)
        self.assertIn("account", str(caught.exception))

    def test_account_id_falls_back_to_the_environment(self):
        with mock.patch.dict(os.environ, {"DATABRICKS_ACCOUNT_ID": ACCOUNT_ID}):
            record = adapter.read_run(self.run_dir, self.registry_dir)
        self.assertEqual(record.account_id, ACCOUNT_ID)

    def test_status_outside_the_five_buckets_rejects_the_run(self):
        run_dir = self.copy_run()

        def green(findings):
            findings[0]["status"] = "green"
        self.edit_findings(run_dir, green)
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.read_run(run_dir, self.registry_dir, account_id=ACCOUNT_ID)
        self.assertIn("green", str(caught.exception))

    def test_status_that_disagrees_with_the_hashed_evidence_rejects_the_run(self):
        """findings.json is not hashed; a deviation edited to compliant must not publish."""
        run_dir = self.copy_run()

        def whitewash(findings):
            next(f for f in findings if f["status"] == "deviation")["status"] = "compliant"
        self.edit_findings(run_dir, whitewash)
        with self.assertRaises(adapter.AdapterError):
            adapter.read_run(run_dir, self.registry_dir, account_id=ACCOUNT_ID)

    # --- completeness (F1): findings.json is not hashed -----------------

    def test_deleted_finding_rejects_the_run(self):
        """A deviation dropped from findings.json leaves a smaller run whose counts add up."""
        run_dir = self.copy_run()
        dropped = {}

        def drop(findings):
            i = next(i for i, f in enumerate(findings) if f["status"] == "deviation")
            dropped.update(findings.pop(i))
        self.edit_findings(run_dir, drop)
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.read_run(run_dir, self.registry_dir, account_id=ACCOUNT_ID)
        self.assertIn(dropped["control"], str(caught.exception))
        self.assertIn(dropped["scope"], str(caught.exception))

    def test_duplicate_scope_rejects_the_run(self):
        run_dir = self.copy_run()
        duplicated = {}

        def duplicate(findings):
            duplicated.update(next(f for f in findings if f["status"] == "deviation"))
            findings.append(dict(duplicated))
        self.edit_findings(run_dir, duplicate)
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.read_run(run_dir, self.registry_dir, account_id=ACCOUNT_ID)
        self.assertIn("duplicate", str(caught.exception))
        self.assertIn(duplicated["control"], str(caught.exception))
        self.assertIn(duplicated["scope"], str(caught.exception))

    def test_stray_evidence_file_rejects_the_run(self):
        run_dir = self.copy_run()
        shutil.copy(run_dir / "evidence" / "SEC-06.json", run_dir / "evidence" / "SEC-98.json")
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.read_run(run_dir, self.registry_dir, account_id=ACCOUNT_ID)
        self.assertIn("SEC-98", str(caught.exception))

    def test_control_dropped_with_its_evidence_rejects_the_run(self):
        """Every registry control gets a finding (ctl assess), so a whole control
        missing from both findings.json and evidence\\ is an omission too."""
        run_dir = self.copy_run()
        self.edit_findings(run_dir, lambda findings: findings.__setitem__(
            slice(None), [f for f in findings if f["control"] != "SEC-06"]))
        (run_dir / "evidence" / "SEC-06.json").unlink()
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.read_run(run_dir, self.registry_dir, account_id=ACCOUNT_ID)
        self.assertIn("SEC-06", str(caught.exception))

    def test_control_not_in_the_registry_rejects_the_run(self):
        run_dir = self.copy_run()

        def rename(findings):
            findings[0]["control"] = "SEC-99"
        self.edit_findings(run_dir, rename)
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.read_run(run_dir, self.registry_dir, account_id=ACCOUNT_ID)
        self.assertIn("SEC-99", str(caught.exception))

    def test_missing_or_unparseable_artifact_rejects_the_run(self):
        for name, action in (("state.json", "delete"), ("findings.json", "corrupt"),
                             ("evidence/SEC-01.json", "delete")):
            with self.subTest(artifact=name, action=action):
                run_dir = self.copy_run()
                path = run_dir / name
                if action == "delete":
                    path.unlink()
                else:
                    path.write_text("{not json", encoding="utf-8")
                with self.assertRaises(adapter.AdapterError):
                    adapter.read_run(run_dir, self.registry_dir, account_id=ACCOUNT_ID)

    def test_live_run_is_marked_live(self):
        run_dir = self.copy_run()
        (run_dir / "requests.json").write_text("[]", encoding="utf-8")
        record = adapter.read_run(run_dir, self.registry_dir, account_id=ACCOUNT_ID)
        self.assertEqual(record.estate, "live")

    def test_reading_writes_nothing(self):
        before = snapshot(self.run_dir)
        adapter.read_run(self.run_dir, self.registry_dir, account_id=ACCOUNT_ID)
        self.assertEqual(snapshot(self.run_dir), before)

    # --- finding ctl --------------------------------------------------

    def test_ctl_root_unset_or_invalid_is_an_adapter_error(self):
        for value in (None, str(self.tmp / "no-such-tool")):
            with self.subTest(value=value):
                env = {k: v for k, v in os.environ.items() if k != "CTL_ROOT"}
                if value is not None:
                    env["CTL_ROOT"] = value
                with mock.patch.dict(os.environ, env, clear=True):
                    with self.assertRaises(adapter.AdapterError) as caught:
                        adapter.load_ctl()
                self.assertIn("CTL_ROOT", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
