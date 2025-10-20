# Summary of Changes: Patient-Specific Save Structure

## Overview

Modified the FHIR bundle save functionality to automatically organize generated data in patient-specific folders with improved file naming.

## Changes Made

### 1. Modified `src/open_compute/agents/ai_journey_to_fhir.py`

#### Added `_extract_patient_name()` method

- Extracts patient's first and last name from the Patient resource
- Sanitizes names for filesystem compatibility (lowercased, special chars → underscores)
- Preserves international characters (e.g., "María" stays as "maría")
- Falls back to "unknown_patient" if names cannot be extracted

#### Updated `_save_bundle()` method

- Changed folder naming from `generation_{patient_id}_{timestamp}` to `firstname_lastname`
- Renamed output files:
  - ~~`bundle.json`~~ → `patient_bundle.json`
  - ~~`bulk/*.ndjson`~~ → `bulk_fhir.jsonl` (single file)
- Updated README.txt to include patient name and better descriptions

### 2. Updated `examples/ai_journey_to_fhir_example.py`

- Removed manual save code (auto_save handles it now)
- Added comments explaining the new save structure
- Clarified that files are automatically saved to `output/firstname_lastname/`

### 3. Updated `README.md`

- Added AI-Powered FHIR Generation section
- Documented the new save structure
- Included quick example showing auto_save usage

### 4. Created Documentation

- **`docs/SAVE_STRUCTURE.md`**: Comprehensive guide to the save structure
  - Directory structure explanation
  - File format descriptions
  - Usage examples
  - Integration with Bulk Data APIs

### 5. Added Tests

- **`tests/test_save_structure.py`**: Test suite for save functionality
  - Tests name extraction with various edge cases
  - Tests complete save structure
  - Verifies file formats (Bundle JSON and JSONL)

## New Directory Structure

```
output/
└── firstname_lastname/
    ├── patient_bundle.json    # Complete FHIR Bundle
    ├── bulk_fhir.jsonl        # All resources in JSONL format
    └── README.txt             # Generation metadata and summary
```

## Example Usage

### Automatic Save (Default)

```python
from open_compute import generate_fhir_from_journey, PatientJourney, JourneyStage

journey = PatientJourney(
    patient_id="patient-123",
    summary="Patient journey description",
    stages=[...]
)

result = generate_fhir_from_journey(
    journey=journey,
    patient_context="Patient context...",
    auto_save=True,  # Default: True
)

# Files automatically saved to: output/john_doe/
# (where patient name is extracted from generated Patient resource)
```

### Custom Output Directory

```python
from open_compute import AIJourneyToFHIR

agent = AIJourneyToFHIR(
    auto_save=True,
    save_directory="custom_output"
)

result = agent.generate_from_journey(journey, patient_context)
# Files saved to: custom_output/john_doe/
```

## Benefits

1. **Patient-Centric Organization**: Each patient's data in their own folder
2. **Clear Naming**: `patient_bundle.json` and `bulk_fhir.jsonl` are self-explanatory
3. **FHIR Compliance**: JSONL format follows [FHIR Bulk Data specification](https://hl7.org/fhir/uv/bulkdata/)
4. **Easy Integration**: Single JSONL file simplifies bulk import pipelines
5. **International Support**: Preserves non-ASCII characters in folder names

## File Formats

### patient_bundle.json

Standard FHIR Bundle format:

```json
{
  "resourceType": "Bundle",
  "type": "collection",
  "timestamp": "2024-01-15T14:30:00Z",
  "entry": [...]
}
```

### bulk_fhir.jsonl

JSONL format (one resource per line):

```jsonl
{"resourceType":"Patient","id":"patient-123","name":[...]}
{"resourceType":"Observation","id":"obs-456","status":"final",...}
{"resourceType":"Condition","id":"cond-789",...}
```

## Testing

Run the test suite to verify functionality:

```bash
cd /Users/bkyritz/Code/Jori/Open-Compute
python tests/test_save_structure.py
```

All tests pass ✓

## Migration Notes

If you have existing code that manually saves bundles:

### Before:

```python
result = generate_fhir_from_journey(journey, patient_context)

# Manual save
output_file = "generated_fhir_bundle.json"
bundle_dict = {
    "resourceType": result.fhir_data.resourceType,
    "type": "collection",
    "entry": result.fhir_data.entries,
}
with open(output_file, "w") as f:
    json.dump(bundle_dict, f, indent=2)
```

### After:

```python
result = generate_fhir_from_journey(
    journey,
    patient_context,
    auto_save=True  # Default: True
)
# Files automatically saved to: output/firstname_lastname/
```

## Additional Resources

- **Full Documentation**: See `docs/SAVE_STRUCTURE.md`
- **Example**: See `examples/ai_journey_to_fhir_example.py`
- **Tests**: See `tests/test_save_structure.py`
