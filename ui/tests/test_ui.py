import base64
import json
import pathlib
import re

import pytest
from playwright.sync_api import Page, Route, expect

SECRET_NAME = "valid-secret-name"
SECRET_KEY = "my-secret-key"
SECRET_VALUE = "my-secret-value"
FILE_CONTENT = "This is a test file."
SEALED_VALUE = "AgSealedValue"
ONE_MEBIBYTE = 1024 * 1024


class SealingApi:
    """Stand-in for `POST /secrets`: there is no API behind the dev server."""

    def __init__(self, page: Page, status: int = 200, body=None, hold: bool = False):
        self.requests: list[dict] = []
        self.status = status
        self.body = body
        # With `hold` a request is not answered until `release()`, so that a
        # test can look at the page while it is sealing.
        self.hold = hold
        self._held: list[Route] = []
        page.route("**/secrets", self._handle)

    def release(self):
        # Requests that arrive after this (the page may not have sent one yet)
        # are answered right away instead of being held for good.
        self.hold = False
        held, self._held = self._held, []
        for route in held:
            self._answer(route)

    def _handle(self, route: Route):
        assert route.request.method == "POST"
        self.requests.append(route.request.post_data_json)
        if self.hold:
            self._held.append(route)
        else:
            self._answer(route)

    def _answer(self, route: Route):
        payload = route.request.post_data_json
        body = self.body
        if body is None:
            body = [
                {"key": entry["key"], "value": SEALED_VALUE}
                for entry in payload["secrets"]
            ]
        route.fulfill(
            status=self.status,
            content_type="application/json",
            body=json.dumps(body),
        )

    @property
    def only_request(self) -> dict:
        assert len(self.requests) == 1, f"Expected one request: {self.requests}"
        return self.requests[0]


def b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def test_config_json_is_requested_once_per_page_load(page: Page):
    config_requests: list[str] = []
    page.on(
        "request",
        lambda request: (
            config_requests.append(request.url)
            if request.url.endswith("/config.json")
            else None
        ),
    )
    page.route(
        "**/config", lambda route: route.fulfill(json={"kubesealVersion": "0.27.1"})
    )
    SealingApi(page)

    page.goto("/")
    # both consumers of the configuration have rendered
    expect(page.locator("footer .version-pill")).to_have_count(3)
    # the display name labels the environment in the header
    expect(page.locator("header .env-badge")).to_contain_text("Test")
    # sealing needs the API URL from the configuration again
    seal_one_value(page)

    assert len(config_requests) == 1, config_requests


def mock_application_properties(page: Page, kubeseal_version: str = "0.27.1"):
    """Answer `GET /config` (there is no API behind the dev server)."""
    page.route(
        "**/config", lambda route: route.fulfill(json={"kubesealVersion": kubeseal_version})
    )


def footer_versions(page: Page) -> list[tuple[str, str]]:
    """The (label, value) pills of the footer, whitespace normalised."""
    pills = page.locator("footer .version-pill")
    return [
        (
            " ".join(pill.locator("dt").inner_text().split()),
            " ".join(pill.locator("dd").inner_text().split()),
        )
        for pill in pills.all()
    ]


def test_footer_shows_the_versions(page: Page):
    mock_application_properties(page)
    page.goto("/")

    footer = page.locator("footer")
    expect(footer).to_contain_text("Kubeseal WebGui")
    expect(footer.locator(".version-pill")).to_have_count(3)
    assert footer_versions(page) == [
        ("kubeseal", "0.27.1"),
        ("UI", "2.1.0"),
        ("API", "2.1.0"),
    ]
    # loaded: a green dot, no message
    expect(footer.locator(".status-dot--ok")).to_have_count(1)
    expect(footer.locator(".status-message")).to_have_count(0)
    repository = footer.get_by_role("link", name="GitHub")
    expect(repository).to_have_attribute(
        "href", "https://github.com/Jaydee94/kubeseal-webgui"
    )
    expect(repository).to_have_attribute("target", "_blank")
    expect(repository).to_have_attribute("rel", "noopener noreferrer")


def test_footer_reports_an_unreachable_api(page: Page):
    page.route(
        "**/config",
        lambda route: route.fulfill(status=500, json={"detail": "Internal Server Error"}),
    )
    page.goto("/")

    footer = page.locator("footer")
    expect(footer).to_contain_text("Could not retrieve application properties.")
    expect(footer.locator(".status-dot--error")).to_have_count(1)
    expect(footer.locator(".status-dot--ok")).to_have_count(0)
    expect(footer.locator(".version-pill")).to_have_count(0)
    # the link to the repository does not depend on the properties
    expect(footer.get_by_role("link", name="GitHub")).to_be_visible()


def test_footer_shows_that_it_is_loading(page: Page):
    pending: list[Route] = []

    def hold(route: Route) -> None:
        pending.append(route)

    page.route("**/config", hold)
    page.goto("/")

    footer = page.locator("footer")
    expect(footer).to_contain_text("Loading application properties.")
    expect(footer.locator(".version-pill")).to_have_count(0)
    expect(footer.locator(".status-dot")).to_have_count(0)

    pending[0].fulfill(json={"kubesealVersion": "0.27.1"})
    expect(footer.locator(".version-pill")).to_have_count(3)
    expect(footer).not_to_contain_text("Loading application properties.")


def test_footer_link_is_reachable_with_the_keyboard(page: Page):
    page.goto("/")
    link = page.locator("footer").get_by_role("link", name="GitHub")
    # the last stop of the page when tabbing from the top
    for _ in range(60):
        page.keyboard.press("Tab")
        if page.evaluate("document.activeElement === document.querySelector('footer a')"):
            break
    expect(link).to_be_focused()
    # a native link: Enter follows it, no script needed
    assert page.evaluate("document.activeElement.tagName") == "A"


def test_header_has_no_about_button_any_more(page: Page):
    page.goto("/")
    expect(page.get_by_role("button", name="About")).to_have_count(0)
    expect(page.locator(".about-card, .about-versions")).to_have_count(0)
    # the theme toggle is still there
    expect(dark_mode_toggle(page)).to_be_visible()


def test_footer_is_part_of_the_page_not_fixed_to_the_viewport(page: Page):
    mock_application_properties(page)
    page.goto("/")
    expect(page.locator(".v-footer")).to_have_count(0)
    footer = page.locator("footer")
    expect(footer).to_be_visible()
    assert footer.evaluate("el => getComputedStyle(el).position") == "static"
    content = page.locator(".v-main").bounding_box()
    # below all the content, wherever the page is scrolled to
    assert content["y"] + content["height"] <= footer.bounding_box()["y"] + 1
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    box = footer.bounding_box()
    assert abs(box["y"] + box["height"] - page.viewport_size["height"]) <= 1, box
    assert page.evaluate("document.documentElement.scrollWidth") <= page.viewport_size["width"]


def test_footer_is_pushed_to_the_bottom_of_a_short_page(page: Page):
    mock_application_properties(page)
    page.set_viewport_size({"width": 1280, "height": 2000})
    page.goto("/")
    box = page.locator("footer").bounding_box()
    assert abs(box["y"] + box["height"] - 2000) <= 1, box
    # no scrollbar for a footer that is only pushed down
    assert page.evaluate("document.documentElement.scrollHeight") <= 2000


@pytest.mark.parametrize("width", [375, 1280])
def test_footer_never_covers_content(page: Page, width: int):
    page.set_viewport_size({"width": width, "height": 600})
    page.goto("/")
    # the scroll position does not matter for something that is not fixed
    namespace_select(page)
    secret_name(page)
    add_secret_key_value(page)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    footer = page.locator("footer")
    encrypt = page.get_by_role("button", name="Encrypt")
    expect(encrypt).to_be_visible()
    assert not boxes_overlap(encrypt.bounding_box(), footer.bounding_box())
    assert encrypt.bounding_box()["y"] + encrypt.bounding_box()["height"] <= footer.bounding_box()["y"]

    SealingApi(page)
    click_encrypt_button(page)
    expect(page.locator("#sealed-secret-result")).to_be_visible()
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    footer_box = footer.bounding_box()
    for name in ("Clear", "Edit Secrets"):
        button = page.get_by_role("button", name=name).bounding_box()
        assert not boxes_overlap(button, footer_box), name
        assert button["y"] + button["height"] <= footer_box["y"], name
    # still the last thing of the scrolled page
    assert footer_box["y"] + footer_box["height"] <= 600 + 1
    assert page.evaluate("document.documentElement.scrollWidth") <= width


@pytest.mark.parametrize("width", [375, 1280])
def test_footer_fits_the_screen_and_stacks_on_a_phone(page: Page, width: int):
    mock_application_properties(page)
    page.set_viewport_size({"width": width, "height": 800})
    page.goto("/")
    footer = page.locator("footer")
    expect(footer.locator(".version-pill")).to_have_count(3)
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    footer_box = footer.bounding_box()
    brand = footer.locator(".app-footer__brand").bounding_box()
    pills = footer.locator(".version-pills").bounding_box()
    link = footer.get_by_role("link", name="GitHub").bounding_box()
    for box in (brand, pills, link):
        assert inside(box, footer_box)
        assert box["x"] >= 0 and box["x"] + box["width"] <= width
    assert not boxes_overlap(brand, link) and not boxes_overlap(brand, pills)
    assert not boxes_overlap(pills, link)
    if width < 600:
        # the pills get a row of their own below brand and link
        assert pills["y"] >= max(brand["y"] + brand["height"], link["y"] + link["height"]) - 1
    else:
        # one row: brand at the left, pills and link at the right
        assert abs((pills["y"] + pills["height"] / 2) - (brand["y"] + brand["height"] / 2)) <= 12
        assert link["x"] + link["width"] <= footer_box["x"] + footer_box["width"]


def test_footer_follows_the_theme(page: Page):
    mock_application_properties(page)
    page.goto("/")
    footer = page.locator("footer")
    expect(footer.locator(".version-pill")).to_have_count(3)

    def colours() -> tuple[str, str]:
        return footer.evaluate(
            "el => [getComputedStyle(el).color, getComputedStyle(el).borderTopColor]"
        )

    before = colours()
    page.get_by_role("button", name=re.compile("^Switch to (dark|light) theme$")).click()
    page.wait_for_timeout(300)
    assert colours() != before


def test_header_stays_opaque_while_scrolling(page: Page):
    page.goto("/")
    page.add_style_tag(content="body { min-height: 3000px; }")
    page.mouse.wheel(0, 400)
    bar = page.locator(".glass-app-bar")
    expect(bar).to_have_class(re.compile("glass-app-bar--scrolled"))

    def alpha() -> float:
        # rgba(r, g, b, a) of the bar's background
        return float(
            bar.evaluate("el => getComputedStyle(el).backgroundColor")
            .rstrip(")")
            .split(",")[-1]
        )

    # light and dark each paint their own surface colour, both mostly opaque
    assert 0.7 <= alpha() <= 0.9
    dark_before = is_dark(page)
    page.get_by_role("button", name="Switch to dark theme").click()
    # the toggle really switched, so that the second check sees the other surface
    assert is_dark(page) != dark_before
    assert 0.7 <= alpha() <= 0.9
    assert bar.evaluate("el => getComputedStyle(el).backdropFilter").startswith("blur(12px)")


def test_page_has_one_heading_and_icons(page: Page):
    page.goto("/")
    expect(page.get_by_role("heading", level=1)).to_have_text("Kubeseal WebGui")
    expect(page.get_by_role("link", name="Kubeseal WebGui, start page")).to_have_count(1)
    expect(page.locator('link[rel="icon"][type="image/svg+xml"]')).to_have_attribute(
        "href", "./favicon.svg"
    )
    assert page.request.get("/favicon.svg").ok


# Makes the made-up namespace list of the dev server the same on every load.
SEEDED_RANDOM = """
    let seed = 42;
    Math.random = () => {
        seed = (seed * 1664525 + 1013904223) % 4294967296;
        return seed / 4294967296;
    };
"""


def open_namespace_list(page: Page) -> list[str]:
    page.click("input#namespaceSelection")
    page.wait_for_selector(".v-list-item-title")
    return page.locator(".v-list-item-title").all_inner_texts()


def reopen_namespace_list(page: Page) -> list[str]:
    """Close and open the list again: it then starts at its first entry.

    The list is virtual, so only a list at its first entry is sure to have
    rendered the favorites.
    """
    page.keyboard.press("Escape")
    expect(page.locator(".v-overlay .v-list-item-title")).to_have_count(0)
    return open_namespace_list(page)


def list_headings(page: Page) -> list[str]:
    return page.locator(".v-overlay .v-list-subheader").all_inner_texts()


def namespace_item(page: Page, name: str):
    return page.locator(".v-overlay .v-list-item", has_text=name)


def favorite_toggle(page: Page, name: str):
    return namespace_item(page, name).locator(".v-list-item__prepend").get_by_role("button")


def favorite_names(page: Page) -> list[str]:
    return page.locator(
        ".v-overlay .v-list-item:has(.mdi-heart) .v-list-item-title"
    ).all_inner_texts()


def test_favorite_namespaces_are_listed_first_and_remembered(page: Page):
    page.add_init_script(SEEDED_RANDOM)
    page.goto("/")
    page.wait_for_selector("input#namespaceSelection")
    names = open_namespace_list(page)
    assert names == sorted(names) and len(names) >= 5
    assert favorite_names(page) == []
    assert list_headings(page) == []

    # marking a namespace moves it to the top, under its own heading
    favorite_toggle(page, names[3]).click()
    # toggling a favorite does not select the namespace
    expect(page.locator("input#namespaceSelection")).to_have_value("")
    expect(page.locator(".v-autocomplete__selection-text")).to_have_text("")
    assert reopen_namespace_list(page) == [
        names[3],
        *names[:3],
        *names[4:],
    ]
    assert favorite_names(page) == [names[3]]
    assert list_headings(page) == ["Favorites", "All namespaces"]

    favorite_toggle(page, names[1]).click()
    assert reopen_namespace_list(page) == [
        names[1],
        names[3],
        names[0],
        names[2],
        *names[4:],
    ]
    assert favorite_names(page) == [names[1], names[3]]
    assert list_headings(page) == ["Favorites", "All namespaces"]
    assert json.loads(page.evaluate("localStorage.favoriteNamespaces")) == [
        names[3],
        names[1],
    ]

    # favorites are kept across page loads
    page.reload()
    page.wait_for_selector("input#namespaceSelection")
    assert open_namespace_list(page)[:2] == [names[1], names[3]]
    assert favorite_names(page) == [names[1], names[3]]

    # and can be removed again
    favorite_toggle(page, names[1]).click()
    assert reopen_namespace_list(page)[:3] == [names[3], names[0], names[1]]
    assert favorite_names(page) == [names[3]]


