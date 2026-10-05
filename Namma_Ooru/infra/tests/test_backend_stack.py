"""CDK assertions for the Namma Ooru independently deployable BackendStack."""

from __future__ import annotations

import json

import aws_cdk as cdk
import pytest
from aws_cdk import assertions

from namma_ooru_infra.backend_stack import LAMBDA_BUNDLING_COMMAND, BackendStack
from namma_ooru_infra.config import NammaOoruConfig

ACCOUNT = "111122223333"
REGION = "ap-south-1"
KNOWLEDGE_BASE_ID = "TESTKB123"
PRIMARY_PROFILE = "us.amazon.nova-pro-v1:0"
FALLBACK_PROFILE = "global.amazon.nova-2-lite-v1:0"


@pytest.fixture(scope="module")
def template() -> assertions.Template:
    app = cdk.App(context={"namma-ooru:corsAllowedOrigins": ["https://app.example.test"]})
    config = NammaOoruConfig.from_context(app)
    stack = BackendStack(
        app,
        "test-backend",
        config=config,
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        env=cdk.Environment(account=ACCOUNT, region=REGION),
    )
    return assertions.Template.from_stack(stack)


def test_creates_python_lambda_and_http_api(template: assertions.Template) -> None:
    template.resource_count_is("AWS::Lambda::Function", 1)
    template.resource_count_is("AWS::ApiGatewayV2::Api", 1)
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {"Handler": "app.lambda_handler.handler", "Runtime": "python3.11", "Timeout": 29},
    )
    template.has_resource_properties("AWS::ApiGatewayV2::Api", {"ProtocolType": "HTTP"})


def test_restricts_cors_to_configured_frontend_origin(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::ApiGatewayV2::Api",
        {
            "CorsConfiguration": {
                "AllowOrigins": ["https://app.example.test"],
                "AllowMethods": ["GET", "POST"],
                "AllowHeaders": ["content-type"],
                "AllowCredentials": False,
            }
        },
    )


def test_lambda_bundling_installs_dependencies_and_copies_catalog() -> None:
    command = LAMBDA_BUNDLING_COMMAND[2]
    assert "/asset-input/backend/requirements.txt" in command
    assert "-t /asset-output" in command
    assert "/asset-input/data/destinations.json" in command
    assert "/asset-output/data/destinations.json" in command


def test_exposes_backend_api_url(template: assertions.Template) -> None:
    assert "BackendApiUrl" in template.find_outputs("*")


def test_runtime_role_scopes_bedrock_to_profiles_and_associated_models(
    template: assertions.Template,
) -> None:
    policies = template.find_resources("AWS::IAM::Policy")
    statements = [
        statement
        for policy in policies.values()
        for statement in policy["Properties"]["PolicyDocument"]["Statement"]
    ]
    by_sid = {statement["Sid"]: statement for statement in statements}
    assert set(by_sid) == {
        "WriteBackendLogs",
        "RetrieveGroundedKnowledge",
        "GenerateGroundedResponses",
    }
    assert by_sid["RetrieveGroundedKnowledge"]["Action"] == "bedrock:Retrieve"
    generation = by_sid["GenerateGroundedResponses"]
    assert generation["Action"] == "bedrock:InvokeModel"
    serialized_resources = json.dumps(generation["Resource"], sort_keys=True)
    for expected_resource in (
        f"inference-profile/{PRIMARY_PROFILE}",
        f"inference-profile/{FALLBACK_PROFILE}",
        "foundation-model/amazon.nova-pro-v1:0",
        "foundation-model/amazon.nova-2-lite-v1:0",
    ):
        assert expected_resource in serialized_resources
    for statement in statements:
        resources = statement["Resource"]
        assert resources != "*"
        if isinstance(resources, list):
            assert all(resource != "*" for resource in resources)


def test_lambda_receives_non_secret_runtime_configuration(template: assertions.Template) -> None:
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Environment": {
                "Variables": {
                    "AI_PROVIDER": "bedrock",
                    "CORS_ALLOWED_ORIGINS": "https://app.example.test",
                    "BEDROCK_KB_ID": KNOWLEDGE_BASE_ID,
                    "BEDROCK_PRIMARY_MODEL_ID": PRIMARY_PROFILE,
                    "BEDROCK_FALLBACK_MODEL_ID": FALLBACK_PROFILE,
                }
            }
        },
    )
