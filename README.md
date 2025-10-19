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
