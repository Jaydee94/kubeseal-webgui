"""Logging helpers: request correlation, JSON output and access-log filtering.

The classes in here are referenced by name from ``config/logging_config.yaml``
(and the copy in the Helm chart), so renaming them is a breaking change for
anyone shipping a custom logging config.
"""

import json
import logging
import re
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

LOGGER_NAME = "kubeseal-webgui"
REQUEST_ID_HEADER = "X-Request-ID"
NO_REQUEST_ID = "-"

# Request ids end up in log lines and response headers, so anything a client
# sends is only accepted if it cannot be used to forge log entries.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

request_id_var: ContextVar[str] = ContextVar("request_id", default=NO_REQUEST_ID)


def get_request_id() -> str:
    return request_id_var.get()


class RequestIdMiddleware:
    """Give every HTTP request an id that shows up in all of its log lines.

    An incoming ``X-Request-ID`` (set by the nginx sidecar) is reused so that
    the nginx access log, the API logs and the browser console can be joined
    on one value. The id is echoed back in the response header.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER, "")
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        # Deliberately not reset afterwards: uvicorn runs every request in its
        # own task (own context), and keeping the value lets uvicorn's access
        # and "Exception in ASGI application" records carry the id as well.
        request_id_var.set(request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        await self.app(scope, receive, send_with_request_id)


# The two filters below are flagged by the "configuring loggers is security
# sensitive" audit rule. Reviewed: they only add a field to a record or drop
# probe lines, and are wired up from the static logging config, never from
# request data.
class RequestIdFilter(logging.Filter):  # skipcq: PY-A6006
    """Expose the current request id to formatters as ``%(request_id)s``."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class HealthCheckAccessFilter(logging.Filter):  # skipcq: PY-A6006
    """Drop access-log records of successful ``GET /`` health probes.

    The kubelet probes the API every few seconds; those lines carry no
    information and bury real requests. Failing probes are still logged.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not isinstance(args, tuple) or len(args) != 5:
            return True
        _client, method, path, _http_version, status = args
        try:
            successful = 200 <= int(status) < 300  # type: ignore[call-overload]
        except (TypeError, ValueError):
            return True
        return not (method == "GET" and path == "/" and successful)


class JsonFormatter(logging.Formatter):
    """Render records as one JSON object per line for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", NO_REQUEST_ID),
        }

        args = record.args
        if (
            record.name == "uvicorn.access"
            and isinstance(args, tuple)
            and len(args) == 5
        ):
            client, method, path, http_version, status = args
            payload.update(
                client=client,
                method=method,
                path=path,
                http_version=http_version,
                status=status,
            )

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str, ensure_ascii=False)
