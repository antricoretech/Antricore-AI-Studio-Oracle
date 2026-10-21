#!/usr/bin/env python3
"""Non-destructive responsive and accessibility smoke test for /workspace."""

from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate canonical workspace responsive and keyboard states")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args(argv)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Install requirements-browser.txt first.", file=sys.stderr)
        return 2

    persona = {"id": "fixture-persona", "name": "Fixture Persona", "current_version": {"id": "fixture-version", "state": "frozen"}}
    reference_pack = {
        "id": "fixture-pack",
        "name": "Fixture Identity Core",
        "pack_type": "identity",
        "content_class": "identity",
        "persona_version_id": "fixture-version",
        "identity_authority": "identity",
        "review": "approved",
        "canonical_selected": 0,
        "items": [],
    }
    content_pack = {
        "id": "fixture-content-pack",
        "name": "Fixture ContentPack",
        "content_class": "adult_glamour",
        "persona_version_id": "fixture-version",
        "review": "approved",
        "identity_core": True,
        "identity_authority": "identity_and_style",
        "items": [],
    }
    workflow = {"id": "fixture-workflow", "label": "Fixture verified workflow", "ready": True, "requires_reference": False}

    def fulfill(route):
        url = route.request.url
        if url.endswith("/api/personas"):
            return route.fulfill(json=[persona])
        if url.endswith("/api/summary"):
            return route.fulfill(json={"personas": 1, "jobs": 0, "approved": 0, "clicks": 0})
        if url.endswith("/api/personas/fixture-persona/reference-packs"):
            return route.fulfill(json=[reference_pack])
        if url.endswith("/api/personas/fixture-persona/content-packs"):
            return route.fulfill(json=[content_pack])
        if url.endswith("/api/personas/fixture-persona/versions"):
            return route.fulfill(json=[persona["current_version"]])
        if url.endswith("/api/assets"):
            return route.fulfill(json=[])
        if url.endswith("/api/jobs"):
            return route.fulfill(json=[])
        if url.endswith("/api/workflows"):
            return route.fulfill(json=[workflow])
        return route.continue_()

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            for width in (320, 768, 1024, 1440):
                page = browser.new_page(viewport={"width": width, "height": 900})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.route("**/api/**", fulfill)
                page.goto(f"{args.url}/workspace#production", wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(250)
                assert page.locator("#workspace-main").is_visible(), "main landmark is not visible"
                assert page.locator("#generation-form").is_visible(), "generation form is not visible"
                assert page.locator("#workspace-view").get_attribute("aria-busy") == "false", "workspace remains busy"
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), f"horizontal overflow at {width}px"
                assert page.locator("#workspace-main").get_attribute("aria-labelledby") == "view-title"

                page.keyboard.press("Tab")
                assert page.evaluate("document.activeElement?.getAttribute('href') === '#workspace-view'"), "skip link is not first keyboard target"

                unnamed = page.locator("button, a, input, select, textarea").evaluate_all(
                    """elements => elements.filter(element => {
                        const style = window.getComputedStyle(element);
                        if (style.display === 'none' || style.visibility === 'hidden' || element.getClientRects().length === 0) return false;
                        const label = element.getAttribute('aria-label') || element.textContent || '';
                        const wrapped = element.closest('label')?.textContent || '';
                        const labelled = element.id ? document.querySelector(`label[for=\\"${element.id}\\"]`)?.textContent || '' : '';
                        return !(label.trim() || wrapped.trim() || labelled.trim());
                    }).map(element => element.outerHTML.slice(0, 160))"""
                )
                assert not unnamed, f"unnamed interactive controls at {width}px: {unnamed}"
                assert not errors, errors
                page.close()
            browser.close()
    except Exception as exc:
        print(f"Canonical workspace accessibility smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Canonical workspace accessibility/responsive smoke passed at 320, 768, 1024, and 1440px.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