def test_open_list_follows_a_new_favorite_to_the_top(page: Page):
    page.add_init_script(SEEDED_RANDOM)
    page.goto("/")
    page.wait_for_selector("input#namespaceSelection")
    names = open_namespace_list(page)
    namespace_list = page.locator(".v-overlay .v-list")

    # the last entry is only reachable by scrolling
    favorite_toggle(page, names[-1]).scroll_into_view_if_needed()
    assert namespace_list.evaluate("list => list.scrollTop") > 0
    favorite_toggle(page, names[-1]).click()

    expect(namespace_item(page, names[-1])).to_be_in_viewport()
    assert namespace_list.evaluate("list => list.scrollTop") == 0
    assert favorite_names(page) == [names[-1]]


def test_favorite_toggle_works_with_the_keyboard(page: Page):
    page.add_init_script(SEEDED_RANDOM)
    page.goto("/")
    page.wait_for_selector("input#namespaceSelection")
    names = open_namespace_list(page)
    focused = page.locator("*:focus")

    # arrow keys walk through the list: an item, then its favorite toggle
    page.focus("input#namespaceSelection")
    page.keyboard.press("ArrowDown")
    expect(focused).to_have_text(names[0])
    page.keyboard.press("ArrowDown")
    expect(focused).to_have_role("button")
    expect(focused).to_have_attribute("aria-label", f"Add {names[0]} to favorites")
    expect(focused).to_have_attribute("aria-pressed", "false")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    expect(focused).to_have_attribute("aria-label", f"Add {names[1]} to favorites")

    # Enter toggles the favorite and does not select the namespace
    page.keyboard.press("Enter")
    expect(page.locator("input#namespaceSelection")).to_have_value("")
    expect(page.locator(".v-autocomplete__selection-text")).to_have_text("")
    assert reopen_namespace_list(page)[0] == names[1]
    assert favorite_names(page) == [names[1]]
    toggle = favorite_toggle(page, names[1])
    expect(toggle).to_have_attribute("aria-label", f"Remove {names[1]} from favorites")
    expect(toggle).to_have_attribute("aria-pressed", "true")

    # so does Space
    toggle.focus()
    page.keyboard.press("Space")
    expect(page.locator("input#namespaceSelection")).to_have_value("")
    assert reopen_namespace_list(page) == names
    assert favorite_names(page) == []


def is_dark(page: Page) -> bool:
    return page.locator(".v-application.v-theme--dark").count() == 1


def dark_mode_toggle(page: Page):
    return page.locator(".dark-mode-toggle")


def test_dark_mode_follows_the_system_until_the_user_chooses(page: Page):
    page.emulate_media(color_scheme="dark")
    page.goto("/")
    expect(dark_mode_toggle(page)).to_have_attribute("aria-label", "Switch to light theme")
    assert is_dark(page)
    # nothing is stored before the user makes a choice
    assert page.evaluate("localStorage.getItem('useDarkTheme')") is None

    dark_mode_toggle(page).click()
    expect(dark_mode_toggle(page)).to_have_attribute("aria-label", "Switch to dark theme")
    assert not is_dark(page)
    assert page.evaluate("localStorage.getItem('useDarkTheme')") == "false"

    # the choice wins over the system preference on the next visit
    page.reload()
    expect(dark_mode_toggle(page)).to_have_attribute("aria-label", "Switch to dark theme")
    assert not is_dark(page)

    dark_mode_toggle(page).click()
    expect(dark_mode_toggle(page)).to_have_attribute("aria-label", "Switch to light theme")
    assert is_dark(page)
    assert page.evaluate("localStorage.getItem('useDarkTheme')") == "true"


def test_light_system_preference_starts_light(page: Page):
    page.emulate_media(color_scheme="light")
    page.goto("/")
    expect(dark_mode_toggle(page)).to_have_attribute("aria-label", "Switch to dark theme")
    assert not is_dark(page)


def test_dark_mode_toggle_works_with_the_keyboard(page: Page):
    page.emulate_media(color_scheme="light")
    page.goto("/")
    toggle = page.get_by_role("button", name="Switch to dark theme")
    toggle.focus()
    page.keyboard.press("Enter")
    assert is_dark(page)
    page.keyboard.press("Space")
    assert not is_dark(page)


def test_ui_works_without_local_storage(page: Page):
    # e.g. a browser that blocks site data: reading window.localStorage throws
    page.add_init_script("""
        Object.defineProperty(window, 'localStorage', {
            get() { throw new DOMException('The operation is insecure.', 'SecurityError') }
        })
    """)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.emulate_media(color_scheme="light")
    page.goto("/")

    expect(dark_mode_toggle(page)).to_have_attribute("aria-label", "Switch to dark theme")
    dark_mode_toggle(page).click()
    expect(dark_mode_toggle(page)).to_have_attribute("aria-label", "Switch to light theme")
    assert is_dark(page)

    names = open_namespace_list(page)
    favorite_toggle(page, names[2]).click()
    assert reopen_namespace_list(page)[0] == names[2]
    assert errors == []


def test_logo_links_to_the_start_page(app_page: Page):
    logo = app_page.locator("a#logo")
    # Relative, so that it also leads to the start page under a path prefix.
    expect(logo).to_have_attribute("href", "./")
    expect(logo).to_have_attribute("aria-label", "Kubeseal WebGui, start page")


def test_dark_theme_has_a_logo_with_light_lettering(page: Page):
    page.goto("/")
    logo = page.locator("#logo-img")
    light_src = logo.get_attribute("src")
    assert "logo-2025-dark" not in light_src

    page.get_by_role("button", name="Switch to dark theme").click()
    expect(logo).to_have_attribute("src", re.compile("logo-2025-dark"))
    # decorative: the link carries the name
    expect(logo).to_have_attribute("alt", "")
    # the image really loaded (an uncached file may still be downloading)
    page.wait_for_function(
        """() => {
            const img = document.querySelector('#logo-img')
            return img.src.includes('logo-2025-dark') && img.complete && img.naturalWidth > 0
        }""",
        timeout=5000,
    )

    page.get_by_role("button", name="Switch to light theme").click()
    expect(logo).to_have_attribute("src", light_src)


def test_ui_start(app_page: Page):
    assert app_page.title() == "Kubeseal WebGui - Sealed Secrets Management"


def serve_clusters(page: Page, clusters, status: int = 200, **config):
    """Say in config.json that there are several clusters (as the chart does
    for sealedSecrets.certs), with further config.json keys, and answer
    `GET /clusters`: there is no API behind the dev server."""

    def config_json(route: Route):
        body = route.fetch().json()
        body["multiple_clusters"] = True
        body.update(config)
        route.fulfill(json=body)

    page.route("**/config.json", config_json)
    page.route("**/clusters", lambda route: route.fulfill(status=status, json=clusters))


TWO_CLUSTERS = [
    {"name": "acc", "inCluster": True, "fingerprint": "AA:BB:CC:DD:EE:FF:00:11"},
    {"name": "prod", "inCluster": False, "fingerprint": "11:22:33:44:55:66:77:88"},
]


def selected_cluster(page: Page):
    return page.locator(".cluster-picker .v-select__selection-text")


def pick_cluster(page: Page, name: str):
    page.locator(".cluster-picker .v-field").click()
    page.get_by_role("option", name=name).click()
    expect(selected_cluster(page)).to_have_text(name)


def test_a_single_cluster_works_as_before(page: Page):
    # config.json of a release without sealedSecrets.certs: no multiple_clusters
    cluster_requests = []
    page.on(
        "request",
        lambda request: (
            cluster_requests.append(request.url)
            if request.url.endswith("/clusters")
            else None
        ),
    )
    api = SealingApi(page)
    page.goto("/")
    page.wait_for_selector("#secretName")

    expect(page.locator("#clusterSelection")).to_have_count(0)
    secret_name(page)
    namespace_select(page)
    add_secret_key_value(page)
    click_encrypt_button(page)
    expect(page.locator("#sealed-secret-result")).to_be_visible()
    # the same request as before, and no question about clusters
    assert "cluster" not in api.only_request
    assert cluster_requests == []
    expect(page.locator(".summary-chip", has_text="default")).to_have_count(0)


def test_one_configured_cluster_has_no_selector(page: Page):
    serve_clusters(page, [{"name": "acc", "inCluster": True}])
    api = SealingApi(page)
    page.goto("/")
    page.wait_for_selector("#secretName")

    expect(page.locator("#clusterSelection")).to_have_count(0)
    secret_name(page)
    namespace_select(page)
    add_secret_key_value(page)
    click_encrypt_button(page)
    expect(page.locator("#sealed-secret-result")).to_be_visible()
    # named all the same: explicit is safer than the API's default
    assert api.only_request["cluster"] == "acc"


def test_sealing_waits_for_the_clusters(page: Page):
    serve_clusters(page, TWO_CLUSTERS)
    held: list[Route] = []
    # registered last, so it answers /clusters: held until released
    page.route("**/clusters", lambda route: held.append(route))
    page.goto("/")
    page.wait_for_selector("#secretName")
    select_scope(page, "cluster-wide")
    secret_name(page)
    add_secret_key_value(page)

    # everything is filled in, but whose certificate would seal is not known
    expect(page.locator('button:has-text("Encrypt")')).to_be_disabled()
    for _ in range(100):  # the request is held, not lost
        if held:
            break
        page.wait_for_timeout(50)
    assert len(held) == 1
    held[0].fulfill(json=TWO_CLUSTERS)

    expect(page.locator("#clusterSelection")).to_have_count(1)
    expect(page.locator('button:has-text("Encrypt")')).to_be_enabled()


@pytest.mark.parametrize("status", [404, 500])
def test_sealing_is_blocked_when_the_clusters_are_unknown(page: Page, status: int):
    serve_clusters(page, {"detail": "nope"}, status=status)
    page.goto("/")
    page.wait_for_selector("#secretName")
    # cluster-wide needs no namespace, so nothing else is missing
    select_scope(page, "cluster-wide")
    secret_name(page)
    add_secret_key_value(page)

    expect(page.locator(".v-snackbar")).to_contain_text("Failed to fetch the clusters")
    expect(page.locator('button:has-text("Encrypt")')).to_be_disabled()


def test_secret_is_sealed_for_the_picked_cluster(page: Page):
    serve_clusters(page, TWO_CLUSTERS)
    api = SealingApi(page)
    page.goto("/")
    page.wait_for_selector("#clusterSelection")

    # the first cluster is preselected, and it is the one of the API: a list
    expect(selected_cluster(page)).to_have_text("acc")
    expect(page.locator(".v-autocomplete")).to_have_count(1)

    pick_cluster(page, "prod")
    # the namespaces of another cluster are not known: a text field
    expect(page.locator(".v-autocomplete")).to_have_count(0)
    expect(page.get_by_text("namespaces of this cluster are typed in")).to_be_visible()
    secret_name(page)
    page.fill("input#namespaceSelection", "team-a")
    add_secret_key_value(page)
    click_encrypt_button(page)

    expect(page.locator("#sealed-secret-result")).to_be_visible()
    assert api.only_request["cluster"] == "prod"
    assert api.only_request["namespace"] == "team-a"
    # the result says which cluster sealed it
    expect(page.locator(".summary-chip", has_text="prod")).to_be_visible()


def test_namespace_is_cleared_when_the_namespace_mode_changes(page: Page):
    serve_clusters(page, TWO_CLUSTERS)
    page.goto("/")
    page.wait_for_selector("#clusterSelection")

    pick_cluster(page, "prod")
    page.fill("input#namespaceSelection", "team-a")

    # a typed-in name is no entry of the list, so back to the list it starts empty
    pick_cluster(page, "acc")
    expect(page.locator(".v-autocomplete")).to_have_count(1)
    expect(page.locator("input#namespaceSelection")).to_have_value("")


def test_typed_in_namespace_is_kept_while_it_stays_typed_in(page: Page):
    serve_clusters(page, TWO_CLUSTERS)
    page.goto("/")
    page.wait_for_selector("#clusterSelection")

    # a new namespace is typed in, in the cluster of the API ...
    page.locator("#newNamespaceCheckbox").check()
    page.fill("input#namespaceSelection", "team-new")
    # ... and is still typed in for another cluster: nothing to clear
    pick_cluster(page, "prod")
    expect(page.locator("input#namespaceSelection")).to_have_value("team-new")


def test_import_is_not_offered_for_another_cluster(page: Page):
    requested_urls = enable_sealed_secret_import(page)
    # registered last, so it answers config.json: the import stays on
    serve_clusters(page, TWO_CLUSTERS, enable_existing_sealed_secret_loading=True)
    page.goto("/")
    page.wait_for_selector("#clusterSelection")
    import_button = page.get_by_role("button", name="Import existing sealed secret")

    pick_cluster(page, "prod")
    page.fill("input#namespaceSelection", "team-a")
    expect(import_button).to_have_count(0)
    assert requested_urls == []


def test_summary_names_the_cluster(page: Page):
    serve_clusters(page, TWO_CLUSTERS)
    SealingApi(page)
    page.goto("/")
    page.wait_for_selector("#clusterSelection")

    secret_name(page)
    namespace_select(page)
    add_secret_key_value(page)

    expect(page.locator(".action-bar__status")).to_contain_text("acc")


def additional_namespace_chips(page: Page):
    """The chips of the field for more namespaces, and no other chips."""
    field = page.locator(".v-field", has=page.locator("input#additionalNamespaces"))
    return field.locator(".v-chip")


def add_additional_namespaces(page: Page, names: list[str]):
    """Type namespaces into the field for more namespaces (free text)."""
    field = page.locator("input#additionalNamespaces")
    field.fill(",".join(names) + ",")
    expect(additional_namespace_chips(page)).to_have_count(len(names))


