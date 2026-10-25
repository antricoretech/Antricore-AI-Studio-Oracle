#!/usr/bin/env python3
"""Non-destructive responsive and accessibility smoke test for /workspace."""

from __future__ import annotations

import argparse
import sys


AXE_URL = "https://cdn.jsdelivr.net/npm/axe-core@4.10.2/axe.min.js"


def assert_axe_clean(page):
    page.add_script_tag(url=AXE_URL)
    result = page.evaluate("""async () => await axe.run(document, {
        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] }
    })""")
    violations = [f"{item['id']} ({item['impact']})" for item in result["violations"]]
    assert not violations, f"axe violations: {violations}"


def assert_accessibility_tree(page):
    session = page.context.new_cdp_session(page)
    tree = session.send("Accessibility.getFullAXTree")["nodes"]
    roles = {node.get("role", {}).get("value") for node in tree}
    assert "main" in roles, "accessibility tree has no main landmark"
    assert "navigation" in roles, "accessibility tree has no navigation landmark"
    assert "heading" in roles, "accessibility tree has no heading"


def run_error_and_empty_states(browser, base_url, fulfill):
    error_page = browser.new_page(viewport={"width": 1024, "height": 900})

    def api_failure(route):
        if "/api/personas" in route.request.url:
            return route.fulfill(status=503, json={"detail": "Fixture API unavailable"})
        return route.continue_()

    error_page.route("**/api/**", api_failure)
    error_page.goto(f"{base_url}/workspace#overview", wait_until="networkidle", timeout=30000)
    error_page.wait_for_function("document.querySelector('#workspace-status')?.getAttribute('role') === 'alert'", timeout=10000)
    assert error_page.locator("#workspace-status").get_attribute("role") == "alert", "base API failure did not announce an alert"
    assert "canonical API could not load" in error_page.locator("#workspace-view").inner_text(), "base API failure did not render recovery empty state"
    error_page.close()

    empty_page = browser.new_page(viewport={"width": 1024, "height": 900})

    def empty_data(route):
        url = route.request.url
        if url.endswith("/api/personas"):
            return route.fulfill(json=[])
        if url.endswith("/api/summary"):
            return route.fulfill(json={"personas": 0, "jobs": 0, "approved": 0, "clicks": 0})
        return route.continue_()

    empty_page.route("**/api/**", empty_data)
    empty_page.goto(f"{base_url}/workspace#personas", wait_until="networkidle", timeout=30000)
    empty_page.wait_for_timeout(250)
    assert "No Master Personas are available yet" in empty_page.locator("#workspace-view").inner_text(), "empty persona state is missing"
    assert empty_page.locator("#workspace-view").get_attribute("aria-busy") == "false", "empty persona state remains busy"
    empty_page.close()

    partial_page = browser.new_page(viewport={"width": 1024, "height": 900})

    def partial_failure(route):
        url = route.request.url
        if url.endswith("/api/personas"):
            return route.fulfill(json=[{"id": "fixture-persona", "name": "Fixture Persona", "current_version": {"id": "fixture-version", "state": "frozen"}}])
        if url.endswith("/api/summary"):
            return route.fulfill(json={"personas": 1, "jobs": 0, "approved": 0, "clicks": 0})
        if url.endswith("/api/personas/fixture-persona/reference-packs"):
            return route.fulfill(status=503, json={"detail": "Reference service unavailable"})
        if url.endswith("/api/assets"):
            return route.fulfill(json=[])
        return route.continue_()

    partial_page.route("**/api/**", partial_failure)
    partial_page.goto(f"{base_url}/workspace#references", wait_until="networkidle", timeout=30000)
    partial_page.wait_for_function("document.querySelector('#workspace-status')?.getAttribute('role') === 'alert'", timeout=10000)
    assert partial_page.locator("#workspace-status").get_attribute("role") == "alert", "view API failure did not announce an alert"
    assert "unavailable" in partial_page.locator("#workspace-status").inner_text().lower(), "view API failure message is missing"
    partial_page.close()

    loading_page = browser.new_page(viewport={"width": 1024, "height": 900})
    loading_page.route("**/api/**", fulfill)
    loading_page.goto(f"{base_url}/workspace#production", wait_until="networkidle", timeout=30000)

    loading_page.unroute("**/api/**", fulfill)
    loading_page.route("**/api/**", fulfill)
    loading_page.evaluate("""() => {
        const nativeFetch = window.fetch.bind(window);
        window.fetch = (input, init) => new Promise(resolve => {
            window.setTimeout(() => resolve(nativeFetch(input, init)), 750);
        });
    }""")
    loading_page.locator("#refresh-button").evaluate("button => button.click()")
    loading_page.wait_for_timeout(100)
    assert loading_page.locator("#workspace-view").get_attribute("aria-busy") == "true", "loading state did not set aria-busy"
    loading_page.wait_for_timeout(3000)
    assert loading_page.locator("#workspace-view").get_attribute("aria-busy") == "false", "loading state did not settle"
    loading_page.close()


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
                assert page.locator("#workspace-status").get_attribute("role") == "status"
                assert_axe_clean(page)
                assert_accessibility_tree(page)

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
            run_error_and_empty_states(browser, args.url, fulfill)
            browser.close()
    except Exception as exc:
        print(f"Canonical workspace accessibility smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Canonical workspace axe, accessibility-tree, responsive, loading, empty, and error smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
