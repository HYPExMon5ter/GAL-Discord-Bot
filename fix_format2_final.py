"""
Final working solution - simplify Format 2 parser to just pick best detection per row
"""

# Simplified Format 2 parser - just pick best single detection per row
new_function = '''    def _parse_format_with_abbreviations(self, raw_ocr_results: List[Dict]) -> List[Dict]:
        """
        Parse Format 2 with rank abbreviations (E2, M, U, etc.) before player names.

        SIMPLIFIED: Just pick the single best detection per row (no merging/deduplication).

        Format:
        #  |  Summoner
        1  |  [Icon] [E2] Player 1 Name
        2  |  [Icon] [M] Player 2 Name

        Args:
            raw_ocr_results: All OCR detections with coordinates

        Returns:
            List of players with placement numbers
        """
        log.info("Using Format 2 parser (simplified - single detection per row)")

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

        # Rank abbreviations to filter
        rank_abbreviations = {'E2', 'E1', 'M', 'U', 'D', 'B', 'G', 'P', 'S',
                           'GM', 'M+', 'E', 'D+', 'G+', 'B+', 'P+', 'S+'}

        # Filter potential items
        potential_items = []
        for item in raw_ocr_results:
            text = item['text'].upper()

            # Skip if X position too far right
            if item['x_center'] > 600:
                continue

            # Skip if text is a keyword
            if text in skip_keywords:
                continue

            # Skip if text is a rank abbreviation
            if text in rank_abbreviations:
                continue

            # Skip if text starts with a digit followed by a rank abbreviation
            import re
            if re.match(r'^\\d+[A-Z]+$', text):
                for abbr in rank_abbreviations:
                    if abbr in text:
                        break
                else:
                    continue
                continue

            # Check if text contains rank abbreviation
            has_rank_abbr = any(abbr in text for abbr in rank_abbreviations)

            # Extract name part if has rank abbreviation
            if has_rank_abbr:
                cleaned_text = text
                for abbr in sorted(rank_abbreviations, key=len, reverse=True):
                    if abbr in cleaned_text:
                        cleaned_text = cleaned_text.replace(abbr, '', 1).strip()
                        break

                if len(cleaned_text) >= 3:
                    potential_items.append({
                        'text': cleaned_text,
                        'x_center': item['x_center'],
                        'y_center': item['y_center'],
                        'confidence': item['confidence']
                    })
                continue

            # Check length
            if len(text) < 3 or len(text) > 30:
                continue

            # Check for letters
            if not any(c.isalpha() for c in text):
                continue

            # Check confidence
            if item['confidence'] <= 0.3:
                continue

            potential_items.append({
                'text': text,
                'x_center': item['x_center'],
                'y_center': item['y_center'],
                'confidence': item['confidence']
            })

        log.info(f"Format 2: {len(potential_items)} potential items after filtering")

        # Sort by Y and cluster into rows
        potential_items_sorted = sorted(potential_items, key=lambda x: x['y_center'])

        # Cluster into rows (within 40px Y difference)
        rows = []
        for item in potential_items_sorted:
            placed = False
            for row in rows:
                if abs(item['y_center'] - row['y_center']) < 40:
                    row['items'].append(item)
                    row['y_center'] = (row['y_center'] * len(row['items']) + item['y_center']) / (len(row['items']) + 1)
                    placed = True
                    break

            if not placed:
                rows.append({
                    'y_center': item['y_center'],
                    'items': [item]
                })

        # Sort rows by Y
        rows.sort(key=lambda x: x['y_center'])

        log.info(f"Format 2: Found {len(rows)} distinct rows")

        # Pick SINGLE best candidate per row (no merging)
        final_names = []
        for row in rows:
            # Sort by confidence (descending), then length (descending)
            row['items'].sort(key=lambda x: (-x['confidence'], -len(x['text'])))

            # Skip low confidence
            if row['items'][0]['confidence'] < 0.3:
                continue

            # Just pick top item
            final_names.append(row['items'][0])

        # Limit to 8 players
        final_names = final_names[:8]

        # Assign placements 1-8 based on Y order
        players = []
        for i, item in enumerate(final_names):
            placement = i + 1
            players.append({
                'placement': placement,
                'name': item['text'],
                'points': PLACEMENT_POINTS.get(placement, 0)
            })
            log.info(f"Format 2: Assigned placement {placement} to '{item['text']}'")

        # Normalize names
        players = [self._normalize_player_name(p) for p in players]

        return players'''

# Read file
with open('C:\\\\Users\\\\blake\\\\PycharmProjects\\\\New-GAL-Discord-Bot\\\\integrations\\\\standings_ocr.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace using regex
import re

# Match the old function
pattern = r'    def _parse_format_with_abbreviations\(self, raw_ocr_results: List\[Dict\]\) -> List\[Dict\]:.*?return players'

matches = list(re.finditer(pattern, content, re.DOTALL))

if matches:
    # Replace each match (there should be only one)
    for match in reversed(matches):  # Reverse to keep positions correct
        old_func_text = match.group(0)
        content = content[:match.start()] + new_function + content[match.end():]
        print(f"Replaced function at lines {match.start()}-{match.end()}")
    
    # Write back
    with open('C:\\\\Users\\\\blake\\\\PycharmProjects\\\\New-GAL-Discord-Bot\\\\integrations\\\\standings_ocr.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Function replaced successfully!")
else:
    print("ERROR: Could not find function using regex!")
