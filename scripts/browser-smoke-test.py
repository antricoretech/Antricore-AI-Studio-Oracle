#!/usr/bin/env python3
"""Optional Playwright smoke test for the rendered dashboard shell."""

from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run a non-destructive browser smoke test")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args(argv)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Install requirements-browser.txt first.", file=sys.stderr)
        return 2

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(args.url, wait_until="networkidle", timeout=30000)
            assert page.locator(".brand").is_visible(), "brand is not visible"
            assert page.locator("#dashboard").is_visible(), "dashboard is not visible"
            for key in ("persona-library", "generation-brief", "workflow-manager", "monitoring"):
                button = page.locator(f'[data-nav-key="{key}"]').first
                assert button.count() == 1, f"missing navigation item: {key}"
                button.click()
                assert page.locator("#page-title").inner_text(), f"page title did not update for {key}"
            page.locator('[data-nav-key="monitoring"]').click()
            page.wait_for_timeout(500)
            assert page.locator("#monitor-overview").is_visible(), "monitoring view did not mount"
            browser.close()
    except Exception as exc:
        print(f"Browser smoke test failed: {exc}", file=sys.stderr)
        return 1
    print("Browser smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
