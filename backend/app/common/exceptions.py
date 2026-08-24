"""Central application errors. Route handlers should not invent ad-hoc HTTP errors."""


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found.", code: str = "NOT_FOUND") -> None:
        super().__init__(code, message, 404)


class UnauthorizedError(AppError):
    def __init__(
        self,
        message: str = "Authentication required.",
        code: str = "UNAUTHORIZED",
    ) -> None:
        super().__init__(code, message, 401)


class ForbiddenError(AppError):
    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        code: str = "FORBIDDEN",
    ) -> None:
        super().__init__(code, message, 403)


class ConflictError(AppError):
    def __init__(self, message: str, code: str = "CONFLICT") -> None:
        super().__init__(code, message, 409)


class RateLimitedError(AppError):
    def __init__(
        self,
        message: str = "Too many requests. Try again later.",
        code: str = "RATE_LIMITED",
    ) -> None:
        super().__init__(code, message, 429)


class PayloadTooLargeError(AppError):
    def __init__(
        self,
        message: str = "Request body is too large.",
        code: str = "PAYLOAD_TOO_LARGE",
    ) -> None:
        super().__init__(code, message, 413)
