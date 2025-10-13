---
id: sops.event_name_validation
version: 1.0
last_updated: 2025-10-13
tags: [sop, validation, event-name, data-integrity]
---

# Event Name Validation SOP

## Overview
This Standard Operating Procedure (SOP) outlines the validation requirements and procedures for event names in the Guardian Angel League Live Graphics Dashboard, ensuring data consistency and integrity across all graphics and templates.

## Purpose
- Ensure consistent event name formatting
- Maintain data integrity across the system
- Provide clear validation rules for event names
- Standardize event naming conventions

## Scope
- Event name validation in graphic creation
- Event name validation in graphic editing
- Event name validation in copy operations
- Event name validation in API endpoints
- Event name validation in database schema

## Validation Requirements

### Required Field Validation
- **Mandatory Field**: Event name is required for all graphics
- **Non-Empty Validation**: Event name cannot be empty or whitespace only
- **Length Requirements**: Event name must be between 3 and 100 characters
- **Character Restrictions**: No special characters that break system functionality

### Format Standards

#### Allowed Characters
- **Letters**: A-Z, a-z (Unicode letters supported)
- **Numbers**: 0-9
- **Spaces**: Single spaces between words
- **Special Characters**: Hyphen (-), underscore (_), parentheses (()), brackets ([]])

