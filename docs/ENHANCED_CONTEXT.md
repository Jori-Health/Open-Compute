# Enhanced FHIR Context for Better Generation

## Overview

The **Enhanced Context** feature significantly improves FHIR resource generation quality by incorporating rich FHIR specification data into the AI prompts. This results in more accurate, compliant, and complete FHIR resources.

## What's Included

### Previously (Basic Schema Only)

- ✅ `fhir.schema.json` - Basic resource structure and property descriptions

### Now Available (Enhanced Context)

- ✅ `fhir.schema.json` - Basic resource structure
- ✅ `valuesets.json` - Valid coded values for enumerated fields
- ✅ `profiles-resources.json` - Detailed resource profiles with constraints
- ✅ `profiles-types.json` - Type profiles and data type definitions
- ✅ `search-parameters.json` - Important/searchable fields

## Benefits

### 1. **Accurate Coded Values**

The AI now has access to valid value sets, so it generates correct codes for fields like:

- `status` (e.g., "active", "completed", "cancelled")
- `intent` (e.g., "proposal", "plan", "order")
- `priority` (e.g., "routine", "urgent", "asap", "stat")
- `category` (proper FHIR coding systems)

**Before:** AI might guess invalid status values  
**After:** AI uses only valid values from FHIR valuesets

### 2. **Better Field Usage**

Search parameters indicate which fields are important and commonly used:

- Helps AI prioritize essential fields
- Ensures searchable/important fields are populated
- Improves resource discoverability

### 3. **Constraint Adherence**

Resource profiles provide detailed constraints:

- Required cardinality (min/max occurrences)
- Value restrictions
- Binding strength for coded elements
- Element definitions and usage notes

### 4. **Reduced Validation Errors**

With richer context, the AI generates more correct resources from the start:

- Fewer validation errors
- Fewer fix iterations needed
- Higher success rate

## Usage

### Basic Usage (Automatic)

Enhanced context is **enabled by default**:

```python
from open_compute import generate_fhir_from_journey, PatientJourney, JourneyStage

journey = PatientJourney(
    patient_id="patient-123",
    summary="Patient visit",
    stages=[
        JourneyStage(name="Visit", description="Initial visit")
    ]
)

# Enhanced context is enabled by default
result = generate_fhir_from_journey(
    journey=journey,
    model="gpt-5-mini",
)
```

The system will automatically find your FHIR data files in:

1. `{project_root}/data/fhir/STU6/`
2. `{cwd}/data/fhir/STU6/`
3. `~/Desktop/definitions.json/`

### Advanced Usage (Custom Data Directory)

If your FHIR data is in a custom location:

```python
from open_compute import AIJourneyToFHIR

agent = AIJourneyToFHIR(
    model="gpt-5-mini",
    fhir_data_directory="/path/to/your/fhir/data/STU6",
    use_enhanced_context=True,  # Default is True
)

result = agent.generate_from_journey(journey)
```

### Disabling Enhanced Context

If you want to use only basic schema (not recommended):

```python
result = generate_fhir_from_journey(
    journey=journey,
    use_enhanced_context=False,  # Disable enhanced features
)
```

## What the AI Sees

### Example: Generating an Observation Resource

**With Enhanced Context**, the AI receives:

```
=== FHIR Observation Reference Data ===

Description: Measurements and simple assertions made about a patient...

Required fields (MUST be present):
  - resourceType
  - status
  - code

Valid values for status:
  registered, preliminary, final, amended, corrected, cancelled, entered-in-error, unknown

Valid values for category:
  vital-signs, laboratory, exam, imaging, procedure, survey, ...

Important fields (commonly searched/used):
  - code: Type of observation (Coding/name)
  - subject: Who and/or what the observation is about
  - effective: Clinically relevant time/time-period for observation
  - value: Actual result
  - status: registered | preliminary | final | amended | ...

Key properties:
  - status: The status of the result value
  - code: Type of observation (code / type)
  - subject: Who and/or what the observation is about
  - effective[x]: Clinically relevant time/time-period
  - value[x]: Actual result
  ...
```

This rich context helps the AI make better decisions about:

- Which status to use
- What categories are appropriate
- Which fields are essential
- What valid values exist

## Data Files Explained

### valuesets.json (113k lines)

Contains FHIR value sets - collections of coded values for use in specific contexts.

**Example usage:**

- Valid status codes for different resources
- Medical terminologies (LOINC, SNOMED CT, RxNorm)
- Administrative codes

### profiles-resources.json (479k lines)

Detailed structural definitions for each FHIR resource type.

**Includes:**

- Element definitions with descriptions
- Cardinality constraints (min/max)
- Value set bindings
- Data type specifications

### profiles-types.json (36k lines)

Definitions for FHIR data types (CodeableConcept, Quantity, etc.).

