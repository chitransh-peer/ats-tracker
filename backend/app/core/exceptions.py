from fastapi import HTTPException, status


class AppError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(AppError):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status.HTTP_404_NOT_FOUND, detail)


class ConflictError(AppError):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status.HTTP_409_CONFLICT, detail)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail)


class ForbiddenError(AppError):
    def __init__(self, detail: str = "You do not have permission to perform this action"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)


class PasswordChangeRequiredError(AppError):
    """The caller is authenticated but still holds a temporary password.

    A distinct 403 rather than a 401: the credentials are valid, so the client
    must not treat this as an expired session and try to refresh. The frontend
    keys off this exact detail string to route to the change-password screen.
    """

    def __init__(self, detail: str = "Password change required"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)


class ValidationAppError(AppError):
    def __init__(self, detail: str = "Invalid request"):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)
