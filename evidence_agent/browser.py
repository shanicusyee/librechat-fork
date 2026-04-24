"""AgentCore Browser session management for the Evidence Agent.

Provides a context manager that creates a managed browser session via
Amazon Bedrock AgentCore Browser, connects Playwright over CDP, and
yields a ready-to-use Page object. Handles connection timeouts with
structured logging and proper resource cleanup.
"""

import logging
import sys
from contextlib import contextmanager

from bedrock_agentcore.tools.browser_client import browser_session
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class BrowserConnectionError(Exception):
    """Raised when the browser session fails to connect to the target application."""

    def __init__(self, url: str, timeout: int, cause: Exception | None = None):
        self.url = url
        self.timeout = timeout
        self.cause = cause
        message = (
            f"Failed to connect to {url} within {timeout}s"
        )
        if cause:
            message += f": {cause}"
        super().__init__(message)


@contextmanager
def create_browser_session(app_url: str, timeout: int = 60):
    """Create an AgentCore Browser session and yield a Playwright Page.

    Opens a managed browser session via the bedrock-agentcore SDK,
    connects Playwright over CDP, navigates to ``app_url``, and yields
    the Page object for screenshot capture.

    Args:
        app_url: The deployed application URL to navigate to.
        timeout: Connection timeout in seconds (default 60).

    Yields:
        playwright.sync_api.Page: A Playwright page connected to the
        AgentCore Browser session, already navigated to ``app_url``.

    Raises:
        BrowserConnectionError: If the browser cannot connect or navigate
            to the application within the timeout period.
    """
    playwright = None
    browser = None

    try:
        with browser_session() as session:
            logger.info("AgentCore Browser session created, connecting Playwright via CDP")
            playwright = sync_playwright().start()
            browser = playwright.chromium.connect_over_cdp(session.cdp_endpoint)
            context = browser.contexts[0]
            page = context.pages[0]

            page.set_default_timeout(timeout * 1000)
            page.set_default_navigation_timeout(timeout * 1000)

            logger.info("Navigating to %s (timeout=%ds)", app_url, timeout)
            page.goto(app_url, wait_until="load", timeout=timeout * 1000)
            logger.info("Successfully connected to %s", app_url)

            yield page

    except (PlaywrightTimeoutError, TimeoutError) as exc:
        logger.error(
            "Connection timeout: failed to reach %s within %ds",
            app_url,
            timeout,
        )
        # Attempt error-state screenshot if page is available
        try:
            if browser and browser.contexts and browser.contexts[0].pages:
                error_page = browser.contexts[0].pages[0]
                error_page.screenshot(path="error-state.png", full_page=True)
                logger.info("Captured error-state screenshot to error-state.png")
        except Exception as screenshot_err:
            logger.warning("Could not capture error-state screenshot: %s", screenshot_err)

        raise BrowserConnectionError(app_url, timeout, cause=exc) from exc

    except Exception as exc:
        logger.error("Browser session failed: %s", exc)
        raise

    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if playwright:
            try:
                playwright.stop()
            except Exception:
                pass
