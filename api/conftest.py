import pytest

from app import create_app


@pytest.fixture(name="app")
def fixture_app():
    return create_app(
        {
            "TESTING": True,
        }
    )


@pytest.fixture(name="client")
def fixture_client(app):
    return app.test_client()


@pytest.fixture(name="runner")
def fixture_runner(app):
    return app.test_cli_runner()
