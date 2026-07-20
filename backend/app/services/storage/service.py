import uuid
from functools import lru_cache

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import get_settings


@lru_cache
def get_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint_url,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        region_name=settings.storage_region,
        config=BotoConfig(signature_version="s3v4"),
    )


def ensure_bucket_exists() -> None:
    settings = get_settings()
    client = get_client()
    try:
        client.head_bucket(Bucket=settings.storage_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.storage_bucket)


def build_storage_key(candidate_id: uuid.UUID, file_name: str) -> str:
    return f"candidates/{candidate_id}/{uuid.uuid4()}-{file_name}"


def upload_bytes(key: str, data: bytes, content_type: str) -> None:
    settings = get_settings()
    ensure_bucket_exists()
    get_client().put_object(Bucket=settings.storage_bucket, Key=key, Body=data, ContentType=content_type)


def download_bytes(key: str) -> bytes:
    settings = get_settings()
    response = get_client().get_object(Bucket=settings.storage_bucket, Key=key)
    return response["Body"].read()
