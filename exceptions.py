class EnvironmentVariableError(Exception):
    """Exception raised when a variable is not found or has an empty value."""

    pass


class AuthenticationError(Exception):
    """Exception raised for authentication errors."""

    pass


class BadRequestError(Exception):
    """Exception raised for bad requests (HTTP 400)."""

    pass
