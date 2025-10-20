#!/usr/bin/env python3
"""
Quick test script for FHIR validator.

This script performs basic smoke tests to verify the validator is working.
Run this before running the full test suite.
"""

import sys
import json


def test_imports():
    """Test that all required imports work."""
    print("Testing imports...")
    try:
        from open_compute.utils.fhir_validator import (
            FHIRValidator,
            ValidationResult,
            validate_fhir_resource,
        )
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        print("\nPlease install dependencies:")
        print("  pip install fhir.resources")
        return False


def test_valid_patient():
    """Test validation of a valid patient."""
    print("\nTesting valid Patient resource...")
    from open_compute.utils.fhir_validator import validate_fhir_resource

    patient = {
        "resourceType": "Patient",
        "id": "example",
        "name": [{"family": "Doe", "given": ["John"]}],
        "gender": "male",
        "birthDate": "1974-12-25"
    }

    result = validate_fhir_resource(patient, version="R4")

    if result.is_valid:
        print("✓ Valid patient validated successfully")
        print(f"  Resource type: {result.resource_type}")
        return True
    else:
        print(f"✗ Unexpected validation failure: {result.errors}")
        return False


def test_invalid_patient():
    """Test that invalid patient is rejected."""
    print("\nTesting invalid Patient resource...")
    from open_compute.utils.fhir_validator import validate_fhir_resource

    invalid_patient = {
        "resourceType": "Patient",
        "id": "example",
        "gender": "invalid_gender_code"
    }

    result = validate_fhir_resource(invalid_patient, version="R4")

    if not result.is_valid:
        print("✓ Invalid patient correctly rejected")
        print(f"  Errors detected: {len(result.errors)}")
        return True
    else:
        print("✗ Invalid patient was incorrectly validated as valid")
        return False


def test_observation():
    """Test validation of an observation."""
    print("\nTesting Observation resource...")
    from open_compute.utils.fhir_validator import FHIRValidator

    validator = FHIRValidator(version="R4")

    observation = {
        "resourceType": "Observation",
        "id": "example",
        "status": "final",
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "15074-8",
                "display": "Glucose"
            }]
        },
        "subject": {"reference": "Patient/example"},
        "valueQuantity": {
            "value": 6.3,
            "unit": "mmol/l",
            "system": "http://unitsofmeasure.org",
            "code": "mmol/L"
        }
    }

    result = validator.validate(observation)

    if result.is_valid:
        print("✓ Observation validated successfully")
        return True
    else:
        print(f"✗ Observation validation failed: {result.errors}")
        return False


def test_bundle():
    """Test bundle validation."""
    print("\nTesting Bundle validation...")
    from open_compute.utils.fhir_validator import FHIRValidator

    validator = FHIRValidator(version="R4")

    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient1",
                    "name": [{"family": "Smith"}],
                    "gender": "female"
                }
            },
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient2",
                    "name": [{"family": "Jones"}],
                    "gender": "male"
                }
            }
        ]
    }

    result = validator.validate_bundle(bundle)

    if result.is_valid:
        print(
            f"✓ Bundle with {len(result.entry_results)} entries validated successfully")
        return True
    else:
        print(f"✗ Bundle validation failed")
        print(f"  Bundle errors: {result.bundle_errors}")
        return False


def test_json_string():
    """Test validation from JSON string."""
    print("\nTesting JSON string validation...")
    from open_compute.utils.fhir_validator import validate_fhir_resource

    patient_json = json.dumps({
        "resourceType": "Patient",
        "id": "example",
        "name": [{"family": "TestUser"}],
        "gender": "other"
    })

    result = validate_fhir_resource(patient_json, version="R4")

    if result.is_valid:
        print("✓ JSON string validated successfully")
        return True
    else:
        print(f"✗ JSON string validation failed: {result.errors}")
        return False


def main():
    """Run all quick tests."""
    print("=" * 60)
    print("FHIR Validator - Quick Smoke Tests")
    print("=" * 60)

    tests = [
        test_imports,
        test_valid_patient,
        test_invalid_patient,
        test_observation,
        test_bundle,
        test_json_string,
    ]

    results = []

    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✅ All tests passed! The validator is working correctly.")
        print("\nNext steps:")
        print("  1. Run the full test suite:")
        print("     pytest tests/test_fhir_validator.py -v")
        print("  2. Run the examples:")
        print("     python examples/fhir_validator_example.py")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("\nTroubleshooting:")
        print("  1. Make sure fhir.resources is installed:")
        print("     pip install fhir.resources")
        print("  2. Make sure the package is installed:")
        print("     pip install -e .")
        print("  3. Check the error messages above for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
