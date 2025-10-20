# Validation Error Handling & Version Mismatch Analysis

## Question 1: Do we feed validation errors to the LLM?

**YES!** ✅ The validation errors ARE being fed to the LLM in the fix loop.

### How It Works:

1. **Initial Generation** (lines 681-786 in `ai_journey_to_fhir.py`):

   - AI generates a FHIR resource
   - Resource is validated using `FHIRValidator`
   - If validation fails, errors are captured in `ValidationResult`

2. **Error Fixing Loop** (lines 1111-1236):

   - Invalid resource and validation errors are passed to `_fix_invalid_resource()`
   - Errors are formatted into text (line 1140-1141):
     ```python
     errors_text = "\n".join(f"- {error}" for error in validation_result.errors)
     ```
   - Errors are included in the fix prompt (lines 1158-1166):

     ```
     ORIGINAL RESOURCE (with errors):
     {json.dumps(invalid_resource, indent=2)}

     VALIDATION ERRORS:
     {errors_text}
     ```

3. **Iterative Fixing** (lines 1177-1227):
   - AI attempts to fix the resource (up to `max_fix_retries` times, default 3)
   - After each fix attempt, resource is re-validated
   - If still invalid, the NEW errors are fed back to the AI for another attempt
   - This continues until resource is valid or max retries reached

### Example from Your Output:

```
Validation failed for Encounter:
- period: Extra inputs are not permitted
- reasonCode: Extra inputs are not permitted
```

These errors get formatted and sent to the AI with instructions to fix them.

---

## Question 2: What version are we validating against?

**VERSION MISMATCH DETECTED!** ⚠️

### Current Situation:

| Component                | Version            | Notes                                     |
| ------------------------ | ------------------ | ----------------------------------------- |
| **Schema Data**          | FHIR 6.0.0-ballot3 | `data/fhir/STU6/`                         |
| **Validator Library**    | FHIR 5.0.0         | `fhir.resources v8.1.0`                   |
| **AI Generation Target** | "R4" (FHIR 4.0.1)  | Default in `generate_fhir_from_journey()` |

### The Problem:

1. **You're loading FHIR R6 schema data** (`data/fhir/STU6/`)
2. **But validating against FHIR R5** (what `fhir.resources v8.1.0` supports)
3. **And telling the AI to generate R4 resources** (the default parameter)

This creates a **three-way mismatch**!

### Why This Causes Issues:

#### Field Structure Changes Between Versions:

**FHIR R4 (v4.0.1)**:

- `Encounter.period` - Simple Period element
- `Encounter.reasonCode` - CodeableConcept array
- `MedicationRequest.medicationCodeableConcept` - Choice type

**FHIR R5 (v5.0.0)** - What you're validating against:

- `Encounter.period` - **Removed/changed**
- `Encounter.reasonCode` - **Changed to `reason` (different structure)**
- `MedicationRequest.medication` - **Changed to CodeableReference**

**FHIR R6 (v6.0.0)** - What your schema data is for:

- Even more changes and new resource types

### Your Validation Errors Explained:

```
Encounter: period - Extra inputs are not permitted
Encounter: reasonCode - Extra inputs are not permitted
Procedure: performedDateTime - Extra inputs are not permitted
```

These fields don't exist (or have different names) in FHIR R5!

---

## The Solution: Pick ONE Version

### Option 1: Use FHIR R5 (Recommended) ✅

**Steps:**

1. **Update schema data to R5**:

   ```bash
   # Download FHIR R5 definitions
   wget https://hl7.org/fhir/R5/definitions.json.zip
   unzip definitions.json.zip -d data/fhir/R5/
   ```

2. **Update AI generation to target R5**:

   ```python
   result = generate_fhir_from_journey(
       journey=journey,
       fhir_version="R5",  # Changed from "R4"
       model="gpt-4o-mini",
   )
   ```

3. **Update data loader** to use R5 directory:
   ```python
   # In fhir_data_loader.py, update the path
   Path(__file__).parent.parent.parent.parent / "data" / "fhir" / "R5"
   ```

### Option 2: Downgrade to FHIR R4

**Steps:**

1. **Download FHIR R4 schema data**:

   ```bash
   wget https://hl7.org/fhir/R4/definitions.json.zip
   unzip definitions.json.zip -d data/fhir/R4/
   ```

2. **Install R4-compatible validator**:

   ```bash
   pip install fhir.resources==6.5.0  # Last version for R4
   ```

3. **Keep existing code** (already defaults to R4)

### Option 3: Wait for R6 Support (Not Ready Yet)

FHIR R6 is still in ballot (draft) stage. The `fhir.resources` library doesn't support it yet.

---

## Immediate Fix for Current Errors

The errors you're seeing are because the AI is generating R4-style fields that don't exist in R5:

### 1. Encounter Fields

**Remove from guidance:**

- ❌ `period` field
- ❌ `reasonCode` field

**These don't exist in R5!**

### 2. Procedure Field

**Remove from guidance:**

- ❌ `performedDateTime` field

**In R5, use `occurrence[x]` instead (but it's optional, so we can just omit it)**

### 3. MedicationRequest Field

**Already fixed** - we updated to use:

```json
{
  "medication": {
    "concept": {
      "text": "Aspirin 325mg"
    }
  }
}
```

This is the R5 `CodeableReference` structure.

---

## Recommended Action Plan

### Immediate (Fixes current errors):

1. ✅ Update Encounter guidance to remove `period` and `reasonCode`
2. ✅ Update Procedure guidance to remove `performedDateTime`
3. ✅ Update prompts to explicitly state "DO NOT use these R4 fields"

### Short-term (Aligns everything):

1. Download FHIR R5 schema data
2. Update data loader path to use R5
3. Explicitly set `fhir_version="R5"` in generation calls
4. Update all guidance to use R5 field names

### Long-term (Best practice):

1. Choose ONE FHIR version for your project
2. Document this version clearly
3. Ensure all components use the same version:
   - Schema data
   - Validator library
   - AI generation target
   - Documentation examples

---

## Testing the Fix

After removing those fields from guidance, test again:

```bash
export OPENAI_API_KEY='your-key-here'
python examples/patient_journey_to_fhir_example.py
```

You should see:

- ✅ No more `period` errors
- ✅ No more `reasonCode` errors
- ✅ No more `performedDateTime` errors

---

## Summary

| Question                                 | Answer                                                 |
| ---------------------------------------- | ------------------------------------------------------ |
| **Do we feed validation errors to LLM?** | YES - errors are formatted and included in fix prompts |
| **What version do we validate against?** | FHIR R5 (v5.0.0) via `fhir.resources v8.1.0`           |
| **What version is our schema data?**     | FHIR R6 (v6.0.0-ballot3) ⚠️ MISMATCH                   |
| **What version should we use?**          | Pick R5 (recommended) and align everything             |

The validation errors you're seeing are because the AI is trying to use R4 field names, but the validator expects R5 structures. By updating the guidance to match R5, these errors will disappear.
