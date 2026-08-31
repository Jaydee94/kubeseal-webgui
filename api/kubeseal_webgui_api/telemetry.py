"""OpenTelemetry tracing setup for kubeseal-webgui-api."""

import logging
from os import environ

import fastapi

LOGGER = logging.getLogger("kubeseal-webgui")


def setup_tracing(app: fastapi.FastAPI) -> None:
    """Initialise OpenTelemetry tracing when ``OTEL_ENABLED=true``.

    Standard OTEL environment variables control the exporter:
    - ``OTEL_EXPORTER_OTLP_ENDPOINT`` – collector endpoint (e.g. ``http://otel-collector:4318``)
    - ``OTEL_SERVICE_NAME``            – reported service name (default: ``kubeseal-webgui-api``)
    - ``OTEL_EXPORTER_OTLP_HEADERS``   – optional bearer-token / auth headers

    If ``OTEL_ENABLED`` is not ``true`` (case-insensitive) the function is a
    no-op so the application starts normally without any tracing overhead.
    """
    if environ.get("OTEL_ENABLED", "false").lower() != "true":
        LOGGER.debug("OpenTelemetry tracing disabled (OTEL_ENABLED != true).")
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.instrumentation.fastapi import (
        FastAPIInstrumentor,
    )
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    service_name = environ.get("OTEL_SERVICE_NAME", "kubeseal-webgui-api")
    resource = Resource(attributes={SERVICE_NAME: service_name})

    provider = TracerProvider(resource=resource)
    # OTLPSpanExporter reads OTEL_EXPORTER_OTLP_ENDPOINT and
    # OTEL_EXPORTER_OTLP_HEADERS automatically from the environment.
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)

    LOGGER.info(
        "OpenTelemetry tracing enabled – service='%s' endpoint='%s'.",
        service_name,
        environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "<default>"),
    )
