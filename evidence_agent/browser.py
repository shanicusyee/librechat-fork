"""AgentCore Browser session management for the Evidence Agent.

Provides a context manager that creates a managed browser session via
Amazon Bedrock AgentCore Browser, connects Playwright over CDP, and
yields a ready-to-use Page object.
"""

import logging
from contextlib import contextmanager

from bedrock_agentcore.tools.browser_client import browser_session
from playwright.sync_api import sync_playwright, BrowserType

logger = logging.getLogger(__name__)


class BrowserConnectionError(Exception):
    """Raised when the browser session fails to connect."""

    def __init__(self, url: str, timeout: int, cause: Exception | None = None):
        self.url = url
        self.timeout = timeout
        self.cause = cause
        message = f"Failed to connect to {url} within {timeout}s"
        if cause:
            message += f": {cause}"
        super().__init__(message)


@contextmanager
def create_browser_session(app_url: str, timeout: int = 60, region: str = "ap-southeast-1"):
    """Create an AgentCore Browser session and yield a Playwright Page.

    Args:
        app_url: The deployed application URL to navigate to.
        timeout: Connection timeout in seconds (default 60).
        region: AWS region for the browser session.

    Yields:
        playwright.sync_api.Page connected to the AgentCore Browser session.

    Raises:
        BrowserConnectionError: If the browser cannot connect within timeout.
    """
    playwright_instance = None
    browser = None

    try:
        with browser_session(region) as client:
            ws_url, headers = client.generate_ws_headers()
            logger.info("AgentCore Browser session created, connecting Playwright via CDP")

            playwright_instance = sync_playwright().start()
            chromium: BrowserType = playwright_instance.chromium
            browser = chromium.connect_over_cdp(ws_url, headers=headers)

            context = browser.contexts[0]
            page = context.pages[0]

            page.set_default_timeout(timeout * 1000)
            page.set_default_navigation_timeout(timeout * 1000)

            logger.info("Navigating to %s (timeout=%ds)", app_url, timeout)
            page.goto(app_url, wait_until="load", timeout=timeout * 1000)
            logger.info("Successfully connected to %s", app_url)

            yield page

    except Exception as exc:
        logger.error("Browser session failed: %s", exc)
        raise BrowserConnectionError(app_url, timeout, cause=exc) from exc

    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if playwright_instance:
            try:
                playwright_instance.stop()
            except Exception:
                pass
