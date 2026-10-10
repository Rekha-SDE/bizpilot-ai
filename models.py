from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text

from database import Base


class BusinessIdea(Base):
    """Database model for storing business ideas locally."""

    __tablename__ = "business_ideas"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SavedBusinessPlan(Base):
    """Database model for persistently storing generated business plans."""

    __tablename__ = "saved_business_plans"

    id = Column(Integer, primary_key=True, index=True)
    idea = Column(String(1000), nullable=False)
    location = Column(String(200), nullable=False)
    budget = Column(Float, nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    target_customers = Column(JSON, nullable=False)
    startup_costs = Column(JSON, nullable=False)
    operating_costs = Column(JSON, nullable=False)
    resources = Column(JSON, nullable=False)
    risks = Column(JSON, nullable=False)
    launch_steps = Column(JSON, nullable=False)
    estimates_and_assumptions = Column(JSON, nullable=False)
    disclaimer = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

