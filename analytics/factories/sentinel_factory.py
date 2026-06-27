"""
Sentinel Factory

Creates all domain models.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from analytics.domain.campaign import Campaign
from analytics.domain.campaign import CampaignType
from analytics.domain.dataset import Dataset
from analytics.domain.dataset import DatasetSource
from analytics.domain.dataset import DatasetType
from analytics.domain.entity import Entity
from analytics.domain.entity import EntityType
from analytics.domain.milestone import Milestone
from analytics.domain.snapshot import Snapshot


class SentinelFactory:
    """
    Factory for all Sentinel domain models.
    """

    @staticmethod
    def create_campaign(
        name: str,
        campaign_type: CampaignType,
        description: str = "",
    ) -> Campaign:

        return Campaign(
            id=str(uuid4()),
            name=name,
            campaign_type=campaign_type,
            description=description,
        )

    @staticmethod
    def create_milestone(
        campaign_id: str,
        name: str,
        sequence: int,
    ) -> Milestone:

        return Milestone(
            id=str(uuid4()),
            campaign_id=campaign_id,
            name=name,
            sequence=sequence,
        )

    @staticmethod
    def create_dataset(
        campaign_id: str,
        milestone_id: str,
        server: int,
        dataset_type: DatasetType,
        source: DatasetSource,
    ) -> Dataset:

        return Dataset(
            id=str(uuid4()),
            campaign_id=campaign_id,
            milestone_id=milestone_id,
            server=server,
            dataset_type=dataset_type,
            source=source,
            uploaded_at=datetime.utcnow(),
        )

    @staticmethod
    def create_snapshot(
        campaign_id: str,
        milestone_id: str,
        server: int,
    ) -> Snapshot:

        return Snapshot(
            id=str(uuid4()),
            campaign_id=campaign_id,
            milestone_id=milestone_id,
            server=server,
            created_at=datetime.utcnow(),
        )

    @staticmethod
    def create_entity(
        entity_type: EntityType,
        name: str,
        server: int | None = None,
    ) -> Entity:

        return Entity(
            id=str(uuid4()),
            entity_type=entity_type,
            name=name,
            server=server,
        )