def test_one_secret_is_sealed_for_several_typed_in_namespaces(page: Page):
    disable_namespace_listing(page)
    api = SealingApi(page)
    page.goto("/")
    secret_name(page)
    add_secret_key_value(page)

    # offered only once there is a main namespace
    expect(page.locator("input#additionalNamespaces")).to_have_count(0)
    page.fill("input#namespaceSelection", "team-a")
    add_additional_namespaces(page, ["team-b", "team-c", "team-a"])
    expect(page.locator(".action-bar__status")).to_contain_text("3 namespaces")
    click_encrypt_button(page)

    expect(page.locator("#sealed-secret-result")).to_be_visible()
    # one request per namespace (in parallel, so in no fixed order); a repeat
    # is sealed once
    namespaces = [request["namespace"] for request in api.requests]
    assert sorted(namespaces) == ["team-a", "team-b", "team-c"]
    assert len(api.requests) == 3
    # one manifest per namespace, in the order of the form
    expect(page.locator(".result-card")).to_have_count(3)
    expect(page.locator("#sealed-secret-result-2")).to_be_visible()
    texts = [
        page.locator(selector).inner_text()
        for selector in (
            "#sealed-secret-result",
            "#sealed-secret-result-2",
            "#sealed-secret-result-3",
        )
    ]
    assert [re.search(r"namespace: (\S+)", text).group(1) for text in texts] == [
        "team-a",
        "team-b",
        "team-c",
    ]
    # buttons of the cards can be told apart
    expect(page.get_by_role("button", name="Copy manifest of team-b")).to_be_visible()


def test_additional_namespaces_are_picked_from_the_list(app_page: Page):
    page = app_page
    api = SealingApi(page)
    secret_name(page)
    add_secret_key_value(page)
    main = namespace_select(page)

    page.locator("input#additionalNamespaces").click()
    active_list = page.locator(".v-overlay--active .v-list-item")
    expect(active_list.first).to_be_visible()
    offered = page.locator(".v-overlay--active .v-list-item-title").all_inner_texts()
    # the main namespace is not offered a second time
    assert offered and main not in offered
    active_list.first.click()
    page.keyboard.press("Escape")
    click_encrypt_button(page)

    # the requests run in parallel, so only their set is fixed; the order of
    # the results is the order of the form, the main namespace first
    expect(page.locator(".result-card")).to_have_count(2)
    namespaces = {request["namespace"] for request in api.requests}
    assert len(api.requests) == 2 and len(namespaces) == 2 and main in namespaces
    assert re.search(
        r"namespace: (\S+)", page.locator("#sealed-secret-result").inner_text()
    ).group(1) == main


def test_invalid_additional_namespace_blocks_sealing(page: Page):
    disable_namespace_listing(page)
    SealingApi(page)
    page.goto("/")
    secret_name(page)
    add_secret_key_value(page)
    page.fill("input#namespaceSelection", "team-a")

    add_additional_namespaces(page, ["Not_Valid"])

    expect(page.get_by_text('"Not_Valid" is not a valid namespace name')).to_be_visible()
    expect(page.locator('button:has-text("Encrypt")')).to_be_disabled()


def test_additional_namespaces_are_not_offered_for_cluster_wide_secrets(app_page: Page):
    page = app_page
    namespace_select(page)
    expect(page.locator("input#additionalNamespaces")).to_have_count(1)

    select_scope(page, "cluster-wide")

    expect(page.locator("input#additionalNamespaces")).to_have_count(0)


def test_failed_sealing_for_one_of_several_namespaces_names_it(page: Page):
    disable_namespace_listing(page)
    SealingApi(page, status=500, body={"detail": "Failed to seal secrets."})
    page.goto("/")
    secret_name(page)
    add_secret_key_value(page)
    page.fill("input#namespaceSelection", "team-a")
    add_additional_namespaces(page, ["team-b"])
    click_encrypt_button(page)

    expect(page.locator(".v-snackbar")).to_contain_text('for namespace "team-')
    # nothing is shown for the namespaces that did work
    expect(page.locator(".result-card")).to_have_count(0)
    expect(page.locator('button:has-text("Encrypt")')).to_be_enabled()


def test_clear_forgets_the_additional_namespaces(page: Page):
    disable_namespace_listing(page)
    SealingApi(page)
    page.goto("/")
    secret_name(page)
    add_secret_key_value(page)
    page.fill("input#namespaceSelection", "team-a")
    add_additional_namespaces(page, ["team-b"])
    click_encrypt_button(page)
    expect(page.locator(".result-card")).to_have_count(2)

    page.get_by_role("button", name="Clear").click()
    page.fill("input#namespaceSelection", "team-a")

    expect(page.locator("input#additionalNamespaces")).to_have_count(1)
    expect(additional_namespace_chips(page)).to_have_count(0)


def test_secret_form_with_value(app_page: Page):
    page = app_page
    api = SealingApi(page)

    disabled_encrypt_button(page)
    namespace = namespace_select(page)
    secret_name(page)
    scope_strict(page)
    add_secret_key_value(page)
    click_encrypt_button(page)

    # exact text: this is what users copy into their manifests (the strict
    # scope has no annotations line)
    assert sealed_secret_yaml(page) == (
        "apiVersion: bitnami.com/v1alpha1\n"
        "kind: SealedSecret\n"
        "metadata:\n"
        f"  name: {SECRET_NAME}\n"
        f"  namespace: {namespace}\n"
        "spec:\n"
        "  encryptedData: \n"
        f"    {SECRET_KEY}: {SEALED_VALUE}"
    )
    assert api.only_request == {
        "secret": SECRET_NAME,
        "namespace": namespace,
        "scope": "strict",
        "secrets": [{"key": SECRET_KEY, "value": b64(SECRET_VALUE)}],
    }

    # one card per key with the sealed value
    key_card = page.locator(".secret-key-card")
    expect(key_card).to_have_count(1)
    expect(key_card.locator(".secret-key-card__name")).to_have_text(SECRET_KEY)
    expect(key_card.locator("code")).to_have_text(SEALED_VALUE)


def test_secret_form_with_file(app_page: Page, tmp_path):
    page = app_page
    api = SealingApi(page)

    disabled_encrypt_button(page)
    namespace = namespace_select(page)
    secret_name(page)
    scope_strict(page)
    add_secret_key_file(page, tmp_path)
    click_encrypt_button(page)

    expect(page.locator("#sealed-secret-result")).to_contain_text(
        f"    {SECRET_KEY}: {SEALED_VALUE}"
    )
    assert api.only_request == {
        "secret": SECRET_NAME,
        "namespace": namespace,
        "scope": "strict",
        "secrets": [{"key": SECRET_KEY, "file": b64(FILE_CONTENT)}],
    }


def test_namespace_wide_result_without_secret_name(app_page: Page):
    page = app_page
    api = SealingApi(page)

    disabled_encrypt_button(page)
    select_scope(page, "namespace-wide")
    namespace = namespace_select(page)
    add_secret_key_value(page)
    click_encrypt_button(page)

    assert sealed_secret_yaml(page) == (
        "apiVersion: bitnami.com/v1alpha1\n"
        "kind: SealedSecret\n"
        "metadata:\n"
        "  name: # no secret name given\n"
        f"  namespace: {namespace}\n"
        '  annotations: { sealedsecrets.bitnami.com/namespace-wide: "true" }\n'
        "spec:\n"
        "  encryptedData: \n"
        f"    {SECRET_KEY}: {SEALED_VALUE}"
    )
    request = api.only_request
    assert request["secret"] == ""
    assert request["namespace"] == namespace
    assert request["scope"] == "namespace-wide"
    assert request["secrets"] == [{"key": SECRET_KEY, "value": b64(SECRET_VALUE)}]


def test_failed_sealing_keeps_the_form_and_shows_the_error(app_page: Page):
    page = app_page
    detail = "Failed to seal secrets. See the API logs for details."
    api = SealingApi(page, status=500, body={"detail": detail})

    namespace_select(page)
    secret_name(page)
    add_secret_key_value(page)
    click_encrypt_button(page)

    snackbar = page.locator(".v-snackbar").get_by_text(
        f"Failed to seal secrets. Error Message: HTTP 500 - {detail}"
    )
    expect(snackbar).to_be_visible()
    assert len(api.requests) == 1

    # the form with everything the user entered is still there
    expect(page.locator("#sealed-secret-result")).to_have_count(0)
    expect(page.locator("#secretName")).to_have_value(SECRET_NAME)
    expect(page.locator("input#secretKey-0")).to_have_value(SECRET_KEY)
    expect(page.locator("textarea#secretValue-0")).to_have_value(SECRET_VALUE)

    # a failed attempt does not lock the form: the user can simply try again
    expect(page.locator('button:has-text("Encrypt")')).to_be_enabled()
    api.status, api.body = 200, None
    click_encrypt_button(page)
    expect(page.locator("#sealed-secret-result")).to_be_visible()
    assert len(api.requests) == 2
    expect(snackbar).to_be_hidden()


def test_result_cards_show_their_title_above_the_content(app_page: Page):
    page = app_page
    SealingApi(page)
    seal_one_value(page)

    for card in (".result-card", ".secret-key-card"):
        title = page.locator(f"{card} .v-card-title").bounding_box()
        content = page.locator(f"{card} pre").bounding_box()
        buttons = page.locator(f"{card} .v-card-title .v-btn")
        expect(page.locator(f"{card} .v-card-title .copy-btn")).to_have_count(1)
        last = buttons.last.bounding_box()
        assert title["y"] + title["height"] <= content["y"], card
        # the buttons sit in the header, at its right
        for button in buttons.all():
            box = button.bounding_box()
            assert title["y"] <= box["y"] and box["y"] + box["height"] <= title["y"] + title["height"], card
        assert last["x"] + last["width"] >= title["x"] + title["width"] - 32, card


def test_logo_and_header_buttons_do_not_overlap_on_a_phone(page: Page):
    page.set_viewport_size({"width": 375, "height": 800})
    page.goto("/")
    logo = page.locator("#logo-img").bounding_box()
    toggle = dark_mode_toggle(page).bounding_box()

    assert logo["x"] >= 0
    assert logo["x"] + logo["width"] <= toggle["x"]
    assert toggle["x"] + toggle["width"] <= 375
    assert page.evaluate("document.documentElement.scrollWidth") <= 375


def test_clear_on_result_view_returns_to_an_empty_form(app_page: Page):
    page = app_page
    SealingApi(page)
    seal_one_value(page)

    page.get_by_role("button", name="Clear").click()

    expect(page.locator("#sealed-secret-result")).to_have_count(0)
    expect(page.locator("#secretName")).to_have_value("")
    expect(page.locator("input#secretKey-0")).to_have_value("")
    expect(page.locator("textarea#secretValue-0")).to_have_value("")
    # Vuetify keeps an (empty) selection element for the empty string
    expect(page.locator(".v-autocomplete__selection-text")).to_have_text("")
    expect(page.locator("input#namespaceSelection")).to_have_value("")
    expect(page.locator('button:has-text("Encrypt")')).to_be_disabled()


def serve_default_scope(page: Page, default_scope):
    """Serve config.json with `default_scope` (the chart's `defaultScope`)."""

    def config_json(route: Route):
        config = route.fetch().json()
        config["default_scope"] = default_scope
        route.fulfill(json=config)

    page.route("**/config.json", config_json)


def selected_scope(page: Page):
    return page.locator('.scope-toggle button[aria-pressed="true"]')


def test_configured_default_scope_is_used_at_start_and_after_clear(page: Page):
    serve_default_scope(page, "namespace-wide")
    api = SealingApi(page)
    page.goto("/")

    expect(selected_scope(page)).to_have_attribute("data-scope", "namespace-wide")
    # the secret name is optional in this scope
    namespace_select(page)
    add_secret_key_value(page)
    click_encrypt_button(page)
    assert api.only_request["scope"] == "namespace-wide"

    page.get_by_role("button", name="Clear").click()
    expect(page.locator("#sealed-secret-result")).to_have_count(0)
    expect(selected_scope(page)).to_have_attribute("data-scope", "namespace-wide")

    # another scope can still be picked for a secret
    select_scope(page, "strict")
    expect(selected_scope(page)).to_have_attribute("data-scope", "strict")


def test_scope_picked_while_config_loads_is_kept(page: Page):
    # config.json is held back until the user has picked a scope
    held: list[Route] = []

    def hold(route: Route):
        held.append(route)

    page.route("**/config.json", hold)
    page.goto("/")
    page.wait_for_selector(".scope-toggle")

    # away from strict and back again: still a choice of the user
    select_scope(page, "namespace-wide")
    select_scope(page, "strict")

    page.wait_for_function("() => true")  # let the request reach the route
    assert len(held) == 1
    config = json.loads(
        (pathlib.Path(__file__).parent.parent / "public" / "config.json").read_text()
    )
    config["default_scope"] = "cluster-wide"
    held[0].fulfill(json=config)

    # the namespaces are loaded after config.json: wait for them
    namespace_select(page)
    expect(selected_scope(page)).to_have_attribute("data-scope", "strict")


def test_unknown_default_scope_falls_back_to_strict(page: Page):
    serve_default_scope(page, "global")
    # strict is also the scope before config.json is loaded: wait for the
    # warning, so that the check is about the loaded configuration
    with page.expect_console_message(
        predicate=lambda message: "Unknown default_scope" in message.text
    ):
        page.goto("/")

    expect(selected_scope(page)).to_have_count(1)
    expect(selected_scope(page)).to_have_attribute("data-scope", "strict")


def test_copy_buttons_copy_the_displayed_text(app_page: Page):
    page = app_page
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    SealingApi(page)
    seal_one_value(page)
    displayed_yaml = sealed_secret_yaml(page)

    # the first button of the manifest card (its label changes while it is copied)
    copy_manifest = page.locator(".result-card .copy-btn").first
    copy_manifest.click()

    expect(page.locator(".v-snackbar").get_by_text("Sealed secret copied to clipboard!")).to_be_visible()
    assert page.evaluate("navigator.clipboard.readText()") == displayed_yaml
    # the button confirms the copy for a moment, then offers it again
    expect(copy_manifest).to_have_text("Copied!")
    expect(copy_manifest.locator(".mdi-check")).to_have_count(1)
    expect(copy_manifest).to_have_text("Copy", timeout=5000)
    expect(copy_manifest.locator(".mdi-content-copy")).to_have_count(1)

    page.locator(".secret-key-card").get_by_role("button", name=f"Copy {SECRET_KEY}").click()

    expect(
        page.locator(".v-snackbar").get_by_text(f'Secret key "{SECRET_KEY}" copied to clipboard!')
    ).to_be_visible()
    assert page.evaluate("navigator.clipboard.readText()") == SEALED_VALUE


