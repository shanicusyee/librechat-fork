"""Pipeline configuration sourced from environment variables."""

import os
from dataclasses import dataclass


@dataclass
class PipelineConfig:
    """Configuration for the Evidence Agent pipeline.

    All required fields must be provided via environment variables.
    Optional fields have sensible defaults.
    """

    app_url: str
    s3_bucket: str
    run_id: str
    aws_region: str
    connection_timeout: int = 60
    max_upload_retries: int = 3

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Create a PipelineConfig from environment variables.

        Required env vars:
            APP_URL          - Deployed application URL
            S3_BUCKET        - Evidence S3 bucket name
            GITHUB_RUN_ID    - GitHub Actions run ID
            AWS_REGION       - AWS region

        Optional env vars:
            CONNECTION_TIMEOUT   - AgentCore Browser timeout in seconds (default: 60)
            MAX_UPLOAD_RETRIES   - S3 upload retry count (default: 3)

        Raises:
            ValueError: If any required environment variable is missing.
        """
        required = {
            "APP_URL": "app_url",
            "S3_BUCKET": "s3_bucket",
            "GITHUB_RUN_ID": "run_id",
            "AWS_REGION": "aws_region",
        }

        missing = [var for var in required if not os.environ.get(var)]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(sorted(missing))}. "
                "Set these variables before running the Evidence Agent."
            )

        connection_timeout = int(os.environ.get("CONNECTION_TIMEOUT", "60"))
        max_upload_retries = int(os.environ.get("MAX_UPLOAD_RETRIES", "3"))

        return cls(
            app_url=os.environ["APP_URL"],
            s3_bucket=os.environ["S3_BUCKET"],
            run_id=os.environ["GITHUB_RUN_ID"],
            aws_region=os.environ["AWS_REGION"],
            connection_timeout=connection_timeout,
            max_upload_retries=max_upload_retries,
        )
