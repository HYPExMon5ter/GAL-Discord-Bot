"""
Create placement tracking tables in the database.

This script creates the new tables needed for screenshot-based placement extraction:
- processing_batches
- placement_submissions
- round_placements
- player_aliases
- ocr_corrections
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from api.models import Base, ProcessingBatch, PlacementSubmission, RoundPlacement, PlayerAlias, OCRCorrection

# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dashboard/dashboard.db")

def create_tables():
    """Create all placement-related tables."""
    print(f"Connecting to database: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL, echo=True)
    
    print("\nCreating placement tables...")
    
    # Create only the new tables (existing tables won't be affected)
    Base.metadata.create_all(
        engine,
        tables=[
            ProcessingBatch.__table__,
            PlacementSubmission.__table__,
            RoundPlacement.__table__,
            PlayerAlias.__table__,
            OCRCorrection.__table__,
        ],
        checkfirst=True  # Only create if they don't exist
    )
    
    print("\n✅ Placement tables created successfully!")
    print("\nCreated tables:")
    print("  - processing_batches")
    print("  - placement_submissions")
    print("  - round_placements")
    print("  - player_aliases")
    print("  - ocr_corrections")


if __name__ == "__main__":
    try:
        create_tables()
    except Exception as e:
        print(f"\n❌ Error creating tables: {e}")
        sys.exit(1)
