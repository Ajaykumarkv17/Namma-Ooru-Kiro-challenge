"""CDK assertions for backend CloudWatch monitoring resources."""

from __future__ import annotations

import json

import aws_cdk as cdk
from aws_cdk import assertions
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs

from namma_ooru_infra.config import NammaOoruConfig
from namma_ooru_infra.monitoring_stack import MonitoringStack


def test_creates_backend_alarms_dashboard_and_log_query() -> None:
    app = cdk.App()
    stack = cdk.Stack(app, "backend-resources")
    function = lambda_.Function(
        stack,
        "Function",
        runtime=lambda_.Runtime.PYTHON_3_11,
        handler="index.handler",
        code=lambda_.Code.from_inline("def handler(event, context): return {}"),
    )
    api = apigwv2.HttpApi(stack, "Api")
    log_group = logs.LogGroup(stack, "LogGroup")
    monitoring = MonitoringStack(
        app,
        "test-monitoring",
        config=NammaOoruConfig.from_context(app),
        backend_function=function,
        backend_api=api,
        backend_log_group=log_group,
    )
    template = assertions.Template.from_stack(monitoring)

    template.resource_count_is("AWS::CloudWatch::Alarm", 2)
    template.resource_count_is("AWS::CloudWatch::Dashboard", 1)
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {"Threshold": 1, "EvaluationPeriods": 1, "TreatMissingData": "notBreaching"},
    )
    assert "OperationsDashboardName" in template.find_outputs("*")
    dashboard = next(iter(template.find_resources("AWS::CloudWatch::Dashboard").values()))
    assert "Recent backend Lambda logs" in json.dumps(dashboard["Properties"]["DashboardBody"])
