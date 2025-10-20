"""
Inspect the actual fields expected by fhir.resources models.
"""

from fhir.resources.encounter import Encounter
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.procedure import Procedure
from pydantic import BaseModel
import inspect

print("="*60)
print("ENCOUNTER FIELD INSPECTION")
print("="*60)
print(
    f"Encounter.class type hint: {Encounter.model_fields.get('class_fhir', {}).annotation if hasattr(Encounter, 'model_fields') else 'Not found'}")

# Check for alternative field names
for field_name in dir(Encounter):
    if 'class' in field_name.lower():
        print(f"Found field: {field_name}")

print("\n" + "="*60)
print("MEDICATION REQUEST FIELD INSPECTION")
print("="*60)

for field_name in dir(MedicationRequest):
    if 'medic' in field_name.lower():
        print(f"Found field: {field_name}")

print("\n" + "="*60)
print("PROCEDURE FIELD INSPECTION")
print("="*60)

for field_name in dir(Procedure):
    if 'perform' in field_name.lower():
        print(f"Found field: {field_name}")

# Try to get model schema
print("\n" + "="*60)
print("ENCOUNTER MODEL SCHEMA")
print("="*60)
if hasattr(Encounter, 'model_fields'):
    for field_name, field_info in Encounter.model_fields.items():
        if 'class' in field_name or 'period' in field_name:
            print(f"{field_name}: {field_info}")

print("\n" + "="*60)
print("MEDICATION REQUEST MODEL SCHEMA")
print("="*60)
if hasattr(MedicationRequest, 'model_fields'):
    for field_name, field_info in MedicationRequest.model_fields.items():
        if 'medic' in field_name:
            print(
                f"{field_name}: {field_info.annotation if hasattr(field_info, 'annotation') else field_info}")

print("\n" + "="*60)
print("PROCEDURE MODEL SCHEMA")
print("="*60)
if hasattr(Procedure, 'model_fields'):
    for field_name, field_info in Procedure.model_fields.items():
        if 'perform' in field_name:
            print(
                f"{field_name}: {field_info.annotation if hasattr(field_info, 'annotation') else field_info}")
