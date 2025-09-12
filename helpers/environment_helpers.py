# helpers/environment_helpers.py

import os
import logging
from typing import Optional, Tuple


class EnvironmentHelper:
    """Helper class for managing environment-specific logic."""
    
    @staticmethod
    def get_environment_info() -> Tuple[bool, Optional[str]]:
        """
        Get current environment information.
        
        Returns:
            Tuple of (is_production, dev_guild_id)
        """
        is_production = os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"
        dev_guild_id = os.getenv("DEV_GUILD_ID")
        return is_production, dev_guild_id
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production environment."""
        return os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"
    
    @staticmethod
    def get_dev_guild_id() -> Optional[str]:
        """Get the development guild ID."""
        return os.getenv("DEV_GUILD_ID")
    
    @staticmethod
    def should_process_guild(guild_id: int) -> bool:
        """
        Check if a guild should be processed in the current environment.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            True if guild should be processed, False otherwise
        """
        is_production, dev_guild_id = EnvironmentHelper.get_environment_info()
        
        if is_production:
            # In production, process all guilds
            return True
        else:
            # In development, only process the dev guild
            if dev_guild_id:
                return str(guild_id) == dev_guild_id
            else:
                logging.warning("Development mode but no DEV_GUILD_ID set")
                return False
    
    @staticmethod
    def get_environment_type() -> str:
        """Get human-readable environment type."""
        return "Production" if EnvironmentHelper.is_production() else "Development"
    
    @staticmethod
    def log_environment_info():
        """Log current environment configuration."""
        is_production, dev_guild_id = EnvironmentHelper.get_environment_info()
        env_type = EnvironmentHelper.get_environment_type()
        
        logging.info(f"Environment: {env_type}")
        if not is_production and dev_guild_id:
            logging.info(f"Development Guild ID: {dev_guild_id}")
        elif not is_production:
            logging.warning("Development mode but no DEV_GUILD_ID set")
    
    @staticmethod
    def validate_environment() -> bool:
        """
        Validate environment configuration.
        
        Returns:
            True if environment is properly configured
        """
        is_production, dev_guild_id = EnvironmentHelper.get_environment_info()
        
        if not is_production:
            if not dev_guild_id:
                logging.error("Development mode requires DEV_GUILD_ID environment variable")
                return False
            
            try:
                int(dev_guild_id)
            except ValueError:
                logging.error(f"Invalid DEV_GUILD_ID: {dev_guild_id} (must be numeric)")
                return False
        
        return True