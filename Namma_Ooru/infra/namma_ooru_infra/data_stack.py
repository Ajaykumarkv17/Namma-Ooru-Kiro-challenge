"""DataStack: source-document S3 bucket and application data resources.

Owns the S3 bucket that holds the Knowledge Base source documents
(``data/kb/<id>.md`` and ``<id>.md.metadata.json`` sidecars) plus their source
URLs. The AI stack ingests these documents via a Bedrock S3 data source.
"""

from __future__ import annotations

from typing import Any

from aws_cdk import CfnOutput, Stack
from constructs import Construct

from namma_ooru_infra.config import NammaOoruConfig
from namma_ooru_infra.constructs import SourceDataBucket


class DataStack(Stack):
    """Application data resources for Namma Ooru."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: NammaOoruConfig,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.config = config

        # S3 bucket holding the KB source documents and metadata sidecars.
        self.source_data = SourceDataBucket(self, "SourceData")

        CfnOutput(
            self,
            "SourceDataBucketName",
            value=self.source_data.bucket_name,
            description="S3 bucket holding Knowledge Base source documents.",
            export_name=f"{config.app_name}-source-data-bucket-name",
        )
        CfnOutput(
            self,
            "SourceDataBucketArn",
            value=self.source_data.bucket_arn,
            description="ARN of the Knowledge Base source-document bucket.",
            export_name=f"{config.app_name}-source-data-bucket-arn",
        )

    @property
    def source_bucket_arn(self) -> str:
        """ARN of the source-document bucket (consumed by the AI stack)."""
        return self.source_data.bucket_arn

    @property
    def source_bucket_name(self) -> str:
        """Name of the source-document bucket."""
        return self.source_data.bucket_name
