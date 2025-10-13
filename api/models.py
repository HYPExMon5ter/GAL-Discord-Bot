"""
SQLAlchemy models for graphics management
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Graphic(Base):
    """Model for graphics/canvas data"""
    __tablename__ = "graphics"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    event_name = Column(String(255), nullable=True, index=True)
    data_json = Column(Text, default="{}")
    created_by = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    archived = Column(Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    locks = relationship("CanvasLock", back_populates="graphic", cascade="all, delete-orphan")
    archives = relationship("Archive", back_populates="graphic", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Graphic(id={self.id}, title='{self.title}', event_name='{self.event_name}', created_by='{self.created_by}')>"


class CanvasLock(Base):
    """Model for canvas editing locks"""
    __tablename__ = "canvas_locks"
    
    id = Column(Integer, primary_key=True, index=True)
    graphic_id = Column(Integer, ForeignKey("graphics.id"), nullable=False, index=True)
    user_name = Column(String(255), nullable=False, index=True)
    locked = Column(Boolean, default=True, nullable=False)
    locked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Relationships
    graphic = relationship("Graphic", back_populates="locks")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_graphic_user_lock', 'graphic_id', 'user_name', 'locked'),
        Index('idx_expires_active', 'expires_at', 'locked'),
    )
    
    def __repr__(self):
        return f"<CanvasLock(id={self.id}, graphic_id={self.graphic_id}, user='{self.user_name}', locked={self.locked})>"


class Archive(Base):
    """Model for archive tracking"""
    __tablename__ = "archives"
    
    id = Column(Integer, primary_key=True, index=True)
    graphic_id = Column(Integer, ForeignKey("graphics.id"), nullable=False, index=True)
    archived_by = Column(String(255), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
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
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user_agent = Column(Text, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_timestamp', 'username', 'timestamp'),
        Index('idx_ip_success', 'ip_address', 'success'),
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_token_expiry', 'session_token', 'expires_at'),
        Index('idx_user_activity', 'username', 'last_activity'),
    )
    
    def __repr__(self):
        return f"<ActiveSession(id={self.id}, user='{self.username}', expires_at='{self.expires_at}')>"
