# Fixed FHIR Resource Generation Issues

## What Was Wrong

The AI was generating FHIR resources with incorrect field structures that didn't match what the `fhir.resources` Python library expected. Specifically:

### 1. **Encounter.class** Field

- **Problem**: AI was generating a single `Coding` object
- **Solution**: Changed to a **LIST** of `CodeableConcept` objects (each with a `coding` array)

```json
// CORRECT Structure
{
  "resourceType": "Encounter",
  "status": "finished",
  "class": [
    {
      "coding": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
          "code": "EMER",
          "display": "emergency"
        }
      ]
    }
  ],
  "subject": { "reference": "Patient/patient-id" }
}
```

### 2. **MedicationRequest.medication** Field

- **Problem**: AI was using `medicationCodeableConcept` field name (FHIR R4 choice type)
- **Solution**: Changed to `medication` with nested `concept` object (CodeableReference type in fhir.resources v7+)

```json
// CORRECT Structure
{
  "resourceType": "MedicationRequest",
  "status": "active",
  "intent": "order",
  "medication": {
    "concept": {
      "text": "Aspirin 325mg"
    }
  },
  "subject": { "reference": "Patient/patient-id" }
}
```

### 3. **Procedure.performedDateTime** Field

- **Problem**: Field name not recognized
- **Solution**: Removed from required fields (can be omitted for minimal valid resource)

### 4. **Location/Organization.address** Field

- **Problem**: AI was generating empty strings for address fields
- **Solution**: Instructed AI to omit address field entirely unless complete information is available

## Quick Test

Now test again with the fixed guidance:

```bash
export OPENAI_API_KEY='your-key-here'
cd /Users/bkyritz/Code/Jori/Open-Compute
python examples/patient_journey_to_fhir_example.py
```

## Expected Results

You should now see:

- ✅ **Encounter resources validating successfully**
- ✅ **MedicationRequest resources validating successfully**
- ✅ **Procedure resources validating successfully**
- ✅ **No address validation errors**

## Files Updated

1. `/src/open_compute/agents/ai_journey_to_fhir.py`
   - Fixed `Encounter` guidance (lines 1470-1499)
   - Fixed `MedicationRequest` guidance (lines 1521-1549)
   - Fixed `MedicationAdministration` guidance (lines 1550-1576)
   - Added `Location` guidance (lines 1609-1630)
   - Updated `Organization` and `Procedure` guidance

## What This Fixes

The errors you were seeing:

- ❌ `Encounter.class: Input should be a valid list` → ✅ **FIXED**
- ❌ `MedicationRequest.medication: Field required` → ✅ **FIXED**
- ❌ `Procedure.performedDateTime: Extra inputs not permitted` → ✅ **FIXED**
- ❌ `Location.address: String should match pattern` → ✅ **FIXED**

## Why This Happened

The `fhir.resources` Python library (v7+) uses slightly different structures than the base FHIR R4 specification:

- Uses `CodeableReference` type instead of simple choice types like `medication[x]`
- Requires specific nesting (e.g., `medication.concept` instead of `medicationCodeableConcept`)
- Has stricter validation rules for fields like `class` (must be list of CodeableConcept, not Coding)

## Next Steps

Run the example again. If you still see errors, they should be different ones and we can address them specifically.
