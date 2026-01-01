"""
Script to add Format 1 parser for "Standing | Player" format
"""

new_function = '''    def _parse_format_with_columns(self, raw_ocr_results: List[Dict]) -> List[Dict]:
        """
        Parse Format 1 with clear column structure (Standing | Player).

        Format:
        Standing  |  Player
        1         |  Player 1 Name
        2         |  Player 2 Name

        Args:
            raw_ocr_results: All OCR detections with coordinates

        Returns:
            List of players with placement numbers
        """
        log.info("Using Format 1 parser (with columns)")

        # Skip keywords
        skip_keywords = {'FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS',
                      'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
                      'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'STANDINGS',
                      'PLAY', 'AGAIN', 'CONTINUE', '-', 'ROUND',
                      'TACTICS', 'TEAMFIGHT', 'TFT', 'SET',
                      'TRAITS', 'HINT', 'CHAMPIONS', 'STREAK', 'LEVEL', 'XP',
                      'GOLD', 'HP', 'SHOP', 'ITEMS', 'BOARD', 'BENCH',
                      'READY', 'START', 'GAME', 'ROUND', 'STANDING',
                      'NNT', 'HINT', 'PLAY', 'IRAILS', 'GAMELD', 'PLATER'}

        # Separate placement numbers and player names
        placements = []
        names = []

        for item in raw_ocr_results:
            text = item['text'].upper()
            x_center = item['x_center']
            y_center = item['y_center']
            confidence = item['confidence']

            # Skip keywords
            if text in skip_keywords:
                continue

            # Placement numbers: single digit, X < 100
            if text.isdigit() and len(text) == 1 and 1 <= int(text) <= 8 and x_center < 100:
                placements.append({
                    'text': text,
                    'x_center': x_center,
                    'y_center': y_center,
                    'confidence': confidence,
                    'placement': int(text)
                })
                log.debug(f"Found placement number: {text} at X={x_center:.0f}, Y={y_center:.0f}")

            # Player names: X > 100, X < 600, length >= 3
            elif x_center > 100 and x_center < 600 and len(text) >= 3 and len(text) <= 30:
                # Check for letters
                if not any(c.isalpha() for c in text):
                    continue

                # Check confidence
                if confidence <= 0.3:
                    continue

                names.append({
                    'text': text,
                    'x_center': x_center,
                    'y_center': y_center,
                    'confidence': confidence
                })
                log.debug(f"Found potential name: {text} at X={x_center:.0f}, Y={y_center:.0f}")

        log.info(f"Format 1: {len(placements)} placement numbers, {len(names)} potential names")

        # Match placements to names by Y position
        players = []

        for placement in placements:
            placement_num = placement['placement']
            placement_y = placement['y_center']

            # Find closest name by Y position
            closest_name = None
            closest_distance = float('inf')

            for name in names:
                name_y = name['y_center']
                y_diff = abs(name_y - placement_y)

                # Name should be close to placement (Y diff < 20px)
                if y_diff < 20 and y_diff < closest_distance:
                    closest_name = name
                    closest_distance = y_diff

            if closest_name:
                # Check if name already used
                if name['text'] in [p['name'] for p in players]:
                    log.debug(f"Name {name['text']} already used, skipping")
                    continue

                players.append({
                    'placement': placement_num,
                    'name': closest_name['text'],
                    'points': PLACEMENT_POINTS.get(placement_num, 0)
                })
                log.info(f"Format 1: Matched placement {placement_num} with name '{closest_name['text']}' (Y diff: {closest_distance:.1f}px)")

        # Sort by placement
        players.sort(key=lambda x: x['placement'])

        # Normalize names
        players = [self._normalize_player_name(p) for p in players]

        return players'''

# Read file
with open('C:\\\\Users\\\\blake\\\\PycharmProjects\\\\New-GAL-Discord-Bot\\\\integrations\\\\standings_ocr.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Insert new function before _parse_format_with_abbreviations
insert_line = None
for i, line in enumerate(lines):
    if 'def _parse_format_with_abbreviations(self, raw_ocr_results: List[Dict]) -> List[Dict]:' in line:
        insert_line = i
        break

if insert_line:
    new_lines = lines[:insert_line] + [new_function] + lines[insert_line:]
    
    # Write back
    with open('C:\\\\Users\\\\blake\\\\PycharmProjects\\\\New-GAL-Discord-Bot\\\\integrations\\\\standings_ocr.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"Function inserted at line {insert_line + 1}!")
else:
    print("ERROR: Could not find insertion point!")
