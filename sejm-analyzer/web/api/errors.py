"""API errors and validation helpers."""


class NotFoundError(Exception):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found"):
        self.message = message
        super().__init__(self.message)


class ValidationError(Exception):
    """Validation error."""

    def __init__(self, message: str = "Validation error"):
        self.message = message
        super().__init__(self.message)


# Valid term range (Polish Sejm)
MIN_TERM = 1
MAX_TERM = 15


def validate_term_id(term_id: int) -> None:
    """Validate term_id is in valid range."""
    if not MIN_TERM <= term_id <= MAX_TERM:
        raise ValidationError(f"Invalid term_id: {term_id}. Must be between {MIN_TERM} and {MAX_TERM}")
