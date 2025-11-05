#!/usr/bin/env python3

import asyncio
from integrations.sheet_detector import detect_sheet_columns

async def main():
    print("Detecting sheet columns for guild 1385739351505240074...")
    
    try:
        detections = await detect_sheet_columns('1385739351505240074', force_refresh=True)
        print(f"\nFound {len(detections)} column detections:")
        
        for col_type, detection in detections.items():
            print(f"  {col_type:12} -> Column {detection.column_letter} ('{detection.header_value}') - {detection.confidence_score:.2f} confidence")
            
        print(f"\nColumn Mapping:")
        if 'discord' in detections:
            print(f"  Discord: {detections['discord'].column_letter}")
        else:
            print(f"  Discord: NOT FOUND")
            
        if 'ign' in detections:
            print(f"  IGN: {detections['ign'].column_letter}")
        else:
            print(f"  IGN: NOT FOUND")
            
        if 'registered' in detections:
            print(f"  Registered: {detections['registered'].column_letter}")
        else:
            print(f"  Registered: NOT FOUND")
            
        if 'checkin' in detections:
            print(f"  Check-in: {detections['checkin'].column_letter}")
        else:
            print(f"  Check-in: NOT FOUND")
            
        if 'pronouns' in detections:
            print(f"  Pronouns: {detections['pronouns'].column_letter}")
        else:
            print(f"  Pronouns: NOT FOUND")
            
        if 'alt_ign' in detections:
            print(f"  Alt IGNs: {detections['alt_ign'].column_letter}")
        else:
            print(f"  Alt IGNs: NOT FOUND")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
