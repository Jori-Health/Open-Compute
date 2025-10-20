"""
FHIR Validator module using fhir.resources library.

This module provides functionality to validate FHIR resources against
the FHIR specification using the fhir.resources library.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Union, Optional, Literal
from pathlib import Path

try:
    from fhir.resources import get_fhir_model_class
    from fhir.resources.bundle import Bundle
except ImportError:
    raise ImportError(
        "fhir.resources is required for FHIR validation. "
        "Install it with: pip install fhir.resources"
    )


class FHIRValidationError(Exception):
    """Custom exception for FHIR validation errors."""
    pass


@dataclass
class ValidationResult:
    """Result of a FHIR resource validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    resource_type: Optional[str] = None
    validated_resource: Optional[Any] = None

    def __str__(self) -> str:
        if self.is_valid:
            return f"Valid {self.resource_type} resource"
        else:
            error_str = "\n".join(f"  - {err}" for err in self.errors)
            return f"Invalid {self.resource_type or 'FHIR'} resource:\n{error_str}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "resource_type": self.resource_type,
            "has_validated_resource": self.validated_resource is not None,
        }


@dataclass
class BundleValidationResult:
    """Result of a FHIR Bundle validation."""
    is_valid: bool
    bundle_errors: List[str] = field(default_factory=list)
    entry_results: List[Dict[str, Any]] = field(default_factory=list)

    def __str__(self) -> str:
        if self.is_valid:
            return f"Valid Bundle with {len(self.entry_results)} entries"
        else:
            error_lines = []
            if self.bundle_errors:
                error_lines.append("Bundle errors:")
                error_lines.extend(f"  - {err}" for err in self.bundle_errors)

            invalid_entries = [
                entry for entry in self.entry_results
                if not entry["result"].is_valid
            ]
            if invalid_entries:
                error_lines.append(f"Invalid entries: {len(invalid_entries)}")
                for entry in invalid_entries:
                    error_lines.append(
                        f"  Entry {entry['index']} ({entry['resource_type']}): "
                        f"{', '.join(entry['result'].errors)}"
                    )

            return "Invalid Bundle:\n" + "\n".join(error_lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary."""
        return {
            "is_valid": self.is_valid,
            "bundle_errors": self.bundle_errors,
            "entry_results": [
                {
                    "index": entry["index"],
                    "resource_type": entry["resource_type"],
                    "result": entry["result"].to_dict(),
                }
                for entry in self.entry_results
            ],
        }


class FHIRValidator:
    """
    Validator for FHIR resources using the fhir.resources library.

    Attributes:
        version: FHIR version to validate against (R4, R4B, R5, STU3)
    """

    def __init__(self, version: Literal["R4", "R4B", "R5", "STU3"] = "R4"):
        """
        Initialize the FHIR validator.

        Args:
            version: FHIR version to validate against
        """
        self.version = version

    def validate(
        self,
        resource: Union[Dict[str, Any], str],
        resource_type: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a FHIR resource.

        Args:
            resource: FHIR resource as dict or JSON string
            resource_type: Optional resource type to validate against

        Returns:
            ValidationResult with validation status and any errors
        """
        errors = []
        validated_resource = None

        try:
            # Parse JSON string if needed
            if isinstance(resource, str):
                try:
                    resource = json.loads(resource)
                except json.JSONDecodeError as e:
                    return ValidationResult(
                        is_valid=False,
                        errors=[f"Invalid JSON: {str(e)}"],
                        resource_type=resource_type,
                    )

            # Check for resourceType
            if not isinstance(resource, dict):
                return ValidationResult(
                    is_valid=False,
                    errors=["Resource must be a dictionary"],
                    resource_type=resource_type,
                )

            detected_type = resource.get("resourceType")
            if not detected_type:
                return ValidationResult(
                    is_valid=False,
                    errors=["Missing required field: resourceType"],
                    resource_type=resource_type,
                )

            # Use detected type if not explicitly provided
            if not resource_type:
                resource_type = detected_type

            # Validate using fhir.resources
            try:
                # Get the appropriate FHIR model class
                model_class = get_fhir_model_class(resource_type)

                # Parse and validate the resource using model_validate (Pydantic v2)
                validated_resource = model_class.model_validate(resource)

                # If we got here, validation passed
                return ValidationResult(
                    is_valid=True,
                    errors=[],
                    resource_type=resource_type,
                    validated_resource=validated_resource,
                )

            except Exception as e:
                # Collect validation errors
                error_message = str(e)
                errors.append(error_message)

        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")

        return ValidationResult(
            is_valid=False,
            errors=errors,
            resource_type=resource_type,
        )

    def validate_from_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """
        Validate a FHIR resource from a JSON file.

        Args:
            file_path: Path to JSON file containing FHIR resource

        Returns:
            ValidationResult with validation status and any errors
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return ValidationResult(
                    is_valid=False,
                    errors=[f"File not found: {file_path}"],
                )

            with open(path, "r") as f:
                resource = json.load(f)

            return self.validate(resource)

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error reading file: {str(e)}"],
            )

    def validate_bundle(
        self, bundle: Union[Dict[str, Any], str]
    ) -> BundleValidationResult:
        """
        Validate a FHIR Bundle and all its entries.

        Args:
            bundle: FHIR Bundle as dict or JSON string

        Returns:
            BundleValidationResult with validation status for bundle and entries
        """
        bundle_errors = []
        entry_results = []

        try:
            # Parse JSON string if needed
            if isinstance(bundle, str):
                try:
                    bundle = json.loads(bundle)
                except json.JSONDecodeError as e:
                    return BundleValidationResult(
                        is_valid=False,
                        bundle_errors=[f"Invalid JSON: {str(e)}"],
                    )

            # Validate the Bundle itself
            bundle_validation = self.validate(bundle, resource_type="Bundle")
            if not bundle_validation.is_valid:
                bundle_errors.extend(bundle_validation.errors)

            # Validate each entry
            entries = bundle.get("entry", [])
            for idx, entry in enumerate(entries):
                resource = entry.get("resource", {})
                resource_type = resource.get("resourceType", "Unknown")

                entry_validation = self.validate(resource)
                entry_results.append(
                    {
                        "index": idx,
                        "resource_type": resource_type,
                        "result": entry_validation,
                    }
                )

            # Determine overall validity
            is_valid = (
                len(bundle_errors) == 0
                and all(entry["result"].is_valid for entry in entry_results)
            )

            return BundleValidationResult(
                is_valid=is_valid,
                bundle_errors=bundle_errors,
                entry_results=entry_results,
            )

        except Exception as e:
            return BundleValidationResult(
                is_valid=False,
                bundle_errors=[f"Unexpected error: {str(e)}"],
            )


def validate_fhir_resource(
    resource: Union[Dict[str, Any], str],
    version: Literal["R4", "R4B", "R5", "STU3"] = "R4",
    resource_type: Optional[str] = None,
) -> ValidationResult:
    """
    Convenience function to validate a FHIR resource.

    Args:
        resource: FHIR resource as dict or JSON string
        version: FHIR version to validate against
        resource_type: Optional resource type to validate against

    Returns:
        ValidationResult with validation status and any errors
    """
    validator = FHIRValidator(version=version)
    return validator.validate(resource, resource_type=resource_type)
