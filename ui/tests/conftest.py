import os

import pytest
from playwright.sync_api import Page

# The dev server (`npm run dev`) listens here; CI starts it before the tests.
DEFAULT_BASE_URL = "http://localhost:8080"


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for pytest-playwright, so that tests can use relative URLs."""
    return os.environ.get("UI_BASE_URL", DEFAULT_BASE_URL)


@pytest.fixture
def app_page(page: Page) -> Page:
    """Return a page with the application loaded."""
    page.goto("/")
    page.wait_for_load_state("load")
    return page
