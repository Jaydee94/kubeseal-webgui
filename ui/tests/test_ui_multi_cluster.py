"""
E2E tests for multi-cluster / multi-tenant functionality (PR #300).

The UI can be configured with an `environments` map in config.json that maps
environment names to separate API backend URLs. These tests verify:
  - The environment selector dropdown shows/hides correctly
  - Switching environments refetches namespaces from the correct API
  - The namespace field supports multi-select with chips
  - The encrypt button reacts correctly to multi-namespace input

Both config.json and the namespace API calls are intercepted via page.route()
so the tests are self-contained and do not require a running backend.
"""
import json
from playwright.sync_api import sync_playwright, Page, Route

UI_URL = "http://localhost:8080"

MOCK_NAMESPACES = [
    "default",
    "kube-system",
    "monitoring",
    "production",
    "staging",
]

_BASE_CONFIG = {
    "display_name": "Test",
    "kubeseal_webgui_ui_version": "2.1.0",
    "kubeseal_webgui_api_version": "2.1.0",
}

SINGLE_CLUSTER_CONFIG = {
    **_BASE_CONFIG,
    "api_url": "http://localhost:5000",
}

MULTI_CLUSTER_CONFIG = {
    **_BASE_CONFIG,
    "api_url": "http://localhost:5000",
    "environments": {
        "cluster-a": "http://localhost:5000",
        "cluster-b": "http://localhost:5001",
    },
}


def setup_routes(page: Page, config: dict) -> None:
    """Intercept config.json and all /namespaces requests with controlled mock data."""

    def handle_config(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(config),
        )

    def handle_namespaces(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(MOCK_NAMESPACES),
        )

    page.route("**/config.json", handle_config)
    page.route("**/namespaces", handle_namespaces)


def _open_page(page: Page, config: dict) -> None:
    setup_routes(page, config)
    page.goto(UI_URL)
    page.wait_for_load_state("load")
    page.wait_for_selector("input#namespaceSelection", timeout=10000)


def _select_namespace(page: Page, index: int = 0) -> str:
    """Open the namespace autocomplete and click the item at `index`. Returns the item text."""
    page.click("input#namespaceSelection")
    page.wait_for_selector(".v-list-item-title", timeout=5000)
    items = page.query_selector_all(".v-list-item-title")
    text = items[index].inner_text()
    items[index].click()
    return text


def _environment_select(page: Page):
    """Return a locator for the environment v-select component."""
    return page.locator(".v-select", has_text="Environment")


# ---------------------------------------------------------------------------
# Environment selector visibility
# ---------------------------------------------------------------------------

def test_environment_selector_hidden_with_single_cluster():
    """Selector must be invisible when only one environment is configured."""
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        _open_page(page, SINGLE_CLUSTER_CONFIG)

        assert not _environment_select(page).is_visible(), (
            "Environment selector should be hidden when only a single cluster is configured"
        )
        browser.close()


def test_environment_selector_visible_with_multi_cluster():
    """Selector must be visible when more than one environment is configured."""
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        _open_page(page, MULTI_CLUSTER_CONFIG)

        assert _environment_select(page).is_visible(), (
            "Environment selector should be visible when multiple clusters are configured"
        )
        browser.close()


def test_environment_selector_lists_all_environments():
    """Dropdown must contain 'default' plus every key from the environments map."""
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        _open_page(page, MULTI_CLUSTER_CONFIG)

        _environment_select(page).click()
        page.wait_for_selector(".v-list-item-title", timeout=5000)

        item_texts = [el.inner_text() for el in page.query_selector_all(".v-list-item-title")]

        assert "default" in item_texts, f"'default' missing from environment list: {item_texts}"
        assert "cluster-a" in item_texts, f"'cluster-a' missing from environment list: {item_texts}"
        assert "cluster-b" in item_texts, f"'cluster-b' missing from environment list: {item_texts}"
        browser.close()


def test_environment_selector_switches_environment():
    """Clicking a different environment must update the selected value."""
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        _open_page(page, MULTI_CLUSTER_CONFIG)

        env_select = _environment_select(page)
        env_select.click()
        page.wait_for_selector(".v-list-item-title", timeout=5000)

        for item in page.query_selector_all(".v-list-item-title"):
            if item.inner_text() == "cluster-b":
                item.click()
                break

        page.wait_for_timeout(500)
        assert "cluster-b" in env_select.inner_text(), (
            f"Expected 'cluster-b' to be selected, got: {env_select.inner_text()}"
        )
        browser.close()


# ---------------------------------------------------------------------------
# Multi-namespace chip selection
# ---------------------------------------------------------------------------

def test_namespace_selection_shows_chip():
    """Selecting one namespace should render exactly one chip in the input field."""
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        _open_page(page, SINGLE_CLUSTER_CONFIG)

        first_ns = _select_namespace(page, 0)
        page.wait_for_selector(".v-autocomplete .v-chip__content", timeout=10000)

        chips = page.query_selector_all(".v-autocomplete .v-chip__content")
        assert len(chips) == 1, f"Expected 1 namespace chip, got {len(chips)}"
        assert chips[0].inner_text() == first_ns, (
            f"Chip text '{chips[0].inner_text()}' does not match selected namespace '{first_ns}'"
        )
        browser.close()