def test_copy_buttons_of_the_result_have_distinct_names(app_page: Page):
    page = app_page
    SealingApi(page, body=[
        {"key": "ONE", "value": SEALED_VALUE},
        {"key": "TWO", "value": SEALED_VALUE},
    ])
    seal_one_value(page)

    # each button's name starts with its visible text "Copy" and says what it copies
    for name in ("Copy manifest", "Copy ONE", "Copy TWO"):
        expect(page.get_by_role("button", name=name, exact=True)).to_have_count(1)


def test_copy_works_without_the_async_clipboard_api(page: Page):
    # served over plain HTTP the browser has no navigator.clipboard
    page.add_init_script(
        "Object.defineProperty(Navigator.prototype, 'clipboard', { get: () => undefined })"
    )
    page.goto("/")
    SealingApi(page)
    seal_one_value(page)
    assert page.evaluate("navigator.clipboard === undefined")

    copy_manifest = page.get_by_role("button", name="Copy manifest")
    expect(copy_manifest).to_be_visible()
    copy_manifest.click()

    expect(page.locator(".v-snackbar").get_by_text("Sealed secret copied to clipboard!")).to_be_visible()


def test_edit_on_result_view_returns_to_the_filled_form(app_page: Page):
    page = app_page
    SealingApi(page)
    namespace = seal_one_value(page)

    page.get_by_role("button", name="Edit Secrets").click()

    expect(page.locator("#sealed-secret-result")).to_have_count(0)
    expect(page.locator("#secretName")).to_have_value(SECRET_NAME)
    expect(page.locator("input#secretKey-0")).to_have_value(SECRET_KEY)
    expect(page.locator("textarea#secretValue-0")).to_have_value(SECRET_VALUE)
    expect(page.locator(".v-autocomplete__selection-text")).to_have_text(namespace)
    expect(page.locator('button:has-text("Encrypt")')).to_be_enabled()


@pytest.mark.parametrize("reduced_motion", [True, False])
def test_focus_follows_the_view_swaps(page: Page, reduced_motion: bool):
    page.emulate_media(reduced_motion="reduce" if reduced_motion else "no-preference")
    page.goto("/")
    SealingApi(page)
    # the first appearance of the form must not grab the focus
    page.locator("input#namespaceSelection").wait_for()
    assert page.evaluate("document.activeElement === document.body")

    seal_one_value(page)
    # the result is announced by its title, not left to the removed form
    expect(page.locator(".result-card__title")).to_be_focused()

    page.get_by_role("button", name="Edit Secrets").click()
    expect(page.locator("input#namespaceSelection")).to_be_focused()

    click_encrypt_button(page)
    expect(page.locator(".result-card__title")).to_be_focused()
    page.get_by_role("button", name="Clear").click()
    expect(page.locator("input#namespaceSelection")).to_be_focused()


def test_edit_focuses_the_secret_name_of_a_cluster_wide_secret(app_page: Page):
    page = app_page
    SealingApi(page)
    page.locator("input#secretKey-0").wait_for()
    select_scope(page, "cluster-wide")
    secret_name(page)
    add_secret_key_value(page)
    click_encrypt_button(page)
    expect(page.locator("#sealed-secret-result")).to_be_visible()

    page.get_by_role("button", name="Edit Secrets").click()

    # the namespace is disabled for this scope
    expect(page.locator("#secretName")).to_be_focused()


def test_form_stays_visible_while_sealing(app_page: Page):
    page = app_page
    api = SealingApi(page, hold=True)
    namespace_select(page)
    secret_name(page)
    add_secret_key_value(page)
    click_encrypt_button(page)

    button = page.get_by_role("button", name="Sealing…")
    expect(button).to_be_disabled()
    expect(button).to_have_attribute("aria-busy", "true")
    expect(button.locator(".mdi-lock-open-variant")).to_have_count(1)
    # no spinner instead of the form: everything entered is still on screen
    expect(page.locator(".v-progress-circular")).to_have_count(0)
    expect(page.locator("#secretName")).to_be_visible()
    expect(page.locator("input#secretKey-0")).to_have_value(SECRET_KEY)
    expect(page.locator("textarea#secretValue-0")).to_be_visible()

    # screen readers hear that something is happening (the form is inert)
    expect(page.locator(".seal-status")).to_have_text("Sealing…")

    # neither the button nor the shortcut seals a second time
    page.keyboard.press("Control+Enter")
    page.keyboard.press("Meta+Enter")
    page.wait_for_timeout(200)
    assert len(api.requests) == 1

    # the sealed secret closes the lock, then the result replaces the form
    api.release()
    expect(button.locator(".mdi-lock")).to_have_count(1)
    expect(page.locator("#sealed-secret-result")).to_be_visible()
    expect(page.locator("#secretName")).to_have_count(0)
    expect(page.locator(".seal-status")).to_have_text("Sealed secret ready.")
    assert len(api.requests) == 1


def test_failed_sealing_gives_the_form_back(app_page: Page):
    page = app_page
    api = SealingApi(page, status=500, body={"detail": "boom"}, hold=True)
    namespace_select(page)
    secret_name(page)
    add_secret_key_value(page)
    click_encrypt_button(page)
    expect(page.get_by_role("button", name="Sealing…")).to_be_disabled()

    api.release()

    expect(page.get_by_role("button", name="Encrypt")).to_be_enabled()
    expect(page.get_by_role("button", name="Encrypt")).to_be_focused()
    expect(page.locator("#secretName")).to_be_editable()
    assert len(api.requests) == 1


# While Vue swaps the views it puts these classes on them for the duration of
# the transition, and the form is a .modern-card that has a transition of its own,
# so the probe is such a card. (The classes are on for a single frame when there
# is no transition, too short to observe, hence the probe.)
SWAP_PROBE = """(state) => {
    const probe = document.createElement('div')
    probe.className = `modern-card swap-${state}-active`
    document.body.appendChild(probe)
    const duration = getComputedStyle(probe).transitionDuration
    probe.remove()
    return duration
}"""


@pytest.mark.parametrize("reduced_motion", [True, False])
def test_swap_to_the_result_is_instant_for_reduced_motion(page: Page, reduced_motion: bool):
    page.emulate_media(reduced_motion="reduce" if reduced_motion else "no-preference")
    page.goto("/")
    SealingApi(page)
    seal_one_value(page)

    durations = {state: page.evaluate(SWAP_PROBE, state) for state in ("enter", "leave")}
    if reduced_motion:
        assert durations == {"enter": "0s", "leave": "0s"}
    else:
        assert durations == {"enter": "0.28s, 0.28s", "leave": "0.15s, 0.15s"}
    # and the result is there to use at once
    expect(page.get_by_role("button", name="Edit Secrets")).to_be_visible()


def test_lock_snaps_shut_unless_motion_is_reduced(app_page: Page):
    page = app_page
    api = SealingApi(page, hold=True)
    namespace_select(page)
    secret_name(page)
    add_secret_key_value(page)
    click_encrypt_button(page)
    page.get_by_role("button", name="Sealing…").wait_for()
    api.release()

    lock = page.locator(".encrypt-btn .mdi-lock.lock-snap")
    expect(lock).to_have_count(1)
    assert lock.evaluate("el => getComputedStyle(el).animationName") == "lock-snap"
    page.emulate_media(reduced_motion="reduce")
    assert lock.evaluate("el => getComputedStyle(el).animationName") == "none"


def test_result_shows_a_summary_of_what_was_sealed(app_page: Page):
    page = app_page
    SealingApi(page)
    namespace = seal_one_value(page)

    summary = page.get_by_role("group", name="Summary")
    expect(summary.locator(".v-chip")).to_have_text(["1 key", namespace, "strict scope"])


def test_summary_counts_keys_and_names_cluster_wide(app_page: Page):
    page = app_page
    SealingApi(page)
    select_scope(page, "cluster-wide")
    add_secret_key_value(page)
    page.get_by_role("button", name="Add key-value pair").click()
    page.fill("input#secretKey-1", "second")
    page.fill("textarea#secretValue-1", "value")
    click_encrypt_button(page)

    summary = page.get_by_role("group", name="Summary")
    expect(summary.locator(".v-chip")).to_have_text(["2 keys", "cluster-wide"])


def test_manifest_is_highlighted_and_wraps(app_page: Page):
    page = app_page
    long_value = "Ag" + "A" * 3000
    SealingApi(page, body=[{"key": SECRET_KEY, "value": long_value}])
    seal_one_value(page)

    result = page.locator("#sealed-secret-result")
    expect(result.locator(".yaml-key").first).to_have_text("apiVersion")
    expect(result.locator(".yaml-key")).to_have_text(
        ["apiVersion", "kind", "metadata", "name", "namespace", "spec", "encryptedData", SECRET_KEY]
    )
    expect(result.locator(".yaml-punctuation").first).to_have_text(":")
    # the colours are there, and differ between keys and values
    key_color = result.locator(".yaml-key").first.evaluate("el => getComputedStyle(el).color")
    text_color = result.evaluate("el => getComputedStyle(el).color")
    assert key_color != text_color
    # still the plain manifest for selecting and copying
    assert sealed_secret_yaml(page).endswith(f"    {SECRET_KEY}: {long_value}")
    # long values wrap instead of scrolling sideways
    box = page.locator(".result-card pre")
    assert box.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
    assert page.evaluate("document.documentElement.scrollWidth") <= 1280


def test_manifest_has_no_empty_annotations_for_the_strict_scope(app_page: Page):
    page = app_page
    SealingApi(page)
    seal_one_value(page)
    assert "annotations" not in sealed_secret_yaml(page)


def test_download_saves_the_manifest_named_after_the_secret(app_page: Page):
    page = app_page
    SealingApi(page)
    seal_one_value(page)
    displayed_yaml = sealed_secret_yaml(page)

    with page.expect_download() as download_info:
        page.get_by_role("button", name="Download .yaml").click()

    download = download_info.value
    assert download.suggested_filename == f"{SECRET_NAME}.yaml"
    with open(download.path(), encoding="utf-8") as saved:
        assert saved.read() == displayed_yaml
    expect(page.locator(".v-snackbar").get_by_text(f"Downloaded {SECRET_NAME}.yaml")).to_be_visible()


def test_download_without_a_secret_name_is_called_sealed_secret(app_page: Page):
    page = app_page
    SealingApi(page)
    select_scope(page, "cluster-wide")
    add_secret_key_value(page)
    click_encrypt_button(page)
    expect(page.locator("#sealed-secret-result")).to_be_visible()

    with page.expect_download() as download_info:
        page.get_by_role("button", name="Download .yaml").click()

    assert download_info.value.suggested_filename == "sealed-secret.yaml"


@pytest.mark.parametrize("width", [375, 1280])
def test_snackbars_stay_clear_of_the_result_actions(page: Page, width: int):
    page.set_viewport_size({"width": width, "height": 800})
    page.goto("/")
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    SealingApi(page)
    seal_one_value(page)

    page.get_by_role("button", name="Copy manifest").click()
    snackbar = page.locator(".v-snackbar__wrapper", has_text="Sealed secret copied")
    expect(snackbar).to_be_visible()
    # let its entry transition finish
    page.wait_for_timeout(400)
    toast = snackbar.bounding_box()
    bar = page.locator(".glass-app-bar").bounding_box()

    assert toast["y"] >= bar["y"] + bar["height"], "the snackbar is below the app bar"
    assert toast["x"] >= 0 and toast["x"] + toast["width"] <= width
    # the actions of the card are not covered either, at the top of the page
    # (a page scrolled further puts any content under the snackbar)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    for button in page.locator(".result-card .v-card-title .v-btn").all():
        assert not boxes_overlap(toast, button.bounding_box()), button.inner_text()
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(100)
    for name in ("Clear", "Edit Secrets"):
        button = page.get_by_role("button", name=name).bounding_box()
        assert not boxes_overlap(toast, button), name
    # and a click on them goes through
    page.get_by_role("button", name="Edit Secrets").click()
    expect(page.locator("#secretName")).to_be_visible()


def test_an_error_replaces_a_success_message_instead_of_overlapping_it(app_page: Page):
    page = app_page
    drop_files(
        page,
        [
            (".env", "A=1\nB=2", ""),
            ("big.bin", "x" * (ONE_MEBIBYTE + 1), "application/octet-stream"),
        ],
    )

    expect(page.locator(".v-snackbar").get_by_text("File size should be less than 1 MB!")).to_be_visible()
    # the import itself is not affected
    assert key_value_pairs(page) == [("A", "1"), ("B", "2")]
    expect(page.locator(".v-snackbar").get_by_text("Imported 2 keys")).to_have_count(0)


def boxes_overlap(a: dict, b: dict) -> bool:
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


def inside(box: dict, container: dict) -> bool:
    return (
        box["x"] >= container["x"] - 0.5
        and box["x"] + box["width"] <= container["x"] + container["width"] + 0.5
        and box["y"] >= container["y"] - 0.5
        and box["y"] + box["height"] <= container["y"] + container["height"] + 0.5
    )


@pytest.mark.parametrize("width", [375, 1280])
def test_result_fits_the_screen_with_long_keys_and_values(page: Page, width: int):
    page.set_viewport_size({"width": width, "height": 800})
    page.goto("/")
    long_key = "A_VERY_LONG_KEY_" + "X" * 44
    SealingApi(page, body=[
        {"key": "POSTGRES_PASSWORD", "value": "Ag" + "B" * 2000},
        {"key": long_key, "value": SEALED_VALUE},
        {"key": "short", "value": SEALED_VALUE},
    ])
    namespace_select(page)
    secret_name(page)
    add_secret_key_value(page)
    click_encrypt_button(page)
    expect(page.locator("#sealed-secret-result")).to_be_visible()

    assert page.evaluate("document.documentElement.scrollWidth") <= width
    main_card = page.locator(".result-card").bounding_box()
    assert main_card["x"] >= 0 and main_card["x"] + main_card["width"] <= width
    for button in page.locator(".result-card .v-card-title .v-btn").all():
        assert inside(button.bounding_box(), main_card), button.inner_text()

    cards = page.locator(".secret-key-card")
    expect(cards).to_have_count(3)
    for card in cards.all():
        card_box = card.bounding_box()
        assert card_box["x"] >= 0 and card_box["x"] + card_box["width"] <= width
        copy = card.get_by_role("button", name=re.compile("^Copy "))
        expect(copy).to_be_visible()
        assert inside(copy.bounding_box(), card_box), card.inner_text()
    # a cut-off name is still available in full
    expect(page.locator(".secret-key-card__name", has_text="A_VERY_LONG")).to_have_attribute(
        "title", long_key
    )


