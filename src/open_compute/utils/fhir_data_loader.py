"""
Enhanced FHIR Data Loader utility.

This module loads and extracts comprehensive FHIR data including:
- Schema definitions (fhir.schema.json)
- Value sets (valuesets.json) 
- Resource profiles (profiles-resources.json)
- Type profiles (profiles-types.json)
- Search parameters (search-parameters.json)

This provides rich context for AI-powered FHIR resource generation.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from functools import lru_cache


class FHIRDataLoader:
    """Loads and extracts comprehensive FHIR data definitions."""

    def __init__(self, data_directory: Optional[str] = None):
        """
        Initialize the FHIR data loader.

        Args:
            data_directory: Path to directory containing FHIR data files. 
                          If None, looks in common locations.
        """
        self.data_directory = data_directory
        self.schema = None
        self.valuesets = None
        self.resource_profiles = None
        self.type_profiles = None
        self.search_parameters = None
        self._load_all_data()

    def _find_data_directory(self) -> Optional[Path]:
        """Find the FHIR data directory."""
        if self.data_directory:
            data_dir = Path(self.data_directory)
            if data_dir.exists():
                return data_dir

        # Try common locations
        possible_paths = [
            # Project data directory
            Path(__file__).parent.parent.parent.parent /
            "data" / "fhir" / "STU6",
            # Desktop location
            Path.home() / "Desktop" / "definitions.json",
            # Current working directory
            Path.cwd() / "data" / "fhir" / "STU6",
        ]

        for path in possible_paths:
            if path.exists() and (path / "fhir.schema.json").exists():
                return path

        return None

    def _load_all_data(self):
        """Load all FHIR data files."""
        data_dir = self._find_data_directory()

        if not data_dir:
            print(
                "Warning: FHIR data directory not found. Generation will proceed without enhanced context.")
            return

        print(f"✓ Found FHIR data directory: {data_dir}")

        # Load schema
        self._load_json_file(data_dir / "fhir.schema.json",
                             "schema", "FHIR Schema")

        # Load valuesets
        self._load_json_file(data_dir / "valuesets.json",
                             "valuesets", "Value Sets")

        # Load resource profiles
        self._load_json_file(data_dir / "profiles-resources.json",
                             "resource_profiles", "Resource Profiles")

        # Load type profiles
        self._load_json_file(data_dir / "profiles-types.json",
                             "type_profiles", "Type Profiles")

        # Load search parameters
        self._load_json_file(data_dir / "search-parameters.json",
                             "search_parameters", "Search Parameters")

    def _load_json_file(self, filepath: Path, attr_name: str, display_name: str):
        """Load a JSON file and set it as an attribute."""
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                setattr(self, attr_name, data)
                print(f"  ✓ Loaded {display_name}")
            except Exception as e:
                print(f"  Warning: Could not load {display_name}: {e}")
                setattr(self, attr_name, None)
        else:
            print(f"  Warning: {display_name} file not found at {filepath}")
            setattr(self, attr_name, None)

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

    @lru_cache(maxsize=128)
    def get_resource_profile(self, resource_type: str) -> Optional[Dict[str, Any]]:
        """
        Get the detailed profile for a FHIR resource from profiles-resources.json.

        Args:
            resource_type: The FHIR resource type

        Returns:
            Profile definition dict or None if not found
        """
        if not self.resource_profiles:
            return None

        # profiles-resources.json is a Bundle, search entries
        entries = self.resource_profiles.get("entry", [])
        for entry in entries:
            resource = entry.get("resource", {})
            if resource.get("type") == resource_type and resource.get("kind") == "resource":
                return resource

        return None

    @lru_cache(maxsize=256)
    def get_valueset_for_element(self, resource_type: str, element_path: str) -> Optional[Dict[str, Any]]:
        """
        Get the valueset binding for a specific element path.

        Args:
            resource_type: The FHIR resource type
            element_path: The element path (e.g., "Observation.status")

        Returns:
            ValueSet information or None if not found
        """
        profile = self.get_resource_profile(resource_type)
        if not profile:
            return None

        # Look through snapshot elements for the path
        snapshot = profile.get("snapshot", {})
        elements = snapshot.get("element", [])

        for element in elements:
            if element.get("path") == element_path or element.get("path") == f"{resource_type}.{element_path}":
                binding = element.get("binding")
                if binding:
                    return {
                        "strength": binding.get("strength"),
                        "valueSet": binding.get("valueSet"),
                        "description": binding.get("description")
                    }

        return None

    @lru_cache(maxsize=128)
    def get_valid_codes_for_element(self, resource_type: str, element_name: str, max_codes: int = 20) -> List[str]:
        """
        Get valid code values for a specific element (like status, code, etc.).

        Args:
            resource_type: The FHIR resource type
            element_name: The element name (e.g., "status")
            max_codes: Maximum number of codes to return

        Returns:
            List of valid code values
        """
        element_path = f"{resource_type}.{element_name}"
        valueset_info = self.get_valueset_for_element(
            resource_type, element_path)

        if not valueset_info or not self.valuesets:
            return []

        valueset_url = valueset_info.get("valueSet")
        if not valueset_url:
            return []

        # Search for the valueset in valuesets.json
        entries = self.valuesets.get("entry", [])
        for entry in entries:
            resource = entry.get("resource", {})
            if resource.get("url") == valueset_url and resource.get("resourceType") == "ValueSet":
                # Extract codes from expansion or compose
                codes = []

                # Try expansion first
                expansion = resource.get("expansion", {})
                contains = expansion.get("contains", [])
                for item in contains[:max_codes]:
                    code = item.get("code")
                    if code:
                        codes.append(code)

                if codes:
                    return codes

                # Try compose if no expansion
                compose = resource.get("compose", {})
                includes = compose.get("include", [])
                for include in includes:
                    concepts = include.get("concept", [])
                    for concept in concepts[:max_codes]:
                        code = concept.get("code")
                        if code:
                            codes.append(code)
                    if len(codes) >= max_codes:
                        break

                return codes[:max_codes]

        return []

    @lru_cache(maxsize=128)
    def get_search_parameters_for_resource(self, resource_type: str) -> List[Dict[str, Any]]:
        """
        Get search parameters for a resource type.
        These indicate which fields are important/searchable.

        Args:
            resource_type: The FHIR resource type

        Returns:
            List of search parameter definitions
        """
        if not self.search_parameters:
            return []

        params = []
        entries = self.search_parameters.get("entry", [])

        for entry in entries:
            resource = entry.get("resource", {})
            if resource.get("resourceType") == "SearchParameter":
                base = resource.get("base", [])
                if resource_type in base:
                    params.append({
                        "name": resource.get("name"),
                        "code": resource.get("code"),
                        "type": resource.get("type"),
                        "description": resource.get("description"),
                        "expression": resource.get("expression")
                    })

        return params

    def get_required_fields(self, resource_type: str) -> List[str]:
        """
        Get the list of required fields for a FHIR resource.

        Args:
            resource_type: The FHIR resource type

        Returns:
            List of required field names
        """
        # First try schema
        definition = self.get_resource_definition(resource_type)
        if definition:
            schema_required = definition.get("required", [])
            if schema_required:
                return schema_required

        # Then try profile
        profile = self.get_resource_profile(resource_type)
        if profile:
            snapshot = profile.get("snapshot", {})
            elements = snapshot.get("element", [])
            required = []

            for element in elements:
                min_card = element.get("min", 0)
                if min_card > 0:
                    path = element.get("path", "")
                    # Extract field name from path (e.g., "Observation.status" -> "status")
                    if "." in path:
                        field = path.split(".")[-1]
                        required.append(field)

            return required

        return []

    def format_enhanced_context_for_prompt(self, resource_type: str, max_examples: int = 10) -> str:
        """
        Format comprehensive FHIR context for inclusion in AI prompts.

        This includes schema, valid codes, important fields, and examples.

        Args:
            resource_type: The FHIR resource type
            max_examples: Maximum number of example values to include

        Returns:
            Formatted string with comprehensive FHIR context
        """
        if not self.schema:
            return "Note: FHIR data not loaded. Please ensure proper FHIR structure."

        lines = [f"=== FHIR {resource_type} Reference Data ===", ""]

        # 1. Basic description from schema
        definition = self.get_resource_definition(resource_type)
        if definition:
            description = definition.get("description", "")
            if description:
                lines.append(f"Description: {description[:300]}")
                lines.append("")

        # 2. Required fields
        required = self.get_required_fields(resource_type)
        if required:
            lines.append("Required fields (MUST be present):")
            for field in required[:15]:  # Limit to avoid prompt bloat
                lines.append(f"  - {field}")
            lines.append("")

        # 3. Valid codes for common enumerated fields
        common_coded_fields = ["status", "intent",
                               "priority", "category", "code"]
        for field in common_coded_fields:
            valid_codes = self.get_valid_codes_for_element(
                resource_type, field, max_codes=max_examples)
            if valid_codes:
                lines.append(f"Valid values for {field}:")
                lines.append(f"  {', '.join(valid_codes)}")
                lines.append("")

        # 4. Important/searchable fields
        search_params = self.get_search_parameters_for_resource(resource_type)
        if search_params:
            lines.append("Important fields (commonly searched/used):")
            for param in search_params[:10]:  # Limit to top 10
                name = param.get("code", "")
                desc = param.get("description", "")
                if name:
                    desc_short = desc[:60] + "..." if len(desc) > 60 else desc
                    lines.append(f"  - {name}: {desc_short}")
            lines.append("")

        # 5. Key properties from schema
        if definition:
            properties = definition.get("properties", {})
            if properties:
                lines.append("Key properties:")

                # Prioritize important properties
                priority_props = ["resourceType", "id", "status", "code", "subject",
                                  "patient", "encounter", "value", "effective", "issued",
                                  "category", "intent", "authoredOn", "requester"]

                shown = 0
                for prop in priority_props:
                    if prop in properties and shown < 15:
                        prop_def = properties[prop]
                        prop_desc = prop_def.get("description", "")
                        if prop_desc:
                            prop_desc = prop_desc[:80] + \
                                "..." if len(prop_desc) > 80 else prop_desc
                            lines.append(f"  - {prop}: {prop_desc}")
                            shown += 1

        return "\n".join(lines)

    def is_loaded(self) -> bool:
        """Check if data is successfully loaded."""
        return self.schema is not None


# Global instance for easy access
_global_loader: Optional[FHIRDataLoader] = None


def get_data_loader(data_directory: Optional[str] = None) -> FHIRDataLoader:
    """
    Get or create the global FHIR data loader instance.

    Args:
        data_directory: Optional path to data directory

    Returns:
        FHIRDataLoader instance
    """
    global _global_loader
    if _global_loader is None or data_directory:
        _global_loader = FHIRDataLoader(data_directory)
    return _global_loader
