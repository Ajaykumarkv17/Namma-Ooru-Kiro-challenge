"""BackendStack: FastAPI Lambda and independently deployable HTTP API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aws_cdk import BundlingOptions, CfnOutput, Duration, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct

from namma_ooru_infra.config import NammaOoruConfig

LAMBDA_BUNDLING_COMMAND = [
    "bash",
    "-c",
    "pip install --no-cache-dir -r /asset-input/backend/requirements.txt -t /asset-output && "
    "cp -r /asset-input/backend/app /asset-output/app && "
    "mkdir -p /asset-output/data && "
    "cp /asset-input/data/destinations.json /asset-output/data/destinations.json",
]


class BackendStack(Stack):
    """Deploy the FastAPI backend behind a CORS-restricted HTTP API."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: NammaOoruConfig,
        knowledge_base_id: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_directory = Path(__file__).resolve().parents[2]
        function_name = f"{config.app_name}-backend"
        self.log_group = logs.LogGroup(
            self,
            "BackendLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_MONTH,
        )
        self.runtime_role = iam.Role(
            self,
            "BackendRuntimeRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Least-privilege runtime role for the Namma Ooru backend Lambda.",
        )
        self.runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="WriteBackendLogs",
                effect=iam.Effect.ALLOW,
                actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                resources=[f"{self.log_group.log_group_arn}:*"],
            )
        )

        knowledge_base_arn = self.format_arn(
            service="bedrock",
            resource="knowledge-base",
            resource_name=knowledge_base_id,
        )
        generation_profiles = (
            config.primary_generation_model_id,
            config.fallback_generation_model_id,
        )
        generation_resources = [
            f"arn:{self.partition}:bedrock:{self.region}::inference-profile/{profile}"
            for profile in generation_profiles
        ]
        # System inference profiles can route generation to their associated model in
        # more than one region. Scope this to only the two selected model IDs rather
        # than granting access to every foundation model.
        generation_resources.extend(
            f"arn:{self.partition}:bedrock:*::foundation-model/{profile.split('.', 1)[1]}"
            for profile in generation_profiles
        )
        self.runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="RetrieveGroundedKnowledge",
                effect=iam.Effect.ALLOW,
                actions=["bedrock:Retrieve"],
                resources=[knowledge_base_arn],
            )
        )
        self.runtime_role.add_to_policy(
            iam.PolicyStatement(
                sid="GenerateGroundedResponses",
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=generation_resources,
            )
        )

        self.function = lambda_.Function(
            self,
            "BackendFunction",
            function_name=function_name,
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="app.lambda_handler.handler",
            code=lambda_.Code.from_asset(
                str(project_directory),
                exclude=[
                    ".git",
                    ".workflow-artifacts",
                    "backend/.hypothesis",
                    "backend/.mypy_cache",
                    "backend/.pytest_cache",
                    "backend/.ruff_cache",
                    "backend/tests",
                    "backend/.venv",
                    "frontend",
                    "infra",
                ],
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    command=LAMBDA_BUNDLING_COMMAND,
                ),
            ),
            role=self.runtime_role,
            timeout=Duration.seconds(29),
            memory_size=512,
            environment={
                "AI_PROVIDER": "bedrock",
                "CORS_ALLOWED_ORIGINS": ",".join(config.cors_allowed_origins),
                "BEDROCK_KB_ID": knowledge_base_id,
                "BEDROCK_PRIMARY_MODEL_ID": config.primary_generation_model_id,
                "BEDROCK_FALLBACK_MODEL_ID": config.fallback_generation_model_id,
            },
        )
        self.function.node.add_dependency(self.log_group)

        self.api = apigwv2.HttpApi(
            self,
            "BackendApi",
            api_name=f"{config.app_name}-api",
            description="Namma Ooru FastAPI HTTP API.",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=list(config.cors_allowed_origins),
                allow_methods=[apigwv2.CorsHttpMethod.GET, apigwv2.CorsHttpMethod.POST],
                allow_headers=["content-type"],
                allow_credentials=False,
                max_age=Duration.hours(1),
            ),
        )
        self.api.add_routes(
            path="/{proxy+}",
            methods=[apigwv2.HttpMethod.ANY],
            integration=integrations.HttpLambdaIntegration("BackendIntegration", self.function),
        )
        self.api.add_routes(
            path="/",
            methods=[apigwv2.HttpMethod.ANY],
            integration=integrations.HttpLambdaIntegration("BackendRootIntegration", self.function),
        )

        CfnOutput(
            self,
            "BackendApiUrl",
            value=self.api.api_endpoint,
            description="Namma Ooru backend API URL for frontend configuration.",
            export_name=f"{config.app_name}-backend-api-url",
        )
