class PulsebeamError(Exception):
    """Base class for every error raised by this package."""


class PostgrestError(PulsebeamError):
    """PostgREST answered with a non-2xx status. Fields mirror its JSON error body."""

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        code: str | None = None,
        details: str | None = None,
        hint: str | None = None,
    ) -> None:
        prefix = f"{status_code} {code}" if code else str(status_code)
        super().__init__(f"{prefix}: {message}")
        self.status_code = status_code
        self.message = message
        self.code = code
        self.details = details
        self.hint = hint


class UnexpectedResponseError(PulsebeamError):
    """A 2xx response whose body is not the JSON array of objects PostgREST returns."""


class PulsebeamConnectionError(PulsebeamError):
    """The request never got a response: DNS, connect, read timeout and similar."""