LONG_SEALED_VALUE = "Ag" + "Bx9Qz" * 200


def seal_with_values(page: Page, values: dict[str, str]):
    SealingApi(page, body=[{"key": key, "value": value} for key, value in values.items()])
    seal_one_value(page)


def key_card(page: Page, key: str):
    return page.locator(".secret-key-card").filter(
        has=page.locator(".secret-key-card__name", has_text=key)
    )


@pytest.mark.parametrize("width", [375, 1280])
def test_long_values_are_cut_to_an_excerpt_until_expanded(page: Page, width: int):
    page.set_viewport_size({"width": width, "height": 800})
    page.goto("/")
    seal_with_values(page, {"LONG": LONG_SEALED_VALUE})
    card = key_card(page, "LONG")
    value = card.locator("pre")
    toggle = card.get_by_role("button", name="Show all of LONG")
    expect(toggle).to_have_text("Show all")
    expect(toggle).to_have_attribute("aria-expanded", "false")

    # visually about three lines (plus the padding of the block) ...
    line_height = card.locator("code").evaluate("el => parseFloat(getComputedStyle(el).lineHeight)")
    clamped = value.bounding_box()["height"]
    assert clamped <= line_height * 3 + 40, clamped
    card_height = card.bounding_box()["height"]
    # ... while the whole value is still there to select and copy
    assert card.locator("code").text_content() == LONG_SEALED_VALUE
    assert card.locator("code").inner_text() == LONG_SEALED_VALUE

    toggle = card.get_by_role("button", name="Show less of LONG")
    card.get_by_role("button", name="Show all of LONG").click()
    expect(toggle).to_have_text("Show less")
    expect(toggle).to_have_attribute("aria-expanded", "true")
    expanded = value.bounding_box()["height"]
    assert expanded > clamped * 2, (expanded, clamped)
    # the code is not cut off any more: its box holds all of its text
    assert card.locator("code").evaluate("el => el.scrollHeight <= el.clientHeight + 1")
    assert card.bounding_box()["height"] > card_height

    toggle.click()
    expect(card.get_by_role("button", name="Show all of LONG")).to_have_attribute(
        "aria-expanded", "false"
    )
    assert value.bounding_box()["height"] == clamped
    assert page.evaluate("document.documentElement.scrollWidth") <= width


def test_short_values_have_no_toggle(app_page: Page):
    page = app_page
    seal_with_values(page, {"SHORT": SEALED_VALUE, "LONG": LONG_SEALED_VALUE})

    expect(page.get_by_role("button", name=re.compile("^Show (all|less)"))).to_have_count(1)
    expect(key_card(page, "SHORT").get_by_role("button", name=re.compile("^Show "))).to_have_count(0)
    expect(key_card(page, "SHORT").locator("code")).to_have_text(SEALED_VALUE)


def test_long_value_cards_have_the_same_height(page: Page):
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto("/")
    seal_with_values(
        page,
        {"ONE": LONG_SEALED_VALUE, "TWO": "Ag" + "Kd7Lm" * 120, "THREE": "Ag" + "Qw3Rt" * 400},
    )
    heights = [card.bounding_box()["height"] for card in page.locator(".secret-key-card").all()]
    assert max(heights) - min(heights) <= 2, heights


def test_copy_copies_the_whole_value_not_the_excerpt(app_page: Page):
    page = app_page
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    seal_with_values(page, {"LONG": LONG_SEALED_VALUE})

    key_card(page, "LONG").get_by_role("button", name="Copy LONG").click()

    assert page.evaluate("navigator.clipboard.readText()") == LONG_SEALED_VALUE


def test_the_toggle_follows_the_width_of_the_card(page: Page):
    # fits three lines on a desktop, needs more on a phone
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto("/")
    seal_with_values(page, {"MEDIUM": "Ag" + "Bx9Qz" * 30})
    toggle = key_card(page, "MEDIUM").get_by_role("button", name=re.compile("^Show "))
    expect(toggle).to_have_count(0)

    page.set_viewport_size({"width": 375, "height": 800})
    expect(toggle).to_have_count(1)
    page.set_viewport_size({"width": 1280, "height": 800})
    expect(toggle).to_have_count(0)


def test_a_single_key_card_is_centred(app_page: Page):
    page = app_page
    SealingApi(page)
    seal_one_value(page)

    card = page.locator(".secret-key-card").bounding_box()
    area = page.locator(".key-cards").bounding_box()
    left, right = card["x"] - area["x"], area["x"] + area["width"] - (card["x"] + card["width"])
    assert abs(left - right) <= 2


def test_removing_a_row_keeps_the_other_rows_intact(app_page: Page):
    page = app_page
    add_button = page.get_by_role("button", name="Add key-value pair")
    add_button.click()
    add_button.click()
    expect(page.locator("input[id^='secretKey-']")).to_have_count(3)
    assert duplicate_ids(page) == []

    page.fill("input#secretKey-0", "first-key")
    page.fill("textarea#secretValue-0", "first value")
    # the middle row has been edited and shows a validation error
    page.fill("input#secretKey-1", "second-key")
    page.fill("input#secretKey-1", "")
    expect(page.locator(".secret-row:has(#secretKey-1) .v-input--error")).to_have_count(1)
    # the last row is valid (a new row takes the focus, so an empty key would
    # already count as visited)
    page.fill("input#secretKey-2", "third-key")
    page.fill("textarea#secretValue-2", "third value")
    expect(page.locator(".secret-row:has(#secretKey-2) .v-input--error")).to_have_count(0)

    # remove the middle row with its delete icon
    page.get_by_role("button", name="Remove pair 2").click()

    expect(page.locator("input[id^='secretKey-']")).to_have_count(2)
    expect(page.locator("input#secretKey-0")).to_have_value("first-key")
    expect(page.locator("textarea#secretValue-0")).to_have_value("first value")
    expect(page.locator("input#secretKey-1")).to_have_value("third-key")
    expect(page.locator("textarea#secretValue-1")).to_have_value("third value")
    # the error went away with the removed row instead of moving to its neighbour
    expect(page.locator(".secret-row:has(#secretKey-1) .v-input--error")).to_have_count(0)
    assert duplicate_ids(page) == []


def test_removing_the_only_row_leaves_a_blank_row(app_page: Page):
    page = app_page
    add_secret_key_value(page)

    page.get_by_role("button", name="Remove pair 1").click()

    expect(page.locator("input[id^='secretKey-']")).to_have_count(1)
    expect(page.locator("input#secretKey-0")).to_have_value("")
    expect(page.locator("textarea#secretValue-0")).to_have_value("")


def test_remove_all_leaves_one_blank_row(app_page: Page):
    page = app_page
    add_secret_key_value(page)
    page.get_by_role("button", name="Add key-value pair").click()
    page.fill("input#secretKey-1", "another-key")

    page.get_by_role("button", name="Remove All").click()

    expect(page.locator("input[id^='secretKey-']")).to_have_count(1)
    expect(page.locator("input#secretKey-0")).to_have_value("")
    expect(page.locator("textarea#secretValue-0")).to_have_value("")


def test_duplicate_keys_are_marked_and_block_encrypting(app_page: Page):
    page = app_page
    namespace_select(page)
    secret_name(page)
    add_secret_key_value(page)
    page.get_by_role("button", name="Add key-value pair").click()
    page.fill("input#secretKey-1", "other-key")
    page.fill("textarea#secretValue-1", "other value")
    expect(page.locator('button:has-text("Encrypt")')).to_be_enabled()
    expect(page.locator(".v-messages__message", has_text="Duplicate key")).to_have_count(0)

    # the same key in a second row marks both rows and blocks sealing
    page.fill("input#secretKey-1", SECRET_KEY)
    for row in ("0", "1"):
        expect(
            page.locator(f".secret-row:has(#secretKey-{row}) .v-messages__message")
        ).to_have_text("Duplicate key")
    expect(page.locator('button:has-text("Encrypt")')).to_be_disabled()

    # a third row with an empty key is not a duplicate of anything
    page.get_by_role("button", name="Add key-value pair").click()
    expect(page.locator(".secret-row:has(#secretKey-2) .v-input--error")).to_have_count(0)

    # renaming one of the rows resolves both
    page.fill("input#secretKey-1", "other-key")
    expect(page.locator(".v-messages__message", has_text="Duplicate key")).to_have_count(0)
    page.get_by_role("button", name="Remove pair 3").click()
    expect(page.locator('button:has-text("Encrypt")')).to_be_enabled()


def test_row_layout_does_not_depend_on_the_content(app_page: Page, tmp_path):
    page = app_page
    page.set_viewport_size({"width": 1280, "height": 900})
    # the column, not the input: the input gives way to the clear icon
    key = page.locator(".secret-row__key")
    key.wait_for()

    def boxes():
        return (
            key.bounding_box(),
            page.locator(".secret-row__value").bounding_box(),
            page.evaluate("document.documentElement.scrollWidth"),
        )

    empty = boxes()
    key_box, value_box, _ = empty
    # key about a third, value about two thirds
    assert 1.8 < value_box["width"] / key_box["width"] < 2.2

    page.fill("input#secretKey-0", SECRET_KEY)
    page.fill("textarea#secretValue-0", SECRET_VALUE)
    with_value = boxes()
    page.fill("textarea#secretValue-0", "")
    page.locator("input#fileInput-0").set_input_files(
        write_file(tmp_path, "layout.txt", FILE_CONTENT)
    )
    expect(page.locator(".secret-file")).to_be_visible()
    with_file = boxes()

    for other in (with_value, with_file):
        assert other[0]["width"] == empty[0]["width"]
        assert other[1]["width"] == empty[1]["width"]
        assert other[2] <= 1280


def test_file_is_chosen_with_the_paperclip_and_removed_with_its_chip(
    app_page: Page, tmp_path
):
    page = app_page
    page.fill("input#secretKey-0", SECRET_KEY)
    paperclip = page.get_by_role("button", name="Upload file as value")

    with page.expect_file_chooser() as chooser:
        paperclip.click()
    chooser.value.set_files(write_file(tmp_path, "cert.pem", FILE_CONTENT))

    chip = page.locator(".secret-file")
    expect(chip).to_contain_text("cert.pem")
    expect(chip).to_contain_text(f"{len(FILE_CONTENT)} B")
    expect(page.locator("textarea#secretValue-0")).to_have_count(0)

    # removing the chip brings the text input back, and the file can be chosen again
    chip.get_by_label("Remove file").click()
    expect(chip).to_have_count(0)
    expect(page.locator("textarea#secretValue-0")).to_have_value("")
    page.locator("input#fileInput-0").set_input_files(
        write_file(tmp_path, "cert.pem", FILE_CONTENT)
    )
    expect(chip).to_contain_text("cert.pem")


def test_paperclip_is_off_while_a_value_is_typed(app_page: Page):
    page = app_page
    paperclip = page.get_by_role("button", name="Upload file as value")
    expect(paperclip).to_be_enabled()
    page.fill("textarea#secretValue-0", SECRET_VALUE)
    expect(paperclip).to_be_disabled()
    page.fill("textarea#secretValue-0", "")
    expect(paperclip).to_be_enabled()


def test_value_is_masked_until_revealed(app_page: Page):
    page = app_page
    api = SealingApi(page)
    value = page.locator("textarea#secretValue-0")
    text_security = "getComputedStyle(element).webkitTextSecurity"

    # typing works as usual, but the characters are not shown
    value.fill("line one\nline two")
    expect(value).to_have_value("line one\nline two")
    assert value.evaluate(f"(element) => {text_security}") == "disc"

    # the name stays the same, only the pressed state tells what it does
    reveal = page.get_by_role("button", name="Show value")
    expect(reveal).to_have_attribute("aria-pressed", "false")
    reveal.click()
    expect(reveal).to_have_attribute("aria-pressed", "true")
    expect(reveal).to_have_attribute("aria-label", "Show value")
    assert value.evaluate(f"(element) => {text_security}") == "none"
    reveal.click()
    expect(reveal).to_have_attribute("aria-pressed", "false")
    assert value.evaluate(f"(element) => {text_security}") == "disc"

    # sealing sends what was typed, not what is displayed
    namespace_select(page)
    secret_name(page)
    scope_strict(page)
    page.fill("input#secretKey-0", SECRET_KEY)
    click_encrypt_button(page)
    assert api.only_request["secrets"] == [
        {"key": SECRET_KEY, "value": b64("line one\nline two")}
    ]


def test_rows_are_cards_and_all_actions_fit_on_a_phone(page: Page):
    enable_sealed_secret_import(page)
    page.set_viewport_size({"width": 375, "height": 800})
    page.goto("/")
    namespace_select(page)
    page.get_by_role("button", name="Add key-value pair").click()

    for name in ("Import existing sealed secret", "Remove All", "Remove pair 1"):
        button = page.get_by_role("button", name=name)
        expect(button).to_be_visible()
        box = button.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 375, name
    assert page.evaluate("document.documentElement.scrollWidth") <= 375

    # every pair is a bordered card numbered in its header, key above value
    rows = page.locator(".secret-row")
    expect(rows).to_have_count(2)
    expect(rows.nth(1).locator(".secret-row__number")).to_have_text("#2")
    assert rows.nth(0).evaluate("(row) => getComputedStyle(row).borderTopWidth") == "1px"
    key_box = page.locator("input#secretKey-1").bounding_box()
    value_box = page.locator("textarea#secretValue-1").bounding_box()
    assert key_box["y"] < value_box["y"]


