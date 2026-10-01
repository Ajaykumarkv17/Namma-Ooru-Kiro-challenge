"""FrontendStack: optional AWS Amplify Hosting for the Vite frontend."""

from __future__ import annotations

from typing import Any

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_amplify as amplify
from constructs import Construct

from namma_ooru_infra.config import NammaOoruConfig


class FrontendStack(Stack):
    """Deploy the frontend through Amplify when hosting is enabled in CDK context."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: NammaOoruConfig,
        backend_api_url: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.amplify_app: amplify.CfnApp | None = None
        self.production_branch: amplify.CfnBranch | None = None
        if not config.frontend_enabled:
            return

        app_properties: dict[str, Any] = {
            "name": f"{config.app_name}-frontend",
            "platform": "WEB",
            "build_spec": _build_spec(),
            "environment_variables": [
                amplify.CfnApp.EnvironmentVariableProperty(
                    name="VITE_API_BASE_URL",
                    value=backend_api_url,
                )
            ],
            "custom_rules": [
                amplify.CfnApp.CustomRuleProperty(
                    source="/<*>",
                    target="/index.html",
                    status="404-200",
                )
            ],
        }
        if config.frontend_repository_url:
            app_properties["repository"] = config.frontend_repository_url

        self.amplify_app = amplify.CfnApp(self, "FrontendApp", **app_properties)
        self.production_branch = amplify.CfnBranch(
            self,
            "ProductionBranch",
            app_id=self.amplify_app.attr_app_id,
            branch_name=config.frontend_branch,
            enable_auto_build=True,
            stage="PRODUCTION",
        )
        CfnOutput(
            self,
            "FrontendHostingUrl",
            value=f"https://{config.frontend_branch}.{self.amplify_app.attr_default_domain}",
            description="Namma Ooru Amplify Hosting URL.",
        )


def _build_spec() -> str:
    """Return the Vite build instructions used by Amplify Hosting."""
    return """version: 1
applications:
  - appRoot: frontend
    frontend:
      phases:
        preBuild:
          commands:
            - npm ci
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: dist
        files:
          - '**/*'
      cache:
        paths:
          - node_modules/**/*
"""
