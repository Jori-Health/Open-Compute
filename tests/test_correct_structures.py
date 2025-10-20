"""
Test the CORRECT structures based on field inspection.
"""

from fhir.resources.encounter import Encounter
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.procedure import Procedure
import json

print("="*60)
print("ENCOUNTER TEST - CodeableConcept List")
print("="*60)

# class should be a LIST of CodeableConcept
encounter_dict = {
    "resourceType": "Encounter",
    "id": "test-encounter",
    "status": "finished",
    "class": [
        {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "EMER",
                "display": "emergency"
            }]
        }
    ],
    "subject": {
        "reference": "Patient/test-patient"
    }
}

try:
    encounter = Encounter.model_validate(encounter_dict)
    print("✅ Encounter: SUCCESS")
    print(json.dumps(encounter.model_dump(
        exclude_none=True, by_alias=True), indent=2))
except Exception as e:
    print(f"❌ Encounter: FAILED - {e}")

print("\n" + "="*60)
print("MEDICATION REQUEST TEST - CodeableReference")
print("="*60)

# medication should be a CodeableReference
med_req_dict = {
    "resourceType": "MedicationRequest",
    "id": "test-med",
    "status": "active",
    "intent": "order",
    "medication": {
        "concept": {
            "text": "Aspirin 325mg"
        }
    },
    "subject": {
        "reference": "Patient/test-patient"
    }
}

try:
    med_req = MedicationRequest.model_validate(med_req_dict)
    print("✅ MedicationRequest: SUCCESS")
    print(json.dumps(med_req.model_dump(exclude_none=True, by_alias=True), indent=2))
except Exception as e:
    print(f"❌ MedicationRequest: FAILED - {e}")

print("\n" + "="*60)
print("PROCEDURE TEST - Check performed field")
print("="*60)

# Let's check what the performed field looks like
if hasattr(Procedure, 'model_fields'):
    for field_name, field_info in Procedure.model_fields.items():
        if 'perform' in field_name and 'performer' not in field_name:
            print(f"{field_name}: {field_info}")

# Try with occurred field instead
procedure_dict1 = {
    "resourceType": "Procedure",
    "id": "test-procedure",
    "status": "completed",
    "code": {
        "text": "Cardiac catheterization"
    },
    "subject": {
        "reference": "Patient/test-patient"
    }
}

try:
    procedure = Procedure.model_validate(procedure_dict1)
    print("\n✅ Procedure (minimal): SUCCESS")
    print(json.dumps(procedure.model_dump(
        exclude_none=True, by_alias=True), indent=2))
except Exception as e:
    print(f"\n❌ Procedure (minimal): FAILED - {e}")
