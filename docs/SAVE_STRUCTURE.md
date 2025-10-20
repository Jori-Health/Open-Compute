# FHIR Bundle Save Structure

## Overview

When generating FHIR resources from patient journeys, the system automatically saves the generated data in a structured, patient-specific format under the `output/` directory.

## Directory Structure

```
output/
└── firstname_lastname/
    ├── patient_bundle.json
    ├── bulk_fhir.jsonl
    └── README.txt
```

### Folder Naming

The patient-specific folder is named using the pattern `firstname_lastname`, where:

- **firstname**: The first given name from the Patient resource
- **lastname**: The family name from the Patient resource
- Both names are sanitized (lowercased, special characters replaced with underscores)
- If names cannot be extracted, defaults to `unknown_patient`

### File Descriptions

#### 1. `patient_bundle.json`

A complete FHIR Bundle containing all generated resources in standard JSON format.

**Structure:**

```json
{
  "resourceType": "Bundle",
  "type": "collection",
  "timestamp": "2024-01-15T14:30:00.000Z",
  "entry": [
    {
      "resource": {
        "resourceType": "Patient",
        "id": "patient-123",
        ...
      }
    },
    {
      "resource": {
        "resourceType": "Observation",
        "id": "obs-456",
        ...
      }
    }
  ]
}
```

#### 2. `bulk_fhir.jsonl`

All resources in JSONL (JSON Lines) format - the standard format for FHIR Bulk Data export.

**Structure:**
Each line is a complete, valid JSON resource:

```jsonl
{"resourceType":"Patient","id":"patient-123","name":[{"given":["John"],"family":"Doe"}]}
{"resourceType":"Observation","id":"obs-456","status":"final","code":{...}}
{"resourceType":"Condition","id":"cond-789","clinicalStatus":{...}}
```

This format is ideal for:

- Bulk data operations
- ETL pipelines
- Stream processing
- Large dataset handling

#### 3. `README.txt`

Metadata summary about the generation including:

- Patient name and ID
- Generation timestamp
- FHIR version used
- AI model used
- Resource type summary

## Usage Examples

### Automatic Save (Recommended)

The simplest way is to enable `auto_save` (enabled by default):

```python
from open_compute import generate_fhir_from_journey, PatientJourney, JourneyStage

journey = PatientJourney(
    patient_id="patient-123",
    summary="58 year old male with chest pain",
    stages=[...]
)

result = generate_fhir_from_journey(
    journey=journey,
    patient_context="Additional patient context...",
    model="gpt-5-mini",
    auto_save=True,  # Default: True
)

# Files automatically saved to: output/john_doe/
```

### Custom Save Directory

You can specify a custom output directory:

```python
from open_compute import AIJourneyToFHIR

agent = AIJourneyToFHIR(
    auto_save=True,
    save_directory="custom_output_folder"
)

result = agent.generate_from_journey(journey, patient_context)
# Files saved to: custom_output_folder/john_doe/
```

### Disable Auto-Save

If you want to handle saving manually:

```python
result = generate_fhir_from_journey(
    journey=journey,
    patient_context=patient_context,
    auto_save=False,
)

# Manually process result.fhir_data
# Access via result.generated_resources
```

## Name Extraction Logic

The system extracts patient names from the generated Patient resource:

1. Searches for a Patient resource in the generated bundle
2. Extracts the first name from `Patient.name[0].given[0]`
3. Extracts the family name from `Patient.name[0].family`
4. Sanitizes both names for filesystem compatibility
5. Falls back to "unknown_patient" if extraction fails

## Example Output

After generating FHIR for a patient named "John Doe":

```
output/john_doe/
├── patient_bundle.json      # 15 KB - Complete bundle
├── bulk_fhir.jsonl          # 14 KB - JSONL format
└── README.txt               # 1 KB - Metadata

README.txt contents:
==================================================
FHIR Generation Results
==================================================

Patient: John Doe
Patient ID: patient-123
Generated: 2024-01-15T14:30:00.123456
FHIR Version: R4
Model: gpt-5-mini

Files:
  - patient_bundle.json: Complete FHIR Bundle with all resources
  - bulk_fhir.jsonl: All resources in JSONL format (one resource per line)

Resource Summary:
  - Condition: 1
  - Encounter: 2
  - MedicationAdministration: 2
  - Observation: 4
  - Patient: 1
  - Procedure: 1
```

## Benefits

1. **Organized**: Each patient's data is isolated in their own folder
2. **Flexible**: Two formats support different use cases
3. **Traceable**: README provides generation metadata
4. **Standard**: Uses FHIR-compliant formats (Bundle and JSONL)
5. **Scalable**: JSONL format supports streaming and bulk operations

## Integration with Bulk Data APIs

The `bulk_fhir.jsonl` format follows the [FHIR Bulk Data specification](https://hl7.org/fhir/uv/bulkdata/), making it compatible with:

- FHIR Bulk Data import APIs
- Cloud storage bulk imports
- ETL pipelines
- Data warehouses
- Analytics platforms

## Notes

- The system creates the `output/` directory automatically if it doesn't exist
- If a patient folder already exists, files are overwritten with the latest generation
- All files use UTF-8 encoding
- JSONL files use newline (`\n`) as the line separator
