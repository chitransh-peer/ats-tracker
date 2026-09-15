"""Guards on how the S3 client is constructed.

These matter because the same code has to serve MinIO in development and real S3
on AWS, and the failure mode of getting it wrong is silent: uploads land in the
wrong place, or boto3 refuses an empty-string endpoint at runtime.
"""

import pytest
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.services.storage import service as storage


@pytest.fixture
def storage_settings():
    settings = get_settings()
    fields = ("storage_endpoint_url", "storage_access_key", "storage_secret_key", "storage_region")
    original = {f: getattr(settings, f) for f in fields}
    storage.get_client.cache_clear()
    storage.ensure_bucket_exists.cache_clear()
    yield settings
    for f, v in original.items():
        setattr(settings, f, v)
    storage.get_client.cache_clear()
    storage.ensure_bucket_exists.cache_clear()


def test_blank_endpoint_resolves_to_real_aws(storage_settings):
    """An empty endpoint must become None so boto3 picks the regional AWS host."""
    storage_settings.storage_endpoint_url = ""
    storage_settings.storage_access_key = ""
    storage_settings.storage_secret_key = ""
    storage_settings.storage_region = "ap-south-1"
    storage.get_client.cache_clear()

    client = storage.get_client()

    assert client.meta.endpoint_url == "https://s3.ap-south-1.amazonaws.com"


def test_custom_endpoint_is_honoured(storage_settings):
    """S3-compatible services (MinIO) still work."""
    storage_settings.storage_endpoint_url = "http://minio:9000"
    storage.get_client.cache_clear()

    assert storage.get_client().meta.endpoint_url == "http://minio:9000"


def test_missing_bucket_on_real_s3_raises_instead_of_creating(storage_settings, monkeypatch):
    """On AWS the bucket is provisioned ahead of time and the instance role isn't
    expected to hold CreateBucket — so a missing bucket is a deployment error,
    not something to paper over."""
    storage_settings.storage_endpoint_url = ""
    storage.get_client.cache_clear()
    storage.ensure_bucket_exists.cache_clear()

    error = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket")

    class FakeClient:
        def head_bucket(self, **_kwargs):
            raise error

        def create_bucket(self, **_kwargs):
            raise AssertionError("create_bucket must not be called against real S3")

    monkeypatch.setattr(storage, "get_client", lambda: FakeClient())

    with pytest.raises(ClientError):
        storage.ensure_bucket_exists()


def test_missing_bucket_is_created_for_a_custom_endpoint(storage_settings, monkeypatch):
    """Local development against MinIO should still bootstrap its own bucket."""
    storage_settings.storage_endpoint_url = "http://minio:9000"
    storage_settings.storage_region = "us-east-1"
    storage.ensure_bucket_exists.cache_clear()

    created = {}

    class FakeClient:
        def head_bucket(self, **_kwargs):
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket")

        def create_bucket(self, **kwargs):
            created.update(kwargs)

    monkeypatch.setattr(storage, "get_client", lambda: FakeClient())

    storage.ensure_bucket_exists()

    assert created["Bucket"] == storage_settings.storage_bucket
    # us-east-1 must not send a LocationConstraint — S3 rejects it.
    assert "CreateBucketConfiguration" not in created


def test_bucket_check_runs_once_per_process(storage_settings, monkeypatch):
    """It used to run on every upload, costing an S3 round trip per résumé."""
    storage_settings.storage_endpoint_url = ""
    storage.ensure_bucket_exists.cache_clear()

    calls = {"n": 0}

    class FakeClient:
        def head_bucket(self, **_kwargs):
            calls["n"] += 1

    monkeypatch.setattr(storage, "get_client", lambda: FakeClient())

    storage.ensure_bucket_exists()
    storage.ensure_bucket_exists()
    storage.ensure_bucket_exists()

    assert calls["n"] == 1
