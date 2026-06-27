"""
Sentinel Factory

Creates all domain models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from analytics.domain.campaign import Campaign, CampaignType
from analytics.domain.dataset import Dataset, DatasetSource, DatasetType
from analytics.domain.entity import Entity, EntityType
from analytics.domain.milestone import Milestone
from analytics.domain.snapshot import Snapshot


class SentinelFactory:
    """
    Factory for all Sentinel domain models.
    """

    @staticmethod
    def _id() -> str:
        return str(uuid4())

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def create_campaign(
        name: str,
        campaign_type: CampaignType,
        description: str = "",
    ) -> Campaign:
        return Campaign(
            id=SentinelFactory._id(),
            name=name,
            campaign_type=campaign_type,
            description=description,
        )

    @staticmethod
    def create_milestone(
        campaign_id: str,
        name: str,
        sequence: int,
        description: str = "",
    ) -> Milestone:
        return Milestone(
            id=SentinelFactory._id(),
            campaign_id=campaign_id,
            name=name,
            sequence=sequence,
            description=description,
        )

    @staticmethod
    def create_snapshot(
        campaign_id: str,
        milestone_id: str,
        server: int,
        name: str = "",
    ) -> Snapshot:
        return Snapshot(
            id=SentinelFactory._id(),
            campaign_id=campaign_id,
            milestone_id=milestone_id,
            server=server,
            name=name,
            created_at=SentinelFactory._now(),
        )

    @staticmethod
    def create_dataset(
        snapshot_id: str,
        server: int,
        dataset_type: DatasetType,
        source: DatasetSource,
    ) -> Dataset:
        return Dataset(
            id=SentinelFactory._id(),
            snapshot_id=snapshot_id,
            server=server,
            dataset_type=dataset_type,
            source=source,
            uploaded_at=SentinelFactory._now(),
        )

    @staticmethod
    def create_entity(
        entity_type: EntityType,
        name: str,
        server: int | None = None,
    ) -> Entity:
        return Entity(
            id=SentinelFactory._id(),
            entity_type=entity_type,
            name=name,
            server=server,
        )