def test_row_buttons_have_accessible_names(app_page: Page):
    page = app_page
    for name in ("Remove pair 1", "Show value", "Upload file as value"):
        expect(page.get_by_role("button", name=name)).to_have_count(1)
    expect(page.get_by_role("textbox", name="Secret key")).to_have_count(1)
    expect(page.get_by_role("textbox", name="Secret value")).to_have_count(1)


def focused_name(page: Page) -> str:
    """The id or accessible name of the element that has the focus."""
    return page.evaluate(
        "document.activeElement.id || document.activeElement.getAttribute('aria-label')"
    )


@pytest.mark.parametrize("width", [1280, 375])
def test_tab_goes_through_a_row_from_key_to_remove(page: Page, width: int):
    page.set_viewport_size({"width": width, "height": 900})
    page.goto("/")
    page.get_by_role("button", name="Add key-value pair").click()
    page.fill("input#secretKey-0", SECRET_KEY)
    page.locator("input#secretKey-0").focus()

    order = []
    for _ in range(4):
        page.keyboard.press("Tab")
        order.append(focused_name(page))
    # the key field is followed by its value, the value's buttons and then
    # remove, before anything of the next row
    assert order == [
        "secretValue-0",
        "Show value",
        "Upload file as value",
        "Remove pair 1",
    ]
    page.keyboard.press("Tab")
    assert focused_name(page) == "secretKey-1"


def test_paperclip_explains_why_it_is_off(app_page: Page):
    page = app_page
    choosers = []

    def remember(chooser) -> None:
        choosers.append(chooser)

    page.on("filechooser", remember)
    hint = "Clear the value to upload a file instead"
    paperclip = page.get_by_role("button", name="Upload file as value")
    expect(paperclip).to_have_attribute("aria-disabled", "false")

    page.fill("textarea#secretValue-0", SECRET_VALUE)
    expect(paperclip).to_have_attribute("aria-disabled", "true")
    # exposed to assistive technology ...
    description_id = paperclip.get_attribute("aria-describedby")
    expect(page.locator(f"[id='{description_id}']")).to_have_text(hint)
    # ... and to sighted users, with the keyboard and with the mouse
    tooltip = page.locator(".v-tooltip.v-overlay--active", has_text=hint)
    page.get_by_role("button", name="Show value").focus()
    page.keyboard.press("Tab")
    expect(paperclip).to_be_focused()
    expect(tooltip).to_have_text(hint)
    page.locator("input#secretKey-0").focus()
    expect(tooltip).to_have_count(0)
    paperclip.hover()
    expect(tooltip).to_have_text(hint)

    # it still does nothing, with the mouse or the keyboard
    paperclip.click(force=True)
    page.keyboard.press("Enter")
    page.wait_for_timeout(200)
    assert choosers == []
    expect(page.locator("input#fileInput-0")).to_be_disabled()

    # and works again once the value is gone
    page.fill("textarea#secretValue-0", "")
    expect(paperclip).to_have_attribute("aria-disabled", "false")
    expect(page.locator(f"[id='{description_id}']")).to_have_count(0)
    with page.expect_file_chooser():
        paperclip.click()


def test_adding_a_pair_focuses_its_key(app_page: Page):
    page = app_page
    page.get_by_role("button", name="Add key-value pair").click()
    expect(page.locator("input#secretKey-1")).to_be_focused()
    # typing continues right there
    page.keyboard.type("second-key")
    expect(page.locator("input#secretKey-1")).to_have_value("second-key")
    expect(page.locator("input#secretKey-0")).to_have_value("")

    # also with the keyboard alone
    page.get_by_role("button", name="Add key-value pair").focus()
    page.keyboard.press("Enter")
    expect(page.locator("input#secretKey-2")).to_be_focused()


@pytest.mark.parametrize("shortcut", ["Control+Enter", "Meta+Enter"])
def test_ctrl_or_cmd_enter_seals_a_ready_form(app_page: Page, shortcut: str):
    page = app_page
    api = SealingApi(page)
    namespace = namespace_select(page)
    secret_name(page)
    page.fill("input#secretKey-0", SECRET_KEY)
    page.fill("textarea#secretValue-0", SECRET_VALUE)

    # works from the value, where plain Enter has to add a line
    page.locator("textarea#secretValue-0").press(shortcut)

    expect(page.locator("#sealed-secret-result")).to_be_visible()
    assert api.only_request["namespace"] == namespace
    assert api.only_request["secrets"] == [
        {"key": SECRET_KEY, "value": b64(SECRET_VALUE)}
    ]


def test_ctrl_enter_does_nothing_until_the_form_is_ready(app_page: Page):
    page = app_page
    api = SealingApi(page)
    namespace_select(page)
    secret_name(page)
    page.fill("input#secretKey-0", SECRET_KEY)
    # no value yet
    page.locator("input#secretKey-0").press("Control+Enter")
    page.wait_for_timeout(700)
    assert api.requests == []
    expect(page.locator("#sealed-secret-result")).to_have_count(0)

    # a duplicate key blocks it as well
    page.fill("textarea#secretValue-0", SECRET_VALUE)
    page.get_by_role("button", name="Add key-value pair").click()
    page.fill("input#secretKey-1", SECRET_KEY)
    page.fill("textarea#secretValue-1", SECRET_VALUE)
    page.keyboard.press("Control+Enter")
    page.wait_for_timeout(700)
    assert api.requests == []

    page.fill("input#secretKey-1", "other-key")
    page.keyboard.press("Control+Enter")
    expect(page.locator("#sealed-secret-result")).to_be_visible()
    assert len(api.requests) == 1


def test_ctrl_enter_on_an_incomplete_form_shows_what_is_missing(app_page: Page):
    page = app_page
    api = SealingApi(page)
    page.locator("input#secretKey-0").wait_for()
    # nothing was visited, so nothing complains yet
    expect(page.locator(".v-messages__message")).to_have_count(0)

    page.locator("input#secretKey-0").press("Control+Enter")

    assert api.requests == []
    # the namespace, name, key and value that are missing say so...
    expect(page.locator(".v-input--error")).to_have_count(4)
    for field in ("input#namespaceSelection", "#secretName", "input#secretKey-0", "textarea#secretValue-0"):
        expect(page.locator(f".v-input:has({field}) .v-messages__message")).to_have_text(
            "Must not be empty"
        )
    # ...and the first of them is where the user continues
    expect(page.locator("input#namespaceSelection")).to_be_focused()

    # filled in, the errors go and the shortcut seals
    namespace_select(page)
    secret_name(page)
    add_secret_key_value(page)
    expect(page.locator(".v-input--error")).to_have_count(0)
    page.keyboard.press("Control+Enter")
    expect(page.locator("#sealed-secret-result")).to_be_visible()


def test_ctrl_enter_on_an_invalid_form_shows_the_invalid_field(app_page: Page):
    page = app_page
    api = SealingApi(page)
    namespace_select(page)
    add_secret_key_value(page)
    # a second row that was never filled in
    page.get_by_role("button", name="Add key-value pair").click()
    expect(page.locator("input#secretKey-1")).to_be_focused()
    expect(page.locator(".v-messages__message")).to_have_count(0)
    page.locator("input#secretKey-1").press("Control+Enter")

    assert api.requests == []
    expect(page.locator(".v-input--error")).to_have_count(3)
    expect(page.locator("#secretName")).to_be_visible()
    expect(page.locator("#secretName")).to_be_focused()


def test_plain_enter_adds_a_line_to_the_value_and_does_not_seal(app_page: Page):
    page = app_page
    api = SealingApi(page)
    namespace_select(page)
    secret_name(page)
    page.fill("input#secretKey-0", SECRET_KEY)
    value = page.locator("textarea#secretValue-0")
    value.fill("one")
    value.press("Enter")
    value.press_sequentially("two")
    page.wait_for_timeout(300)
    expect(value).to_have_value("one\ntwo")
    assert api.requests == []


def test_ctrl_enter_is_ignored_outside_the_form(app_page: Page):
    page = app_page
    api = SealingApi(page)
    namespace_select(page)
    secret_name(page)
    add_secret_key_value(page)
    # focus on the page outside the form
    dark_mode_toggle(page).focus()
    page.keyboard.press("Control+Enter")
    page.wait_for_timeout(500)
    assert api.requests == []


def test_shortcut_is_shown_next_to_the_encrypt_button(app_page: Page):
    page = app_page
    hint = page.locator(".shortcut-hint kbd")
    expect(hint).to_be_visible()
    expect(hint).to_have_text(re.compile(r"^(Ctrl|⌘) Enter$"))
    expect(page.get_by_role("button", name="Encrypt")).to_have_attribute(
        "aria-keyshortcuts", "Control+Enter Meta+Enter"
    )
    assert page.evaluate("document.documentElement.scrollWidth") <= 1280


def drop_files(page: Page, files: list[tuple[str, str, str]], event: str = "drop"):
    """Drag files over the list and drop them there.

    Each file is (name, content, mime type). Playwright cannot start a native
    drag of a file, so the events carry a DataTransfer the page builds.
    """
    transfer = page.evaluate_handle(
        """(files) => {
            const transfer = new DataTransfer()
            for (const [name, content, type] of files) {
                transfer.items.add(new File([content], name, { type }))
            }
            return transfer
        }""",
        files,
    )
    target = ".secrets-list"
    page.dispatch_event(target, "dragenter", {"dataTransfer": transfer})
    page.dispatch_event(target, "dragover", {"dataTransfer": transfer})
    if event == "drop":
        page.dispatch_event(target, "drop", {"dataTransfer": transfer})
    return transfer


def test_remove_all_waits_for_dropped_files_that_are_still_read(app_page: Page):
    page = app_page
    # Hold every file read until the test lets it go.
    page.evaluate(
        """() => {
            const read = File.prototype.text
            window.releaseReads = []
            File.prototype.text = function () {
                return new Promise((resolve) => window.releaseReads.push(() => resolve(read.call(this))))
            }
        }"""
    )
    remove_all = page.get_by_role("button", name="Remove All")
    expect(remove_all).to_be_enabled()

    drop_files(page, [(".env", "A=1\nB=2", "")])
    # clearing now would not stick: the rows arrive once the file is read
    expect(remove_all).to_be_disabled()
    expect(page.get_by_role("button", name="Encrypt")).to_be_disabled()

    page.evaluate("() => window.releaseReads.forEach((release) => release())")
    expect(remove_all).to_be_enabled()
    assert key_value_pairs(page) == [("A", "1"), ("B", "2")]
    remove_all.click()
    assert key_value_pairs(page) == [("", "")]


def expect_key_value_pairs(page: Page, expected: list[tuple[str, str]]):
    """Wait for the rows of `expected`, then compare them.

    A dropped file is read asynchronously, so the rows arrive after the drop
    event: reading them right away can see the list half updated.
    """
    expect(page.locator(".secret-row")).to_have_count(len(expected))
    expect(page.locator("input#secretKey-" + str(len(expected) - 1))).to_have_value(
        expected[-1][0]
    )
    assert key_value_pairs(page) == expected


def key_value_pairs(page: Page) -> list[tuple[str, str]]:
    """(key, value) per row; the value of a row with a file is "<file>"."""
    pairs = []
    for row in page.locator(".secret-row").all():
        key = row.locator("input[id^='secretKey-']").input_value()
        text = row.locator("textarea")
        pairs.append((key, text.input_value() if text.count() else "<file>"))
    return pairs


def test_dragging_files_over_the_list_shows_a_drop_zone(app_page: Page):
    page = app_page
    zone = page.locator(".drop-zone")
    expect(zone).to_have_count(0)

    transfer = drop_files(page, [("a.txt", "x", "text/plain")], event="over")
    expect(zone).to_be_visible()
    expect(zone).to_contain_text("Drop .env or files here")
    # it must not catch the pointer, or the drag would flicker over the rows
    assert zone.evaluate("(zone) => getComputedStyle(zone).pointerEvents") == "none"

    page.dispatch_event(".secrets-list", "dragleave", {"dataTransfer": transfer})
    expect(zone).to_have_count(0)


def test_dragging_text_does_not_show_the_drop_zone(app_page: Page):
    page = app_page
    transfer = page.evaluate_handle(
        """() => {
            const transfer = new DataTransfer()
            transfer.setData('text/plain', 'just words')
            return transfer
        }"""
    )
    page.dispatch_event(".secrets-list", "dragenter", {"dataTransfer": transfer})
    expect(page.locator(".drop-zone")).to_have_count(0)


def test_dropping_a_dotenv_file_creates_one_pair_per_variable(app_page: Page):
    page = app_page
    api = SealingApi(page)
    namespace_select(page)
    secret_name(page)
    env = (
        "# database\n"
        "DB_HOST=db.local\n"
        "export DB_PASSWORD='s3cr3t # not a comment'\n"
        "\n"
        'GREETING="hello\\nworld"\n'
        "this line is not valid\n"
    )

    drop_files(page, [(".env", env, "")])

    # the blank row made way for the three pairs
    expect_key_value_pairs(
        page,
        [
            ("DB_HOST", "db.local"),
            ("DB_PASSWORD", "s3cr3t # not a comment"),
            ("GREETING", "hello\nworld"),
        ],
    )
    expect(page.locator(".drop-zone")).to_have_count(0)
    expect(page.locator("div[role='status']")).to_have_text(
        re.compile(r"Imported 3 keys from \.env")
    )
    click_encrypt_button(page)
    expect(page.locator("#sealed-secret-result")).to_be_visible()
    assert api.only_request["secrets"] == [
        {"key": "DB_HOST", "value": b64("db.local")},
        {"key": "DB_PASSWORD", "value": b64("s3cr3t # not a comment")},
        {"key": "GREETING", "value": b64("hello\nworld")},
    ]


def test_dropped_pairs_are_appended_to_filled_rows(app_page: Page):
    page = app_page
    add_secret_key_value(page)

    drop_files(page, [("prod.env", "ONE=1\nTWO=2", "")])

    expect_key_value_pairs(
        page,
        [
            (SECRET_KEY, SECRET_VALUE),
            ("ONE", "1"),
            ("TWO", "2"),
        ],
    )
    expect(page.locator("div[role='status']")).to_have_text(
        re.compile(r"Imported 2 keys from prod\.env")
    )


