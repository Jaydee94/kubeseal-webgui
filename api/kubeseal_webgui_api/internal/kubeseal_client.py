import logging
import subprocess  # noqa: S404 the binary has to be configured by an admin
from os import environ
from pathlib import Path
from typing import Optional, Union

LOGGER = logging.getLogger("kubeseal-webgui")
DEFAULT_KUBESEAL_CERT = Path("/dev/null")
DEFAULT_KUBESEAL_BINARY = Path("/bin/kubeseal")


class KubesealClient:
    def __init__(
        self,
        cert: Path = DEFAULT_KUBESEAL_CERT,
        binary: Path = DEFAULT_KUBESEAL_BINARY,
        namespace: str = "sealed-secrets",
        controller: str = "sealed-secrets-controller",
    ):
        self.cert = str(cert)
        self.binary = str(binary)
        self.namespace = namespace
        self.controller = controller

    def get_version(self) -> str:
        LOGGER.debug("Retrieving kubeseal binary version.")
        version = self.run("--version", stdin=None, encoding="utf-8")

        return str(version).split(":")[1].replace('"', "").strip()

    def get_certificate(self) -> str:
        LOGGER.info(
            "Fetch certificate from sealed secrets controller '%s' in namespace '%s'",
            self.controller,
            self.namespace,
        )
        return self.run(
            "--fetch-cert",
            "--controller-name",
            self.controller,
            "--controller-namespace",
            self.namespace,
            stdin=None,
            encoding="utf-8",
        )

    def seal_string(
        self,
        value: str,
        scope: str,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> str:
        args = [
            "--raw",
            "--from-file=/dev/stdin",
            "--cert",
            self.cert,
            "--scope",
            scope,
        ]
        if namespace is not None:
            args.extend(["--namespace", namespace])
        if name is not None:
            args.extend(["--name", name])

        result = self.run(*args, stdin=value, encoding="utf-8")

        return "".join(result.split("\n"))

    def seal_bytes(
        self,
        value: bytes,
        scope: str,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> str:
        args = [
            "--raw",
            "--from-file=/dev/stdin",
            "--cert",
            self.cert,
            "--scope",
            scope,
        ]
        if namespace is not None:
            args.extend(["--namespace", namespace])
        if name is not None:
            args.extend(["--name", name])

        result = self.run(*args, stdin=value, encoding=None)

        return "".join(result.split("\n"))

    def run(
        self,
        *args,
        stdin: Optional[Union[str, bytes]] = None,
        encoding: Optional[str] = None,
    ) -> str:
        try:
            argv = [self.binary] + list(map(str, args))
            proc = subprocess.Popen(  # noqa: S603
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding=encoding,
            )
        except FileNotFoundError as file_error:
            raise RuntimeError("Could not find kubeseal binary") from file_error

        output, error = proc.communicate(input=stdin)
        if encoding is None:
            output, error = output.decode("utf-8"), error.decode("utf-8")
        if error:
            error_message = f"Error while executing {self.binary}: {error}"
            LOGGER.error(error_message)
            raise RuntimeError(error_message)

        return output  # noqa: R504


class MockKubesealClient(KubesealClient):
    def run(
        self,
        *args,
        stdin: Optional[Union[str, bytes]] = None,
        encoding: Optional[str] = None,
    ) -> str:
        if len(args) == 0:
            return ""

        if args[0] == "--version":
            version = environ.get("KUBESEAL_VERSION", "0.1.0")
            return f"kubeseal version: {version}"

        if args[0] == "--fetch-cert":
            pem = [
                "-----BEGIN CERTIFICATE REQUEST-----",
                "THIS0IS0NOT0A0VALID0CERTIFICATE0",
                "-----END CERTIFICATE REQUEST-----",
            ]
            return "\n".join(pem)

        return "THIS-IS-A-MOCK-RESPONSE"
