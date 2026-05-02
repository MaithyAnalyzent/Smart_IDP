from __future__ import annotations
import boto3
from botocore.exceptions import ClientError

from core.exceptions import StorageError
from configs.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)


class S3Store:
    """S3-compatible object storage.

    Works identically with AWS S3 (leave STORAGE_ENDPOINT blank) and
    self-hosted MinIO (set STORAGE_ENDPOINT to the MinIO address).
    """

    def __init__(self) -> None:
        settings = get_settings()
        client_kwargs: dict = {
            "aws_access_key_id": settings.STORAGE_ACCESS_KEY,
            "aws_secret_access_key": settings.STORAGE_SECRET_KEY,
            "region_name": settings.STORAGE_REGION,
        }
        if settings.STORAGE_ENDPOINT:
            client_kwargs["endpoint_url"] = settings.STORAGE_ENDPOINT
            client_kwargs["use_ssl"] = settings.STORAGE_USE_SSL
        self._client = boto3.client("s3", **client_kwargs)
        self._bucket = settings.STORAGE_BUCKET

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        try:
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
            )
            logger.info("storage_upload", key=key, bytes=len(data))
            return key
        except ClientError as exc:
            raise StorageError(f"Upload failed [{key}]: {exc}") from exc

    async def download(self, key: str) -> bytes:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()
        except ClientError as exc:
            raise StorageError(f"Download failed [{key}]: {exc}") from exc

    async def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            logger.info("storage_delete", key=key)
        except ClientError as exc:
            raise StorageError(f"Delete failed [{key}]: {exc}") from exc

    async def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except ClientError as exc:
            raise StorageError(f"Presigned URL failed [{key}]: {exc}") from exc
