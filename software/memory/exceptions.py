class MemoryError(Exception):
    """Base exception for the KRYZETH memory subsystem."""


class MemoryPersistenceError(MemoryError):
    """Raised when persistent memory cannot be safely read or written."""
