"""
SQLAlchemy models for graphics management
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.mutable import MutableDict, MutableList

Base = declarative_base()


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime compatible with SQLAlchemy defaults."""
    return datetime.now(UTC)


class Graphic(Base):
    """Model for graphics/canvas data"""

    __tablename__ = "graphics"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    event_name = Column(String(255), nullable=True, index=True)
    data_json = Column(Text, default="{}")
    created_by = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    archived = Column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    locks = relationship("CanvasLock", back_populates="graphic", cascade="all, delete-orphan")
    archives = relationship("Archive", back_populates="graphic", cascade="all, delete-orphan")

    def __repr__(self):
        return (
            f"<Graphic(id={self.id}, title='{self.title}', event_name='{self.event_name}', "
            f"created_by='{self.created_by}')>"
        )


class CanvasLock(Base):
    """Model for canvas editing locks - simplified for single shared login"""

    __tablename__ = "canvas_locks"

    id = Column(Integer, primary_key=True, index=True)
    graphic_id = Column(Integer, ForeignKey("graphics.id"), nullable=False, unique=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)  # Track which browser session owns the lock
    locked = Column(Boolean, default=True, nullable=False)
    locked_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    graphic = relationship("Graphic", back_populates="locks")

    # Indexes for performance
    __table_args__ = (
        Index("idx_expires_active", "expires_at", "locked"),
    )

    def __repr__(self):
        return (
            f"<CanvasLock(id={self.id}, graphic_id={self.graphic_id}, "
            f"session_id='{self.session_id}', locked={self.locked})>"
        )


