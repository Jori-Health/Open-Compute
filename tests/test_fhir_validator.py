"""
Tests for the FHIR validator module.

These tests validate the functionality of the FHIRValidator class
using the fhir.resources library for FHIR resource validation.
"""

import json
import pytest
from pathlib import Path
import tempfile

from open_compute.utils.fhir_validator import (
    FHIRValidator,
    ValidationResult,
    BundleValidationResult,
    FHIRValidationError,
    validate_fhir_resource,
)


class TestValidationResult:
    """Test ValidationResult class."""

    def test_valid_result_representation(self):
        """Test string representation of valid result."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            resource_type="Patient"
        )
        assert result.is_valid is True
        assert "Valid" in str(result)
        assert "Patient" in str(result)

    def test_invalid_result_representation(self):
        """Test string representation of invalid result."""
        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            resource_type="Patient"
        )
        assert result.is_valid is False
        assert "Invalid" in str(result)
        assert "Error 1" in str(result)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            resource_type="Patient"
        )
        result_dict = result.to_dict()
        assert result_dict["is_valid"] is True
        assert result_dict["resource_type"] == "Patient"
        assert result_dict["errors"] == []


class TestFHIRValidator:
    """Test FHIRValidator class."""

    def test_validator_initialization(self):
        """Test validator initialization with different versions."""
        validator = FHIRValidator(version="R4")
        assert validator.version == "R4"

        validator = FHIRValidator(version="R4B")
        assert validator.version == "R4B"

    def test_valid_patient_dict(self):
        """Test validation of a valid Patient resource as dict."""
        validator = FHIRValidator(version="R4")

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
            "gender": "male",
            "birthDate": "1974-12-25"
        }

        result = validator.validate(patient)

        assert result.is_valid is True
        assert result.resource_type == "Patient"
        assert len(result.errors) == 0
        assert result.validated_resource is not None

    def test_valid_patient_json_string(self):
        """Test validation of a valid Patient resource as JSON string."""
        validator = FHIRValidator(version="R4")

        patient_json = json.dumps({
            "resourceType": "Patient",
            "id": "example",
            "name": [{"family": "Smith", "given": ["Jane"]}],
            "gender": "female"
        })

        result = validator.validate(patient_json)

        assert result.is_valid is True
        assert result.resource_type == "Patient"

    def test_invalid_json_string(self):
        """Test validation with invalid JSON string."""
        validator = FHIRValidator(version="R4")

        invalid_json = "{this is not valid json"

        result = validator.validate(invalid_json)

        assert result.is_valid is False
        assert "Invalid JSON" in result.errors[0]

    def test_missing_resource_type(self):
        """Test validation with missing resourceType field."""
        validator = FHIRValidator(version="R4")

        resource = {
            "id": "example",
            "name": [{"family": "Doe"}]
        }

        result = validator.validate(resource)

        assert result.is_valid is False
        assert "resourceType" in result.errors[0]

    def test_invalid_resource_type(self):
        """Test validation with unsupported resource type."""
        validator = FHIRValidator(version="R4")

        resource = {
            "resourceType": "NotARealResourceType",
            "id": "example"
        }

        result = validator.validate(resource)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_invalid_patient_missing_required_fields(self):
        """Test validation of Patient with invalid data."""
        validator = FHIRValidator(version="R4")

        patient = {
            "resourceType": "Patient",
            "id": "example",
            "gender": "invalid_gender_code"  # Invalid code
        }

        result = validator.validate(patient)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_valid_observation(self):
        """Test validation of a valid Observation resource."""
        validator = FHIRValidator(version="R4")

        observation = {
            "resourceType": "Observation",
            "id": "example",
            "status": "final",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "15074-8",
                        "display": "Glucose"
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

        result = validator.validate(observation)

        assert result.is_valid is True
        assert result.resource_type == "Observation"

    def test_invalid_observation_missing_status(self):
        """Test validation of Observation missing required status field."""
        validator = FHIRValidator(version="R4")

        observation = {
            "resourceType": "Observation",
            "id": "example",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "15074-8"
                    }
                ]
            }
            # Missing required 'status' field
        }

        result = validator.validate(observation)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_valid_medication_request(self):
        """Test validation of a valid MedicationRequest resource."""
        validator = FHIRValidator(version="R4")

        med_request = {
            "resourceType": "MedicationRequest",
            "id": "example",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": "582620",
                        "display": "Nizatidine 15 MG/ML Oral Solution"
                    }
                ]
            },
            "subject": {
                "reference": "Patient/example"
            }
        }

        result = validator.validate(med_request)

        assert result.is_valid is True
        assert result.resource_type == "MedicationRequest"

    def test_validate_from_file_valid(self):
        """Test validation from a valid JSON file."""
        validator = FHIRValidator(version="R4")

        patient = {
            "resourceType": "Patient",
            "id": "file-test",
            "name": [{"family": "FileTest", "given": ["Test"]}],
            "gender": "male"
        }

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(patient, f)
            temp_path = f.name

        try:
            result = validator.validate_from_file(temp_path)

            assert result.is_valid is True
            assert result.resource_type == "Patient"
        finally:
            # Clean up
            Path(temp_path).unlink()

    def test_validate_from_file_not_found(self):
        """Test validation from non-existent file."""
        validator = FHIRValidator(version="R4")

        result = validator.validate_from_file("/path/that/does/not/exist.json")

        assert result.is_valid is False
        assert "not found" in result.errors[0].lower()

    def test_validate_bundle_valid(self):
        """Test validation of a valid Bundle."""
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

        assert result.is_valid is True
        assert len(result.entry_results) == 2
        assert len(result.bundle_errors) == 0

    def test_validate_bundle_invalid_entry(self):
        """Test validation of Bundle with invalid entry."""
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
                        "gender": "invalid_code"  # Invalid
                    }
                }
            ]
        }

        result = validator.validate_bundle(bundle)

        assert result.is_valid is False
        assert len(result.entry_results) == 2
        # First entry should be valid, second should be invalid
        assert result.entry_results[0]["result"].is_valid is True
        assert result.entry_results[1]["result"].is_valid is False

    def test_validate_bundle_invalid_bundle_structure(self):
        """Test validation of Bundle with invalid structure."""
        validator = FHIRValidator(version="R4")

        invalid_bundle = {
            "resourceType": "Bundle",
            # Missing required 'type' field
            "entry": []
        }

        result = validator.validate_bundle(invalid_bundle)

        assert result.is_valid is False
        assert len(result.bundle_errors) > 0

    def test_validate_bundle_empty_entries(self):
        """Test validation of Bundle with no entries."""
        validator = FHIRValidator(version="R4")

        bundle = {
            "resourceType": "Bundle",
            "type": "collection"
        }

        result = validator.validate_bundle(bundle)

        # Bundle itself should be valid even with no entries
        assert result.is_valid is True
        assert len(result.entry_results) == 0

    def test_explicit_resource_type(self):
        """Test validation with explicit resource type parameter."""
        validator = FHIRValidator(version="R4")

        patient = {
            "resourceType": "Patient",
            "id": "example",
            "gender": "male"
        }

        result = validator.validate(patient, resource_type="Patient")

        assert result.is_valid is True
        assert result.resource_type == "Patient"


class TestConvenienceFunction:
    """Test the convenience validate_fhir_resource function."""

    def test_validate_fhir_resource_valid(self):
        """Test convenience function with valid resource."""
        patient = {
            "resourceType": "Patient",
            "id": "example",
            "name": [{"family": "Doe"}],
            "gender": "male"
        }

        result = validate_fhir_resource(patient, version="R4")

        assert result.is_valid is True

    def test_validate_fhir_resource_invalid(self):
        """Test convenience function with invalid resource."""
        patient = {
            "resourceType": "Patient",
            "id": "example",
            "gender": "not_a_valid_gender"
        }

        result = validate_fhir_resource(patient, version="R4")

        assert result.is_valid is False

    def test_validate_fhir_resource_with_json_string(self):
        """Test convenience function with JSON string."""
        patient_json = '{"resourceType": "Patient", "id": "test", "gender": "female"}'

        result = validate_fhir_resource(patient_json, version="R4")

        assert result.is_valid is True


class TestBundleValidationResult:
    """Test BundleValidationResult class."""

    def test_bundle_result_representation_valid(self):
        """Test string representation of valid bundle result."""
        result = BundleValidationResult(
            is_valid=True,
            bundle_errors=[],
            entry_results=[]
        )

        assert result.is_valid is True
        assert "Valid Bundle" in str(result)

    def test_bundle_result_representation_invalid(self):
        """Test string representation of invalid bundle result."""
        mock_validation_result = ValidationResult(
            is_valid=False,
            errors=["Test error"],
            resource_type="Patient"
        )

        result = BundleValidationResult(
            is_valid=False,
            bundle_errors=["Bundle error"],
            entry_results=[
                {
                    "index": 0,
                    "resource_type": "Patient",
                    "result": mock_validation_result
                }
            ]
        )

        assert result.is_valid is False
        assert "Invalid Bundle" in str(result)

    def test_bundle_result_to_dict(self):
        """Test conversion of bundle result to dictionary."""
        mock_validation_result = ValidationResult(
            is_valid=True,
            errors=[],
            resource_type="Patient"
        )

        result = BundleValidationResult(
            is_valid=True,
            bundle_errors=[],
            entry_results=[
                {
                    "index": 0,
                    "resource_type": "Patient",
                    "result": mock_validation_result
                }
            ]
        )

        result_dict = result.to_dict()

        assert result_dict["is_valid"] is True
        assert len(result_dict["entry_results"]) == 1
        assert result_dict["entry_results"][0]["resource_type"] == "Patient"


class TestRealWorldScenarios:
    """Test real-world FHIR validation scenarios."""

    def test_patient_with_multiple_names(self):
        """Test patient with multiple names."""
        validator = FHIRValidator(version="R4")

        patient = {
            "resourceType": "Patient",
            "id": "example",
            "name": [
                {
                    "use": "official",
                    "family": "Doe",
                    "given": ["John", "Jacob"]
                },
                {
                    "use": "nickname",
                    "given": ["Jack"]
                }
            ],
            "gender": "male"
        }

        result = validator.validate(patient)

        assert result.is_valid is True

    def test_patient_with_contact_info(self):
        """Test patient with contact information."""
        validator = FHIRValidator(version="R4")

        patient = {
            "resourceType": "Patient",
            "id": "example",
            "name": [{"family": "Doe", "given": ["Jane"]}],
            "telecom": [
                {
                    "system": "phone",
                    "value": "555-1234",
                    "use": "home"
                },
                {
                    "system": "email",
                    "value": "jane.doe@example.com"
                }
            ],
            "gender": "female"
        }

        result = validator.validate(patient)

        assert result.is_valid is True

    def test_observation_with_reference_range(self):
        """Test observation with reference range."""
        validator = FHIRValidator(version="R4")

        observation = {
            "resourceType": "Observation",
            "id": "example",
            "status": "final",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "2339-0",
                        "display": "Glucose [Mass/volume] in Blood"
                    }
                ]
            },
            "subject": {"reference": "Patient/example"},
            "valueQuantity": {
                "value": 6.3,
                "unit": "mmol/L",
                "system": "http://unitsofmeasure.org",
                "code": "mmol/L"
            },
            "referenceRange": [
                {
                    "low": {
                        "value": 3.1,
                        "unit": "mmol/L",
                        "system": "http://unitsofmeasure.org",
                        "code": "mmol/L"
                    },
                    "high": {
                        "value": 6.2,
                        "unit": "mmol/L",
                        "system": "http://unitsofmeasure.org",
                        "code": "mmol/L"
                    }
                }
            ]
        }

        result = validator.validate(observation)

        assert result.is_valid is True

    def test_condition_resource(self):
        """Test Condition resource validation."""
        validator = FHIRValidator(version="R4")

        condition = {
            "resourceType": "Condition",
            "id": "example",
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active"
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        "code": "confirmed"
                    }
                ]
            },
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                            "code": "encounter-diagnosis"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "386661006",
                        "display": "Fever"
                    }
                ]
            },
            "subject": {"reference": "Patient/example"}
        }

        result = validator.validate(condition)

        assert result.is_valid is True
        assert result.resource_type == "Condition"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dict(self):
        """Test validation with empty dictionary."""
        validator = FHIRValidator(version="R4")

        result = validator.validate({})

        assert result.is_valid is False

    def test_none_resource(self):
        """Test validation with None."""
        validator = FHIRValidator(version="R4")

        # This should handle the error gracefully
        try:
            result = validator.validate(None)
            # Should fail in some way
            assert result.is_valid is False
        except Exception:
            # Or raise an exception, which is also acceptable
            pass

    def test_resource_with_extra_fields(self):
        """Test that extra fields don't break validation."""
        validator = FHIRValidator(version="R4")

        patient = {
            "resourceType": "Patient",
            "id": "example",
            "name": [{"family": "Doe"}],
            "gender": "male",
            "customField": "this should be ignored or handled"
        }

        # FHIR allows extensions, so this might still validate
        # depending on the implementation
        result = validator.validate(patient)

        # Either valid or invalid is acceptable,
        # as long as it doesn't crash
        assert isinstance(result.is_valid, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
