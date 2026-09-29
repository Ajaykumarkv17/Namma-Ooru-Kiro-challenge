"""Reusable secure S3 bucket construct for Namma Ooru source data."""

from __future__ import annotations

from aws_cdk import RemovalPolicy
from aws_cdk import aws_s3 as s3
from constructs import Construct


class SourceDataBucket(Construct):
    """A hardened S3 bucket for storing source documents.

    Security defaults (Security steering): all public access blocked, SSL
    enforced, S3-managed encryption, and versioning enabled so ingested source
    documents have an auditable history.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        versioned: bool = True,
    ) -> None:
        super().__init__(scope, construct_id)

        self.bucket = s3.Bucket(
            self,
            "Bucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=versioned,
            removal_policy=RemovalPolicy.RETAIN,
        )

    @property
    def bucket_arn(self) -> str:
        """ARN of the underlying bucket."""
        return self.bucket.bucket_arn

    @property
    def bucket_name(self) -> str:
        """Name of the underlying bucket."""
        return self.bucket.bucket_name
