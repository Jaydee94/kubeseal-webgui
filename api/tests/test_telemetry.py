from unittest.mock import MagicMock

import fastapi
import pytest
from fastapi.testclient import TestClient
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from kubeseal_webgui_api import telemetry


def _build_app() -> fastapi.FastAPI:
    app = fastapi.FastAPI()

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"status": "ok"}

    return app


@pytest.fixture(autouse=True)
def _clean_otel_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("OTEL_ENABLED", "OTEL_SERVICE_NAME", "OTEL_EXPORTER_OTLP_ENDPOINT"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("value", [None, "", "false", "0", "yes"])
def test_tracing_is_noop_unless_explicitly_enabled(monkeypatch, value):
    instrument = MagicMock()
    monkeypatch.setattr(FastAPIInstrumentor, "instrument_app", instrument)
    if value is not None:
        monkeypatch.setenv("OTEL_ENABLED", value)

    telemetry.setup_tracing(_build_app())

    instrument.assert_not_called()


@pytest.mark.parametrize("value", ["true", "TRUE", " True "])
def test_tracing_enabled_instruments_app_with_service_name(monkeypatch, value):
    provider_holder = {}
    instrument = MagicMock()
    monkeypatch.setattr(FastAPIInstrumentor, "instrument_app", instrument)
    monkeypatch.setattr(
        "opentelemetry.trace.set_tracer_provider",
        lambda provider: provider_holder.setdefault("provider", provider),
    )
    monkeypatch.setenv("OTEL_ENABLED", value)
    monkeypatch.setenv("OTEL_SERVICE_NAME", "custom-service")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:1")
    app = _build_app()

    telemetry.setup_tracing(app)

    instrument.assert_called_once_with(app)
    provider = provider_holder["provider"]
    assert provider.resource.attributes["service.name"] == "custom-service"
    provider.shutdown()


def test_tracing_uses_default_service_name(monkeypatch):
    provider_holder = {}
    monkeypatch.setattr(FastAPIInstrumentor, "instrument_app", MagicMock())
    monkeypatch.setattr(
        "opentelemetry.trace.set_tracer_provider",
        lambda provider: provider_holder.setdefault("provider", provider),
    )
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:1")

    telemetry.setup_tracing(_build_app())

    provider = provider_holder["provider"]
    assert provider.resource.attributes["service.name"] == "kubeseal-webgui-api"
    provider.shutdown()


def test_instrumented_request_emits_span(monkeypatch):
    """A request against an instrumented app produces a server span."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    app = _build_app()

    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    try:
        assert TestClient(app).get("/ping").status_code == 200
    finally:
        FastAPIInstrumentor.uninstrument_app(app)

    spans = exporter.get_finished_spans()
    assert any(span.attributes.get("http.route") == "/ping" for span in spans)
