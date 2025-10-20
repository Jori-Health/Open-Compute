"""
FHIR Schema Loader utility.

This module loads and extracts relevant FHIR schema definitions
to provide context for AI-powered FHIR resource generation.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from functools import lru_cache


class FHIRSchemaLoader:
    """Loads and extracts FHIR schema definitions."""

    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize the FHIR schema loader.

        Args:
            schema_path: Path to fhir.schema.json file. If None, looks in common locations.
        """
        self.schema_path = schema_path
        self.schema = None
        self._load_schema()

    def _load_schema(self):
        """Load the FHIR schema from file."""
        if self.schema_path:
            schema_file = Path(self.schema_path)
        else:
            # Try common locations
            possible_paths = [
                # Project data directory
                Path(__file__).parent.parent.parent.parent /
                "data" / "fhir" / "STU6" / "fhir.schema.json",
                # Desktop location
                Path.home() / "Desktop" / "definitions.json" / "fhir.schema.json",
                # Project root
                Path(__file__).parent.parent.parent.parent / "fhir.schema.json",
                # Current working directory
                Path.cwd() / "fhir.schema.json",
                Path.cwd() / "data" / "fhir" / "STU6" / "fhir.schema.json",
            ]

            schema_file = None
            for path in possible_paths:
                if path.exists():
                    schema_file = path
                    break

        if schema_file and schema_file.exists():
            try:
                with open(schema_file, 'r') as f:
                    self.schema = json.load(f)
                print(f"✓ Loaded FHIR schema from: {schema_file}")
            except Exception as e:
                print(f"Warning: Could not load FHIR schema: {e}")
                self.schema = None
        else:
            print(
                "Warning: FHIR schema file not found. Generation will proceed without schema context.")
            self.schema = None

    @lru_cache(maxsize=128)
    def get_resource_definition(self, resource_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema definition for a specific FHIR resource type.

        Args:
            resource_type: The FHIR resource type (e.g., "Patient", "Observation")

        Returns:
            Schema definition dict or None if not found
        """
        if not self.schema or "definitions" not in self.schema:
            return None

        definitions = self.schema.get("definitions", {})
        return definitions.get(resource_type)

    def get_resource_properties(self, resource_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the properties definition for a FHIR resource.

        Args:
            resource_type: The FHIR resource type

        Returns:
            Properties dict or None if not found
        """
        definition = self.get_resource_definition(resource_type)
        if definition:
            return definition.get("properties", {})
        return None

    def get_required_fields(self, resource_type: str) -> List[str]:
        """
        Get the list of required fields for a FHIR resource.

        Args:
            resource_type: The FHIR resource type

        Returns:
            List of required field names
        """
        definition = self.get_resource_definition(resource_type)
        if definition:
            return definition.get("required", [])
        return []

    def format_schema_for_prompt(self, resource_type: str, max_properties: int = 20) -> str:
        """
        Format schema information for inclusion in AI prompts.

        Args:
            resource_type: The FHIR resource type
            max_properties: Maximum number of properties to include (for brevity)

        Returns:
            Formatted string with schema information
        """
        if not self.schema:
            return "Note: FHIR schema not loaded. Please ensure proper FHIR structure."

        definition = self.get_resource_definition(resource_type)
        if not definition:
            return f"Note: Schema definition for {resource_type} not found."

        lines = [f"FHIR {resource_type} Schema:"]
        lines.append("")

        # Description
        description = definition.get("description", "")
        if description:
            lines.append(f"Description: {description[:200]}")
            lines.append("")

        # Required fields
        required = definition.get("required", [])
        if required:
            lines.append("Required fields:")
            for field in required:
                lines.append(f"  - {field}")
            lines.append("")

        # Key properties
        properties = definition.get("properties", {})
        if properties:
            lines.append("Key properties (showing most important):")

            # Prioritize important properties
            priority_props = ["resourceType", "id", "status", "code", "subject",
                              "patient", "encounter", "value", "effective", "issued"]

            # Show priority properties first
            shown = 0
            for prop in priority_props:
                if prop in properties and shown < max_properties:
                    prop_def = properties[prop]
                    prop_desc = prop_def.get("description", "")
                    if prop_desc:
                        # Truncate long descriptions
                        prop_desc = prop_desc[:100] + \
                            "..." if len(prop_desc) > 100 else prop_desc
                        lines.append(f"  - {prop}: {prop_desc}")
                        shown += 1

            # Show other important properties
            for prop, prop_def in list(properties.items())[:max_properties - shown]:
                if prop not in priority_props:
                    prop_desc = prop_def.get("description", "")
                    if prop_desc:
                        prop_desc = prop_desc[:100] + \
                            "..." if len(prop_desc) > 100 else prop_desc
                        lines.append(f"  - {prop}: {prop_desc}")

        return "\n".join(lines)

    def get_example_structure(self, resource_type: str) -> str:
        """
        Generate a minimal example structure for a resource type.

        Args:
            resource_type: The FHIR resource type

        Returns:
            JSON string with minimal example structure
        """
        if not self.schema:
            return "{}"

        definition = self.get_resource_definition(resource_type)
        if not definition:
            return "{}"

        required = definition.get("required", [])
        properties = definition.get("properties", {})

        # Build minimal example with required fields
        example = {
            "resourceType": resource_type
        }

        # Add required fields with placeholder values
        for field in required:
            if field == "resourceType":
                continue

            prop_def = properties.get(field, {})
            # Add a simple placeholder based on the field name/type
            if "date" in field.lower():
                example[field] = "2024-01-01"
            elif "code" in field.lower() or "status" in field.lower():
                example[field] = "example-value"
            elif "reference" in field.lower():
                example[field] = {"reference": "Patient/example"}
            else:
                example[field] = "required-value"

        return json.dumps(example, indent=2)

    def is_loaded(self) -> bool:
        """Check if schema is successfully loaded."""
        return self.schema is not None


# Global instance for easy access
_global_loader: Optional[FHIRSchemaLoader] = None


def get_schema_loader(schema_path: Optional[str] = None) -> FHIRSchemaLoader:
    """
    Get or create the global FHIR schema loader instance.

    Args:
        schema_path: Optional path to schema file

    Returns:
        FHIRSchemaLoader instance
    """
    global _global_loader
    if _global_loader is None or schema_path:
        _global_loader = FHIRSchemaLoader(schema_path)
    return _global_loader
