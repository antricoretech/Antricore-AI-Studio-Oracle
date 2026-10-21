#!/usr/bin/env python3
"""Optional Playwright smoke test for the rendered dashboard shell."""

from __future__ import annotations

import argparse
import sys


AXE_URL = "https://cdn.jsdelivr.net/npm/axe-core@4.10.2/axe.min.js"


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
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(args.url, wait_until="networkidle", timeout=30000)
            assert page.locator(".brand-title h1").is_visible(), "legacy brand is not visible"
            assert page.locator("#global-persona-select").is_visible(), "legacy persona selector is not visible"
            assert page.locator("a[href='/workspace']").is_visible(), "canonical workspace bridge is not visible"
            canonical_targets = {
                "personas": "/workspace#personas",
                "production": "/workspace#production",
                "content-packs": "/workspace#content-packs",
                "assets": "/workspace#assets",
                "overview": "/workspace#overview",
            }
            active_persona_id = page.locator("#global-persona-select").input_value()
            assert active_persona_id, "legacy active persona selector did not resolve"
            for target, href in canonical_targets.items():
                bridge = page.locator(f"a[data-canonical-target='{target}']")
                assert bridge.count() == 1, f"missing legacy-to-canonical bridge: {target}"
                expected_href = href.replace('/workspace', f'/workspace?persona_id={active_persona_id}')
                assert bridge.get_attribute("href") == expected_href, f"incorrect canonical bridge target: {target}"
            tab_targets = {
                "#nav-btn-vault": "#tab-vault",
                "#nav-btn-orchestrator": "#tab-orchestrator",
                "#nav-btn-story": "#tab-story",
                "#nav-btn-gallery": "#tab-gallery",
                "#nav-btn-telemetry": "#tab-telemetry",
            }
            for button_selector, panel_selector in tab_targets.items():
                button = page.locator(button_selector)
                assert button.count() == 1, f"missing legacy navigation item: {button_selector}"
                button.click()
                assert page.locator(panel_selector).is_visible(), f"legacy panel did not mount: {panel_selector}"
            page.locator("#nav-btn-vault").click()
            assert page.locator("#tab-vault").is_visible(), "legacy shell did not return to the vault"
            page.add_script_tag(url=AXE_URL)
            result = page.evaluate("""async () => await axe.run(document, {
                runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] }
            })""")
            assert not result["violations"], f"legacy axe violations: {[item['id'] for item in result['violations']]}"
            tree = page.context.new_cdp_session(page).send("Accessibility.getFullAXTree")["nodes"]
            roles = {node.get("role", {}).get("value") for node in tree}
            assert "main" in roles and "navigation" in roles and "heading" in roles, "legacy accessibility tree landmarks are incomplete"
            assert not errors, errors
            browser.close()
    except Exception as exc:
        print(f"Browser smoke test failed: {exc}", file=sys.stderr)
        return 1
    print("Browser smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
