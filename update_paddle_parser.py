"""Update paddle_ocr_engine.py with improved parsing logic."""

# Read file
with open('integrations/paddle_ocr_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the _structure_tft_data function that handles Y-based matching (line 363)
# We need to replace from that function to just before the _calculate_confidence function

start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if 'def _structure_tft_data(self, text_results: List[Dict]) -> Dict:' in line and i > 360:
        start_idx = i
    if start_idx and 'def _calculate_confidence' in line:
        end_idx = i
        break

if start_idx and end_idx:
    print(f"Found function at lines {start_idx}-{end_idx}")

    new_function = '''    def _structure_tft_data(self, text_results: List[Dict]) -> Dict:
        """
        Structure OCR results into TFT standings format.

        Improved approach:
        1. Filter low-confidence detections (< 85%)
        2. Separate placements and names
        3. Match using Y position or sequential ordering
        """
        # Filter out UI elements
        skip_keywords = ['FIRST', 'PLACE', 'STANDING', 'TEAMFIGHT', 'TACTICS',
                        'NORMAL', 'GAMED', 'ONLINE', 'SOCIAL', 'PLAYER',
                        'SUMMONER', 'ROUND', 'TRAILS', 'CHAMPIONS', 'TANDING',
                        'PLAY', 'AGAIN', 'CONTINUE', 'GAMEID']

        placements = []  # (placement, y_pos)
        names = []  # (name, y_pos)

        for item in text_results:
            text = item["text"].strip()
            y_pos = item["center_y"]
            text_upper = text.upper()
            confidence = item["confidence"]

            # Skip low confidence detections (< 85%)
            if confidence < 85:
                continue

            # Skip UI keywords
            if any(keyword in text_upper for keyword in skip_keywords):
                continue

            # Check if this is a placement number (1-8)
            if text.isdigit() and 1 <= int(text) <= 8:
                placements.append((int(text), y_pos))

            # Check if this looks like a player name
            # Valid names: 3+ chars, contains at least one letter
            # Additional: Avoid garbage like "GamelD", single letters, etc.
            text_alpha_only = ''.join(c for c in text if c.isalpha())
            if (len(text_alpha_only) >= 3 and
                len(text_alpha_only) / len(text) >= 0.7 and  # 70%+ letters
                not any(char.isdigit() for char in text_alpha_only)):  # No digits in name
                names.append((text, y_pos))

        print(f"[DEBUG] After filtering: {len(placements)} placements, {len(names)} names")

        # STRATEGY: Match names to placements
        players = []

        if placements and names:
            # Sort names by Y
            names.sort(key=lambda x: x[1])

            # CASE 1: 8 placements detected (ideal case)
            if len(placements) == 8:
                print(f"[DEBUG] Using Y-distance matching (8 placements detected)")
                placements.sort(key=lambda x: x[1])

                used_names = set()
                for placement, p_y in placements:
                    best_name = None
                    best_dist = float('inf')
                    best_idx = -1

                    for idx, (name, n_y) in enumerate(names):
                        if idx in used_names:
                            continue

                        dist = abs(p_y - n_y)
                        if dist < best_dist and dist < 150:
                            best_dist = dist
                            best_name = name
                            best_idx = idx

                    if best_name and best_idx >= 0:
                        players.append({
                            "placement": placement,
                            "name": best_name,
                            "points": PLACEMENT_POINTS.get(placement, 0)
                        })
                        used_names.add(best_idx)

            # CASE 2: Some placements detected (4-7), use Y-based ordering
            elif len(placements) >= 4 and len(names) <= 8:
                print(f"[DEBUG] Using Y-based ordering with {len(names)} names")
                # Names sorted by Y = placements 1-8 in order
                for idx, (name, y) in enumerate(names):
                    if idx < 8:
                        players.append({
                            "placement": idx + 1,
                            "name": name,
                            "points": PLACEMENT_POINTS.get(idx + 1, 0)
                        })

            # CASE 3: No placements or too many names, try to infer
            else:
                print(f"[DEBUG] No reliable placements, using Y-only ordering")
                # Just use Y-sorted names as players
                for idx, (name, y) in enumerate(names[:8]):
                    players.append({
                        "placement": idx + 1,
                        "name": name,
                        "points": PLACEMENT_POINTS.get(idx + 1, 0)
                    })

        # Sort by placement
        players.sort(key=lambda x: x["placement"])

        return {
            "players": players,
            "player_count": len(players),
            "expected_players": 8
        }

'''

    # Replace old function with new one
    lines[start_idx:end_idx] = [new_function]

    # Write back
    with open('integrations/paddle_ocr_engine.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print("Successfully updated paddle_ocr_engine.py with improved parsing")
else:
    print("Could not find function to replace")
