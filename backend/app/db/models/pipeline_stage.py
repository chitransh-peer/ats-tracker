import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import TerminalOutcome
from app.db.base import Base, TimestampMixin, uuid_pk


class StageTemplate(TimestampMixin, Base):
    __tablename__ = "stage_templates"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    stages: Mapped[list["StageTemplateStage"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="StageTemplateStage.sort_order"
    )


class StageTemplateStage(Base):
    __tablename__ = "stage_template_stages"
    __table_args__ = (UniqueConstraint("template_id", "sort_order", name="uq_stage_template_stage_order"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stage_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    terminal_outcome: Mapped[str] = mapped_column(String(20), nullable=False, default=TerminalOutcome.NONE.value)

    template: Mapped["StageTemplate"] = relationship(back_populates="stages")
