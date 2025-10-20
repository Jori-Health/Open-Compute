# Quick Start: Enhanced FHIR Context

## 🚀 What Changed?

Your FHIR generation system now uses **ALL the data** from your `data/fhir/STU6/` folder, not just the schema!

### Files Now Being Used:

- ✅ `fhir.schema.json` - Basic structure (was already used)
- ✅ `valuesets.json` - **NEW!** Valid coded values
- ✅ `profiles-resources.json` - **NEW!** Detailed constraints
- ✅ `profiles-types.json` - **NEW!** Type definitions
- ✅ `search-parameters.json` - **NEW!** Important fields

## 🎯 Benefits

**Better Quality Resources:**

- ✅ Correct status values (e.g., "active" instead of guessed values)
- ✅ Valid coded fields (priority, intent, category, etc.)
- ✅ More complete resources (important fields populated)
- ✅ Fewer validation errors
- ✅ Better FHIR compliance

## 📝 How to Use

### Option 1: No Changes Needed (Recommended)

**Enhanced context is enabled by default!** Your existing code will automatically benefit:

```python
from open_compute import generate_fhir_from_journey

# This now uses enhanced context automatically
result = generate_fhir_from_journey(
    journey=journey,
    model="gpt-5-mini",
)
```

That's it! You're already using enhanced context.

### Option 2: Explicit Usage

If you want to be explicit:

```python
result = generate_fhir_from_journey(
    journey=journey,
    model="gpt-5-mini",
    use_enhanced_context=True,  # Explicitly enabled
)
```

### Option 3: Custom Data Location

If your FHIR data is elsewhere:

```python
from open_compute import AIJourneyToFHIR

agent = AIJourneyToFHIR(
    model="gpt-5-mini",
    fhir_data_directory="/custom/path/to/fhir/data/STU6",
)

result = agent.generate_from_journey(journey)
```

## 🧪 Try It Out

Run the new example:

```bash
cd /Users/bkyritz/Code/Jori/Open-Compute
python examples/enhanced_context_example.py
```

## 🔍 What You'll See

When you run your code, you'll see:

```
✓ Found FHIR data directory: /path/to/data/fhir/STU6
  ✓ Loaded FHIR Schema
  ✓ Loaded Value Sets
  ✓ Loaded Resource Profiles
  ✓ Loaded Type Profiles
  ✓ Loaded Search Parameters
```

Then the AI will use all this data to generate better resources!

## 📊 Before vs After

### Before (Basic Schema Only)

```python
{
  "resourceType": "MedicationRequest",
  "status": "pending",  # ❌ Not a valid FHIR status
  "intent": "request",  # ❌ Should be "order" or "plan"
  # Missing important fields
}
```

### After (Enhanced Context)

```python
{
  "resourceType": "MedicationRequest",
  "status": "active",  # ✅ Valid from valueset
  "intent": "order",   # ✅ Correct intent value
  "priority": "routine",  # ✅ Valid priority
  "category": [{  # ✅ Proper category
    "coding": [{
      "system": "http://terminology.hl7.org/CodeSystem/medicationrequest-category",
      "code": "outpatient"
    }]
  }],
  # All important fields populated correctly
}
```

## 💡 Key Points

1. **Automatic** - Works out of the box with your existing code
2. **Better Quality** - More accurate coded values and field usage
3. **Fewer Errors** - Less validation errors and fix iterations
4. **No Downside** - Slightly more tokens but better results

## 🛠️ Troubleshooting

### "Warning: FHIR data directory not found"

**Fix:** Make sure these files exist:

```
/Users/bkyritz/Code/Jori/Open-Compute/data/fhir/STU6/
├── fhir.schema.json
├── valuesets.json
├── profiles-resources.json
├── profiles-types.json
└── search-parameters.json
```

They should already be there! If not, re-download your FHIR definitions.

### Want to Disable It?

If you need to go back to basic schema only:

```python
result = generate_fhir_from_journey(
    journey=journey,
    use_enhanced_context=False,  # Disable enhanced features
)
```

## 📚 Learn More

- **Full Documentation:** See `docs/ENHANCED_CONTEXT.md`
- **Example Code:** See `examples/enhanced_context_example.py`
- **Code Changes:** See `src/open_compute/utils/fhir_data_loader.py`

## ✨ Summary

**What you need to do:** Nothing! It's enabled by default.

**What you get:**

- Better coded values
- More complete resources
- Fewer validation errors
- Higher quality FHIR data

**Recommendation:** Keep enhanced context enabled (the default) for best results.

---

Questions? Check the full docs or run the example!
