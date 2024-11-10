import os
from playwright.sync_api import sync_playwright, Page


def test_ui_start():
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8080")
        page.wait_for_load_state("load")
        assert page.title() == "Kubeseal Webgui"
        browser.close()


def test_secret_form_with_value():
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8080")
        page.wait_for_load_state("load")

        disabled_encrypt_button(page)
        namespace_select(page)
        secret_name(page)
        scope_strict(page)
        add_secret_key_value(page)
        click_encrypt_button(page)

        browser.close()


def test_secret_form_with_file():
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8080")
        page.wait_for_load_state("load")

        disabled_encrypt_button(page)
        namespace_select(page)
        secret_name(page)
        scope_strict(page)
        add_secret_key_file(page)
        click_encrypt_button(page)

        browser.close()


def test_secret_form_with_invalid_file():
    with sync_playwright() as ctx:
        browser = ctx.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8080")
        page.wait_for_load_state("load")

        file_input = page.locator('input[type="file"]#input-16')
        # Try to upload a non-valid file
        invalid_file_path = os.path.join(os.getcwd(), "large_test_file.txt")
        with open(invalid_file_path, "w") as f:
            f.write(
                "X" * (10 * 1024 * 1024)
            )  # Create a 10MB file (assuming it's too large)
        file_input.set_input_files(invalid_file_path)

        # Check for an error message (adjust the selector as needed)
        error_message = page.locator(
            "text='File size should be less than 1 MB!'"
        )  # Replace with actual error message
        assert (
            error_message.is_visible()
        ), "Error message should be visible for invalid file"
        if os.path.exists(invalid_file_path):
            os.remove(invalid_file_path)
        browser.close()


def namespace_select(page: Page):
    input_selector = "input#input-4"
    page.wait_for_selector(input_selector, timeout=10000)
    page.click(input_selector)
    suggestions = page.query_selector_all(".v-list-item-title")
    assert len(suggestions) > 0, "No suggestions found."
    first_suggestion_text = suggestions[0].inner_text()
    suggestions[0].click()
    selected_value = page.input_value(input_selector)
    assert (
        selected_value == first_suggestion_text
    ), f"Expected '{first_suggestion_text}', but got '{selected_value}'"


def secret_name(page: Page):
    input_selector = "#input-secret-name"
    page.wait_for_selector(input_selector)
    input_text = "valid-secret-name"
    page.fill(input_selector, input_text)
    assert (
        page.input_value(input_selector) == input_text
    ), f"Expected {input_text}, but got {page.input_value(input_selector)}"


def scope_strict(page: Page):
    select_selector = "div.v-select"
    page.wait_for_selector(select_selector)
    page.click(select_selector)
    item_selector = "div.v-list-item"
    page.wait_for_selector(item_selector)
    items = page.query_selector_all(item_selector)
    assert len(items) > 0, "No items found in the dropdown."
    for item in items:
        title_element = item.query_selector("div.v-list-item-title")
        if title_element and title_element.inner_text().strip() == "strict":
            item.click()
            break


def add_secret_key_value(page: Page):
    page.wait_for_selector("textarea#input-12")
    page.fill("textarea#input-12", "my-secret-key")
    assert page.locator("textarea#input-12").input_value() == "my-secret-key"
    page.wait_for_selector("textarea#input-14")
    page.fill("textarea#input-14", "my-secret-value")
    assert page.locator("textarea#input-14").input_value() == "my-secret-value"
    file_input = page.locator('input[type="file"]#input-16')
    assert (
        not file_input.is_enabled()
    ), "File input should be disabled when value is filled"


def add_secret_key_file(page: Page):
    page.wait_for_selector("textarea#input-12")
    page.fill("textarea#input-12", "my-secret-key")
    assert page.locator("textarea#input-12").input_value() == "my-secret-key"

    file_input = page.locator('input[type="file"]#input-16')
    assert file_input.is_visible()
    test_file_path = os.path.join(os.getcwd(), "test_file.txt")
    with open(test_file_path, "w") as f:
        f.write("This is a test file.")
    file_input.set_input_files(test_file_path)
    if os.path.exists(test_file_path):
        os.remove(test_file_path)


def disabled_encrypt_button(page: Page):
    encrypt_button = page.locator('button:has-text("Encrypt")')
    encrypt_button.wait_for()
    assert encrypt_button.is_disabled()


def click_encrypt_button(page: Page):
    # Mock the fetchEncodedSecrets function by overriding it in the browser context
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
    encrypt_button = page.locator('button:has-text("Encrypt")')
    encrypt_button.wait_for()
    assert encrypt_button.is_enabled()
    encrypt_button.click()
    is_called = page.evaluate("window.fetchEncodedSecretsCalled === true")
    assert is_called, "fetchEncodedSecrets function was not called!"
