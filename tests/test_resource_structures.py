"""
Test script to understand the exact FHIR resource structures expected by fhir.resources library.
"""

from fhir.resources.encounter import Encounter
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.procedure import Procedure
from fhir.resources.location import Location
from fhir.resources.organization import Organization
import json

# Test Encounter structure
print("="*60)
print("ENCOUNTER TEST")
print("="*60)

# Try with class as a list
encounter_dict = {
    "resourceType": "Encounter",
    "id": "test-encounter",
    "status": "finished",
    "class": [
        {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "EMER",
            "display": "emergency"
        }
    ],
    "subject": {
        "reference": "Patient/test-patient"
    }
}

try:
    encounter = Encounter.model_validate(encounter_dict)
    print("✅ Encounter with class as list: SUCCESS")
    print(json.dumps(encounter.model_dump(exclude_none=True), indent=2))
except Exception as e:
    print(f"❌ Encounter with class as list: FAILED - {e}")

# Try with class as single Coding
encounter_dict2 = {
    "resourceType": "Encounter",
    "id": "test-encounter",
    "status": "finished",
    "class": {
        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
        "code": "EMER",
        "display": "emergency"
    },
    "subject": {
        "reference": "Patient/test-patient"
    }
}

try:
    encounter = Encounter.model_validate(encounter_dict2)
    print("\n✅ Encounter with class as single Coding: SUCCESS")
    print(json.dumps(encounter.model_dump(exclude_none=True), indent=2))
except Exception as e:
    print(f"\n❌ Encounter with class as single Coding: FAILED - {e}")

# Test MedicationRequest structure
print("\n" + "="*60)
print("MEDICATION REQUEST TEST")
print("="*60)

med_req_dict = {
    "resourceType": "MedicationRequest",
    "id": "test-med",
    "status": "active",
    "intent": "order",
    "medicationCodeableConcept": {
        "text": "Aspirin 325mg"
    },
    "subject": {
        "reference": "Patient/test-patient"
    }
}

try:
    med_req = MedicationRequest.model_validate(med_req_dict)
    print("✅ MedicationRequest: SUCCESS")
    print(json.dumps(med_req.model_dump(exclude_none=True), indent=2))
except Exception as e:
    print(f"❌ MedicationRequest: FAILED - {e}")

# Test Procedure structure
print("\n" + "="*60)
print("PROCEDURE TEST")
print("="*60)

procedure_dict = {
    "resourceType": "Procedure",
    "id": "test-procedure",
    "status": "completed",
    "code": {
        "text": "Cardiac catheterization"
    },
    "subject": {
        "reference": "Patient/test-patient"
    },
    "performedDateTime": "2024-01-15T12:00:00Z"
}

try:
    procedure = Procedure.model_validate(procedure_dict)
    print("✅ Procedure with performedDateTime: SUCCESS")
    print(json.dumps(procedure.model_dump(exclude_none=True), indent=2))
except Exception as e:
    print(f"❌ Procedure with performedDateTime: FAILED - {e}")

# Test Location structure
print("\n" + "="*60)
print("LOCATION TEST")
print("="*60)

location_dict = {
    "resourceType": "Location",
    "id": "test-location",
    "status": "active",
    "name": "Emergency Department"
}

try:
    location = Location.model_validate(location_dict)
    print("✅ Location (minimal): SUCCESS")
    print(json.dumps(location.model_dump(exclude_none=True), indent=2))
except Exception as e:
    print(f"❌ Location (minimal): FAILED - {e}")

# Test Organization structure
print("\n" + "="*60)
print("ORGANIZATION TEST")
print("="*60)

org_dict = {
    "resourceType": "Organization",
    "id": "test-org",
    "active": True,
    "name": "Sample Hospital"
}

try:
    org = Organization.model_validate(org_dict)
    print("✅ Organization (minimal): SUCCESS")
    print(json.dumps(org.model_dump(exclude_none=True), indent=2))
except Exception as e:
    print(f"❌ Organization (minimal): FAILED - {e}")

print("\n" + "="*60)
print("TESTS COMPLETE")
print("="*60)
