## Spec: Make Pronouns a Required Field in Discord Bot Registration

### Current State
- **Registration Modal** (`core/views.py`, line 740): Pronouns field has `required=False`
- **Onboarding Modal** (`core/onboard.py`, line 106): Pronouns field already has `required=True` ✅

### Changes Required

**File: `core/views.py`**
- Line 740: Change `required=False` to `required=True` in the `pronouns_input` TextInput field
- This affects the `RegistrationModal` class used for event registration

### Impact
- Users registering via `/register` command will now be required to provide pronouns
- Validation will be enforced at the Discord modal level (cannot submit without filling it)
- The auto-capitalization logic (line 770-774) will continue to work as expected
- All downstream processing already handles pronouns correctly

### Implementation
Simple one-line change from:
```python
required=False,  # Line 740
```
to:
```python
required=True,
```