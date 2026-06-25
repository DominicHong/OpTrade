"""Thin wrappers around Playwright for the chinamoney crawler.

Verified against the actual chinamoney page DOM (2026-06-24):
  https://www.chinamoney.com.cn/chinese/bkcurvuiruuh/

Element IDs:
  Date inputs:     #iuir-curv-his-start-date, #iuir-curv-his-end-date
  Currency select: #iuir-curv-his-curr    (options: 全部, USD.CNY, EUR.CNY, ...)
  RMB rate select: #iuir-curv-his-rmb-rate  (options: 全部, Shibor, Shibor3M..., FR007...)
  Spot select:     #iuir-curv-his-spot    (options: 全部, 即期询价报价均值, 中间价)
  Swap select:     #iuir-curv-his-bp      (options: 全部, 掉期点)
  Export button:   a.san-btn-primary:has-text("导出Excel")

The date inputs are *readonly* and use jQuery UI datepicker, so we set
their values via page.evaluate() + dispatch change events.
"""

from __future__ import annotations

import logging
from datetime import date

from playwright.async_api import Browser, Page, async_playwright

logger = logging.getLogger("optrade.crawler.playwright")

# Page URL (verified working)
_PAGE_URL = "https://www.chinamoney.com.cn/chinese/bkcurvuiruuh/"

# === Known element IDs (verified 2026-06-24) ===
_ID_START_DATE = "iuir-curv-his-start-date"
_ID_END_DATE = "iuir-curv-his-end-date"
_ID_CURRENCY = "iuir-curv-his-curr"
_ID_RMB_RATE = "iuir-curv-his-rmb-rate"
_ID_SPOT = "iuir-curv-his-spot"
_ID_SWAP = "iuir-curv-his-bp"


# ---------------------------------------------------------------------------
# Browser management
# ---------------------------------------------------------------------------


async def launch_browser(headless: bool = True) -> tuple[Browser, "async_playwright"]:
    """Launch MS Edge (or Chromium fallback) via Playwright.

    Returns a ``(browser, playwright)`` tuple.  The caller **must** call
    ``await browser.close()`` followed by ``await playwright.stop()`` to
    release all subprocess resources cleanly.
    """
    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.launch(
            channel="msedge",
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
    except Exception:
        logger.warning("msedge channel failed – falling back to bundled chromium")
        browser = await pw.chromium.launch(headless=headless)
    return browser, pw


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------


async def navigate_to_page(page: Page) -> str:
    """Navigate to the chinamoney curve page.  Returns the URL used."""
    resp = await page.goto(_PAGE_URL, wait_until="domcontentloaded", timeout=30_000)
    if not resp or not resp.ok:
        raise RuntimeError(f"Failed to load {_PAGE_URL}: status={resp.status if resp else 'N/A'}")
    logger.info("Navigated to: %s", _PAGE_URL)
    return _PAGE_URL


async def wait_for_page_ready(page: Page) -> None:
    """Wait for the page to settle (network idle + extra settle time)."""
    try:
        await page.wait_for_load_state("networkidle", timeout=15_000)
    except Exception:
        logger.debug("networkidle timed out — continuing")
    await page.wait_for_timeout(2_000)
    logger.debug("Page ready — title: %s", await page.title())


# ---------------------------------------------------------------------------
# Form interaction
# ---------------------------------------------------------------------------


async def set_date_range(page: Page, date_from: date, date_to: date) -> None:
    """Set the start/end date fields.

    These inputs are readonly (jQuery UI datepicker), so we set values
    via JavaScript and dispatch change events.
    """
    start_str = date_from.strftime("%Y-%m-%d")
    end_str = date_to.strftime("%Y-%m-%d")

    await page.evaluate(
        f"""
        (function() {{
            var s = document.getElementById('{_ID_START_DATE}');
            var e = document.getElementById('{_ID_END_DATE}');
            if (s && e) {{
                s.value = '{start_str}';
                e.value = '{end_str}';
                s.dispatchEvent(new Event('change', {{bubbles: true}}));
                e.dispatchEvent(new Event('change', {{bubbles: true}}));
                s.dispatchEvent(new Event('input', {{bubbles: true}}));
                e.dispatchEvent(new Event('input', {{bubbles: true}}));
            }}
        }})();
        """
    )
    logger.debug("Date range set: %s → %s", start_str, end_str)
    await page.wait_for_timeout(800)


async def set_dropdowns(
    page: Page,
    *,
    currency: str = "全部",
    rmb_rate: str = "FR007利率互换收盘曲线",
    spot: str = "即期询价报价均值",
    swap: str = "掉期点",
) -> None:
    """Set each dropdown to the desired value using exact element IDs."""
    settings = [
        (_ID_RMB_RATE, rmb_rate),
        (_ID_CURRENCY, currency),
        (_ID_SPOT, spot),
        (_ID_SWAP, swap),
    ]
    for select_id, label in settings:
        await page.select_option(f"#{select_id}", label=label)
        logger.debug("Dropdown #%s → %s", select_id, label)
        await page.wait_for_timeout(400)

    # Extra wait for any JS callbacks after selection changes.
    await page.wait_for_timeout(1_500)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


async def click_export_button(page: Page) -> None:
    """Click the '导出Excel' link.

    The button is an ``<a>`` tag with class ``san-btn-primary``.
    """
    btn = page.locator("a:has-text(\"导出Excel\")")
    count = await btn.count()
    if count == 0:
        raise RuntimeError(
            "Cannot find '导出Excel' button on chinamoney page. "
            "The page structure may have changed."
        )
    await btn.first.click()
    logger.debug("Clicked export button")
