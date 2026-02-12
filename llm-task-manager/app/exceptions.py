"""
Custom exceptions for the application.
"""


class BusinessRuleViolation(Exception):
    """Exception raised when a business rule is violated."""
    pass


class EntityNotFound(Exception):
    """Exception raised when an entity is not found."""
    pass


class ValidationError(Exception):
    """Exception raised when validation fails."""
    pass