def test_dropped_pairs_replace_every_blank_row(app_page: Page):
    page = app_page
    # "Add key-value pair" twice leaves three blank rows behind
    add_pair = page.get_by_role("button", name="Add key-value pair")
    add_pair.click()
    add_pair.click()
    expect(page.locator(".secret-row")).to_have_count(3)

    drop_files(page, [("prod.env", "ONE=1\nTWO=2", "")])

    expect_key_value_pairs(page, [("ONE", "1"), ("TWO", "2")])
    # nothing incomplete is left, so the form can be sealed once it is addressed
    namespace_select(page)
    secret_name(page)
    expect(page.locator('button:has-text("Encrypt")')).to_be_enabled()


def test_dropped_keys_go_through_the_duplicate_check(app_page: Page):
    page = app_page
    add_secret_key_value(page)

    drop_files(page, [(".env", f"{SECRET_KEY}=other\nBAD KEY=1\nA=1", "")])

    expect(page.locator(".v-messages__message", has_text="Duplicate key")).to_have_count(2)
    expect(page.locator('button:has-text("Encrypt")')).to_be_disabled()


def test_dropping_another_file_creates_a_file_pair(app_page: Page):
    page = app_page
    api = SealingApi(page)
    namespace_select(page)
    secret_name(page)

    drop_files(page, [("tls.crt", FILE_CONTENT, "")])

    expect(page.locator("input#secretKey-0")).to_have_value("tls.crt")
    chip = page.locator(".secret-file")
    expect(chip).to_have_count(1)
    expect(chip).to_contain_text("tls.crt")
    expect(chip).to_contain_text(f"{len(FILE_CONTENT)} B")
    expect(page.locator("div[role='status']")).to_have_text(re.compile(r"Added 1 file"))
    click_encrypt_button(page)
    expect(page.locator("#sealed-secret-result")).to_be_visible()
    assert api.only_request["secrets"] == [
        {"key": "tls.crt", "file": b64(FILE_CONTENT)}
    ]


def test_dropping_several_files_mixes_pairs_and_files(app_page: Page):
    page = app_page

    drop_files(
        page,
        [
            (".env", "A=1\nB=2", "text/plain"),
            ("ca.pem", "-----BEGIN CERTIFICATE-----", ""),
            ("notes.txt", "just some words", "text/plain"),
        ],
    )

    expect(page.locator("input[id^='secretKey-']")).to_have_count(4)
    assert [
        key.input_value() for key in page.locator("input[id^='secretKey-']").all()
    ] == ["A", "B", "ca.pem", "notes.txt"]
    expect(page.locator(".secret-file")).to_have_count(2)
    expect(page.locator("div[role='status']")).to_have_text(
        re.compile(r"Imported 2 keys from \.env and added 2 files")
    )


def test_plain_text_of_key_value_lines_is_read_as_dotenv(app_page: Page):
    page = app_page

    drop_files(
        page,
        [
            ("settings.txt", "# comment\nMODE=prod\nLEVEL=info\n", "text/plain"),
            ("token.txt", "dGVzdA==", "text/plain"),
        ],
    )

    assert key_value_pairs(page)[:2] == [("MODE", "prod"), ("LEVEL", "info")]
    # base64 padding is not an assignment, so this stays a file
    expect(page.locator("input#secretKey-2")).to_have_value("token.txt")
    expect(page.locator(".secret-file")).to_have_count(1)


@pytest.mark.parametrize("name", ["my file.txt", "Résumé.pdf"])
def test_dropped_file_with_an_invalid_key_shows_its_error_at_once(
    app_page: Page, name: str
):
    page = app_page
    namespace_select(page)
    secret_name(page)

    drop_files(page, [(name, FILE_CONTENT, "")])

    # the key is not renamed, and the reason Encrypt is off is visible
    expect(page.locator("input#secretKey-0")).to_have_value(name)
    expect(page.locator(".secret-row:has(#secretKey-0) .v-messages__message")).to_contain_text(
        "Invalid char"
    )
    expect(page.locator(".secret-row:has(#secretKey-0) .v-input--error")).to_have_count(1)
    expect(page.locator('button:has-text("Encrypt")')).to_be_disabled()
    # a valid name shows no error
    drop_files(page, [("valid-name.txt", FILE_CONTENT, "")])
    expect(page.locator(".secret-row:has(#secretKey-1) .v-input--error")).to_have_count(0)
    # fixing the key by hand lifts the block
    expect(page.locator('button:has-text("Encrypt")')).to_be_disabled()
    page.fill("input#secretKey-0", "my-file.txt")
    expect(page.locator('button:has-text("Encrypt")')).to_be_enabled()


def default_prevented(page: Page, event: str, files: bool, target: str = "body") -> bool:
    """Dispatch a drag event and say whether the page called preventDefault."""
    return page.evaluate(
        """([event, files, target]) => {
            const transfer = new DataTransfer()
            if (files) transfer.items.add(new File(['x'], 'a.txt'))
            else transfer.setData('text/plain', 'words')
            const dragEvent = new DragEvent(event, {
                dataTransfer: transfer, bubbles: true, cancelable: true
            })
            document.querySelector(target).dispatchEvent(dragEvent)
            return dragEvent.defaultPrevented
        }""",
        [event, files, target],
    )


def test_a_file_dropped_outside_the_list_does_not_replace_the_page(app_page: Page):
    page = app_page
    add_secret_key_value(page)
    # without this the browser would open the file and the form would be lost
    for target in ("body", ".v-app-bar", "#secretName"):
        assert default_prevented(page, "dragover", files=True, target=target), target
        assert default_prevented(page, "drop", files=True, target=target), target
    # text can still be dropped into the fields
    assert not default_prevented(page, "dragover", files=False, target="#secretName")
    assert not default_prevented(page, "drop", files=False, target="#secretName")

    # the form is still there, and dropping on the list still imports
    expect(page.locator("input#secretKey-0")).to_have_value(SECRET_KEY)
    drop_files(page, [(".env", "A=1", "")])
    expect_key_value_pairs(page, [(SECRET_KEY, SECRET_VALUE), ("A", "1")])


def test_a_file_dropped_on_the_result_view_does_not_replace_the_page(app_page: Page):
    page = app_page
    SealingApi(page)
    seal_one_value(page)
    assert default_prevented(page, "dragover", files=True)
    assert default_prevented(page, "drop", files=True)


def test_dropping_a_file_over_the_limit_is_rejected(app_page: Page):
    page = app_page

    drop_files(page, [("big.bin", "X" * (ONE_MEBIBYTE + 1), "")])

    expect(page.locator("div[role='status']")).to_contain_text(
        "big.bin: File size should be less than 1 MB!"
    )
    # nothing was added
    assert key_value_pairs(page) == [("", "")]
    expect(page.locator(".secret-file")).to_have_count(0)


def test_dropping_an_empty_dotenv_file_reports_it(app_page: Page):
    page = app_page

    drop_files(page, [(".env", "# nothing here\n", "")])

    expect(page.locator("div[role='status']")).to_contain_text("No KEY=VALUE pairs found")
    assert key_value_pairs(page) == [("", "")]


def write_file(directory, name: str, content: str):
    path = directory / name
    path.write_text(content)
    return path


def enable_sealed_secret_import(page: Page) -> list[str]:
    """Switch the import feature on and serve two existing SealedSecrets."""
    requested_urls: list[str] = []

    def config_json(route: Route):
        config = route.fetch().json()
        config["enable_existing_sealed_secret_loading"] = True
        route.fulfill(json=config)

    def sealed_secrets(route: Route):
        requested_urls.append(route.request.url)
        route.fulfill(
            json=[
                {"name": "app-secrets", "keys": ["API_KEY", "TOKEN"]},
                {"name": "db-secrets", "keys": ["PASSWORD"]},
            ]
        )

    page.route("**/config.json", config_json)
    page.route("**/sealed-secrets/*", sealed_secrets)
    return requested_urls


def import_sealed_secret(page: Page, name: str):
    page.get_by_role("button", name="Import existing sealed secret").click()
    # typing filters the list, whether or not it is open already
    page.get_by_role("combobox", name="Select SealedSecret").fill(name)
    page.get_by_role("option", name=name).click()


def secret_keys(page: Page) -> list[str]:
    return [
        key.input_value() for key in page.locator("input[id^='secretKey-']").all()
    ]


def test_import_keys_of_an_existing_sealed_secret(page: Page):
    requested_urls = enable_sealed_secret_import(page)
    page.goto("/")
    import_button = page.get_by_role("button", name="Import existing sealed secret")

    # only offered for a namespace of the cluster
    page.wait_for_selector("input#namespaceSelection")
    expect(import_button).to_have_count(0)
    namespace = namespace_select(page)
    expect(import_button).to_be_visible()

    # nothing entered yet: the keys are taken over right away
    import_sealed_secret(page, "app-secrets")
    expect(page.locator("input[id^='secretKey-']")).to_have_count(2)
    assert secret_keys(page) == ["API_KEY", "TOKEN"]
    assert requested_urls == [f"{page.url}sealed-secrets/{namespace}"]

    # replacing entered data needs a confirmation
    page.fill("textarea#secretValue-0", SECRET_VALUE)
    import_sealed_secret(page, "db-secrets")
    dialog = page.locator(".v-dialog", has_text="Replace key list?")
    expect(dialog).to_be_visible()
    dialog.get_by_role("button", name="Cancel").click()
    expect(dialog).to_be_hidden()
    assert secret_keys(page) == ["API_KEY", "TOKEN"]
    expect(page.locator("textarea#secretValue-0")).to_have_value(SECRET_VALUE)

    import_sealed_secret(page, "db-secrets")
    expect(dialog).to_be_visible()
    dialog.get_by_role("button", name="Continue").click()
    expect(dialog).to_be_hidden()
    expect(page.locator("input[id^='secretKey-']")).to_have_count(1)
    assert secret_keys(page) == ["PASSWORD"]
    expect(page.locator("textarea#secretValue-0")).to_have_value("")
    # the list of the namespace was loaded once
    assert len(requested_urls) == 1

    # not offered for a namespace that does not exist yet
    page.locator("#newNamespaceCheckbox").check()
    expect(import_button).to_have_count(0)


def disable_namespace_listing(page: Page, import_enabled: bool = False) -> list[str]:
    """Serve config.json with `enable_namespace_listing: false`; return the
    URLs of the requests to /namespaces."""
    namespace_requests: list[str] = []

    def config_json(route: Route):
        config = route.fetch().json()
        config["enable_namespace_listing"] = False
        config["enable_existing_sealed_secret_loading"] = import_enabled
        route.fulfill(json=config)

    page.route("**/config.json", config_json)
    page.on(
        "request",
        lambda request: (
            namespace_requests.append(request.url)
            if request.url.endswith("/namespaces")
            else None
        ),
    )
    return namespace_requests


def test_namespace_is_typed_in_without_the_namespace_list(page: Page):
    namespace_requests = disable_namespace_listing(page)
    api = SealingApi(page)
    page.goto("/")

    # a plain text field, without the "does not exist yet" checkbox
    namespace_input = page.locator("input#namespaceSelection")
    expect(page.get_by_role("textbox", name="Namespace name")).to_be_visible()
    expect(page.locator(".v-autocomplete")).to_have_count(0)
    expect(page.locator("#newNamespaceCheckbox")).to_have_count(0)

    secret_name(page)
    add_secret_key_value(page)
    encrypt = page.locator('button:has-text("Encrypt")')
    namespace_input.fill("Not_Valid")
    expect(encrypt).to_be_disabled()
    namespace_input.fill("team-a")
    expect(encrypt).to_be_enabled()
    click_encrypt_button(page)
    expect(page.locator("#sealed-secret-result")).to_be_visible()
    assert api.only_request["namespace"] == "team-a"

    # still a text field after "Clear"
    page.get_by_role("button", name="Clear").click()
    expect(namespace_input).to_have_value("")
    expect(page.locator("#newNamespaceCheckbox")).to_have_count(0)

    # neither requested nor reported as an error
    expect(page.locator(".v-snackbar").get_by_text("Failed to fetch namespaces")).to_have_count(0)
    assert namespace_requests == []


def test_import_from_a_typed_in_namespace_without_the_namespace_list(page: Page):
    requested_urls = enable_sealed_secret_import(page)
    # registered last, so it is the handler that answers config.json
    disable_namespace_listing(page, import_enabled=True)
    page.goto("/")
    import_button = page.get_by_role("button", name="Import existing sealed secret")
    namespace_input = page.get_by_role("textbox", name="Namespace name")

    # not for a name that is no namespace
    namespace_input.fill("Not_Valid")
    expect(import_button).to_have_count(0)

    namespace_input.fill("team-a")
    import_sealed_secret(page, "app-secrets")
    assert secret_keys(page) == ["API_KEY", "TOKEN"]
    assert requested_urls == [f"{page.url}sealed-secrets/team-a"]


def test_secret_form_with_invalid_file(app_page: Page, tmp_path):
    page = app_page
    file_input = page.locator('input[type="file"]#fileInput-0')
    # Try to upload a file above the 1 MB limit
    invalid_file = tmp_path / "large_test_file.txt"
    invalid_file.write_text("X" * (10 * ONE_MEBIBYTE))
    file_input.set_input_files(invalid_file)

    # Check for the snackbar error message
    snackbar_message = page.locator("div[role='status']").get_by_text(
        "File size should be less than 1 MB!"
    )
    expect(snackbar_message).to_be_visible()

    # the rejected file is not kept, the reason is shown at the input
    row = page.locator(".secret-row:has(#fileInput-0)")
    expect(row.locator(".secret-row__value .v-messages")).to_have_text(
        "File size should be less than 1 MB!"
    )
    expect(row).not_to_contain_text("large_test_file.txt")
    expect(page.locator("textarea#secretValue-0")).to_be_enabled()

    # a file within the limit is accepted and clears the error
    valid_file = tmp_path / "small_test_file.txt"
    valid_file.write_text(FILE_CONTENT)
    file_input.set_input_files(valid_file)
    expect(row.locator(".secret-file")).to_contain_text("small_test_file.txt")
    expect(row.locator(".secret-row__value .v-messages")).to_have_count(0)
    # the file replaces the text area
    expect(page.locator("textarea#secretValue-0")).to_have_count(0)


