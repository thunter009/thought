"""Custom exceptions for the thought package."""


class ServiceNotRegisteredError(Exception):
    """Raised when a service is not properly registered in the registry."""


class CredentialsNotAuthorizedError(Exception):
    """Raised when credentials are not properly authorized."""


class LoadDestinationNotUniqueError(Exception):
    """Raised when the load destination is not unique."""


class CollectionMustAlreadyExistError(Exception):
    """Raised when a collection must already exist but doesn't."""
