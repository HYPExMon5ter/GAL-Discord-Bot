"""Copy this function into integrations/standings_ocr.py"""

def _tft_parsing(self, lines: List[str]) -> List[Dict]:
    """
    Parse TFT screenshots where placement numbers and names are separate.
    Associates nearby placement numbers with player names.
    """
    players = []
    placement_numbers = {}  # {line_index: placement_number}
    
    # First pass: find all standalone placement numbers (1-8)
    for i, line in enumerate(lines):
        line = line.strip()
        # Check if line is JUST a number 1-8
        if line.isdigit() and 1 <= int(line) <= 8:
            # Make sure it's not part of a longer text like "15"
            if len(line) == 1:
                placement_numbers[i] = int(line)
            elif len(line) == 2 and line[1] == '0':
                # Handle "10" or similar edge cases
                pass
    
    # Second pass: associate names with nearby placement numbers
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Skip empty lines or placement-only lines
        if not line or (i in placement_numbers):
            continue
        
        # Skip non-player text
        skip_keywords = ['FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS', 
                       'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
                       'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'STANDINGS']
        
        if any(keyword in line.upper() for keyword in skip_keywords):
            continue
        
        # Try to find nearby placement number
        placement = None
        # Check previous line (placement number BEFORE name)
        if i > 0 and (i - 1) in placement_numbers:
            placement = placement_numbers[i - 1]
        # Check next line (placement number AFTER name)
        elif (i + 1) < len(lines) and (i + 1) in placement_numbers:
            placement = placement_numbers[i + 1]
        # Check 2 lines away
        elif i > 1 and (i - 2) in placement_numbers:
            placement = placement_numbers[i - 2]
        elif (i + 2) < len(lines) and (i + 2) in placement_numbers:
            placement = placement_numbers[i + 2]
        
        # If we found a placement and this looks like a name
        if placement and len(line) >= 3 and len(line) <= 20:
            # Skip if line contains only numbers or special chars
            if line.isalnum() or any(c.isalpha() for c in line):
                players.append({
                    "placement": placement,
                    "name": line,
                    "points": PLACEMENT_POINTS.get(placement, 0)
                })
                # Log the match
                import logging
                log = logging.getLogger(__name__)
                log.debug(f"TFT parser: Associated placement {placement} with name '{line}'")
    
    return players

"""
HOW TO USE:

1. Open integrations/standings_ocr.py
2. Find the _structure_data method
3. Find this line:
   if len(players) < 4:  # Should have at least 4 players
       players = self._alternative_parsing(lines)
4. REPLACE with:
   if len(players) < 4:  # Should have at least 4 players
       players = self._alternative_parsing(lines)
   
   # If still no players, try TFT-specific parsing
   if len(players) < 4:
       players = self._tft_parsing(lines)
5. Add the _tft_parsing method above _structure_data method
"""
