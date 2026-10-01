"""Synthesis smoke test: the full app assembles without error."""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import assertions

from namma_ooru_infra.ai_stack import AiStack
from namma_ooru_infra.backend_stack import BackendStack
from namma_ooru_infra.config import NammaOoruConfig
from namma_ooru_infra.data_stack import DataStack
from namma_ooru_infra.frontend_stack import FrontendStack
from namma_ooru_infra.monitoring_stack import MonitoringStack


def test_full_app_synthesizes() -> None:
    app = cdk.App()
    config = NammaOoruConfig.from_context(app)
    env = cdk.Environment(account="111122223333", region="ap-south-1")

    data_stack = DataStack(app, f"{config.app_name}-data", config=config, env=env)
    ai_stack = AiStack(
        app,
        f"{config.app_name}-ai",
        config=config,
        source_bucket_arn=data_stack.source_bucket_arn,
        env=env,
    )
    backend_stack = BackendStack(
        app,
        f"{config.app_name}-backend",
        config=config,
        knowledge_base_id=ai_stack.knowledge_base.attr_knowledge_base_id,
        env=env,
    )
    FrontendStack(
        app,
        f"{config.app_name}-frontend",
        config=config,
        backend_api_url=backend_stack.api.api_endpoint,
        env=env,
    )
    MonitoringStack(
        app,
        f"{config.app_name}-monitoring",
        config=config,
        backend_function=backend_stack.function,
        backend_api=backend_stack.api,
        backend_log_group=backend_stack.log_group,
        env=env,
    )

    assembly = app.synth()
    stack_names = {s.stack_name for s in assembly.stacks}
    assert f"{config.app_name}-data" in stack_names
    assert f"{config.app_name}-ai" in stack_names
    assert f"{config.app_name}-backend" in stack_names
    assert f"{config.app_name}-frontend" in stack_names
    assert f"{config.app_name}-monitoring" in stack_names


def test_config_defaults_are_sane() -> None:
    app = cdk.App()
    config = NammaOoruConfig.from_context(app)
    assert config.vector_dimension > 0
    assert config.embedding_model_id == "amazon.titan-embed-text-v2:0"
    assert config.primary_generation_model_id == "us.amazon.nova-pro-v1:0"
    assert config.fallback_generation_model_id == "global.amazon.nova-2-lite-v1:0"


def test_data_stack_template_is_valid_json() -> None:
    app = cdk.App()
    config = NammaOoruConfig.from_context(app)
    stack = DataStack(app, "smoke-data", config=config)
    template = assertions.Template.from_stack(stack)
    assert template.to_json()["Resources"]


def test_enabled_full_app_wires_deployable_stacks_with_scoped_access() -> None:
    """Synthesize all stacks together, including the optional frontend deployment.

    This is intentionally cross-stack coverage: individual stack tests own detailed
    resource assertions, while this verifies their references remain valid when the
    independently deployable application is assembled.
    """
    app = cdk.App(
        context={
            "namma-ooru:frontendEnabled": True,
            "namma-ooru:frontendRepositoryUrl": "https://github.com/example/namma-ooru",
            "namma-ooru:corsAllowedOrigins": ["https://travel.example.test"],
        }
    )
    config = NammaOoruConfig.from_context(app)
    env = cdk.Environment(account="111122223333", region="ap-south-1")

    data_stack = DataStack(app, f"{config.app_name}-data", config=config, env=env)
    ai_stack = AiStack(
        app,
        f"{config.app_name}-ai",
        config=config,
        source_bucket_arn=data_stack.source_bucket_arn,
        env=env,
    )
    backend_stack = BackendStack(
        app,
        f"{config.app_name}-backend",
        config=config,
        knowledge_base_id=ai_stack.knowledge_base.attr_knowledge_base_id,
        env=env,
    )
    frontend_stack = FrontendStack(
        app,
        f"{config.app_name}-frontend",
        config=config,
        backend_api_url=backend_stack.api.api_endpoint,
        env=env,
    )
    MonitoringStack(
        app,
        f"{config.app_name}-monitoring",
        config=config,
        backend_function=backend_stack.function,
        backend_api=backend_stack.api,
        backend_log_group=backend_stack.log_group,
        env=env,
    )

    assembly = app.synth()
    assert {stack.stack_name for stack in assembly.stacks} == {
        f"{config.app_name}-data",
        f"{config.app_name}-ai",
        f"{config.app_name}-backend",
        f"{config.app_name}-frontend",
        f"{config.app_name}-monitoring",
    }

    backend_template = assertions.Template.from_stack(backend_stack)
    frontend_template = assertions.Template.from_stack(frontend_stack)
    backend_template.has_resource_properties(
        "AWS::ApiGatewayV2::Api",
        {
            "CorsConfiguration": assertions.Match.object_like(
                {"AllowOrigins": ["https://travel.example.test"]}
            )
        },
    )
    assert "BackendApiUrl" in backend_template.find_outputs("*")
    assert "FrontendHostingUrl" in frontend_template.find_outputs("*")

    frontend_app = next(iter(frontend_template.find_resources("AWS::Amplify::App").values()))
    environment_variables = frontend_app["Properties"]["EnvironmentVariables"]
    api_url_variable = next(
        variable for variable in environment_variables if variable["Name"] == "VITE_API_BASE_URL"
    )
    assert "Fn::ImportValue" in str(api_url_variable["Value"])

    for stack in (ai_stack, backend_stack):
        policies = assertions.Template.from_stack(stack).find_resources("AWS::IAM::Policy")
        for policy in policies.values():
            for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
                resources = statement["Resource"]
                for resource in resources if isinstance(resources, list) else [resources]:
                    assert resource != "*", f"unscoped IAM resource in {statement.get('Sid')}"