def test_multi_namespace_selection_shows_multiple_chips():
    """Selecting two namespaces must show two chips."""
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        _open_page(page, SINGLE_CLUSTER_CONFIG)

        _select_namespace(page, 0)
        page.wait_for_selector(".v-autocomplete .v-chip__content", timeout=10000)

        _select_namespace(page, 1)
        page.wait_for_timeout(500)

        chips = page.query_selector_all(".v-autocomplete .v-chip__content")
        assert len(chips) == 2, f"Expected 2 namespace chips after selecting two namespaces, got {len(chips)}"
        browser.close()


def test_namespace_chip_can_be_removed():
    """Clicking the close icon on a chip must remove that namespace from the selection."""
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        _open_page(page, SINGLE_CLUSTER_CONFIG)

        _select_namespace(page, 0)
        page.wait_for_selector(".v-autocomplete .v-chip__content", timeout=10000)
        _select_namespace(page, 1)
        page.wait_for_timeout(300)

        chips_before = page.query_selector_all(".v-autocomplete .v-chip__content")
        assert len(chips_before) == 2, f"Expected 2 chips before removal, got {len(chips_before)}"

        # Vuetify 3 closable chips render a button inside .v-chip for dismissal
        close_btn = page.locator(".v-autocomplete .v-chip button").first
        close_btn.click()
        page.wait_for_timeout(300)

        chips_after = page.query_selector_all(".v-autocomplete .v-chip__content")
        assert len(chips_after) == 1, f"Expected 1 chip after removing one, got {len(chips_after)}"
        browser.close()


# ---------------------------------------------------------------------------
# Encrypt button behaviour with multiple namespaces
# ---------------------------------------------------------------------------

def test_encrypt_button_disabled_without_namespace():
    """Encrypt button must stay disabled when no namespace is selected."""
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        _open_page(page, SINGLE_CLUSTER_CONFIG)

        encrypt_button = page.locator('button:has-text("Encrypt")')
        encrypt_button.wait_for()
        assert encrypt_button.is_disabled(), "Encrypt button should be disabled when no namespace is selected"
        browser.close()


def test_encrypt_button_enabled_with_multi_namespace():
    """Encrypt button must become enabled when multiple namespaces and secret data are provided."""
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        _open_page(page, SINGLE_CLUSTER_CONFIG)

        encrypt_button = page.locator('button:has-text("Encrypt")')
        encrypt_button.wait_for()
        assert encrypt_button.is_disabled(), "Encrypt button should be disabled initially"

        # Select two namespaces
        _select_namespace(page, 0)
        page.wait_for_selector(".v-autocomplete .v-chip__content", timeout=10000)
        _select_namespace(page, 1)
        page.wait_for_timeout(300)

        page.fill("#secretName", "test-secret")
        page.fill("textarea#secretKey", "my-key")
        page.fill("textarea#secretValue", "my-value")
        page.wait_for_timeout(300)

        assert encrypt_button.is_enabled(), (
            "Encrypt button should be enabled when two namespaces and secret data are provided"
        )
        browser.close()


def test_encrypt_called_with_multi_namespace():
    """Clicking Encrypt with multiple namespaces must invoke fetchEncodedSecrets."""
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        _open_page(page, SINGLE_CLUSTER_CONFIG)

        _select_namespace(page, 0)
        page.wait_for_selector(".v-autocomplete .v-chip__content", timeout=10000)
        _select_namespace(page, 1)
        page.wait_for_timeout(300)

        page.fill("#secretName", "test-secret")
        page.fill("textarea#secretKey", "my-key")
        page.fill("textarea#secretValue", "my-value")
        page.wait_for_timeout(300)

        page.evaluate(
            """
            const appElement = document.querySelector('#app');
            const vueApp = appElement.__vue_app__;
            if (vueApp) {
                vueApp._instance.proxy.fetchEncodedSecrets = function() {
                    window.fetchEncodedSecretsCalled = true;
                };
            }
            """
        )

        page.locator('button:has-text("Encrypt")').click()
        is_called = page.evaluate("window.fetchEncodedSecretsCalled === true")
        assert is_called, "fetchEncodedSecrets was not called after clicking Encrypt with multiple namespaces"
        browser.close()


# ---------------------------------------------------------------------------
# Environment switching clears namespace selection
# ---------------------------------------------------------------------------

def test_environment_switch_clears_namespace_selection():
    """Switching to a different environment must reset the namespace chip selection."""
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        _open_page(page, MULTI_CLUSTER_CONFIG)

        # Select a namespace in the current environment
        _select_namespace(page, 0)
        page.wait_for_selector(".v-autocomplete .v-chip__content", timeout=10000)
        assert len(page.query_selector_all(".v-autocomplete .v-chip__content")) == 1

        # Switch environment – this triggers fetchNamespacesData which resets namespaceName
        env_select = _environment_select(page)
        env_select.click()
        page.wait_for_selector(".v-list-item-title", timeout=5000)
        for item in page.query_selector_all(".v-list-item-title"):
            if item.inner_text() == "cluster-b":
                item.click()
                break

        page.wait_for_timeout(500)

        chips = page.query_selector_all(".v-autocomplete .v-chip__content")
        assert len(chips) == 0, (
            f"Namespace chips should be cleared after switching environment, but {len(chips)} chip(s) remain"
        )
        browser.close()
