"""AiStack: S3 Vectors store, Bedrock Knowledge Base, S3 data source, roles.

The Knowledge Base ingests source documents from the DataStack bucket, embeds
them with Titan, and stores vectors in an S3 Vectors index. A least-privilege
service role lets Bedrock read the source bucket, invoke the embedding model,
and access the vector store — nothing more (Security + Architecture steering,
Req 12.4).
"""

from __future__ import annotations

from typing import Any

from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_bedrock as bedrock
from aws_cdk import aws_iam as iam
from constructs import Construct

from namma_ooru_infra.config import NammaOoruConfig
from namma_ooru_infra.constructs import VectorStore


class AiStack(Stack):
    """RAG infrastructure: vector store, Knowledge Base, data source, KB role."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: NammaOoruConfig,
        source_bucket_arn: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.config = config
        vector_bucket_name = f"{config.app_name}-vectors-{self.account}-{self.region}"
        index_name = f"{config.app_name}-kb-index"

        # Titan embedding model ARN in this account's region.
        embedding_model_arn = (
            f"arn:{self.partition}:bedrock:{self.region}::"
            f"foundation-model/{config.embedding_model_id}"
        )

        # --- S3 Vectors store (bucket + index) -------------------------------
        self.vector_store = VectorStore(
            self,
            "VectorStore",
            vector_bucket_name=vector_bucket_name,
            index_name=index_name,
            dimension=config.vector_dimension,
        )

        # --- Least-privilege Knowledge Base service role ---------------------
        # Trust policy restricts assumption to the Bedrock service within this
        # account (confused-deputy protection via the source-account condition).
        self.knowledge_base_role = iam.Role(
            self,
            "KnowledgeBaseRole",
            assumed_by=iam.ServicePrincipal(
                "bedrock.amazonaws.com",
                conditions={"StringEquals": {"aws:SourceAccount": self.account}},
            ),
            description="Least-privilege role assumed by the Namma Ooru Bedrock Knowledge Base.",
        )

        # Read-only access to exactly the source-document bucket and its objects.
        self.knowledge_base_role.add_to_policy(
            iam.PolicyStatement(
                sid="ReadSourceDocuments",
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[source_bucket_arn, f"{source_bucket_arn}/*"],
            )
        )
        # Invoke only the configured Titan embedding model.
        self.knowledge_base_role.add_to_policy(
            iam.PolicyStatement(
                sid="InvokeEmbeddingModel",
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[embedding_model_arn],
            )
        )
        # Access only this vector store's bucket and index.
        self.knowledge_base_role.add_to_policy(
            iam.PolicyStatement(
                sid="AccessVectorStore",
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3vectors:GetVectors",
                    "s3vectors:PutVectors",
                    "s3vectors:DeleteVectors",
                    "s3vectors:QueryVectors",
                    "s3vectors:GetIndex",
                    "s3vectors:ListVectors",
                ],
                resources=[
                    self.vector_store.vector_bucket_arn,
                    self.vector_store.index_arn,
                ],
            )
        )

        # --- Bedrock Knowledge Base backed by S3 Vectors ---------------------
        self.knowledge_base = bedrock.CfnKnowledgeBase(
            self,
            "KnowledgeBase",
            name=f"{config.app_name}-kb",
            role_arn=self.knowledge_base_role.role_arn,
            description="Namma Ooru grounded Tamil Nadu destination Knowledge Base.",
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=(
                    bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                        embedding_model_arn=embedding_model_arn,
                    )
                ),
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="S3_VECTORS",
                s3_vectors_configuration=bedrock.CfnKnowledgeBase.S3VectorsConfigurationProperty(
                    vector_bucket_arn=self.vector_store.vector_bucket_arn,
                    index_arn=self.vector_store.index_arn,
                ),
            ),
        )
        # KB creation requires the role and vector index to exist first.
        self.knowledge_base.node.add_dependency(self.knowledge_base_role)
        self.knowledge_base.node.add_dependency(self.vector_store)

        # --- S3 data source feeding the Knowledge Base -----------------------
        self.data_source = bedrock.CfnDataSource(
            self,
            "SourceDocumentsDataSource",
            knowledge_base_id=self.knowledge_base.attr_knowledge_base_id,
            name=f"{config.app_name}-source-documents",
            description="Ingests Namma Ooru KB source documents from the source-data bucket.",
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=source_bucket_arn,
                ),
            ),
        )

        # --- Useful CloudFormation outputs -----------------------------------
        CfnOutput(
            self,
            "KnowledgeBaseId",
            value=self.knowledge_base.attr_knowledge_base_id,
            description="Bedrock Knowledge Base id (BEDROCK_KB_ID).",
            export_name=f"{config.app_name}-knowledge-base-id",
        )
        CfnOutput(
            self,
            "DataSourceId",
            value=self.data_source.attr_data_source_id,
            description="Bedrock S3 data source id.",
            export_name=f"{config.app_name}-data-source-id",
        )
        CfnOutput(
            self,
            "VectorBucketArn",
            value=self.vector_store.vector_bucket_arn,
            description="S3 Vectors bucket ARN.",
            export_name=f"{config.app_name}-vector-bucket-arn",
        )
        CfnOutput(
            self,
            "VectorIndexArn",
            value=self.vector_store.index_arn,
            description="S3 Vectors index ARN.",
            export_name=f"{config.app_name}-vector-index-arn",
        )
        CfnOutput(
            self,
            "KnowledgeBaseRoleArn",
            value=self.knowledge_base_role.role_arn,
            description="Least-privilege Knowledge Base service role ARN.",
            export_name=f"{config.app_name}-knowledge-base-role-arn",
        )
