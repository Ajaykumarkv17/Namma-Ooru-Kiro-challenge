"""Reusable S3 Vectors store construct (vector bucket + index).

Wraps the L1 ``aws_s3vectors`` resources so the AI stack can declare a vector
store in one line. The index is configured with the metadata schema required by
the RAG flow: retrieval metadata (district, city, category, region, heritage,
UNESCO, travel type) stays filterable while ``AMAZON_BEDROCK_TEXT`` is declared
non-filterable so it does not consume the filterable-metadata allowance
(design "RAG flow").
"""

from __future__ import annotations

from aws_cdk import aws_s3vectors as s3vectors
from constructs import Construct

# Reserved key that Bedrock Knowledge Bases write the chunk text into. It must
# be excluded from filtering to stay within the filterable-metadata size limit.
BEDROCK_TEXT_METADATA_KEY = "AMAZON_BEDROCK_TEXT"

# Retrieval metadata that must remain filterable for grounded, metadata-filtered
# retrieval (design "RAG flow").
FILTERABLE_METADATA_KEYS: tuple[str, ...] = (
    "district",
    "city",
    "category",
    "region",
    "heritage",
    "unesco",
    "travel_type",
)


class VectorStore(Construct):
    """An S3 Vectors bucket with a single cosine index for KB embeddings."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vector_bucket_name: str,
        index_name: str,
        dimension: int,
        distance_metric: str = "cosine",
        data_type: str = "float32",
    ) -> None:
        super().__init__(scope, construct_id)

        self.vector_bucket = s3vectors.CfnVectorBucket(
            self,
            "VectorBucket",
            vector_bucket_name=vector_bucket_name,
        )

        self.index = s3vectors.CfnIndex(
            self,
            "Index",
            vector_bucket_name=vector_bucket_name,
            index_name=index_name,
            data_type=data_type,
            dimension=dimension,
            distance_metric=distance_metric,
            # Only AMAZON_BEDROCK_TEXT is non-filterable; every retrieval metadata
            # key stays filterable for metadata-scoped retrieval.
            metadata_configuration=s3vectors.CfnIndex.MetadataConfigurationProperty(
                non_filterable_metadata_keys=[BEDROCK_TEXT_METADATA_KEY],
            ),
        )
        # The index must not be created before its bucket exists.
        self.index.add_resource_dependency(self.vector_bucket)

    @property
    def vector_bucket_arn(self) -> str:
        """ARN of the S3 Vectors bucket."""
        return self.vector_bucket.attr_vector_bucket_arn

    @property
    def index_arn(self) -> str:
        """ARN of the S3 Vectors index."""
        return self.index.attr_index_arn
