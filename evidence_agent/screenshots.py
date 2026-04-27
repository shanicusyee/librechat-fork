"""Screenshot capture for the Evidence Agent.

Provides functions to capture full-page screenshots of application pages
using a Playwright page object. Handles individual page failures gracefully,
logging each failure and continuing to remaining pages without short-circuiting.
"""

import logging
from datetime import datetime, timezone

from playwright.sync_api import Error as PlaywrightError

from evidence_agent.artifacts import ScreenshotResult

logger = logging.getLogger(__name__)

DEFAULT_PAGES_CONFIG: list[dict[str, str | None]] = [
    {"name": "login-page", "url": None},
    {"name": "chat-interface", "url": "/c/new"},
]


def capture_page_screenshot(page, page_name: str, url: str | None = None) -> ScreenshotResult:
    """Navigate to a page (if URL provided) and capture a full-page screenshot.

    If ``url`` is provided and is a relative path, it is resolved against the
    page's current origin. If ``url`` is ``None``, the screenshot is taken of
    the current page state without navigation.

    Args:
        page: Playwright Page object.
        page_name: Human-readable name for the page (e.g. "login-page").
        url: Optional URL to navigate to before capturing. ``None`` means
            capture the current page as-is.

    Returns:
        ScreenshotResult with PNG image data on success, or an error message
        on failure.
    """
    try:
        if url is not None:
            # Resolve relative URLs against the current page origin
            if url.startswith("/"):
                origin = page.evaluate("() => window.location.origin")
                full_url = f"{origin}{url}"
            else:
                full_url = url
            logger.info("Navigating to %s for screenshot '%s'", full_url, page_name)
            page.goto(full_url, wait_until="load")

        logger.info("Capturing screenshot '%s'", page_name)
        image_data = page.screenshot(full_page=True, type="png")

        logger.info(
            "Screenshot '%s' captured (%d bytes)", page_name, len(image_data)
        )
        return ScreenshotResult(
            page_name=page_name,
            success=True,
            image_data=image_data,
            error_message=None,
            capture_timestamp=datetime.now(timezone.utc),
        )

    except (PlaywrightError, Exception) as exc:
        error_msg = f"Failed to capture screenshot '{page_name}': {exc}"
        logger.error(error_msg)
        return ScreenshotResult(
            page_name=page_name,
            success=False,
            image_data=None,
            error_message=error_msg,
            capture_timestamp=datetime.now(timezone.utc),
        )


def capture_all_screenshots(
    page, pages_config: list[dict[str, str | None]] | None = None
) -> list[ScreenshotResult]:
    """Capture screenshots for all configured pages.

    Iterates through every page in ``pages_config``, capturing a screenshot
    for each. Individual failures are logged but do **not** short-circuit
    the loop — all remaining pages are still attempted.

    Args:
        page: Playwright Page object.
        pages_config: List of dicts with ``"name"`` and ``"url"`` keys.
            Defaults to :data:`DEFAULT_PAGES_CONFIG` when ``None``.

    Returns:
        List of :class:`ScreenshotResult` objects, one per page in
        ``pages_config``, preserving order.
    """
    if pages_config is None:
        pages_config = DEFAULT_PAGES_CONFIG

    results: list[ScreenshotResult] = []

    for page_cfg in pages_config:
        name = page_cfg["name"]
        url = page_cfg.get("url")
        result = capture_page_screenshot(page, name, url=url)
        results.append(result)

        if not result.success:
            logger.warning(
                "Screenshot failed for '%s': %s — continuing to next page",
                name,
                result.error_message,
            )

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    logger.info(
        "Screenshot capture complete: %d succeeded, %d failed out of %d pages",
        successful,
        failed,
        len(results),
    )

    return results