def test_secret_form_with_new_namespace(app_page: Page):
    page = app_page
    disabled_encrypt_button(page)
    secret_name(page)
    add_secret_key_value(page)

    # a namespace that is not part of the cluster list can only be typed
    # in after opting in via the checkbox
    page.locator("#newNamespaceCheckbox").check()
    namespace_input = page.locator("input#namespaceSelection")
    namespace_input.wait_for()
    namespace_input.fill("Not_Valid")
    assert page.locator('button:has-text("Encrypt")').is_disabled()

    namespace_input.fill("not-created-yet")
    assert namespace_input.input_value() == "not-created-yet"
    assert page.locator('button:has-text("Encrypt")').is_enabled()

    # switching back to the cluster list starts with an empty selection
    page.locator("#newNamespaceCheckbox").uncheck()
    assert page.locator('button:has-text("Encrypt")').is_disabled()


def test_secret_name_is_optional_outside_strict_scope(app_page: Page):
    page = app_page
    disabled_encrypt_button(page)
    select_scope(page, "namespace-wide")
    namespace_select(page)
    add_secret_key_value(page)

    # the name is not sealed into the secret for this scope, so it is
    # optional, but it can still be entered for the generated YAML
    encrypt_button = page.locator('button:has-text("Encrypt")')
    name_input = page.locator("#secretName")
    assert name_input.is_enabled()
    assert encrypt_button.is_enabled()

    # must be a DNS subdomain: no upper case, underscores or empty labels
    for invalid_name in ["Not_Valid", "a_b", "a..b", "a.-b", "a" * 254]:
        name_input.fill(invalid_name)
        assert encrypt_button.is_disabled(), invalid_name

    for valid_name in ["valid-secret-name", "my.secret-1", "a" * 253]:
        name_input.fill(valid_name)
        assert encrypt_button.is_enabled(), valid_name
        # the field rule has to agree with the button state
        assert page.locator(".v-col:has(#secretName) .v-input--error").count() == 0

    # the strict scope requires the name again
    name_input.fill("")
    select_scope(page, "strict")
    assert encrypt_button.is_disabled()


def name_messages(page: Page):
    """The messages under the secret name field, including one that is fading out.

    Use `.last` to assert on the current one: a replaced message is briefly
    still in the DOM, and a locator that matches two elements is an error.
    """
    return page.locator(".v-col:has(#secretName) .v-messages__message")


def test_fresh_form_shows_no_error_before_the_field_was_visited(app_page: Page):
    page = app_page
    name_input = page.locator("#secretName")
    name_input.wait_for()
    expect(page.locator(".v-input--error")).to_have_count(0)
    expect(page.locator(".v-messages__message")).to_have_count(0)

    # leaving the empty field is what reveals the missing value
    name_input.focus()
    page.locator("input#secretKey-0").focus()
    expect(name_messages(page).last).to_have_text(
        "Must not be empty"
    )

    # an invalid name complains while it is typed, a valid one leaves no message
    name_input.fill("Not_Valid")
    expect(name_messages(page).last).to_have_text(
        re.compile("^Invalid char")
    )
    name_input.fill(SECRET_NAME)
    expect(name_messages(page)).to_have_count(0)
    expect(page.locator(".v-col:has(#secretName) .v-input--error")).to_have_count(0)


def test_message_of_the_other_scope_does_not_linger_on_the_secret_name(app_page: Page):
    page = app_page
    name_input = page.locator("#secretName")
    select_scope(page, "namespace-wide")
    name_input.fill("Not_Valid")
    expect(name_messages(page).last).to_have_text(
        re.compile("^Must consist of lower case")
    )
    # the same name is judged by the rules of the new scope
    select_scope(page, "strict")
    expect(name_messages(page).last).to_have_text(
        re.compile("^Invalid char")
    )
    name_input.fill("")
    page.locator("input#secretKey-0").focus()
    expect(name_messages(page).last).to_have_text(
        "Must not be empty"
    )
    select_scope(page, "namespace-wide")
    expect(page.locator(".v-col:has(#secretName) .v-input--error")).to_have_count(0)


def test_invalid_secret_name_offers_a_fix(app_page: Page):
    page = app_page
    name_input = page.locator("#secretName")
    suggestion = page.locator("#secretNameSuggestion")
    expect(suggestion).to_have_count(0)

    # not while typing: "my-secret-" is only invalid because it is unfinished
    name_input.fill("Claude_Test Secret")
    expect(name_messages(page).last).to_have_text(re.compile("^Invalid char"))
    expect(suggestion).to_have_count(0)

    # once the field is left, the fix is offered
    page.locator("input#secretKey-0").focus()
    expect(suggestion).to_have_text(re.compile(r"Use\s+claude-test-secret"))
    suggestion.click()
    expect(name_input).to_have_value("claude-test-secret")
    expect(suggestion).to_have_count(0)
    expect(page.locator(".v-col:has(#secretName) .v-input--error")).to_have_count(0)

    # nothing valid can be made out of this, so nothing is suggested
    name_input.fill("___")
    page.locator("input#secretKey-0").focus()
    expect(page.locator(".v-col:has(#secretName) .v-input--error")).to_have_count(1)
    expect(suggestion).to_have_count(0)


def test_enter_selects_the_first_match_of_the_namespace_filter(app_page: Page):
    page = app_page
    names = open_namespace_list(page)
    filter_text = names[2][:3]
    expected = next(name for name in names if filter_text in name)
    page.fill("input#namespaceSelection", filter_text)
    page.keyboard.press("Enter")
    expect(page.locator(".v-autocomplete__selection-text")).to_have_text(expected)
    expect(page.locator(".v-overlay .v-list")).to_have_count(0)


def test_enter_selects_a_namespace_not_a_heading_with_favorites(page: Page):
    page.add_init_script(SEEDED_RANDOM)
    page.goto("/")
    page.wait_for_selector("input#namespaceSelection")
    names = open_namespace_list(page)
    favorite_toggle(page, names[3]).click()
    assert reopen_namespace_list(page)[0] == names[3]
    assert list_headings(page) == ["Favorites", "All namespaces"]
    selected = page.locator(".v-autocomplete__selection-text")

    # a filter that only matches others: the first match, not the favorite
    filter_text = names[0]
    page.fill("input#namespaceSelection", filter_text)
    expect(page.locator(".v-overlay .v-list-item-title")).to_have_text([names[0]])
    page.keyboard.press("Enter")
    expect(selected).to_have_text(names[0])

    # with an empty filter nothing is highlighted yet, so Enter must not pick
    # anything (in particular no heading)
    page.locator("input#namespaceSelection").fill("")
    page.keyboard.press("Enter")
    expect(selected).to_have_count(0)
    expect(page.locator(".v-overlay .v-list-subheader")).to_have_text(
        ["Favorites", "All namespaces"]
    )

    # walking down (first opening the list, then entering it) lands on the
    # first real entry, the favorite below its heading, and Enter selects it
    page.keyboard.press("Escape")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".v-overlay .v-list-item-title").first).to_have_text(names[3])
    page.keyboard.press("ArrowDown")
    expect(page.locator("*:focus")).to_have_text(names[3])
    page.keyboard.press("Enter")
    expect(selected).to_have_text(names[3])


def test_filtered_namespace_list_has_no_dangling_headings(page: Page):
    page.add_init_script(SEEDED_RANDOM)
    page.goto("/")
    page.wait_for_selector("input#namespaceSelection")
    names = open_namespace_list(page)
    favorite_toggle(page, names[3]).click()
    reopen_namespace_list(page)
    assert list_headings(page) == ["Favorites", "All namespaces"]

    # only the favorite is left: the heading of the others goes with them
    page.fill("input#namespaceSelection", names[3])
    expect(page.locator(".v-overlay .v-list-item-title")).to_have_text([names[3]])
    assert list_headings(page) == ["Favorites"]

    # only others are left: no heading of an empty favorites group
    page.fill("input#namespaceSelection", names[0])
    expect(page.locator(".v-overlay .v-list-item-title")).to_have_text([names[0]])
    assert list_headings(page) == ["All namespaces"]

    # headings are not entries: nothing to pick from them
    expect(page.locator(".v-overlay .v-list-subheader[role=option]")).to_have_count(0)


def test_scope_is_a_segmented_control_with_a_description(app_page: Page):
    page = app_page
    # a labelled group for assistive technology
    group = page.get_by_role("group", name="Scope")
    expect(group).to_have_count(1)
    # at the top, full width, above the namespace and the secret name
    scope = page.locator(".scope-picker").bounding_box()
    namespace = page.locator("input#namespaceSelection").bounding_box()
    name = page.locator("#secretName").bounding_box()
    assert scope["y"] + scope["height"] <= min(namespace["y"], name["y"])
    assert scope["width"] > namespace["width"] + name["width"]
    buttons = group.locator("button")
    expect(buttons).to_have_text(["strict", "namespace-wide", "cluster-wide"])
    description = page.locator("#scopeDescription")
    expect(description).to_have_text("Bound to this name and namespace")
    select_scope(page, "namespace-wide")
    expect(description).to_have_text("Any name within this namespace")
    select_scope(page, "cluster-wide")
    expect(description).to_have_text("Any name in any namespace")
    # one scope always stays selected
    page.locator('.scope-toggle button[data-scope="cluster-wide"]').click()
    expect(page.locator('.scope-toggle button[aria-pressed="true"]')).to_have_count(1)


def test_action_bar_says_what_encrypt_will_seal(app_page: Page):
    page = app_page
    bar = page.locator(".action-bar")
    expect(bar).to_contain_text("Please complete all required fields to encrypt")
    namespace = namespace_select(page)
    secret_name(page)
    add_secret_key_value(page)
    expect(bar).to_contain_text("Ready to seal")
    expect(bar.locator(".meta")).to_have_text(f"1 key · {namespace} · strict")
    # cluster-wide secrets have no namespace
    select_scope(page, "cluster-wide")
    expect(bar.locator(".meta")).to_have_text("1 key · cluster-wide")


def test_header_is_transparent_until_content_scrolls_under_it(page: Page):
    page.goto("/")
    bar = page.locator(".glass-app-bar")
    expect(bar).not_to_have_class(re.compile("glass-app-bar--scrolled"))
    color = bar.evaluate("el => getComputedStyle(el).backgroundColor")
    assert color in ("transparent", "rgba(0, 0, 0, 0)"), color


def test_form_header_fits_a_phone(page: Page):
    page.set_viewport_size({"width": 375, "height": 800})
    page.goto("/")
    page.wait_for_selector("#secretName")
    assert page.evaluate("document.documentElement.scrollWidth") <= 375
    for selector in ["input#namespaceSelection", "#secretName", ".scope-toggle"]:
        box = page.locator(selector).bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 375, selector


def sealed_secret_yaml(page: Page) -> str:
    """Return the generated manifest exactly as shown, whitespace included."""
    result = page.locator("#sealed-secret-result")
    expect(result).to_be_visible()
    text = result.text_content()
    # what a user selects and copies must not differ from the DOM text
    assert result.inner_text() == text
    return text


def duplicate_ids(page: Page) -> list[str]:
    return page.evaluate("""() => {
        const ids = [...document.querySelectorAll('[id]')].map((element) => element.id)
        return [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))]
    }""")


def seal_one_value(page: Page) -> str:
    """Fill the form with one key/value pair, seal it, return the namespace."""
    namespace = namespace_select(page)
    secret_name(page)
    add_secret_key_value(page)
    click_encrypt_button(page)
    expect(page.locator("#sealed-secret-result")).to_be_visible()
    return namespace


def namespace_select(page: Page) -> str:
    """Pick the first namespace of the list and return its name."""
    input_selector = "input#namespaceSelection"
    page.wait_for_selector(input_selector, timeout=10000)
    page.click(input_selector)
    page.wait_for_selector(".v-list-item-title")
    suggestions = page.locator(".v-list-item-title").all()
    assert len(suggestions) > 0, "No suggestions found."
    first_suggestion_text = suggestions[0].inner_text()
    suggestions[0].click()
    selected_text_selector = ".v-autocomplete__selection-text"
    page.wait_for_selector(selected_text_selector, timeout=10000)
    displayed_text = page.locator(selected_text_selector).inner_text()
    assert (
        displayed_text == first_suggestion_text
    ), f"Expected '{first_suggestion_text}', but got '{displayed_text}'"
    return displayed_text


def secret_name(page: Page):
    input_selector = "#secretName"
    page.wait_for_selector(input_selector)
    page.fill(input_selector, SECRET_NAME)
    assert (
        page.input_value(input_selector) == SECRET_NAME
    ), f"Expected {SECRET_NAME}, but got {page.input_value(input_selector)}"


def scope_strict(page: Page):
    select_scope(page, "strict")


def select_scope(page: Page, scope: str):
    button = page.locator(f'.scope-toggle button[data-scope="{scope}"]')
    button.click()
    expect(button).to_have_attribute("aria-pressed", "true")


def add_secret_key_value(page: Page):
    page.wait_for_selector("input#secretKey-0")
    page.fill("input#secretKey-0", SECRET_KEY)
    assert page.locator("input#secretKey-0").input_value() == SECRET_KEY
    page.wait_for_selector("textarea#secretValue-0")
    page.fill("textarea#secretValue-0", SECRET_VALUE)
    assert page.locator("textarea#secretValue-0").input_value() == SECRET_VALUE
    file_input = page.locator('input[type="file"]#fileInput-0')
    assert (
        not file_input.is_enabled()
    ), "File input should be disabled when value is filled"


def add_secret_key_file(page: Page, tmp_path):
    page.wait_for_selector("input#secretKey-0")
    page.fill("input#secretKey-0", SECRET_KEY)
    assert page.locator("input#secretKey-0").input_value() == SECRET_KEY

    file_input = page.locator('input[type="file"]#fileInput-0')
    test_file = tmp_path / "test_file.txt"
    test_file.write_text(FILE_CONTENT)
    file_input.set_input_files(test_file)


def disabled_encrypt_button(page: Page):
    encrypt_button = page.locator('button:has-text("Encrypt")')
    encrypt_button.wait_for()
    assert encrypt_button.is_disabled()


def click_encrypt_button(page: Page):
    encrypt_button = page.locator('button:has-text("Encrypt")')
    encrypt_button.wait_for()
    expect(encrypt_button).to_be_enabled()
    encrypt_button.click()
