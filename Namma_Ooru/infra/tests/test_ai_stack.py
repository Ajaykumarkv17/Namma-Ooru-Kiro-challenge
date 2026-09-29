"""CDK assertion tests for the Namma Ooru AiStack (RAG infrastructure)."""

from __future__ import annotations

import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from namma_ooru_infra.ai_stack import AiStack
from namma_ooru_infra.config import NammaOoruConfig
from namma_ooru_infra.constructs.vector_store import (
    BEDROCK_TEXT_METADATA_KEY,
    FILTERABLE_METADATA_KEYS,
)
from namma_ooru_infra.data_stack import DataStack

ACCOUNT = "111122223333"
REGION = "ap-south-1"


@pytest.fixture(scope="module")
def template() -> assertions.Template:
    app = cdk.App()
    config = NammaOoruConfig.from_context(app)
    env = cdk.Environment(account=ACCOUNT, region=REGION)
    data_stack = DataStack(app, "test-data", config=config, env=env)
    ai_stack = AiStack(
        app,
        "test-ai",
        config=config,
        source_bucket_arn=data_stack.source_bucket_arn,
        env=env,
    )
    return assertions.Template.from_stack(ai_stack)


# --- Core resources ------------------------------------------------------


def test_creates_vector_bucket_and_index(template: assertions.Template) -> None:
    template.resource_count_is("AWS::S3Vectors::VectorBucket", 1)
    template.resource_count_is("AWS::S3Vectors::Index", 1)


def test_creates_knowledge_base_and_data_source(template: assertions.Template) -> None:
    template.resource_count_is("AWS::Bedrock::KnowledgeBase", 1)
    template.resource_count_is("AWS::Bedrock::DataSource", 1)


def test_creates_single_knowledge_base_role(template: assertions.Template) -> None:
    template.resource_count_is("AWS::IAM::Role", 1)


# --- S3 Vectors index metadata configuration ----------------------------


def test_index_marks_bedrock_text_non_filterable(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::S3Vectors::Index",
        {
            "MetadataConfiguration": {
                "NonFilterableMetadataKeys": [BEDROCK_TEXT_METADATA_KEY],
            },
            "DistanceMetric": "cosine",
            "DataType": "float32",
        },
    )


def test_retrieval_metadata_stays_filterable(template: assertions.Template) -> None:
    # Only AMAZON_BEDROCK_TEXT is non-filterable; retrieval keys are absent from
    # the non-filterable list, so they remain filterable.
    index = template.find_resources("AWS::S3Vectors::Index")
    (props,) = (r["Properties"] for r in index.values())
    non_filterable = props["MetadataConfiguration"]["NonFilterableMetadataKeys"]
    for key in FILTERABLE_METADATA_KEYS:
        assert key not in non_filterable


# --- Knowledge Base configuration ----------------------------------------


def test_knowledge_base_uses_s3_vectors_storage(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::Bedrock::KnowledgeBase",
        {
            "KnowledgeBaseConfiguration": {"Type": "VECTOR"},
            "StorageConfiguration": {"Type": "S3_VECTORS"},
        },
    )


def test_data_source_is_s3_type(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::Bedrock::DataSource",
        {"DataSourceConfiguration": {"Type": "S3"}},
    )


# --- Least-privilege IAM --------------------------------------------------


def test_kb_role_trusts_bedrock_service(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "bedrock.amazonaws.com"},
                                "Condition": {"StringEquals": {"aws:SourceAccount": ACCOUNT}},
                            }
                        )
                    ]
                )
            }
        },
    )


def test_kb_policy_has_no_wildcard_resources(template: assertions.Template) -> None:
    policies = template.find_resources("AWS::IAM::Policy")
    assert policies, "expected an inline managed policy for the KB role"
    for policy in policies.values():
        for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
            resources = statement["Resource"]
            resource_list = resources if isinstance(resources, list) else [resources]
            for resource in resource_list:
                # A bare "*" resource would violate least-privilege (Req 12.4).
                assert resource != "*", f"wildcard resource in statement {statement.get('Sid')}"


def test_kb_policy_scopes_bedrock_invoke_to_embedding_model(
    template: assertions.Template,
) -> None:
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Sid": "InvokeEmbeddingModel",
                                "Action": "bedrock:InvokeModel",
                                "Effect": "Allow",
                            }
                        )
                    ]
                )
            }
        },
    )


def test_kb_policy_reads_only_source_bucket(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Sid": "ReadSourceDocuments",
                                "Action": ["s3:GetObject", "s3:ListBucket"],
                                "Effect": "Allow",
                            }
                        )
                    ]
                )
            }
        },
    )


# --- Outputs --------------------------------------------------------------


def test_exposes_expected_outputs(template: assertions.Template) -> None:
    output_keys = set(template.find_outputs("*").keys())
    for expected in (
        "KnowledgeBaseId",
        "DataSourceId",
        "VectorBucketArn",
        "VectorIndexArn",
        "KnowledgeBaseRoleArn",
    ):
        assert expected in output_keys
