class EnvironmentVariableError(Exception):
    """Exception raised when a variable is not found or has an empty value."""

    pass


class EmptyResponseFromAPI(Exception):
    """Exception raised for authentication errors."""

    pass
