"""Fix the paddle_ocr_engine.py _structure_tft_data function."""

# Read the file
with open('integrations/paddle_ocr_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the entire _structure_tft_data function (the second one, starting at line 361)
old_function_start = '    def _structure_tft_data(self, text_results: List[Dict]) -> Dict:\n        """\n        Structure OCR results into TFT standings format.\n\n        TFT screenshots have placement numbers (1-8) followed by player names.\n        Strategy: Find digit 1-8, then collect following text as player name.\n        """'

# Find the section to replace - from old function start to the "return" statement
old_pattern = '''        # Match names to placements by Y position
        # Strategy: Sort both by Y, then assign closest name to each placement
        players = []

        print(f"[DEBUG] Found {len(placements)} placements, {len(names)} names")

        if placements and names:
            # Sort placements by Y
            placements.sort(key=lambda x: x[1])
            # Sort names by Y
            names.sort(key=lambda x: x[1])

            # Assign each placement closest name that hasn't been used
            used_names = set()

            for placement, p_y in placements:
                # Find closest unused name
                best_name = None
                best_dist = float('inf')
                best_idx = -1

                for idx, (name, n_y) in enumerate(names):
                    if idx in used_names:
                        continue

                    # Distance between placement and name
                    dist = abs(p_y - n_y)

                    # Name should be BELOW placement (positive Y distance)
                    # But allow some flexibility for different formats
                    if dist < best_dist and dist < 150:  # Max 150px difference
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

        # Sort by placement
        players.sort(key=lambda x: x["placement"])

        # FALLBACK: If we didn't match all players (6-8), try Y-based ordering
        # This handles cases where OCR detects names but misses some placement numbers
        print(f"[DEBUG] Checking fallback: {len(players)} >= 6 and {len(players)} < 8 and {len(names)} > 0")
        if len(players) >= 6 and len(players) < 8 and names:
            print(f"[DEBUG] FALLBACK TRIGGERED - using Y-based ordering for remaining names")

            # Use Y-based ordering for remaining names
            # Names are already sorted by Y from earlier
            unassigned_names = [(name, y) for idx, (name, y) in enumerate(names)
                               if idx not in used_names]

            print(f"[DEBUG] used_names indices: {used_names}")
            print(f"[DEBUG] unassigned_names: {[n for n,_ in unassigned_names]}")

            # Find all placements (1-8) and mark which we have
            current_placements = set(p["placement"] for p in players)
            missing_placements = [p for p in range(1, 9) if p not in current_placements]

            print(f"[DEBUG] current_placements: {sorted(current_placements)}")
            print(f"[DEBUG] missing_placements: {missing_placements}")

            # Assign unassigned names to missing placements
            # Use Y-sorted order to assign to sorted missing placements
            for idx, (name, _) in enumerate(unassigned_names):
                if idx < len(missing_placements):
                    next_placement = missing_placements[idx]
                    print(f"[DEBUG] Adding {name} at placement {next_placement}")
                    players.append({
                        "placement": next_placement,
                        "name": name,
                        "points": PLACEMENT_POINTS.get(next_placement, 0)
                    })

            # Sort by placement again
            players.sort(key=lambda x: x["placement"])

        return {
            "players": players,
            "player_count": len(players),
            "expected_players": 8
        }'''

new_pattern = '''        # Match names to placements by Y position
        # STRATEGY: If 8 placements detected, match by Y distance. Otherwise use Y-based ordering.
        players = []

        print(f"[DEBUG] Found {len(placements)} placements, {len(names)} names")

        if placements and names:
            # Sort names by Y
            names.sort(key=lambda x: x[1])

            # STRATEGY 1: If we have 8 placements (ideal), match names by Y distance
            if len(placements) == 8:
                print(f"[DEBUG] Using Y-distance matching (8 placements detected)")
                # Sort placements by Y
                placements.sort(key=lambda x: x[1])

                # Assign each placement to closest name that hasn't been used
                used_names = set()

                for placement, p_y in placements:
                    # Find closest unused name
                    best_name = None
                    best_dist = float('inf')
                    best_idx = -1

                    for idx, (name, n_y) in enumerate(names):
                        if idx in used_names:
                            continue

                        # Distance between placement and name
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

            # STRATEGY 2: If placements < 8, use Y-based ordering (inferred placements)
            # This handles cases where OCR detects names but misses some placement numbers
            elif len(names) >= 6:
                print(f"[DEBUG] Using Y-based ordering for {len(names)} names")
                # Names are sorted by Y, assign sequential placements
                for idx, (name, y) in enumerate(names[:8]):  # Limit to 8
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
        }'''

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    with open('integrations/paddle_ocr_engine.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Successfully updated paddle_ocr_engine.py")
else:
    print("❌ Could not find the pattern to replace")