**Helps with:**

- Complex data type structures
- Proper use of FHIR types
- Type constraints

### search-parameters.json (75k lines)

Defines searchable parameters for each resource.

**Indicates:**

- Which fields are important
- Expected data types
- Search expressions

## Performance Considerations

### Token Usage

Enhanced context adds ~500-1000 tokens per resource generation (vs basic schema).

**Trade-off:**

- Slightly higher API costs
- Significantly better quality
- Fewer fix iterations (saves tokens overall)

**Net result:** Usually breaks even or saves tokens due to fewer validation errors.

### Data Loading

All data files are loaded once at initialization and cached in memory.

**File sizes:**

- Total: ~934k lines
- Memory: ~50-100 MB
- Load time: 1-2 seconds

This is negligible compared to API call time.

## Comparison: Before vs After

### Before (Basic Schema Only)

```python
# Observation might have invalid status
{
  "resourceType": "Observation",
  "status": "done",  # ❌ Invalid! Not in valueset
  "code": {...},
  # Missing important fields
}
```

### After (Enhanced Context)

```python
{
  "resourceType": "Observation",
  "status": "final",  # ✅ Valid from valueset
  "category": [{
    "coding": [{
      "system": "http://terminology.hl7.org/CodeSystem/observation-category",
      "code": "vital-signs"
    }]
  }],
  "code": {...},
  "subject": {"reference": "Patient/123"},
  "effectiveDateTime": "2024-01-15T10:30:00Z",
  # All important fields populated
}
```

## Troubleshooting

### Data Files Not Found

If you see:

```
Warning: FHIR data directory not found. Generation will proceed without enhanced context.
```

**Solution:**

1. Check that FHIR data files exist in `data/fhir/STU6/`
2. Verify files: `fhir.schema.json`, `valuesets.json`, `profiles-resources.json`, etc.
3. Or specify custom path: `fhir_data_directory="/path/to/data"`

### Still Getting Validation Errors

Enhanced context improves quality but doesn't guarantee 100% valid resources.

**Tips:**

- Use `max_fix_retries=3` (default) for automatic error correction
- Check validation errors to identify specific issues
- Provide more detailed patient journey information

### Memory Concerns

If you're worried about memory usage:

**Options:**

1. Use `use_enhanced_context=False` for basic schema only
2. Run in environment with sufficient RAM (recommend 512MB+)
3. Data is loaded once per agent instance, not per generation

## Best Practices

### ✅ Recommended Setup

```python
from open_compute import generate_fhir_from_journey

result = generate_fhir_from_journey(
    journey=journey,
    patient_context=detailed_context,  # Provide rich context
    model="gpt-5-mini",
    use_enhanced_context=True,  # Default, explicitly shown here
    max_iterations=3,
    max_fix_retries=3,
)
```

### 🎯 For Production Use

```python
from open_compute import AIJourneyToFHIR

agent = AIJourneyToFHIR(
    model="gpt-4o",  # Best quality
    fhir_data_directory="/absolute/path/to/fhir/data",
    use_enhanced_context=True,
    max_iterations=5,
    max_fix_retries=3,
    auto_save=True,
    parallel_generation=True,
)

result = agent.generate_from_journey(journey, patient_context)
```

### 🧪 For Testing/Development

```python
result = generate_fhir_from_journey(
    journey=simple_journey,
    model="gpt-5-mini",  # Faster, cheaper
    max_iterations=2,
    use_enhanced_context=True,  # Still recommended
)
```

## Migration Guide

### If you're using the old approach:

**Old:**

```python
agent = AIJourneyToFHIR(
    fhir_schema_path="/path/to/fhir.schema.json",
)
```

**New (Backward Compatible):**

```python
agent = AIJourneyToFHIR(
    fhir_data_directory="/path/to/fhir/data/directory",  # Points to directory
    use_enhanced_context=True,  # Recommended
)
```

**Both work!** The old `fhir_schema_path` is still supported for backward compatibility.

## Examples

See `examples/enhanced_context_example.py` for:

- ✅ Using enhanced context (recommended)
- ✅ Comparing with basic context
- ✅ Custom data directory
- ✅ Quality improvements demonstration

## Summary

**Enhanced Context = Better FHIR Resources**

| Feature               | Basic Schema | Enhanced Context |
| --------------------- | ------------ | ---------------- |
| Schema structure      | ✅           | ✅               |
| Property descriptions | ✅           | ✅               |
| Valid coded values    | ❌           | ✅               |
| Value set bindings    | ❌           | ✅               |
| Resource constraints  | ❌           | ✅               |
| Important fields      | ❌           | ✅               |
| Search parameters     | ❌           | ✅               |
| **Result Quality**    | Good         | **Excellent**    |

**Recommendation:** Always use enhanced context (`use_enhanced_context=True`) for production use.
