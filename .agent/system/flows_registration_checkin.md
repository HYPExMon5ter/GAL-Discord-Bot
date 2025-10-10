---
id: system.flows.registration_checkin
version: 1.0
last_updated: 2025-10-10
tags: [flows, registration, checkin]
---

# Registration & Check-In/Out Flows

## Registration (Solo)
1. Gate by schedule window & capacity cap
2. Deduplicate by Discord user; upsert player
3. Mark registration active; grant role; success embed
4. Audit log, refresh embeds

## Registration (Double Up)
- Normalize + fuzzy-check team name similarity (collision prompt)
- Ensure team capacity (≤ 2) and member uniqueness
- Transactional create/get team and add member
- Then same as Solo steps

## Check-In/Out
- Requires active registration + check-in window
- Idempotent toggle; sync roles
- Append to checkins, compute current state
- Respond with appropriate embed
