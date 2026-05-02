from typing import Protocol, runtime_checkable


@runtime_checkable
class IStorage(Protocol):
    """Contract for object storage backends.

    The default implementation (S3Store) targets any S3-compatible endpoint.
    Swap implementations in services/storage/__init__.py's get_storage() factory
    without touching business logic.
    """

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Persist bytes at the given key. Returns the key on success."""
        ...

    async def download(self, key: str) -> bytes:
        """Retrieve bytes for the given key. Raises StorageError if missing."""
        ...

    async def delete(self, key: str) -> None:
        """Remove an object by key. No-op if the key does not exist."""
        ...

    async def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a time-limited pre-signed download URL."""
        ...
