"""
Script to update _parse_format_with_abbreviations function with simplified merging logic
"""

old_function = '''    def _parse_format_with_abbreviations(self, raw_ocr_results: List[Dict]) -> List[Dict]:
        """
        Parse Format 2 with rank abbreviations (E2, M, U, etc.) before player names.

        Format:
        #  |  Summoner
        1  |  [Icon] [E2] Player 1 Name
        2  |  [Icon] [M] Player 2 Name

        Args:
            raw_ocr_results: All OCR detections with coordinates

        Returns:
            List of players with placement numbers
        """
        log.info("Using Format 2 parser (with rank abbreviations)")

        # Skip keywords (including UI elements)
        skip_keywords = {'FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS',
                      'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
                      'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'STANDINGS',
                      'PLAY', 'AGAIN', 'CONTINUE', '-', 'ROUND',
                      'TACTICS', 'TEAMFIGHT', 'TFT', 'SET',
                      'TRAITS', 'HINT', 'CHAMPIONS', 'STREAK', 'LEVEL', 'XP',
                      'GOLD', 'HP', 'SHOP', 'ITEMS', 'BOARD', 'BENCH',
                      'READY', 'START', 'GAME', 'ROUND', 'STANDING',
                      'NNT', 'HINT', 'PLAY'}

        # Rank abbreviations to filter (these appear before player names)
        rank_abbreviations = {'E2', 'E1', 'M', 'U', 'D', 'B', 'G', 'P', 'S',
                           'GM', 'M+', 'E', 'D+', 'G+', 'B+', 'P+', 'S+'}

        # Filter potential items (left side, X < 600)
        potential_items = []
        for item in raw_ocr_results:
            text = item['text'].upper()

            # Skip if X position too far right
            if item['x_center'] > 600:
                continue

            # Skip if text is a keyword
            if any(keyword in text for keyword in skip_keywords):
                continue

            # Skip if text is a rank abbreviation (these are NOT player names)
            if text in rank_abbreviations:
                log.debug(f"Filtered rank abbreviation: {text}")
                continue

            # Skip if text starts with a digit followed by a rank abbreviation (e.g., "1E2")
            import re
            if re.match(r'^\\d+[A-Z]+$', text):
                # Check if it's a rank pattern
                for abbr in rank_abbreviations:
                    if abbr in text:
                        log.debug(f"Filtered rank pattern: {text}")
                        break
                else:
                    continue  # No rank abbreviation found, might be a name
                continue  # Skip this item

            # Check if text contains rank abbreviation (e.g., "E2 Ffoxface")
            has_rank_abbr = any(abbr in text for abbr in rank_abbreviations)

            # If has rank abbreviation, try to extract name part
            if has_rank_abbr:
                # Remove rank abbreviations from text
                cleaned_text = text
                for abbr in sorted(rank_abbreviations, key=len, reverse=True):  # Longest first
                    if abbr in cleaned_text:
                        cleaned_text = cleaned_text.replace(abbr, '', 1).strip()
                        break

                # Validate extracted name
                if len(cleaned_text) >= 3:
                    potential_items.append({
                        'text': cleaned_text,
                        'x_center': item['x_center'],
                        'y_center': item['y_center'],
                        'confidence': item['confidence']
                    })
                continue

            # Check length and characters
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
                    # Update row Y to average
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

        # HORIZONTAL MERGING: Merge text items in same row that are close together
        # This handles cases where "Astrid" is detected as "NOAL" and "ASTRI"
        for row in rows:
            # Sort items by X position (left to right)
            row['items'].sort(key=lambda x: x['x_center'])

            # Merge items that are close together horizontally (X gap < 20px)
            merged_items = []
            i = 0
            while i < len(row['items']):
                current_item = row['items'][i]
                merged_text = current_item['text']
                merged_conf = current_item['confidence']
                merged_x = current_item['x_center']

                # Look ahead for items to merge
                j = i + 1
                while j < len(row['items']):
                    next_item = row['items'][j]
                    x_gap = next_item['x_center'] - merged_x

                    # If X gap is small, merge text
                    if x_gap < 20:
                        merged_text += ' ' + next_item['text']
                        merged_conf = max(merged_conf, next_item['confidence'])
                        merged_x = (merged_x + next_item['x_center']) / 2  # Average X
                        j += 1
                        i += 1  # Skip this item
                    else:
                        break  # Too far apart, stop merging

                merged_items.append({
                    'text': merged_text,
                    'x_center': merged_x,
                    'y_center': row['y_center'],
                    'confidence': merged_conf
                })
                i += 1

            row['items'] = merged_items

        # Pick best candidate from each row
        best_names = []
        for row in rows:
            # Sort items by confidence (descending), then length (descending)
            row_items = sorted(row['items'], key=lambda x: (-x['confidence'], -len(x['text'])))

            # Skip low confidence rows
            if row_items[0]['confidence'] < 0.3:
                log.debug(f"Skipping row Y={row['y_center']:.0f} (low confidence)")
                continue

            # Pick top item
            best_item = row_items[0]
            best_names.append(best_item)
            log.debug(f"Format 2 row Y={row['y_center']:.0f}: Picked '{best_item['text']}' (conf={best_item['confidence']:.3f})")

        # Limit to 8 players
        best_names = best_names[:8]

        # Assign placements 1-8 based on Y order
        players = []
        for i, item in enumerate(best_names):
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

new_function = '''    def _parse_format_with_abbreviations(self, raw_ocr_results: List[Dict]) -> List[Dict]:
        """
        Parse Format 2 with rank abbreviations (E2, M, U, etc.) before player names.

        Format:
        #  |  Summoner
        1  |  [Icon] [E2] Player 1 Name
        2  |  [Icon] [M] Player 2 Name

        Args:
            raw_ocr_results: All OCR detections with coordinates

        Returns:
            List of players with placement numbers
        """
        log.info("Using Format 2 parser (with rank abbreviations)")

        # Skip keywords (including UI elements)
        skip_keywords = {'FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS',
                      'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
                      'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'STANDINGS',
                      'PLAY', 'AGAIN', 'CONTINUE', '-', 'ROUND',
                      'TACTICS', 'TEAMFIGHT', 'TFT', 'SET',
                      'TRAITS', 'HINT', 'CHAMPIONS', 'STREAK', 'LEVEL', 'XP',
                      'GOLD', 'HP', 'SHOP', 'ITEMS', 'BOARD', 'BENCH',
                      'READY', 'START', 'GAME', 'ROUND', 'STANDING',
                      'NNT', 'HINT', 'PLAY', 'IRAILS', 'GAMELD', 'PLATER'}

        # Rank abbreviations to filter (these appear before player names)
        rank_abbreviations = {'E2', 'E1', 'M', 'U', 'D', 'B', 'G', 'P', 'S',
                           'GM', 'M+', 'E', 'D+', 'G+', 'B+', 'P+', 'S+'}

        # Filter potential items (left side, X < 600)
        potential_items = []
        for item in raw_ocr_results:
            text = item['text'].upper()

            # Skip if X position too far right
            if item['x_center'] > 600:
                continue

            # Skip if text is a keyword
            if text in skip_keywords:
                continue

            # Skip if text is a rank abbreviation (these are NOT player names)
            if text in rank_abbreviations:
                log.debug(f"Filtered rank abbreviation: {text}")
                continue

            # Skip if text starts with a digit followed by a rank abbreviation (e.g., "1E2")
            import re
            if re.match(r'^\\d+[A-Z]+$', text):
                # Check if it's a rank pattern
                for abbr in rank_abbreviations:
                    if abbr in text:
                        log.debug(f"Filtered rank pattern: {text}")
                        break
                else:
                    continue  # No rank abbreviation found, might be a name
                continue  # Skip this item

            # Check if text contains rank abbreviation (e.g., "E2 Ffoxface")
            has_rank_abbr = any(abbr in text for abbr in rank_abbreviations)

            # If has rank abbreviation, try to extract name part
            if has_rank_abbr:
                # Remove rank abbreviations from text
                cleaned_text = text
                for abbr in sorted(rank_abbreviations, key=len, reverse=True):  # Longest first
                    if abbr in cleaned_text:
                        cleaned_text = cleaned_text.replace(abbr, '', 1).strip()
                        break

                # Validate extracted name
                if len(cleaned_text) >= 3:
                    potential_items.append({
                        'text': cleaned_text,
                        'x_center': item['x_center'],
                        'y_center': item['y_center'],
                        'confidence': item['confidence']
                    })
                continue

            # Check length and characters
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
                    # Update row Y to average
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

        # DEDUPLICATION: Remove duplicate text detections within same row
        for row in rows:
            # Sort items by confidence (descending)
            row['items'].sort(key=lambda x: -x['confidence'])

            # Deduplicate by text similarity
            seen_texts = set()
            unique_items = []
            for item in row['items']:
                text = item['text']
                # Check if we've seen a similar text before
                duplicate = False
                for seen_text in seen_texts:
                    # Simple similarity: exact match or contains
                    if text == seen_text or text in seen_text or seen_text in text:
                        duplicate = True
                        log.debug(f"Dedup: '{text}' (similar to '{seen_text}')")
                        break

                if not duplicate:
                    seen_texts.add(text)
                    unique_items.append(item)
                else:
                    # Keep higher confidence version
                    for i, u_item in enumerate(unique_items):
                        if u_item['text'] in text or text in u_item['text']:
                            if item['confidence'] > u_item['confidence']:
                                unique_items[i] = item
                                log.debug(f"Dedup: Replaced lower confidence '{u_item['text']}' with higher confidence '{text}'")
                            break

            row['items'] = unique_items

        # SIMPLIFIED MERGING: Combine all text in row with spaces
        for row in rows:
            # Sort items by X position (left to right)
            row['items'].sort(key=lambda x: x['x_center'])

            # Join all text in row with spaces
            combined_text = ' '.join(item['text'] for item in row['items'])
            max_conf = max(item['confidence'] for item in row['items'])
            avg_x = sum(item['x_center'] for item in row['items']) / len(row['items'])

            row['items'] = [{
                'text': combined_text,
                'x_center': avg_x,
                'y_center': row['y_center'],
                'confidence': max_conf
            }]

        # Sort rows by Y and pick top 8
        rows.sort(key=lambda x: x['y_center'])
        best_names = [row['items'][0] for row in rows[:8]]

        # Assign placements 1-8 based on Y order
        players = []
        for i, item in enumerate(best_names):
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

# Read the file
with open('C:\\Users\\blake\\PycharmProjects\\New-GAL-Discord-Bot\\integrations\\standings_ocr.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace function
content = content.replace(old_function, new_function)

# Write back
with open('C:\\Users\\blake\\PycharmProjects\\New-GAL-Discord-Bot\\integrations\\standings_ocr.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Function replaced successfully!")
