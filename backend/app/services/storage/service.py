import uuid
from functools import lru_cache

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import get_settings


@lru_cache
def get_client():
    settings = get_settings()
    # endpoint_url must be None (not "") for real AWS S3 — boto3 rejects an empty
    # string. A value is only set for S3-compatible services like MinIO.
    # Passing None for the keys lets boto3 fall back to its normal credential
    # chain, which on EC2/ECS means the attached IAM role and no stored secrets.
    return boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint_url or None,
        aws_access_key_id=settings.storage_access_key or None,
        aws_secret_access_key=settings.storage_secret_key or None,
        region_name=settings.storage_region,
        config=BotoConfig(signature_version="s3v4"),
    )


@lru_cache
def ensure_bucket_exists() -> None:
    """Verify the bucket is reachable once per process.

    Cached because this used to run on every upload, costing an extra S3 round
    trip per résumé. Auto-creation is limited to custom-endpoint setups (MinIO in
    local development); on AWS the bucket is provisioned ahead of time and the
    instance role is not expected to hold CreateBucket.
    """
    settings = get_settings()
    client = get_client()
    try:
        client.head_bucket(Bucket=settings.storage_bucket)
        return
    except ClientError:
        if not settings.storage_endpoint_url:
            # Real S3: a missing or unreachable bucket is a deployment error, and
            # silently creating one would mask it.
            raise

    client.create_bucket(
        Bucket=settings.storage_bucket,
        **(
            {"CreateBucketConfiguration": {"LocationConstraint": settings.storage_region}}
            if settings.storage_region != "us-east-1"
            else {}
        ),
    )


def build_storage_key(candidate_id: uuid.UUID, file_name: str) -> str:
    return f"candidates/{candidate_id}/{uuid.uuid4()}-{file_name}"


@lru_cache
def get_gcs_bucket():
    """The GCS bucket handle, authenticated as the ambient service account.

    google-cloud-storage resolves Application Default Credentials, which on
    Cloud Run means the identity attached to the service. No key material is
    involved at any point, so there is nothing here to put in a secret store.
    """
    from google.cloud import storage as gcs

    return gcs.Client().bucket(get_settings().storage_bucket)


def _use_gcs() -> bool:
    return get_settings().storage_backend.lower() == "gcs"


def upload_bytes(key: str, data: bytes, content_type: str) -> None:
    settings = get_settings()
    if _use_gcs():
        get_gcs_bucket().blob(key).upload_from_string(data, content_type=content_type)
        return

    ensure_bucket_exists()
    get_client().put_object(Bucket=settings.storage_bucket, Key=key, Body=data, ContentType=content_type)


def download_bytes(key: str) -> bytes:
    settings = get_settings()
    if _use_gcs():
        return get_gcs_bucket().blob(key).download_as_bytes()

    response = get_client().get_object(Bucket=settings.storage_bucket, Key=key)
    return response["Body"].read()
