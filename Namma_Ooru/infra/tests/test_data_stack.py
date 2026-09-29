"""CDK assertion tests for the Namma Ooru DataStack."""

from __future__ import annotations

import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from namma_ooru_infra.config import NammaOoruConfig
from namma_ooru_infra.data_stack import DataStack


@pytest.fixture(scope="module")
def template() -> assertions.Template:
    app = cdk.App()
    config = NammaOoruConfig.from_context(app)
    stack = DataStack(
        app,
        "test-data",
        config=config,
        env=cdk.Environment(account="111122223333", region="ap-south-1"),
    )
    return assertions.Template.from_stack(stack)


def test_creates_exactly_one_source_bucket(template: assertions.Template) -> None:
    template.resource_count_is("AWS::S3::Bucket", 1)


def test_bucket_blocks_public_access(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            }
        },
    )


def test_bucket_is_encrypted_and_versioned(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": assertions.Match.array_with(
                    [
                        {
                            "ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
                        }
                    ]
                )
            },
            "VersioningConfiguration": {"Status": "Enabled"},
        },
    )


def test_bucket_enforces_ssl(template: assertions.Template) -> None:
    # enforce_ssl adds a bucket policy that denies non-TLS access.
    template.has_resource_properties(
        "AWS::S3::BucketPolicy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Effect": "Deny",
                                "Condition": {"Bool": {"aws:SecureTransport": "false"}},
                            }
                        )
                    ]
                )
            }
        },
    )


def test_exposes_bucket_outputs(template: assertions.Template) -> None:
    outputs = template.find_outputs("*")
    output_keys = set(outputs.keys())
    assert "SourceDataBucketName" in output_keys
    assert "SourceDataBucketArn" in output_keys
