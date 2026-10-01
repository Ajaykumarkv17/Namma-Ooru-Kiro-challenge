"""MonitoringStack: CloudWatch alarms, dashboard, and backend log visibility."""

from __future__ import annotations

from typing import Any

from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct

from namma_ooru_infra.config import NammaOoruConfig


class MonitoringStack(Stack):
    """Expose backend health through CloudWatch alarms and a compact dashboard."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: NammaOoruConfig,
        backend_function: lambda_.IFunction,
        backend_api: apigwv2.HttpApi,
        backend_log_group: logs.ILogGroup,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        period = Duration.minutes(5)
        lambda_errors = backend_function.metric_errors(period=period, statistic="sum")
        api_server_errors = cloudwatch.Metric(
            namespace="AWS/ApiGateway",
            metric_name="5xx",
            dimensions_map={"ApiId": backend_api.http_api_id},
            period=period,
            statistic="sum",
        )
        self.lambda_error_alarm = cloudwatch.Alarm(
            self,
            "BackendLambdaErrorsAlarm",
            alarm_name=f"{config.app_name}-backend-lambda-errors",
            alarm_description="Namma Ooru backend Lambda reported one or more errors.",
            metric=lambda_errors,
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        self.api_5xx_alarm = cloudwatch.Alarm(
            self,
            "BackendApi5xxAlarm",
            alarm_name=f"{config.app_name}-backend-api-5xx",
            alarm_description="Namma Ooru backend API returned one or more 5xx responses.",
            metric=api_server_errors,
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        self.dashboard = cloudwatch.Dashboard(
            self,
            "OperationsDashboard",
            dashboard_name=f"{config.app_name}-operations",
        )
        self.dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Backend errors and API 5xx responses",
                left=[lambda_errors, api_server_errors],
                width=12,
            ),
            cloudwatch.GraphWidget(
                title="Backend Lambda duration",
                left=[backend_function.metric_duration(period=period)],
                width=12,
            ),
            cloudwatch.LogQueryWidget(
                title="Recent backend Lambda logs",
                log_group_names=[backend_log_group.log_group_name],
                query_lines=["fields @timestamp, @message", "sort @timestamp desc", "limit 20"],
                width=24,
            ),
        )
        CfnOutput(
            self,
            "OperationsDashboardName",
            value=self.dashboard.dashboard_name,
            description="CloudWatch dashboard for Namma Ooru backend operations.",
        )
