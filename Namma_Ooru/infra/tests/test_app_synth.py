"""Synthesis smoke test: the full app assembles without error."""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import assertions

from namma_ooru_infra.ai_stack import AiStack
from namma_ooru_infra.config import NammaOoruConfig
from namma_ooru_infra.data_stack import DataStack


def test_full_app_synthesizes() -> None:
    app = cdk.App()
    config = NammaOoruConfig.from_context(app)
    env = cdk.Environment(account="111122223333", region="ap-south-1")

    data_stack = DataStack(app, f"{config.app_name}-data", config=config, env=env)
    AiStack(
        app,
        f"{config.app_name}-ai",
        config=config,
        source_bucket_arn=data_stack.source_bucket_arn,
        env=env,
    )

    assembly = app.synth()
    stack_names = {s.stack_name for s in assembly.stacks}
    assert f"{config.app_name}-data" in stack_names
    assert f"{config.app_name}-ai" in stack_names


def test_config_defaults_are_sane() -> None:
    app = cdk.App()
    config = NammaOoruConfig.from_context(app)
    assert config.vector_dimension > 0
    assert config.embedding_model_id
    assert config.knowledge_base_model_id


def test_data_stack_template_is_valid_json() -> None:
    app = cdk.App()
    config = NammaOoruConfig.from_context(app)
    stack = DataStack(app, "smoke-data", config=config)
    template = assertions.Template.from_stack(stack)
    assert template.to_json()["Resources"]
