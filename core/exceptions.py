class DocIntelError(Exception):
    """Root exception for the Doc Intelligence Platform."""


class PipelineStageError(DocIntelError):
    """Raised when a named pipeline stage fails unrecoverably."""
    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(f"[{stage}] {message}")


class UnsupportedFileTypeError(DocIntelError):
    """Raised when an uploaded file's MIME type is not in the allowed list."""


class FileTooLargeError(DocIntelError):
    """Raised when an uploaded file exceeds the configured size limit."""


class StorageError(DocIntelError):
    """Raised on object storage read/write/delete failures."""


class ExtractionError(PipelineStageError):
    def __init__(self, message: str) -> None:
        super().__init__("extract", message)


class ClassificationError(PipelineStageError):
    def __init__(self, message: str) -> None:
        super().__init__("classify", message)


class ValidationRuleError(PipelineStageError):
    def __init__(self, message: str) -> None:
        super().__init__("validate", message)


class TenantNotFoundError(DocIntelError):
    """Raised when a tenant_id does not resolve to an active tenant."""


class SchemaNotFoundError(DocIntelError):
    """Raised when no document schema matches the given type for a tenant."""


class ConfigurationError(DocIntelError):
    """Raised on missing or invalid configuration values at startup."""
