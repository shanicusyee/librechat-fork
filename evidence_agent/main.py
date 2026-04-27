"""Evidence Agent main orchestrator.

Loads configuration, creates an AgentCore Browser session, captures
screenshots, collects the test report, generates a JSON manifest,
uploads all artifacts to S3, and logs a summary.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone

import boto3

from evidence_agent.artifacts import (
    ArtifactEntry,
    build_s3_key_prefix,
    build_summary_log,
    generate_manifest,
    upload_with_retry,
)
from evidence_agent.browser import BrowserConnectionError, create_browser_session
from evidence_agent.config import PipelineConfig
from evidence_agent.screenshots import capture_all_screenshots

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _collect_test_report(report_path: str) -> bytes | None:
    """Read the test report file from disk.

    Args:
        report_path: Path to the test report file.

    Returns:
        File contents as bytes, or ``None`` if the file is missing.
    """
    if not os.path.isfile(report_path):
        logger.warning("Test report not found at %s — proceeding without it", report_path)
        return None

    with open(report_path, "rb") as f:
        data = f.read()
    logger.info("Collected test report from %s (%d bytes)", report_path, len(data))
    return data


def main() -> None:
    """Run the Evidence Agent pipeline."""
    # --- 1. Load configuration ---
    try:
        config = PipelineConfig.from_env()
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    logger.info(
        "Evidence Agent starting — app_url=%s, s3_bucket=%s, run_id=%s",
        config.app_url,
        config.s3_bucket,
        config.run_id,
    )

    now = datetime.now(timezone.utc)
    s3_prefix = build_s3_key_prefix(config.run_id, now)
    artifacts: list[ArtifactEntry] = []

    # --- 2. Browser session: capture screenshots ---
    try:
        with create_browser_session(config.app_url, timeout=config.connection_timeout, region=config.aws_region) as page:
            from evidence_agent.screenshots import capture_page_screenshot
            screenshot_results = []

            # 2a. Login page screenshot
            login_screenshot = capture_page_screenshot(page, "login-page")
            screenshot_results.append(login_screenshot)

            # 2b. Log in with demo user
            try:
                page.fill('input[name="email"]', 'demo@example.com')
                page.fill('input[name="password"]', 'demodemo123')
                page.click('button[type="submit"]')
                page.wait_for_url("**/c/**", timeout=30000)
                page.wait_for_timeout(3000)
                logger.info("Logged in as demo user")
            except Exception as login_err:
                logger.warning("Login failed: %s", login_err)

            # 2c. Chat interface screenshot (empty state)
            chat_screenshot = capture_page_screenshot(page, "chat-interface")
            screenshot_results.append(chat_screenshot)

            # 2d. Model selector screenshot — click the model dropdown
            try:
                # LibreChat model selector is typically in the header/nav area
                model_btn = page.locator('[data-testid="model-selector"], button:has-text("Claude"), button:has-text("Nova"), [class*="model"]').first
                if model_btn.is_visible(timeout=5000):
                    model_btn.click()
                    page.wait_for_timeout(1000)
                    model_selector_screenshot = capture_page_screenshot(page, "model-selector")
                    screenshot_results.append(model_selector_screenshot)
                    # Close dropdown by pressing Escape
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
                else:
                    logger.warning("Model selector not found, skipping screenshot")
            except Exception as model_err:
                logger.warning("Model selector screenshot failed: %s", model_err)

            # 2e. Test Claude model — send a message and capture response
            try:
                logger.info("Testing Claude model — sending message")
                textarea = page.locator('textarea[placeholder*="Message"], textarea[id="prompt-textarea"], textarea').first
                textarea.fill("Hello! What model are you? Reply in one short sentence.")
                textarea.press("Enter")
                # Wait for response to appear
                page.wait_for_timeout(15000)
                claude_screenshot = capture_page_screenshot(page, "claude-response")
                screenshot_results.append(claude_screenshot)
                logger.info("Claude response captured")
            except Exception as claude_err:
                logger.warning("Claude test failed: %s", claude_err)

            # 2f. New chat + test Nova model
            try:
                logger.info("Starting new chat for Nova model test")
                # Click new chat button
                new_chat_btn = page.locator('a[href="/c/new"], button[aria-label*="New"], nav a:first-child').first
                if new_chat_btn.is_visible(timeout=5000):
                    new_chat_btn.click()
                    page.wait_for_timeout(2000)

                # Try to switch model to Nova
                model_btn = page.locator('[data-testid="model-selector"], button:has-text("Claude"), button:has-text("Nova"), [class*="model"]').first
                if model_btn.is_visible(timeout=5000):
                    model_btn.click()
                    page.wait_for_timeout(1000)
                    # Look for Nova option
                    nova_option = page.locator('text=Nova').first
                    if nova_option.is_visible(timeout=3000):
                        nova_option.click()
                        page.wait_for_timeout(1000)
                        logger.info("Switched to Nova model")

                # Send message to Nova
                textarea = page.locator('textarea[placeholder*="Message"], textarea[id="prompt-textarea"], textarea').first
                textarea.fill("What is 2+2? Reply in one short sentence.")
                textarea.press("Enter")
                page.wait_for_timeout(15000)
                nova_screenshot = capture_page_screenshot(page, "nova-response")
                screenshot_results.append(nova_screenshot)
                logger.info("Nova response captured")
            except Exception as nova_err:
                logger.warning("Nova test failed: %s", nova_err)

    except BrowserConnectionError as exc:
        logger.error("Browser connection failed: %s", exc)
        sys.exit(1)

    for result in screenshot_results:
        if result.success and result.image_data:
            s3_key = f"{s3_prefix}screenshots/{result.page_name}.png"
            artifacts.append(
                ArtifactEntry(
                    name=f"{result.page_name}.png",
                    s3_key=s3_key,
                    artifact_type="screenshot",
                    capture_timestamp=result.capture_timestamp,
                    file_size_bytes=len(result.image_data),
                    content=result.image_data,
                )
            )

    # --- 3. Collect test report ---
    report_path = os.environ.get("TEST_REPORT_PATH", "test-results/report.xml")
    report_data = _collect_test_report(report_path)

    if report_data is not None:
        report_name = os.path.basename(report_path)
        s3_key = f"{s3_prefix}reports/{report_name}"
        artifacts.append(
            ArtifactEntry(
                name=report_name,
                s3_key=s3_key,
                artifact_type="test_report",
                capture_timestamp=now,
                file_size_bytes=len(report_data),
                content=report_data,
            )
        )

    # --- 4. Generate manifest ---
    manifest_dict = generate_manifest(artifacts, pipeline_run_id=config.run_id, timestamp=now)
    manifest_bytes = json.dumps(manifest_dict, indent=2).encode("utf-8")
    manifest_s3_key = f"{s3_prefix}manifest.json"

    manifest_entry = ArtifactEntry(
        name="manifest.json",
        s3_key=manifest_s3_key,
        artifact_type="manifest",
        capture_timestamp=now,
        file_size_bytes=len(manifest_bytes),
        content=manifest_bytes,
    )
    artifacts.append(manifest_entry)

    # --- 5. Upload all artifacts to S3 ---
    s3_client = boto3.client("s3", region_name=config.aws_region)
    upload_failures = 0

    for artifact in artifacts:
        try:
            upload_with_retry(
                s3_client,
                config.s3_bucket,
                artifact.s3_key,
                artifact.content,
                max_retries=config.max_upload_retries,
            )
            logger.info("Uploaded %s → s3://%s/%s", artifact.name, config.s3_bucket, artifact.s3_key)
        except Exception as exc:
            logger.error("Failed to upload %s after retries: %s", artifact.name, exc)
            upload_failures += 1

    if upload_failures == len(artifacts):
        logger.error("All artifact uploads failed — exiting with error")
        sys.exit(1)

    # --- 6. Log summary ---
    summary = build_summary_log(artifacts)
    s3_uri = f"s3://{config.s3_bucket}/{s3_prefix}"

    logger.info(
        "Evidence collection complete — screenshots=%d, reports=%d, s3_uri=%s",
        summary["screenshot_count"],
        summary["report_count"],
        s3_uri,
    )

    # Print S3 URI for GitHub Actions job log
    print(f"\n✅ Evidence artifacts uploaded to: {s3_uri}")


if __name__ == "__main__":
    main()
