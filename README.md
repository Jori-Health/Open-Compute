# open-compute

Utilities by Jori Health. Provides:

- `jori_health.ai`: simple AI facade
- `open_compute`: conversion agents between FHIR and patient journey

## Requirements

- Python 3.9+

## Install

### Option A: Install directly from GitHub

```bash
pip install git+https://github.com/jori-health/open-compute.git
```

### Option B: Install from a local clone (editable)

```bash
git clone https://github.com/jori-health/open-compute.git
cd open-compute
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

> Once published to PyPI you will be able to run:

```bash
pip install open-compute
```

## Quickstart

### AI facade: default instance

```python
from jori_health.ai import joriai

print(joriai.ask("hello"))            # -> "world"
print(joriai.ask("How are you?"))     # -> "Echo: How are you?"
```

### Or create your own instance

### Open Compute: FHIR <-> Patient Journey

#### Basic FHIR/Journey Conversion

```python
from open_compute import (
    FHIRPatientData,
    PatientJourney,
    JourneyStage,
    fhir_to_journey,
    journey_to_fhir,
)

# FHIR -> Journey
bundle = FHIRPatientData(entries=[
    {"resource": {"resourceType": "Patient", "id": "pat-123"}},
    {"resource": {"resourceType": "Encounter", "status": "finished", "reasonCode": [{"text": "Annual physical"}]}},
    {"resource": {"resourceType": "Observation", "code": {"text": "Blood Pressure"}, "valueString": "120/80"}},
])

journey = fhir_to_journey(bundle)
print(journey.patient_id)  # "pat-123"
print([s.name for s in journey.stages])  # ["Registration", "Encounter", "Observation"]

# Journey -> FHIR
journey2 = PatientJourney(
    patient_id="pat-123",
    stages=[
        JourneyStage(name="Encounter", description="Follow-up", metadata={"status": "in-progress"}),
        JourneyStage(name="Observation", description="Heart Rate", metadata={"value": "72 bpm"}),
    ],
)

bundle2 = journey_to_fhir(journey2)
print(len(bundle2.entries))  # 3
```

#### AI-Powered FHIR Generation

Generate comprehensive FHIR resources from patient journeys using AI:

```python
from open_compute import (
    PatientJourney,
    JourneyStage,
    generate_fhir_from_journey,
)

# Create a patient journey
journey = PatientJourney(
    patient_id="patient-123",
    summary="58 year old male with chest pain diagnosed with acute MI",
    stages=[
        JourneyStage(
            name="Triage",
            description="Initial assessment - chest pain, elevated BP",
            metadata={"vital_signs": {"blood_pressure": "150/95 mmHg"}},
        ),
        JourneyStage(
            name="Diagnosis",
            description="Diagnosed with acute myocardial infarction",
            metadata={"condition": "Acute MI", "icd10_code": "I21.9"},
        ),
    ],
)

# Generate FHIR resources using AI
result = generate_fhir_from_journey(
    journey=journey,
    patient_context="58 year old male with history of hypertension",
    model="gpt-5-mini",
    auto_save=True,  # Saves to output/firstname_lastname/
)

print(f"Generated {len(result.generated_resources)} resources")
# Files automatically saved to: output/firstname_lastname/
#   - patient_bundle.json: Complete FHIR Bundle
#   - bulk_fhir.jsonl: All resources in JSONL format
#   - README.txt: Generation summary
```

See [examples/ai_journey_to_fhir_example.py](examples/ai_journey_to_fhir_example.py) for more detailed examples.

```python
from jori_health.ai import JoriAI

ai = JoriAI()
print(ai.ask("hello"))  # -> "world"
```

## Testing locally (optional)

```bash
pytest -q
```

## License

MIT