class Archive(Base):
    """Model for archive tracking"""

    __tablename__ = "archives"

    id = Column(Integer, primary_key=True, index=True)
    graphic_id = Column(Integer, ForeignKey("graphics.id"), nullable=False, index=True)
    archived_by = Column(String(255), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    archived_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    graphic = relationship("Graphic", back_populates="archives")

    def __repr__(self):
        return f"<Archive(id={self.id}, graphic_id={self.graphic_id}, archived_by='{self.archived_by}')>"


class AuthLog(Base):
    """Model for authentication logs"""

    __tablename__ = "auth_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False, index=True)  # Support IPv6
    success = Column(Boolean, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    user_agent = Column(Text, nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index("idx_user_timestamp", "username", "timestamp"),
        Index("idx_ip_success", "ip_address", "success"),
    )

    def __repr__(self):
        return f"<AuthLog(id={self.id}, user='{self.username}', success={self.success})>"


class ActiveSession(Base):
    """Model for active user sessions"""

    __tablename__ = "active_sessions"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    ip_address = Column(String(45), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_activity = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index("idx_token_expiry", "session_token", "expires_at"),
        Index("idx_user_activity", "username", "last_activity"),
    )

    def __repr__(self):
        return f"<ActiveSession(id={self.id}, user='{self.username}', expires_at='{self.expires_at}')>"


class ScoreboardSnapshot(Base):
    """Represents a persisted snapshot of tournament standings."""

    __tablename__ = "scoreboard_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(String(255), nullable=True, index=True)
    tournament_name = Column(String(255), nullable=True)
    guild_id = Column(String(64), nullable=True, index=True)
    source = Column(String(64), nullable=True)
    source_timestamp = Column(DateTime(timezone=True), nullable=True, index=True)
    round_names = Column(MutableList.as_mutable(JSON), default=list, nullable=False)
    extras = Column(MutableDict.as_mutable(JSON), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    entries = relationship(
        "ScoreboardEntry",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_scoreboard_snapshot_tournament", "tournament_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ScoreboardSnapshot(id={self.id}, tournament_id={self.tournament_id}, "
            f"rounds={len(self.round_names) if self.round_names else 0})>"
        )


class ScoreboardEntry(Base):
    """Per-player standings data for a scoreboard snapshot."""

    __tablename__ = "scoreboard_entries"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(
        Integer,
        ForeignKey("scoreboard_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id = Column(String(255), nullable=True, index=True)
    player_name = Column(String(255), nullable=False, index=True)
    discord_id = Column(String(255), nullable=True, index=True)
    riot_id = Column(String(255), nullable=True)
    standing_rank = Column(Integer, nullable=True, index=True)
    total_points = Column(Integer, nullable=False, default=0)
    round_scores = Column(MutableDict.as_mutable(JSON), default=dict, nullable=False)
    extras = Column(MutableDict.as_mutable(JSON), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    snapshot = relationship("ScoreboardSnapshot", back_populates="entries")

    __table_args__ = (
        Index("idx_scoreboard_entry_player", "snapshot_id", "player_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<ScoreboardEntry(id={self.id}, snapshot_id={self.snapshot_id}, "
            f"player='{self.player_name}', total_points={self.total_points})>"
        )


class ProcessingBatch(Base):
    """Model for tracking screenshot processing batches."""

    __tablename__ = "processing_batches"

    id = Column(Integer, primary_key=True, index=True)
    guild_id = Column(String(64), nullable=False, index=True)
    tournament_id = Column(String(255), nullable=False)
    round_name = Column(String(255), nullable=True)

    batch_size = Column(Integer, nullable=False)
    completed_count = Column(Integer, default=0, nullable=False)
    validated_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)

    status = Column(String(32), nullable=False, default="processing", index=True)
    average_confidence = Column(Integer, nullable=True)  # Store as 0-100 for simplicity

    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    submissions = relationship("PlacementSubmission", back_populates="batch", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_batch_tournament_round", "tournament_id", "round_name"),
        Index("idx_batch_guild", "guild_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProcessingBatch(id={self.id}, tournament_id={self.tournament_id}, "
            f"round={self.round_name}, status={self.status})>"
        )


class PlacementSubmission(Base):
    """Model for raw screenshot OCR submissions."""

    __tablename__ = "placement_submissions"

    id = Column(Integer, primary_key=True, index=True)
    guild_id = Column(String(64), nullable=False, index=True)
    tournament_id = Column(String(255), nullable=False, index=True)
    round_name = Column(String(255), nullable=False, index=True)
    lobby_number = Column(Integer, nullable=False)

    # Source tracking
    discord_message_id = Column(String(64), nullable=False, unique=True, index=True)
    discord_channel_id = Column(String(64), nullable=False)
    discord_author_id = Column(String(64), nullable=True)
    image_url = Column(Text, nullable=False)
    image_hash = Column(String(64), nullable=True)

    # Processing metadata (stored as 0-100 for simplicity)
    classification_score = Column(Integer, nullable=True)
    ocr_consensus_confidence = Column(Integer, nullable=True)
    ocr_character_confidence = Column(Integer, nullable=True)
    player_match_confidence = Column(Integer, nullable=True)
    structural_validity_score = Column(Integer, nullable=True)
    overall_confidence = Column(Integer, nullable=False)

    # OCR results
    extracted_data_tesseract = Column(MutableDict.as_mutable(JSON), nullable=True)
    extracted_data_easyocr = Column(MutableDict.as_mutable(JSON), nullable=True)
    extracted_data_consensus = Column(MutableDict.as_mutable(JSON), nullable=False)

    # Processing status
    status = Column(String(32), nullable=False, default="pending", index=True)
    validation_method = Column(String(32), nullable=True)
    validated_by_discord_id = Column(String(64), nullable=True)
    validation_notes = Column(Text, nullable=True)
    edited = Column(Boolean, default=False, nullable=False)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Batch tracking
    batch_id = Column(Integer, ForeignKey("processing_batches.id"), nullable=True, index=True)

    # Timestamps
    processed_at = Column(DateTime(timezone=True), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    batch = relationship("ProcessingBatch", back_populates="submissions")
    placements = relationship("RoundPlacement", back_populates="submission", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_submission_tournament_round", "tournament_id", "round_name"),
        Index("idx_submission_guild_tournament", "guild_id", "tournament_id"),
        Index("idx_submission_confidence", "overall_confidence"),
    )

    def __repr__(self) -> str:
        return (
            f"<PlacementSubmission(id={self.id}, tournament={self.tournament_id}, "
            f"round={self.round_name}, lobby={self.lobby_number}, status={self.status})>"
        )


class RoundPlacement(Base):
    """Model for validated per-player placement records."""

    __tablename__ = "round_placements"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(
        Integer,
        ForeignKey("placement_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Player identification
    player_id = Column(String(255), nullable=False, index=True)
    player_name = Column(String(255), nullable=False)
    discord_id = Column(String(64), nullable=True, index=True)
    riot_id = Column(String(255), nullable=True)

    # Tournament context
    tournament_id = Column(String(255), nullable=False, index=True)
    round_name = Column(String(255), nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    lobby_number = Column(Integer, nullable=False)

    # Placement data
    placement = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False)

    # Tie-breaker support
    is_tie = Column(Boolean, default=False, nullable=False)
    tie_breaker_rank = Column(Integer, nullable=True)

    # Confidence tracking (stored as 0-100)
    extraction_confidence = Column(Integer, nullable=True)
    player_match_confidence = Column(Integer, nullable=True)
    match_method = Column(String(32), nullable=True)

    # Validation
    validated = Column(Boolean, default=False, nullable=False, index=True)
    manually_corrected = Column(Boolean, default=False, nullable=False)
    validated_by_discord_id = Column(String(64), nullable=True)
    correction_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    submission = relationship("PlacementSubmission", back_populates="placements")

    __table_args__ = (
        Index("idx_placement_player_tournament", "player_id", "tournament_id"),
        Index("idx_placement_tournament_round", "tournament_id", "round_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<RoundPlacement(id={self.id}, player='{self.player_name}', "
            f"placement={self.placement}, points={self.points})>"
        )


class PlayerAlias(Base):
    """Model for player alias mappings to improve OCR matching."""

    __tablename__ = "player_aliases"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(String(255), nullable=False, index=True)
    discord_id = Column(String(64), nullable=False, index=True)
    alias_name = Column(String(255), nullable=False, index=True)
    alias_type = Column(String(32), nullable=False)

    priority = Column(Integer, default=1, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by = Column(String(64), nullable=True)

    __table_args__ = (
        Index("idx_alias_player_name", "player_id", "alias_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<PlayerAlias(id={self.id}, player_id='{self.player_id}', "
            f"alias='{self.alias_name}', type={self.alias_type})>"
        )


class OCRCorrection(Base):
    """Model for tracking OCR corrections for future learning."""

    __tablename__ = "ocr_corrections"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("placement_submissions.id"), nullable=True, index=True)

    original_text = Column(String(255), nullable=False, index=True)
    corrected_text = Column(String(255), nullable=False, index=True)
    correction_type = Column(String(32), nullable=False)

    corrected_by_discord_id = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<OCRCorrection(id={self.id}, original='{self.original_text}', "
            f"corrected='{self.corrected_text}')>"
        )
