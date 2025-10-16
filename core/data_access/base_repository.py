"""
Base repository interface and common functionality.

Provides the foundation for all data repositories with consistent
CRUD operations, caching, and error handling.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union
from datetime import UTC, datetime, timedelta
import logging
import asyncio
from contextlib import asynccontextmanager

from ..models.base_model import BaseModel


def utcnow() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(UTC)

# Type variables for generic repository
T = TypeVar('T', bound=BaseModel)
ID = TypeVar('ID')


class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class NotFoundError(RepositoryError):
    """Raised when a requested entity is not found."""
    pass


class ValidationError(RepositoryError):
    """Raised when validation fails."""
    pass


class DuplicateError(RepositoryError):
    """Raised when attempting to create a duplicate entity."""
    pass


class BaseRepository(ABC, Generic[T, ID]):
    """
    Abstract base repository providing common CRUD operations.
    
    All repositories should inherit from this class and implement
    the abstract methods for their specific data source.
    """
    
    def __init__(self, cache_manager=None, connection_manager=None):
        """
        Initialize the repository.
        
        Args:
            cache_manager: Cache manager instance for caching operations
            connection_manager: Database connection manager
        """
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.cache_manager = cache_manager
        self.connection_manager = connection_manager
        self._cache_ttl = timedelta(minutes=5)  # Default TTL
        self._cache_prefix = f"{self.__class__.__name__.lower()}:"
    
    @abstractmethod
    async def create(self, entity: T, user_id: Optional[str] = None) -> T:
        """
        Create a new entity.
        
        Args:
            entity: Entity to create
            user_id: ID of user creating the entity
            
        Returns:
            Created entity with generated ID and timestamps
            
        Raises:
            ValidationError: If entity validation fails
            DuplicateError: If entity already exists
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: ID) -> T:
        """
        Get an entity by its ID.
        
        Args:
            entity_id: ID of the entity to retrieve
            
        Returns:
            Entity with the specified ID
            
        Raises:
            NotFoundError: If entity not found
        """
        pass
    
    @abstractmethod
    async def update(self, entity: T, user_id: Optional[str] = None) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: Entity to update (must have ID)
            user_id: ID of user updating the entity
            
        Returns:
            Updated entity
            
        Raises:
            NotFoundError: If entity not found
            ValidationError: If entity validation fails
        """
        pass
    
    @abstractmethod
    async def delete(self, entity_id: ID) -> bool:
        """
        Delete an entity by its ID.
        
        Args:
            entity_id: ID of the entity to delete
            
        Returns:
            True if entity was deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list(self, 
                   limit: Optional[int] = None,
                   offset: Optional[int] = None,
                   filters: Optional[Dict[str, Any]] = None,
                   sort_by: Optional[str] = None,
                   sort_desc: bool = False) -> List[T]:
        """
        List entities with optional filtering, sorting, and pagination.
        
        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            filters: Dictionary of field filters
            sort_by: Field to sort by
            sort_desc: Whether to sort in descending order
            
        Returns:
            List of entities matching the criteria
        """
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities matching optional filters.
        
        Args:
            filters: Dictionary of field filters
            
        Returns:
            Number of matching entities
        """
        pass
    
    @abstractmethod
    async def exists(self, entity_id: ID) -> bool:
        """
        Check if an entity exists.
        
        Args:
            entity_id: ID of the entity to check
            
        Returns:
            True if entity exists, False otherwise
        """
        pass
    
    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[T]:
        """
        Get an entity by a specific field value.
        
        Args:
            field_name: Name of the field to search
            field_value: Value to search for
            
        Returns:
            Entity with matching field value, or None if not found
        """
        filters = {field_name: field_value}
        results = await self.list(limit=1, filters=filters)
        return results[0] if results else None
    
    async def get_multiple_by_ids(self, entity_ids: List[ID]) -> List[T]:
        """
        Get multiple entities by their IDs.
        
        Args:
            entity_ids: List of entity IDs to retrieve
            
        Returns:
            List of entities (order not guaranteed)
        """
        # Default implementation - override for better performance
        results = []
        for entity_id in entity_ids:
            try:
                entity = await self.get_by_id(entity_id)
                results.append(entity)
            except NotFoundError:
                continue
        return results
    
    async def search(self, 
                    query: str,
                    search_fields: Optional[List[str]] = None,
                    limit: Optional[int] = None) -> List[T]:
        """
        Search entities by text query.
        
        Args:
            query: Search query
            search_fields: Fields to search in (default: all text fields)
            limit: Maximum number of results
            
        Returns:
            List of entities matching the search query
        """
        # Default implementation - override for database-specific search
        filters = {}
        if search_fields:
            # Simple implementation - override for full-text search
            for field in search_fields:
                filters[f"{field}__contains"] = query
        
        return await self.list(limit=limit, filters=filters)
    
    def _get_cache_key(self, key: str) -> str:
        """
        Generate a cache key for this repository.
        
        Args:
            key: Base key
            
        Returns:
            Namespaced cache key
        """
        return f"{self._cache_prefix}{key}"
    
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """
        Get a value from cache if cache manager is available.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self.cache_manager:
            return None
        
        cache_key = self._get_cache_key(key)
        return await self.cache_manager.get(cache_key)
    
    async def _set_cache(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """
        Set a value in cache if cache manager is available.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live (uses default if not provided)
        """
        if not self.cache_manager:
            return
        
        cache_key = self._get_cache_key(key)
        cache_ttl = ttl or self._cache_ttl
        await self.cache_manager.set(cache_key, value, cache_ttl)
    
    async def _invalidate_cache(self, key: str) -> None:
        """
        Invalidate a cache entry.
        
        Args:
            key: Cache key to invalidate
        """
        if not self.cache_manager:
            return
        
        cache_key = self._get_cache_key(key)
        await self.cache_manager.delete(cache_key)
    
    async def _invalidate_pattern(self, pattern: str) -> None:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match
        """
        if not self.cache_manager:
            return
        
        cache_pattern = self._get_cache_key(pattern)
        await self.cache_manager.delete_pattern(cache_pattern)
    
    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions.
        
        Override in subclasses for database-specific transaction handling.
        """
        # Default implementation - no transaction support
        try:
            yield
        except Exception as e:
            self.logger.error(f"Transaction failed: {e}")
            raise
    
    async def validate_entity(self, entity: T) -> None:
        """
        Validate an entity before persisting.
        
        Args:
            entity: Entity to validate
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            entity.validate()
        except ValueError as e:
            raise ValidationError(f"Entity validation failed: {str(e)}")
    
    def _sanitize_for_storage(self, entity: T) -> Dict[str, Any]:
        """
        Sanitize entity data for storage.
        
        Args:
            entity: Entity to sanitize
            
        Returns:
            Sanitized dictionary representation
        """
        return entity.to_dict()
    
    def _deserialize_from_storage(self, data: Dict[str, Any]) -> T:
        """
        Deserialize entity data from storage.
        
        Args:
            data: Dictionary data from storage
            
        Returns:
            Deserialized entity
        """
        # This should be implemented by concrete repositories
        # with their specific model type
        raise NotImplementedError("Subclasses must implement _deserialize_from_storage")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the repository's data source.
        
        Returns:
            Health check results
        """
        result = {
            "status": "healthy",
            "repository": self.__class__.__name__,
            "timestamp": utcnow().isoformat(),
            "cache_available": self.cache_manager is not None,
            "connection_available": self.connection_manager is not None
        }
        
        try:
            # Test basic operation
            await self.count()
        except Exception as e:
            result["status"] = "unhealthy"
            result["error"] = str(e)
        
        return result
