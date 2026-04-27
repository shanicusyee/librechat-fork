"""Basic tests for evidence_agent.artifacts module."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from evidence_agent.artifacts import (
    ArtifactEntry,
    build_s3_key_prefix,
    build_summary_log,
    generate_manifest,
    upload_with_retry,
)


class TestBuildS3KeyPrefix:
    def test_basic_format(self):
        ts = datetime(2025, 1, 15, 10, 30, 0)
        result = build_s3_key_prefix("12345", ts)
        assert result == "evidence/12345/2025-01-15T10:30:00/"

    def test_ends_with_slash(self):
        ts = datetime(2025, 6, 1, 0, 0, 0)
        result = build_s3_key_prefix("run-abc", ts)
        assert result.endswith("/")

    def test_starts_with_evidence(self):
        ts = datetime(2025, 1, 1)
        result = build_s3_key_prefix("x", ts)
        assert result.startswith("evidence/")


class TestGenerateManifest:
    def _make_artifact(self, name, artifact_type, size=100):
        return ArtifactEntry(
            name=name,
            s3_key=f"evidence/run1/ts/{name}",
            artifact_type=artifact_type,
            capture_timestamp=datetime(2025, 1, 15, 10, 30, 0),
            file_size_bytes=size,
            content=b"x" * size,
        )

    def test_empty_artifacts(self):
        result = generate_manifest([], "run1", datetime(2025, 1, 15))
        assert result["artifacts"] == []
        assert result["summary"]["total_artifacts"] == 0

    def test_counts_by_type(self):
        artifacts = [
            self._make_artifact("a.png", "screenshot"),
            self._make_artifact("b.png", "screenshot"),
            self._make_artifact("report.xml", "test_report"),
        ]
        result = generate_manifest(artifacts, "run1", datetime(2025, 1, 15))
        assert result["summary"]["total_screenshots"] == 2
        assert result["summary"]["total_reports"] == 1
        assert result["summary"]["total_artifacts"] == 3

    def test_artifact_fields_match(self):
        art = self._make_artifact("login.png", "screenshot", 500)
        result = generate_manifest([art], "run1", datetime(2025, 1, 15))
        entry = result["artifacts"][0]
        assert entry["name"] == "login.png"
        assert entry["type"] == "screenshot"
        assert entry["file_size_bytes"] == 500


class TestBuildSummaryLog:
    def test_mixed_types(self):
        artifacts = [
            ArtifactEntry("a.png", "k", "screenshot", datetime(2025, 1, 1), 1, b""),
            ArtifactEntry("b.xml", "k", "test_report", datetime(2025, 1, 1), 1, b""),
        ]
        result = build_summary_log(artifacts)
        assert result["screenshot_count"] == 1
        assert result["report_count"] == 1

    def test_empty(self):
        result = build_summary_log([])
        assert result["screenshot_count"] == 0
        assert result["report_count"] == 0


class TestUploadWithRetry:
    def test_success_first_attempt(self):
        client = MagicMock()
        upload_with_retry(client, "bucket", "key", b"data", max_retries=3)
        assert client.put_object.call_count == 1

    def test_raises_after_max_retries(self):
        client = MagicMock()
        client.put_object.side_effect = Exception("fail")
        with pytest.raises(Exception, match="fail"):
            upload_with_retry(
                client, "bucket", "key", b"data", max_retries=1, base_delay=0.01
            )
        assert client.put_object.call_count == 2  # initial + 1 retry