#### Prohibited Characters
- **Control Characters**: Newlines, tabs, carriage returns
- **System Characters**: Angle brackets (< >), quotes (' "), pipe (|)
- **URL Characters**: Question mark (?), ampersand (&), equals (=)
- **File System Characters**: Forward slash (/), backslash (\), colon (:), asterisk (*)

#### Format Examples
```
✅ Valid Event Names:
- "Tournament Name 2025"
- "Spring Championship"
- "Weekly Tournament #1"
- "Team_A vs Team_B"
- "Regional Qualifiers"

❌ Invalid Event Names:
- "" (empty string)
- "   " (whitespace only)
- "Event<Name>" (contains prohibited characters)
- "Event?Name" (contains prohibited characters)
- "A" (too short - less than 3 characters)
```

## Implementation Guidelines

### Frontend Validation

#### React Hook Form Integration
```typescript
// Event name validation schema
const eventValidationSchema = z.object({
  event_name: z
    .string()
    .min(3, "Event name must be at least 3 characters long")
    .max(100, "Event name must be less than 100 characters")
    .regex(/^[a-zA-Z0-9\s\-_()[\]]+$/, "Event name contains invalid characters")
    .refine(
      (val) => val.trim().length > 0,
      "Event name cannot be empty or whitespace only"
    ),
});

// Form component with validation
const EventNameField = ({ control, errors }) => (
  <FormField
    control={control}
    name="event_name"
    render={({ field }) => (
      <FormItem>
        <FormLabel>Event Name *</FormLabel>
        <FormControl>
          <Input
            {...field}
            placeholder="Enter event name"
            className={errors.event_name ? "border-red-500" : ""}
          />
        </FormControl>
        <FormMessage>
          {errors.event_name?.message}
        </FormMessage>
      </FormItem>
    )}
  />
);
```

#### Real-time Validation
```typescript
// Custom validation hook
const useEventNameValidation = () => {
  const [validationError, setValidationError] = useState("");
  const [isValid, setIsValid] = useState(false);

  const validateEventName = useCallback((value: string) => {
    // Trim whitespace
    const trimmed = value.trim();
    
    // Length validation
    if (trimmed.length < 3) {
      setValidationError("Event name must be at least 3 characters long");
      setIsValid(false);
      return false;
    }
    
    if (trimmed.length > 100) {
      setValidationError("Event name must be less than 100 characters");
      setIsValid(false);
      return false;
    }
    
    // Character validation
    const validPattern = /^[a-zA-Z0-9\s\-_()[\]]+$/;
    if (!validPattern.test(trimmed)) {
      setValidationError("Event name contains invalid characters");
      setIsValid(false);
      return false;
    }
    
    setValidationError("");
    setIsValid(true);
    return true;
  }, []);

  return { validateEventName, validationError, isValid };
};
```

### Backend Validation

#### Pydantic Schema Validation
```python
# API schema with event name validation
from pydantic import BaseModel, Field, validator
import re

class GraphicBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    event_name: str = Field(..., min_length=3, max_length=100)
    
    @validator('event_name')
    def validate_event_name(cls, v):
        # Trim whitespace
        trimmed = v.strip()
        
        # Length validation
        if len(trimmed) < 3:
            raise ValueError('Event name must be at least 3 characters long')
        
        if len(trimmed) > 100:
            raise ValueError('Event name must be less than 100 characters')
        
        # Character validation
        valid_pattern = re.compile(r'^[a-zA-Z0-9\s\-_()[\]]+$')
        if not valid_pattern.match(trimmed):
            raise ValueError('Event name contains invalid characters')
        
        return trimmed

class GraphicCreate(GraphicBase):
    template_id: int
    tournament_id: Optional[int] = None

class GraphicUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    event_name: Optional[str] = Field(None, min_length=3, max_length=100)
    
    @validator('event_name')
    def validate_event_name(cls, v):
        if v is None:
            return v
        
        # Apply same validation as GraphicBase
        trimmed = v.strip()
        
        if len(trimmed) < 3:
            raise ValueError('Event name must be at least 3 characters long')
        
        if len(trimmed) > 100:
            raise ValueError('Event name must be less than 100 characters')
        
        valid_pattern = re.compile(r'^[a-zA-Z0-9\s\-_()[\]]+$')
        if not valid_pattern.match(trimmed):
            raise ValueError('Event name contains invalid characters')
        
        return trimmed
```

#### Database Constraints
```sql
-- Event name constraints in database
ALTER TABLE graphics 
ADD CONSTRAINT chk_event_name_length 
CHECK (LENGTH(TRIM(event_name)) >= 3 AND LENGTH(event_name) <= 100);

-- Add NOT NULL constraint
ALTER TABLE graphics 
ALTER COLUMN event_name SET NOT NULL;

-- Add unique constraint if needed (optional)
-- ALTER TABLE graphics 
-- ADD CONSTRAINT uq_event_name_title 
-- UNIQUE (event_name, title);
```

## Validation Workflow

### Create Graphic Workflow
1. **Frontend Validation**
   - User enters event name in CreateGraphicDialog
   - Real-time validation provides immediate feedback
   - Form cannot be submitted if validation fails
   - Display specific error messages for validation failures

2. **API Validation**
   - Request sent to backend with event name
   - Pydantic schema validates event name format
   - Returns 400 Bad Request if validation fails
   - Provides detailed error response

3. **Database Validation**
   - Database constraints enforce data integrity
   - Returns error if constraints violated
   - Ensures data consistency at storage level

### Edit Graphic Workflow
1. **Canvas Editor Validation**
   - Event name field in canvas editor header
   - Real-time validation during editing
   - Save operation validates required fields
   - Prevents save without valid event name

2. **API Update Validation**
   - Update endpoint validates event name if provided
   - Same validation rules as creation
   - Maintains data consistency during updates

### Copy Graphic Workflow
1. **Copy Dialog Validation**
   - CopyGraphicDialog requires event name input
   - Pre-populates with source graphic's event name
   - User can modify event name for copy
   - Validation prevents invalid copy operations

## Error Handling

### Frontend Error Messages
```typescript
// Error message mapping
const getEventNameError = (error: string): string => {
  const errorMap: Record<string, string> = {
    'String must have at least 3 characters': 
      'Event name must be at least 3 characters long',
    'String must have at most 100 characters': 
      'Event name must be less than 100 characters',
    'Invalid string format': 
      'Event name contains invalid characters. Use only letters, numbers, spaces, hyphens, underscores, and parentheses.',
    'Event name cannot be empty': 
      'Event name is required and cannot be empty',
  };
  
  return errorMap[error] || 'Invalid event name format';
};
```

### Backend Error Responses
```python
# API error response for validation failures
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error",
            "details": exc.errors(),
            "message": "Please check your input and try again"
        }
    )
```

## Testing Procedures

### Unit Testing

#### Frontend Validation Tests
```typescript
// Test event name validation
describe('Event Name Validation', () => {
  test('should validate minimum length', () => {
    expect(validateEventName('Ab')).toBe(false);
    expect(validateEventName('Abc')).toBe(true);
  });
  
  test('should validate maximum length', () => {
    const longName = 'a'.repeat(101);
    expect(validateEventName(longName)).toBe(false);
    
    const validLongName = 'a'.repeat(100);
    expect(validateEventName(validLongName)).toBe(true);
  });
  
  test('should validate character restrictions', () => {
    expect(validateEventName('Valid Name-123')).toBe(true);
    expect(validateEventName('Invalid<Name>')).toBe(false);
    expect(validateEventName('Invalid?Name')).toBe(false);
  });
  
  test('should handle whitespace correctly', () => {
    expect(validateEventName('   ')).toBe(false);
    expect(validateEventName('  Valid Name  ')).toBe(true);
  });
});
```

#### Backend Validation Tests
```python
# Test Pydantic validation
class TestEventNameValidation:
    def test_valid_event_names(self):
        valid_names = [
            "Tournament Name 2025",
            "Spring Championship",
            "Team_A vs Team_B",
            "Weekly Tournament #1"
        ]
        
        for name in valid_names:
            graphic = GraphicBase(title="Test", event_name=name)
            assert graphic.event_name == name.strip()
    
    def test_invalid_event_names(self):
        invalid_names = [
            "",  # Empty
            "A",  # Too short
            "a" * 101,  # Too long
            "Invalid<Name>",  # Invalid characters
            "Invalid?Name"  # Invalid characters
        ]
        
        for name in invalid_names:
            with pytest.raises(ValidationError):
                GraphicBase(title="Test", event_name=name)
```

### Integration Testing

#### API Endpoint Testing
```python
# Test API validation
def test_create_graphic_invalid_event_name(client):
    invalid_data = {
        "title": "Test Graphic",
        "event_name": "A",  # Too short
        "template_id": 1
    }
    
    response = client.post("/api/graphics", json=invalid_data)
    assert response.status_code == 400
    
    error_detail = response.json()
    assert "event_name" in str(error_detail)

def test_update_graphic_invalid_event_name(client, graphic):
    invalid_data = {
        "event_name": "Invalid<Name>"
    }
    
    response = client.put(f"/api/graphics/{graphic.id}", json=invalid_data)
    assert response.status_code == 400
```

## Migration Procedures

### Data Migration for Existing Graphics
```python
# Migration script to validate and clean existing event names
async def migrate_event_names():
    graphics = await get_all_graphics()
    
    for graphic in graphics:
        if not graphic.event_name or len(graphic.event_name.strip()) < 3:
            # Set default event name for invalid entries
            default_name = f"Untitled Event {graphic.id}"
            await update_graphic_event_name(graphic.id, default_name)
            logger.info(f"Updated graphic {graphic.id} with default event name")
        
        elif not re.match(r'^[a-zA-Z0-9\s\-_()[\]]+$', graphic.event_name):
            # Clean invalid characters
            cleaned_name = re.sub(r'[^a-zA-Z0-9\s\-_()[\]]', '', graphic.event_name)
            if len(cleaned_name) < 3:
                cleaned_name = f"Cleaned Event {graphic.id}"
            
            await update_graphic_event_name(graphic.id, cleaned_name)
            logger.info(f"Cleaned event name for graphic {graphic.id}")
```

## Quality Assurance

### Validation Checklist
- [ ] Frontend form validation implemented
- [ ] Real-time validation feedback provided
- [ ] Backend schema validation active
- [ ] Database constraints enforced
- [ ] Error messages are user-friendly
- [ ] Test coverage for all validation scenarios
- [ ] Migration procedures for existing data
- [ ] Documentation updated with validation rules

### User Experience Validation
- [ ] Validation messages are clear and helpful
- [ ] Form submission prevented for invalid inputs
- [ ] Real-time feedback improves user experience
- [ ] Error recovery process is straightforward
- [ ] Mobile validation works correctly
- [ ] Accessibility standards met for validation

## Monitoring and Reporting

### Validation Metrics
- **Validation Success Rate**: Percentage of valid submissions
- **Common Validation Errors**: Most frequent validation failures
- **User Correction Rate**: How often users fix validation errors
- **Form Abandonment Rate**: Forms abandoned due to validation

### Error Tracking
- Track validation error patterns
- Monitor user behavior with validation
- Identify areas for validation improvement
- Report validation system health

## Related Documentation
- **[API Backend System](../system/api-backend-system.md)** - API validation implementation
- **[Data Models](../system/data-models.md)** - Database schema and constraints
- **[Frontend Components](../system/frontend-components.md)** - Component validation details
- **[Graphics Management SOP](./graphics-management.md)** - Graphic creation and editing procedures

## Version History
- **v1.0** (2025-10-13): Initial SOP creation
  - Established event name validation requirements
  - Defined implementation guidelines for frontend and backend
  - Created testing procedures and quality assurance standards

---

**Document Owner**: Development Team  
**Review Frequency**: Monthly  
**Next Review Date**: 2025-11-13  
**Approval**: Technical Lead
