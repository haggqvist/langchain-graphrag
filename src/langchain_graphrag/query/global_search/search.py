from pathlib import Path

import pandas as pd

from langchain_graphrag.query.global_search.community_report import CommunityReport
from langchain_graphrag.query.global_search.community_weight_calculator import (
    CommunityWeightCalculator,
)
from langchain_graphrag.types.graphs.community import CommunityId, CommunityLevel

from .key_points_aggregator import KeyPointsAggregator
from .key_points_generator import (
    KeyPointsGenerator,
)


class GlobalQuerySearch:
    def __init__(
        self,
        artifacts_dir: Path,
        community_level: CommunityLevel,
        weight_calculator: CommunityWeightCalculator,
        key_points_generator: KeyPointsGenerator,
        key_points_aggregator: KeyPointsAggregator,
    ):
        self._artifacts_dir = artifacts_dir
        self._community_level = community_level
        self._weight_calculator = weight_calculator
        self._key_points_generator = key_points_generator
        self._key_points_aggregator = key_points_aggregator

    def _filter_communities(self) -> list[CommunityReport]:
        df_entities = pd.read_parquet(self._artifacts_dir / "entities.parquet")
        df_reports = pd.read_parquet(
            self._artifacts_dir / "communities_reports.parquet"
        )

        reports_weight: dict[CommunityId, float] = self._weight_calculator(
            df_entities, df_reports
        )

        df_reports_filtered = df_reports[df_reports["level"] <= self._community_level]

        reports = []
        for _, row in df_reports_filtered.iterrows():
            reports.append(
                CommunityReport(
                    id=row["community_id"],
                    weight=reports_weight[row["community_id"]],
                    title=row["title"],
                    summary=row["summary"],
                    rank=row["rating"],
                    content=row["content"],
                )
            )

        return reports

    def invoke(self, query: str) -> str:
        reports = self._filter_communities()

        # TODO: parallelize this
        key_points = []
        for r in reports:
            key_points.append(  # noqa: PERF401
                self._key_points_generator.invoke(query=query, reports=[r])
            )

        return self._key_points_aggregator.invoke(query=query, key_points=key_points)
