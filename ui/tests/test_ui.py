import base64
import json

from playwright.sync_api import Page, Route, expect

SECRET_NAME = "valid-secret-name"
SECRET_KEY = "my-secret-key"
SECRET_VALUE = "my-secret-value"
FILE_CONTENT = "This is a test file."
SEALED_VALUE = "AgSealedValue"
ONE_MEBIBYTE = 1024 * 1024


class SealingApi:
    """Stand-in for `POST /secrets`: there is no API behind the dev server."""

    def __init__(self, page: Page, status: int = 200, body=None):
        self.requests: list[dict] = []
        self._status = status
        self._body = body
        page.route("**/secrets", self._handle)

    def _handle(self, route: Route):
        assert route.request.method == "POST"
        payload = route.request.post_data_json
        self.requests.append(payload)
        body = self._body
        if body is None:
            body = [
                {"key": entry["key"], "value": SEALED_VALUE}
                for entry in payload["secrets"]
            ]
        route.fulfill(
            status=self._status,
            content_type="application/json",
            body=json.dumps(body),
        )

    @property
    def only_request(self) -> dict:
        assert len(self.requests) == 1, f"Expected one request: {self.requests}"
        return self.requests[0]


def b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def test_ui_start(app_page: Page):
    assert app_page.title() == "Kubeseal WebGui - Sealed Secrets Management"


def test_secret_form_with_value(app_page: Page):
    page = app_page
    api = SealingApi(page)

    disabled_encrypt_button(page)
    namespace = namespace_select(page)
    secret_name(page)
    scope_strict(page)
    add_secret_key_value(page)
    click_encrypt_button(page)

    # exact text: this is what users copy into their manifests
    assert sealed_secret_yaml(page) == (
        "apiVersion: bitnami.com/v1alpha1\n"
        "kind: SealedSecret\n"
        "metadata:\n"
        f"  name: {SECRET_NAME}\n"
        f"  namespace: {namespace}\n"
        "  annotations: {}\n"
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
    expect(key_card.locator(".v-card-title")).to_have_text(SECRET_KEY)
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
    expect(page.locator("textarea#secretKey")).to_have_value(SECRET_KEY)
    expect(page.locator("textarea#secretValue")).to_have_value(SECRET_VALUE)


def test_clear_on_result_view_returns_to_an_empty_form(app_page: Page):
    page = app_page
    SealingApi(page)
    seal_one_value(page)

    page.get_by_role("button", name="Clear").click()

    expect(page.locator("#sealed-secret-result")).to_have_count(0)
    expect(page.locator("#secretName")).to_have_value("")
    expect(page.locator("textarea#secretKey")).to_have_value("")
    expect(page.locator("textarea#secretValue")).to_have_value("")
    # Vuetify keeps an (empty) selection element for the empty string
    expect(page.locator(".v-autocomplete__selection-text")).to_have_text("")
    expect(page.locator("input#namespaceSelection")).to_have_value("")
    expect(page.locator('button:has-text("Encrypt")')).to_be_disabled()


def test_edit_on_result_view_returns_to_the_filled_form(app_page: Page):
    page = app_page
    SealingApi(page)
    namespace = seal_one_value(page)

    page.get_by_role("button", name="Edit Secrets").click()

    expect(page.locator("#sealed-secret-result")).to_have_count(0)
    expect(page.locator("#secretName")).to_have_value(SECRET_NAME)
    expect(page.locator("textarea#secretKey")).to_have_value(SECRET_KEY)
    expect(page.locator("textarea#secretValue")).to_have_value(SECRET_VALUE)
    expect(page.locator(".v-autocomplete__selection-text")).to_have_text(namespace)
    expect(page.locator('button:has-text("Encrypt")')).to_be_enabled()


def test_secret_form_with_invalid_file(app_page: Page, tmp_path):
    page = app_page
    file_input = page.locator('input[type="file"]#fileInput')
    # Try to upload a file above the 1 MB limit
    invalid_file = tmp_path / "large_test_file.txt"
    invalid_file.write_text("X" * (10 * ONE_MEBIBYTE))
    file_input.set_input_files(invalid_file)

    # Check for the snackbar error message
    snackbar_message = page.locator("div[role='status']").get_by_text(
        "File size should be less than 1 MB!"
    )
    expect(snackbar_message).to_be_visible()


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


def sealed_secret_yaml(page: Page) -> str:
    """Return the generated manifest exactly as shown, whitespace included."""
    result = page.locator("#sealed-secret-result")
    expect(result).to_be_visible()
    text = result.text_content()
    # what a user selects and copies must not differ from the DOM text
    assert result.inner_text() == text
    return text


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
    select_selector = "div.v-select"
    page.wait_for_selector(select_selector)
    page.click(select_selector)
    item = page.locator("div.v-list-item", has_text=scope).last
    item.wait_for()
    item.click()
    item.wait_for(state="hidden")


def add_secret_key_value(page: Page):
    page.wait_for_selector("textarea#secretKey")
    page.fill("textarea#secretKey", SECRET_KEY)
    assert page.locator("textarea#secretKey").input_value() == SECRET_KEY
    page.wait_for_selector("textarea#secretValue")
    page.fill("textarea#secretValue", SECRET_VALUE)
    assert page.locator("textarea#secretValue").input_value() == SECRET_VALUE
    file_input = page.locator('input[type="file"]#fileInput')
    assert (
        not file_input.is_enabled()
    ), "File input should be disabled when value is filled"


def add_secret_key_file(page: Page, tmp_path):
    page.wait_for_selector("textarea#secretKey")
    page.fill("textarea#secretKey", SECRET_KEY)
    assert page.locator("textarea#secretKey").input_value() == SECRET_KEY

    file_input = page.locator('input[type="file"]#fileInput')
    assert file_input.is_visible()
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
