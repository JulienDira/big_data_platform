import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "infra/scripts/aws-runtime-validate.py"
SPEC = importlib.util.spec_from_file_location("aws_runtime_validate", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeRunner:
    def __init__(self):
        self.commands = []

    def run(self, args, **kwargs):
        self.commands.append((args, kwargs))
        return MODULE.CommandResult(stdout="", stderr="", returncode=0)


class AwsRuntimeValidationTest(unittest.TestCase):
    def test_cleanup_scales_down_ecs_and_stops_raw_streaming(self):
        runner = FakeRunner()
        validator = MODULE.RuntimeValidator(
            repo_root=ROOT,
            artifact_version="abc123",
            evidence_path=ROOT / "build/test-evidence.json",
            runner=runner,
            sleeper=lambda seconds: None,
        )
        validator.ecs_cluster_name = "cluster"
        validator.ecs_service_name = "service"
        validator.raw_streaming_job_name = "raw-job"
        validator.raw_streaming_run_id = "raw-run"

        validator.cleanup()

        commands = [" ".join(args) for args, _kwargs in runner.commands]
        self.assertIn(
            "aws ecs update-service --cluster cluster --service service --desired-count 0",
            commands,
        )
        self.assertIn(
            "aws glue batch-stop-job-run --job-name raw-job --job-run-ids raw-run",
            commands,
        )
        self.assertEqual(
            ["ecs_desired_count_zero", "raw_streaming_stopped"],
            [item["name"] for item in validator.evidence["cleanup"]],
        )

    def test_dry_run_writes_evidence_without_subprocess_calls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            evidence_path = Path(temp_dir) / "evidence.json"
            with patch.dict(os.environ, {"ARTIFACT_VERSION": "abc123"}):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "aws-runtime-validate.py",
                        "--dry-run",
                        "--evidence-file",
                        str(evidence_path),
                    ],
                ):
                    MODULE.main()

            evidence = MODULE.json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual("dry_run", evidence["status"])
            self.assertEqual("abc123", evidence["artifact_version"])
            self.assertEqual("dry_run", evidence["checks"][0]["name"])

    def test_parse_s3_uri(self):
        self.assertEqual(
            ("bucket-name", "prefix/path"),
            MODULE.parse_s3_uri("s3://bucket-name/prefix/path"),
        )


if __name__ == "__main__":
    unittest.main()
