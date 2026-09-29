"""CDK app entry point for Namma Ooru infrastructure.

Environment (account/region) is resolved from the standard CDK environment
variables populated by the AWS credential chain; no credentials are hardcoded.
The data and AI stacks are deployed first so a local frontend can be tested
against a deployed backend before the frontend stack is deployed.
"""

from __future__ import annotations

import os

import aws_cdk as cdk

from namma_ooru_infra.ai_stack import AiStack
from namma_ooru_infra.config import NammaOoruConfig
from namma_ooru_infra.data_stack import DataStack


def _resolve_env() -> cdk.Environment | None:
    """Resolve deploy env from the credential chain, if available."""
    account = os.environ.get("CDK_DEFAULT_ACCOUNT")
    region = os.environ.get("CDK_DEFAULT_REGION")
    if account and region:
        return cdk.Environment(account=account, region=region)
    return None


def main() -> None:
    app = cdk.App()
    config = NammaOoruConfig.from_context(app)
    env = _resolve_env()

    data_stack = DataStack(
        app,
        f"{config.app_name}-data",
        config=config,
        env=env,
    )
    AiStack(
        app,
        f"{config.app_name}-ai",
        config=config,
        source_bucket_arn=data_stack.source_bucket_arn,
        env=env,
    )

    app.synth()


if __name__ == "__main__":
    main()
