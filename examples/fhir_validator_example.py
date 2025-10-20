#!/usr/bin/env python3
"""
Example usage of the FHIR validator using fhir.resources library.

This demonstrates how to validate FHIR resources against the FHIR specification.
"""

from open_compute.utils.fhir_validator import FHIRValidator, validate_fhir_resource


def example_1_valid_patient():
    """Example 1: Validate a simple valid Patient resource."""
    print("=" * 60)
    print("Example 1: Valid Patient Resource")
    print("=" * 60)

    patient = {
        "resourceType": "Patient",
        "id": "example",
        "name": [
            {
                "use": "official",
                "family": "Doe",
                "given": ["John", "Q"]
            }
        ],
        "gender": "male",
        "birthDate": "1974-12-25"
    }

    # Quick validation
    result = validate_fhir_resource(patient, version="R4")
    print(result)
    print()


def example_2_invalid_patient():
    """Example 2: Validate an invalid Patient resource (invalid gender code)."""
    print("=" * 60)
    print("Example 2: Invalid Patient Resource")
    print("=" * 60)

    patient = {
        "resourceType": "Patient",
        "id": "example",
        "name": [
            {
                "use": "official",
                "family": "Doe",
                "given": ["John"]
            }
        ],
        "gender": "invalid_gender",  # Invalid gender code
        "birthDate": "not-a-date"     # Invalid date format
    }

    validator = FHIRValidator(version="R4")
    result = validator.validate(patient)
    print(result)
    print()


def example_3_observation():
    """Example 3: Validate an Observation resource."""
    print("=" * 60)
    print("Example 3: Valid Observation Resource")
    print("=" * 60)

    observation = {
        "resourceType": "Observation",
        "id": "example",
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "15074-8",
                    "display": "Glucose [Moles/volume] in Blood"
                }
            ]
        },
        "subject": {
            "reference": "Patient/example"
        },
        "valueQuantity": {
            "value": 6.3,
            "unit": "mmol/l",
            "system": "http://unitsofmeasure.org",
            "code": "mmol/L"
        }
    }

    result = validate_fhir_resource(observation)
    print(result)
    print()


def example_4_bundle():
    """Example 4: Validate a Bundle with multiple resources."""
    print("=" * 60)
    print("Example 4: Bundle Validation")
    print("=" * 60)

    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient1",
                    "name": [{"family": "Smith", "given": ["Jane"]}],
                    "gender": "female"
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs1",
                    "status": "final",
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "15074-8"
                        }]
                    },
                    "subject": {"reference": "Patient/patient1"}
                }
            },
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient2",
                    "gender": "invalid"  # This will cause an error
                }
            }
        ]
    }

    validator = FHIRValidator(version="R4")
    result = validator.validate_bundle(bundle)
    print(result)
    print()


def example_5_missing_required_fields():
    """Example 5: Missing required fields."""
    print("=" * 60)
    print("Example 5: Missing Required Fields")
    print("=" * 60)

    observation = {
        "resourceType": "Observation",
        "id": "example"
        # Missing required 'status' and 'code' fields
    }

    result = validate_fhir_resource(observation)
    print(result)
    print()


def example_6_validate_from_json_string():
    """Example 6: Validate from JSON string."""
    print("=" * 60)
    print("Example 6: Validate from JSON String")
    print("=" * 60)

    patient_json = """
    {
        "resourceType": "Patient",
        "id": "example",
        "name": [
            {
                "use": "official",
                "family": "Chalmers",
                "given": ["Peter", "James"]
            }
        ],
        "gender": "male",
        "birthDate": "1974-12-25",
        "active": true
    }
    """

    result = validate_fhir_resource(patient_json)
    print(result)
    print()

    if result.is_valid:
        print(
            f"Validated resource type: {result.validated_resource.resource_type}")
        print(f"Patient ID: {result.validated_resource.id}")
        print(f"Patient name: {result.validated_resource.name[0].family}")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "FHIR Validator Examples" + " " * 25 + "║")
    print("║" + " " * 12 + "Using fhir.resources library" + " " * 18 + "║")
    print("╚" + "═" * 58 + "╝")
    print("\n")

    try:
        example_1_valid_patient()
        example_2_invalid_patient()
        example_3_observation()
        example_4_bundle()
        example_5_missing_required_fields()
        example_6_validate_from_json_string()

        print("=" * 60)
        print("All examples completed!")
        print("=" * 60)

    except ImportError as e:
        print("\n⚠️  Error: fhir.resources library not installed")
        print("\nPlease install it with:")
        print("  pip install fhir.resources")
        print(f"\nDetails: {e}")


if __name__ == "__main__":
    main()
