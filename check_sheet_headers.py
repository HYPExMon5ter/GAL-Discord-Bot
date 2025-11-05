#!/usr/bin/env python3

import asyncio
from integrations.sheets import get_sheet_for_guild, retry_until_successful
from config import get_sheet_settings

async def main():
    print("Checking sheet headers...")
    
    try:
        mode = "normal"
        cfg = get_sheet_settings(mode)
        sheet = await get_sheet_for_guild("1385739351505240074", "GAL Database")
        hline = cfg.get("header_line_num", 2)
        
        # Get first few rows to see the structure
        print(f"\nHeader row {hline}:")
        for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
            try:
                cell = await retry_until_successful(sheet.acell, f"{col}{hline}")
                print(f"  Column {col}: '{cell.value}'")
            except Exception as e:
                print(f"  Column {col}: ERROR - {e}")
        
        print(f"\nFirst data row {hline + 1}:")
        for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
            try:
                cell = await retry_until_successful(sheet.acell, f"{col}{hline + 1}")
                print(f"  Column {col}: '{cell.value}'")
            except Exception as e:
                print(f"  Column {col}: ERROR - {e}")
        
        print(f"\nSecond data row {hline + 2}:")
        for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
            try:
                cell = await retry_until_successful(sheet.acell, f"{col}{hline + 2}")
                print(f"  Column {col}: '{cell.value}'")
            except Exception as e:
                print(f"  Column {col}: ERROR - {e}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
