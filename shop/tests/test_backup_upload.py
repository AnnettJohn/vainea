"""Offsite-Backup in den Objektspeicher.

Laeuft gegen einen von moto gemockten S3-Dienst: echter boto3-Code, echte
ACL- und Listing-Aufrufe, kein echter Bucket noetig.
"""

from datetime import datetime, timedelta, timezone

import boto3
import pytest
from moto import mock_aws

from scripts import upload_backup

BACKUP_BUCKET = "vainea-backups"
IMAGE_BUCKET = "vainea-product-images"


@pytest.fixture
def s3_env(monkeypatch):
    settings = upload_backup.settings
    monkeypatch.setattr(settings, "s3_endpoint_url", "https://s3.amazonaws.com")
    monkeypatch.setattr(settings, "s3_region", "us-east-1")
    monkeypatch.setattr(settings, "s3_bucket", IMAGE_BUCKET)
    monkeypatch.setattr(settings, "s3_backup_bucket", BACKUP_BUCKET)
    monkeypatch.setattr(settings, "s3_access_key_id", "test-key")
    monkeypatch.setattr(settings, "s3_secret_access_key", "test-secret")
    monkeypatch.setattr(settings, "backup_retention_days", 30)

    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BACKUP_BUCKET)
        client.create_bucket(Bucket=IMAGE_BUCKET)
        yield client


@pytest.fixture
def dump_file(tmp_path):
    path = tmp_path / "vainea-20260920-032000.dump"
    path.write_bytes(b"PGDMP fake dump content")
    return path


def test_refuses_public_image_bucket(s3_env, monkeypatch):
    """Der Bilder-Bucket ist oeffentlich lesbar. Ein Dump dort waere ein
    Datenleck mit Namen, Adressen und Bestellhistorien - das muss das
    Skript strukturell verhindern, nicht nur die Doku."""
    monkeypatch.setattr(upload_backup.settings, "s3_backup_bucket", IMAGE_BUCKET)

    with pytest.raises(upload_backup.BackupUploadError, match="oeffentlich lesbar"):
        upload_backup.check_target()


def test_refuses_when_backup_bucket_unset(s3_env, monkeypatch):
    monkeypatch.setattr(upload_backup.settings, "s3_backup_bucket", "")

    with pytest.raises(upload_backup.BackupUploadError, match="nicht gesetzt"):
        upload_backup.check_target()


def test_upload_stores_dump_privately(s3_env, dump_file):
    key = upload_backup.upload(s3_env, BACKUP_BUCKET, dump_file)

    assert key == f"db/{dump_file.name}"
    obj = s3_env.get_object(Bucket=BACKUP_BUCKET, Key=key)
    assert obj["ContentLength"] == dump_file.stat().st_size

    # Kein Grant fuer "AllUsers" - das Objekt darf nicht oeffentlich sein.
    acl = s3_env.get_object_acl(Bucket=BACKUP_BUCKET, Key=key)
    grantees = [g["Grantee"].get("URI", "") for g in acl["Grants"]]
    assert not any("AllUsers" in uri for uri in grantees)


def test_upload_detects_truncated_transfer(s3_env, dump_file, monkeypatch):
    """Ein abgebrochener Upload hinterlaesst ein Objekt, das wie ein Backup
    aussieht. Die Groessenpruefung muss das melden."""
    monkeypatch.setattr(
        s3_env, "head_object", lambda **kwargs: {"ContentLength": 3}
    )

    with pytest.raises(upload_backup.BackupUploadError, match="unvollstaendig"):
        upload_backup.upload(s3_env, BACKUP_BUCKET, dump_file)


def test_prune_removes_only_old_dumps(s3_env):
    old_key = "db/vainea-alt.dump"
    new_key = "db/vainea-neu.dump"
    s3_env.put_object(Bucket=BACKUP_BUCKET, Key=old_key, Body=b"alt")
    s3_env.put_object(Bucket=BACKUP_BUCKET, Key=new_key, Body=b"neu")

    # moto setzt LastModified auf "jetzt"; deshalb den Stichtag verschieben,
    # indem wir mit einer Aufbewahrung von 0 Tagen und einem kuenstlich in
    # die Zukunft gelegten Objekt arbeiten.
    original = s3_env.list_objects_v2

    def fake_list(**kwargs):
        result = original(**kwargs)
        for obj in result.get("Contents", []):
            if obj["Key"] == old_key:
                obj["LastModified"] = datetime.now(timezone.utc) - timedelta(days=99)
        return result

    class _Paginator:
        def paginate(self, **kwargs):
            yield fake_list(**kwargs)

    s3_env.get_paginator = lambda name: _Paginator()

    deleted = upload_backup.prune(s3_env, BACKUP_BUCKET, retention_days=30)

    assert deleted == [old_key]
    remaining = [o["Key"] for o in original(Bucket=BACKUP_BUCKET)["Contents"]]
    assert remaining == [new_key]
