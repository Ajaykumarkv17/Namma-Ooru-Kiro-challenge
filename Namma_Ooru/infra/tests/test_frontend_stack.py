"""CDK assertions for the optional Amplify Hosting frontend stack."""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import assertions

from namma_ooru_infra.config import NammaOoruConfig
from namma_ooru_infra.frontend_stack import FrontendStack


def test_enabled_frontend_creates_amplify_hosting_with_backend_url() -> None:
    app = cdk.App(
        context={
            "namma-ooru:frontendEnabled": True,
            "namma-ooru:frontendBranch": "main",
            "namma-ooru:frontendRepositoryUrl": "https://github.com/example/namma-ooru",
        }
    )
    stack = FrontendStack(
        app,
        "test-frontend",
        config=NammaOoruConfig.from_context(app),
        backend_api_url="https://api.example.test",
    )
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::Amplify::App", 1)
    template.resource_count_is("AWS::Amplify::Branch", 1)
    template.has_resource_properties(
        "AWS::Amplify::App",
        {
            "Platform": "WEB",
            "Repository": "https://github.com/example/namma-ooru",
            "EnvironmentVariables": [
                {"Name": "VITE_API_BASE_URL", "Value": "https://api.example.test"}
            ],
        },
    )
    template.has_resource_properties(
        "AWS::Amplify::Branch",
        {"BranchName": "main", "EnableAutoBuild": True, "Stage": "PRODUCTION"},
    )
    assert "FrontendHostingUrl" in template.find_outputs("*")


def test_disabled_frontend_does_not_create_hosting_resources() -> None:
    app = cdk.App()
    stack = FrontendStack(
        app,
        "disabled-frontend",
        config=NammaOoruConfig.from_context(app),
        backend_api_url="https://api.example.test",
    )

    template = assertions.Template.from_stack(stack)
    template.resource_count_is("AWS::Amplify::App", 0)
    template.resource_count_is("AWS::Amplify::Branch", 0)
