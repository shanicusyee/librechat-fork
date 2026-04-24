"""Data models and core functions for evidence artifact management.

Provides dataclasses for artifact entries, manifests, and screenshot results,
along with S3 key formatting, manifest generation, and upload-with-retry logic.
"""

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ScreenshotResult:
    """Outcome of a screenshot capture attempt."""

    page_name: str
    success: bool
    image_data: bytes | None
    error_message: str | None
    capture_timestamp: datetime


@dataclass
class ArtifactEntry:
    """A single evidence artifact collected during a pipeline run."""

    name: str
    s3_key: str
    artifact_type: str  # "screenshot" | "test_report" | "manifest"
    capture_timestamp: datetime
    file_size_bytes: int
    content: bytes  # Raw file content (not persisted in manifest)


@dataclass
class ManifestSummary:
    """Summary counts for a manifest."""

    total_screenshots: int
    total_reports: int
    total_artifacts: int


@dataclass
class Manifest:
    """JSON manifest uploaded alongside artifacts."""

    pipeline_run_id: str
    timestamp: datetime
    artifacts: list[ArtifactEntry]
    summary: ManifestSummary


def build_s3_key_prefix(run_id: str, timestamp: datetime) -> str:
    """Build S3 key prefix: evidence/{run_id}/{iso_timestamp}/

    Args:
        run_id: Pipeline run identifier.
        timestamp: Pipeline run timestamp.

    Returns:
        S3 key prefix string ending with '/'.
    """
    iso_timestamp = timestamp.isoformat()
    return f"evidence/{run_id}/{iso_timestamp}/"


def generate_manifest(
    artifacts: list[ArtifactEntry],
    pipeline_run_id: str = "",
    timestamp: datetime | None = None,
) -> dict:
    """Generate a JSON-serializable manifest dict from artifact entries.

    Produces a manifest with artifact metadata and summary counts matching
    the manifest schema: pipeline_run_id, timestamp, artifacts, and summary.
    The 'content' field of each ArtifactEntry is excluded from the output.

    Args:
        artifacts: List of artifact entries to include in the manifest.
        pipeline_run_id: Pipeline run identifier.
        timestamp: Pipeline run timestamp (defaults to now if not provided).

    Returns:
        Dictionary representing the manifest, ready for JSON serialization.
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    total_screenshots = sum(
        1 for a in artifacts if a.artifact_type == "screenshot"
    )
    total_reports = sum(
        1 for a in artifacts if a.artifact_type == "test_report"
    )

    artifact_dicts = [
        {
            "name": a.name,
            "s3_key": a.s3_key,
            "type": a.artifact_type,
            "capture_timestamp": a.capture_timestamp.isoformat(),
            "file_size_bytes": a.file_size_bytes,
        }
        for a in artifacts
    ]

    return {
        "pipeline_run_id": pipeline_run_id,
        "timestamp": timestamp.isoformat(),
        "artifacts": artifact_dicts,
        "summary": {
            "total_screenshots": total_screenshots,
            "total_reports": total_reports,
            "total_artifacts": len(artifacts),
        },
    }


def build_summary_log(artifacts: list[ArtifactEntry]) -> dict:
    """Build a summary dict for pipeline logging.

    Args:
        artifacts: List of artifact entries to summarize.

    Returns:
        Dictionary with screenshot_count and report_count.
    """
    screenshot_count = sum(
        1 for a in artifacts if a.artifact_type == "screenshot"
    )
    report_count = sum(
        1 for a in artifacts if a.artifact_type == "test_report"
    )
    return {
        "screenshot_count": screenshot_count,
        "report_count": report_count,
    }


def upload_with_retry(
    s3_client,
    bucket: str,
    key: str,
    body: bytes,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> None:
    """Upload to S3 with exponential backoff and jitter.

    Args:
        s3_client: Boto3 S3 client.
        bucket: S3 bucket name.
        key: S3 object key.
        body: File content as bytes.
        max_retries: Maximum number of retry attempts (default 3).
        base_delay: Base delay in seconds for backoff calculation.

    Raises:
        Exception: Re-raises the last exception if all retries are exhausted.
    """
    for attempt in range(max_retries + 1):
        try:
            s3_client.put_object(Bucket=bucket, Key=key, Body=body)
            return
        except Exception as e:
            if attempt == max_retries:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
            logger.warning(
                "Upload failed (attempt %d/%d): %s. Retrying in %.1fs",
                attempt + 1,
                max_retries + 1,
                e,
                delay,
            )
            time.sleep(delay)
