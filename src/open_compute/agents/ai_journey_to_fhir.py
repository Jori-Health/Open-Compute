"""
AI-powered agent to generate FHIR resources from a patient journey.

This module uses OpenAI's API to intelligently generate FHIR resources
that represent a complete patient journey, with validation and iterative
refinement.
"""

import json
import os
import asyncio
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal, Tuple
from pathlib import Path
from datetime import datetime

try:
    from openai import OpenAI, AsyncOpenAI
except ImportError:
    raise ImportError(
        "openai is required for AI-powered FHIR generation. "
        "Install it with: pip install openai"
    )

from ..types import PatientJourney, FHIRPatientData
from ..utils.fhir_validator import FHIRValidator, ValidationResult
from ..utils.fhir_schema_loader import get_schema_loader
from ..utils.fhir_data_loader import get_data_loader


@dataclass
class GenerationPlan:
    """Plan for generating FHIR resources."""
    resources_to_generate: List[Dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    resource_id_map: Dict[str, str] = field(
        default_factory=dict)  # Maps resourceType to UUID


@dataclass
class GenerationResult:
    """Result of FHIR resource generation process."""
    success: bool
    fhir_data: Optional[FHIRPatientData] = None
    generated_resources: List[Dict[str, Any]] = field(default_factory=list)
    validation_results: List[ValidationResult] = field(default_factory=list)
    iterations: int = 0
    errors: List[str] = field(default_factory=list)
    planning_details: Optional[GenerationPlan] = None


class AIJourneyToFHIR:
    """
    AI-powered agent that converts a patient journey into FHIR resources.

    This agent uses OpenAI to:
    1. Analyze the patient journey and decide what FHIR resources to generate
    2. Generate each resource with appropriate content
    3. Validate each resource
    4. Check if the journey is complete or more resources are needed
    5. Iterate until success or max iterations reached
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        fhir_version: Literal["R4", "R4B", "R5", "STU3"] = "R4",
        max_iterations: int = 5,
        max_fix_retries: int = 3,
        fhir_schema_path: Optional[str] = None,
        fhir_data_directory: Optional[str] = None,
        auto_save: bool = True,
        save_directory: str = "output",
        parallel_generation: bool = True,
        use_enhanced_context: bool = True,
    ):
        """
        Initialize the AI agent.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use
            fhir_version: FHIR version to generate
            max_iterations: Maximum number of generation iterations
            max_fix_retries: Maximum number of attempts to fix validation errors per resource
            fhir_schema_path: Optional path to fhir.schema.json file (legacy, use fhir_data_directory instead)
            fhir_data_directory: Optional path to directory containing all FHIR data files (recommended)
            auto_save: Automatically save successful FHIR bundles to disk
            save_directory: Directory to save generated bundles (default: "output")
            parallel_generation: Use parallel generation for faster results (recommended)
            use_enhanced_context: Use enhanced context with valuesets, profiles, etc. (recommended)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key must be provided or set in OPENAI_API_KEY env var"
            )

        self.client = OpenAI(api_key=self.api_key)
        self.async_client = AsyncOpenAI(api_key=self.api_key)
        self.model = model
        self.fhir_version = fhir_version
        self.max_iterations = max_iterations
        self.max_fix_retries = max_fix_retries
        self.validator = FHIRValidator(version=fhir_version)

        # Load FHIR data - use enhanced loader if enabled, fallback to basic schema loader
        self.use_enhanced_context = use_enhanced_context
        if use_enhanced_context:
            self.data_loader = get_data_loader(fhir_data_directory)
            self.schema_loader = get_schema_loader(
                fhir_schema_path)  # Keep for backward compatibility
        else:
            self.data_loader = None
            self.schema_loader = get_schema_loader(fhir_schema_path)

        self.auto_save = auto_save
        self.save_directory = save_directory
        self.parallel_generation = parallel_generation

        # Create output directory if auto_save is enabled
        if self.auto_save:
            Path(self.save_directory).mkdir(parents=True, exist_ok=True)

    def generate_from_journey(
        self, journey: PatientJourney, patient_context: Optional[str] = None
    ) -> GenerationResult:
        """
        Generate FHIR resources from a patient journey.

        Args:
            journey: PatientJourney to convert to FHIR
            patient_context: Optional additional context about the patient

        Returns:
            GenerationResult with generated resources and validation status
        """
        print("\n" + "=" * 70)
        print("🚀 STARTING FHIR GENERATION")
        print("=" * 70)
        print(f"Patient ID: {journey.patient_id or 'N/A'}")
        print(f"Journey Summary: {journey.summary or 'N/A'}")
        print(f"Journey Stages: {len(journey.stages)}")
        print(f"Model: {self.model}")
        print(f"FHIR Version: {self.fhir_version}")
        print(
            f"Parallel Generation: {'Enabled' if self.parallel_generation else 'Disabled'}")
        print(f"Auto-Save: {'Enabled' if self.auto_save else 'Disabled'}")
        print("=" * 70)

        # Step 1: Create a generation plan
        print("\n📋 STEP 1: Creating Generation Plan...")
        plan = self._create_generation_plan(journey, patient_context)

        if not plan.resources_to_generate:
            print("❌ Failed to create generation plan")
            return GenerationResult(
                success=False,
                errors=["Failed to create a generation plan"],
            )

        print(
            f"✓ Plan created: {len(plan.resources_to_generate)} resources to generate")
        print(f"  Rationale: {plan.rationale}")

        print(f"  Resources to generate: {plan.resources_to_generate}")

        # Step 2: Generate resources iteratively with validation
        print(
            f"\n⚙️  STEP 2: Generating Resources (max {self.max_iterations} iterations)...")
        result = self._iterative_generation(journey, plan, patient_context)

        # Step 3: Auto-save if enabled and there's data to save (even if generation wasn't fully successful)
        if self.auto_save and result.fhir_data:
            print(f"\n💾 STEP 3: Auto-Saving Bundle...")
            status_text = "complete" if result.success else "partial (incomplete generation)"
            print(
                f"   Saving {status_text} bundle with {len(result.generated_resources)} resources...")
            saved_path = self._save_bundle(result.fhir_data, journey)
            if saved_path:
                print(f"✓ Auto-saved FHIR bundle to: {saved_path}")
            else:
                print(f"⚠️  Failed to save bundle to disk")

        return result

    def _extract_patient_name(self, fhir_data: FHIRPatientData) -> Tuple[str, str]:
        """
        Extract patient's first and last name from the Patient resource.

        Args:
            fhir_data: FHIR bundle containing resources

        Returns:
            Tuple of (first_name, last_name). Returns ('unknown', 'patient') if not found.
        """
        for entry in fhir_data.entries:
            resource = entry.get("resource", {})
            if resource.get("resourceType") == "Patient":
                # Look for name in the Patient resource
                names = resource.get("name", [])
                if names and len(names) > 0:
                    name = names[0]  # Get the first name entry
                    given = name.get("given", [])
                    family = name.get("family", "")

                    first_name = given[0] if given else "unknown"
                    last_name = family if family else "patient"

                    # Sanitize names for use in folder names
                    first_name = "".join(
                        c if c.isalnum() else "_" for c in str(first_name).lower())
                    last_name = "".join(
                        c if c.isalnum() else "_" for c in str(last_name).lower())

                    return first_name, last_name

        return "unknown", "patient"

    def _save_bundle(self, fhir_data: FHIRPatientData, journey: PatientJourney) -> Optional[str]:
        """
        Save FHIR data to disk in both Bundle and BULK FHIR formats.

        Args:
            fhir_data: FHIR bundle to save
            journey: Original journey (for filename)

        Returns:
            Path to generation folder, or None if save failed
        """
        try:
            # Extract patient name from resources
            first_name, last_name = self._extract_patient_name(fhir_data)
            patient_folder_name = f"{first_name}_{last_name}"

            # Create patient-specific folder under output directory
            patient_dir = Path(self.save_directory) / patient_folder_name
            patient_dir.mkdir(parents=True, exist_ok=True)

            # 1. Save Patient Bundle version
            bundle = {
                "resourceType": "Bundle",
                "type": "collection",
                "timestamp": datetime.now().isoformat(),
                "entry": fhir_data.entries,
            }

            bundle_filepath = patient_dir / "patient_bundle.json"
            with open(bundle_filepath, 'w') as f:
                json.dump(bundle, f, indent=2)

            print(f"   ✓ Saved Patient Bundle: {bundle_filepath}")

            # 2. Save Bulk FHIR version (single JSONL file with all resources)
            bulk_filepath = patient_dir / "bulk_fhir.jsonl"
            with open(bulk_filepath, 'w') as f:
                for entry in fhir_data.entries:
                    resource = entry.get("resource", {})
                    f.write(json.dumps(resource) + '\n')

            resource_count = len(fhir_data.entries)
            print(
                f"   ✓ Saved Bulk FHIR ({resource_count} resources): {bulk_filepath}")

            # 3. Group resources by type for summary
            resources_by_type = {}
            for entry in fhir_data.entries:
                resource = entry.get("resource", {})
                resource_type = resource.get("resourceType", "Unknown")

                if resource_type not in resources_by_type:
                    resources_by_type[resource_type] = []
                resources_by_type[resource_type].append(resource)

            # 4. Create a README with metadata
            patient_id = journey.patient_id or "unknown"
            readme_filepath = patient_dir / "README.txt"
            with open(readme_filepath, 'w') as f:
                f.write(f"FHIR Generation Results\n")
                f.write(f"=" * 50 + "\n\n")
                f.write(f"Patient: {first_name.title()} {last_name.title()}\n")
                f.write(f"Patient ID: {patient_id}\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"FHIR Version: {self.fhir_version}\n")
                f.write(f"Model: {self.model}\n\n")
                f.write(f"Files:\n")
                f.write(
                    f"  - patient_bundle.json: Complete FHIR Bundle with all resources\n")
                f.write(
                    f"  - bulk_fhir.jsonl: All resources in JSONL format (one resource per line)\n\n")
                f.write(f"Resource Summary:\n")
                for resource_type, resources in sorted(resources_by_type.items()):
                    f.write(f"  - {resource_type}: {len(resources)}\n")

            return str(patient_dir)

        except Exception as e:
            print(f"Warning: Could not save bundle: {e}")
            return None

    def _create_generation_plan(
        self, journey: PatientJourney, patient_context: Optional[str] = None
    ) -> GenerationPlan:
        """
        Use AI to decide what FHIR resources to generate.

        Args:
            journey: PatientJourney to analyze
            patient_context: Optional additional context

        Returns:
            GenerationPlan with resources to generate
        """
        # Build the prompt for planning
        journey_description = self._format_journey_for_prompt(journey)

        planning_prompt = f"""You are a FHIR expert. Analyze this patient journey and create a plan for generating FHIR resources.

Patient Journey:
{journey_description}

{f"Additional Context: {patient_context}" if patient_context else ""}

Your task:
1. Identify FHIR resources needed to represent this patient journey
2. For each resource, specify:
   - resourceType (e.g., Patient, Encounter, Condition, Observation, Procedure, MedicationRequest, etc.)
   - A brief description of what the resource should contain
   - Key data points from the journey that should be included

CRITICAL RULES - READ CAREFULLY:
- ALWAYS include administrative/structural resources: Patient, Encounter, Practitioner, Location, Organization (even if not explicitly mentioned in the journey)
- For CLINICAL resources (Condition, Observation, Procedure, Medication, DiagnosticReport, Immunization, etc.):
  * ONLY include them if they are EXPLICITLY mentioned in the patient journey stages or context
  * DO NOT add any clinical resources that are not described in the journey
  * DO NOT make assumptions or add "typical" resources for the condition
  * DO NOT infer clinical events that are not stated
  * If a stage mentions a diagnosis, include ONLY that diagnosis (not related conditions)
  * If a stage mentions a medication, include ONLY that medication (not related medications)
  * If a stage mentions a procedure, include ONLY that procedure (not related procedures)
- Use the journey stages as the ONLY source of truth for clinical events
- When in doubt, DO NOT include a resource - be conservative

FORBIDDEN FIELDS - DO NOT suggest these in key_data (they cause validation errors in FHIR R5):
- For Encounter: DO NOT suggest "period", "reasonCode", or "timestamp"
- For Procedure: DO NOT suggest "performedDateTime" or "performedPeriod"
- For Observation: DO NOT suggest "valueComponent" in components
- These fields don't exist or have different structures in the validation library

EXAMPLES OF WHAT NOT TO DO:
- If journey mentions "diabetes", DON'T add resources for typical diabetes complications unless explicitly mentioned
- If journey mentions "heart attack", DON'T add resources for cardiac rehab unless explicitly mentioned
- If journey mentions one medication, DON'T add other medications in the same class
- DON'T add preventive care resources unless the journey explicitly mentions them

Return your response as a JSON object with this structure:
{{
    "rationale": "Brief explanation of your approach and why you chose these specific resources",
    "resources": [
        {{
            "resourceType": "Patient",
            "description": "Basic patient demographics and identifiers",
            "key_data": ["patient_id", "demographics if available"]
        }},
        {{
            "resourceType": "Encounter",
            "description": "Hospital admission encounter",
            "key_data": ["status", "class", "subject reference"]
        }},
        {{
            "resourceType": "Practitioner",
            "description": "Healthcare provider who treated the patient",
            "key_data": ["practitioner details from journey if available"]
        }},
        {{
            "resourceType": "Location",
            "description": "Healthcare facility where encounter occurred",
            "key_data": ["location details from journey if available"]
        }}
        // ... only add clinical resources that are explicitly mentioned in the journey stages
    ]
}}

Remember: Your rationale should explain how each clinical resource is directly mentioned in the journey. Be extremely conservative - only include what is explicitly stated."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a FHIR expert who creates comprehensive plans for generating FHIR resources from patient journeys.",
                    },
                    {"role": "user", "content": planning_prompt},
                ],

                response_format={"type": "json_object"},
            )

            plan_data = json.loads(response.choices[0].message.content)
            resources = plan_data.get("resources", [])

            # Generate UUIDs for each planned resource
            resource_id_map = {}
            for resource_spec in resources:
                resource_type = resource_spec.get("resourceType")
                if resource_type:
                    # Generate a unique UUID for this resource
                    resource_uuid = str(uuid.uuid4())
                    resource_id_map[resource_type] = resource_uuid
                    # Add the UUID to the resource spec for easy reference
                    resource_spec["assigned_id"] = resource_uuid

            print(f"\n🔑 Generated Resource IDs:")
            for resource_type, resource_id in resource_id_map.items():
                print(f"   {resource_type}: {resource_id}")

            return GenerationPlan(
                resources_to_generate=resources,
                rationale=plan_data.get("rationale", ""),
                resource_id_map=resource_id_map,
            )

        except Exception as e:
            print(f"Error creating generation plan: {e}")
            return GenerationPlan()

    def _iterative_generation(
        self,
        journey: PatientJourney,
        initial_plan: GenerationPlan,
        patient_context: Optional[str] = None,
    ) -> GenerationResult:
        """
        Generate resources iteratively with validation and completeness checking.

        Args:
            journey: PatientJourney to convert
            initial_plan: Initial generation plan
            patient_context: Optional additional context

        Returns:
            GenerationResult with all generated resources
        """
        generated_resources = []
        validation_results = []
        errors = []
        current_iteration = 0

        resources_to_generate = initial_plan.resources_to_generate.copy()
        journey_description = self._format_journey_for_prompt(journey)

        while current_iteration < self.max_iterations:
            current_iteration += 1
            print(
                f"\n=== Iteration {current_iteration}/{self.max_iterations} ===")

            # Generate resources from current list
            if self.parallel_generation and len(resources_to_generate) > 1:
                # Parallel generation for speed
                print(
                    f"\n🔄 Generating {len(resources_to_generate)} resources in parallel...")
                print("   📡 Making concurrent API calls...")

                start_time = time.time()
                batch_results = asyncio.run(
                    self._generate_resources_parallel(
                        resources_to_generate, journey, generated_resources, patient_context, initial_plan.resource_id_map
                    )
                )
                elapsed = time.time() - start_time
                print(f"   ✓ All API calls completed in {elapsed:.1f}s")

                # Process parallel results
                print(
                    f"\n📝 Processing and validating {len(batch_results)} generated resources...")

                # First pass: validate all resources
                validation_data = []
                for idx, (resource_spec, generated_resource) in enumerate(zip(resources_to_generate, batch_results)):
                    resource_type = resource_spec.get("resourceType")
                    print(
                        f"  [{idx+1}/{len(resources_to_generate)}] {resource_type}: ", end="")

                    if not generated_resource:
                        print("❌ Generation failed")
                        errors.append(f"Failed to generate {resource_type}")
                        continue

                    # Validate the resource
                    validation = self.validator.validate(generated_resource)
                    validation_results.append(validation)

                    if validation.is_valid:
                        print("✓ Valid")
                        generated_resources.append(generated_resource)
                    else:
                        print(f"✗ Invalid ({len(validation.errors)} errors)")
                        validation_data.append({
                            'resource': generated_resource,
                            'validation': validation,
                            'spec': resource_spec,
                            'index': idx
                        })

                # Second pass: fix all invalid resources in parallel
                if validation_data:
                    print(
                        f"\n🔧 Fixing {len(validation_data)} invalid resources in parallel...")
                    print("   📡 Making concurrent fix API calls...")

                    start_time = time.time()
                    fix_results = asyncio.run(
                        self._fix_resources_parallel(
                            validation_data, journey, generated_resources, patient_context, initial_plan.resource_id_map
                        )
                    )
                    elapsed = time.time() - start_time
                    print(f"   ✓ All fix calls completed in {elapsed:.1f}s")

                    # Process fix results
                    print(f"\n📝 Validating fixed resources...")
                    for idx, (val_data, fixed_resource) in enumerate(zip(validation_data, fix_results)):
                        resource_type = val_data['spec'].get('resourceType')
                        original_idx = val_data['index']
                        print(
                            f"  [{original_idx+1}] {resource_type}: ", end="")

                        if fixed_resource:
                            # Validate the fixed resource
                            fixed_validation = self.validator.validate(
                                fixed_resource)
                            validation_results.append(fixed_validation)

                            if fixed_validation.is_valid:
                                print("✓ Fixed successfully")
                                generated_resources.append(fixed_resource)
                            else:
                                print(f"✗ Still invalid after fixes")
                                errors.append(
                                    f"Validation failed for {resource_type} after {self.max_fix_retries} attempts: {fixed_validation.errors}"
                                )
                        else:
                            print(f"✗ Could not fix")
                            errors.append(
                                f"Validation failed for {resource_type}: {val_data['validation'].errors}"
                            )
            else:
                # Sequential generation (for single resource or when parallel disabled)
                for resource_spec in resources_to_generate:
                    resource_type = resource_spec.get("resourceType")
                    print(f"Generating {resource_type}...")

                    # Generate the resource
                    generated_resource = self._generate_single_resource(
                        resource_spec, journey, generated_resources, patient_context, initial_plan.resource_id_map
                    )

                    if not generated_resource:
                        errors.append(f"Failed to generate {resource_type}")
                        continue

                    # Validate the resource
                    validation = self.validator.validate(generated_resource)
                    validation_results.append(validation)

                    if validation.is_valid:
                        print(f"  ✓ {resource_type} validated successfully")
                        generated_resources.append(generated_resource)
                    else:
                        print(f"  ✗ {resource_type} validation failed:")
                        for error in validation.errors:
                            print(f"    - {error}")

                        # Try to fix the resource
                        print(f"  → Attempting to fix {resource_type}...")
                        fixed_resource = self._fix_invalid_resource(
                            generated_resource,
                            validation,
                            resource_spec,
                            journey,
                            generated_resources,
                            patient_context,
                            initial_plan.resource_id_map,
                        )

                        if fixed_resource:
                            # Validate the fixed resource
                            fixed_validation = self.validator.validate(
                                fixed_resource)
                            validation_results.append(fixed_validation)

                            if fixed_validation.is_valid:
                                print(
                                    f"  ✓ {resource_type} fixed and validated successfully!")
                                generated_resources.append(fixed_resource)
                            else:
                                print(
                                    f"  ✗ {resource_type} still invalid after fixes")
                                errors.append(
                                    f"Validation failed for {resource_type} after {self.max_fix_retries} attempts: {fixed_validation.errors}"
                                )
                        else:
                            errors.append(
                                f"Validation failed for {resource_type}: {validation.errors}"
                            )

            # Check if we have a complete journey or need more resources
            print(f"\n🔍 Checking Journey Completeness...")
            print(f"   Current resources: {len(generated_resources)}")
            completeness_check = self._check_completeness(
                journey, generated_resources, journey_description, patient_context
            )

            if completeness_check["is_complete"]:
                print("   ✓ Journey is complete!")
                print("\n📦 Creating FHIR Bundle...")
                # Create FHIRPatientData bundle
                fhir_data = self._create_bundle(generated_resources)
                print(
                    f"   ✓ Bundle created with {len(generated_resources)} resources")

                # Print generation summary
                self._print_generation_summary(
                    initial_plan,
                    generated_resources,
                    validation_results,
                    success=True,
                    iterations=current_iteration,
                )

                return GenerationResult(
                    success=True,
                    fhir_data=fhir_data,
                    generated_resources=generated_resources,
                    validation_results=validation_results,
                    iterations=current_iteration,
                    planning_details=initial_plan,
                )

            # Get additional resources to generate
            additional_resources = completeness_check.get(
                "additional_resources", [])
            if not additional_resources:
                print(
                    "   ⚠️  No additional resources suggested, but journey may be incomplete.")
                break

            print(f"   → Missing {len(additional_resources)} resources:")
            for res in additional_resources:
                print(
                    f"      • {res.get('resourceType')}: {res.get('description')}")
            print(f"\n🔄 Proceeding to iteration {current_iteration + 1}...")

            resources_to_generate = additional_resources

        # Max iterations reached
        print(f"\n⚠ Maximum iterations ({self.max_iterations}) reached")

        # Create bundle even if not complete
        fhir_data = self._create_bundle(
            generated_resources) if generated_resources else None

        # Print generation summary
        self._print_generation_summary(
            initial_plan,
            generated_resources,
            validation_results,
            success=False,
            iterations=current_iteration,
        )

        return GenerationResult(
            success=False,
            fhir_data=fhir_data,
            generated_resources=generated_resources,
            validation_results=validation_results,
            iterations=current_iteration,
            errors=errors +
            ["Maximum iterations reached without completing journey"],
            planning_details=initial_plan,
        )

    def _generate_single_resource(
        self,
        resource_spec: Dict[str, Any],
        journey: PatientJourney,
        existing_resources: List[Dict[str, Any]],
        patient_context: Optional[str] = None,
        resource_id_map: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a single FHIR resource using AI.

        Args:
            resource_spec: Specification for the resource to generate
            journey: Original patient journey
            existing_resources: Already generated resources for reference
            patient_context: Optional additional context
            resource_id_map: Map of resourceType to assigned UUIDs

        Returns:
            Generated FHIR resource as dict, or None if generation failed
        """
        resource_type = resource_spec.get("resourceType")
        description = resource_spec.get("description", "")
        key_data = resource_spec.get("key_data", [])
        assigned_id = resource_spec.get("assigned_id")  # Get pre-assigned UUID

        journey_description = self._format_journey_for_prompt(journey)
        existing_resources_summary = self._format_existing_resources(
            existing_resources)

        # Format resource ID map for prompt
        id_map_text = self._format_resource_id_map(resource_id_map or {})

        # Get FHIR context for this resource type - use enhanced if available
        if self.use_enhanced_context and self.data_loader and self.data_loader.is_loaded():
            schema_context = self.data_loader.format_enhanced_context_for_prompt(
                resource_type)
        else:
            schema_context = self.schema_loader.format_schema_for_prompt(
                resource_type)

        # Get resource-specific guidance
        resource_guidance = self._get_resource_specific_guidance(resource_type)

        generation_prompt = f"""Generate a valid FHIR {self.fhir_version} {resource_type} resource.

Patient Journey:
{journey_description}

{f"Additional Context: {patient_context}" if patient_context else ""}

Resource to Generate: {resource_type}
Description: {description}
Key Data Points: {', '.join(key_data) if key_data else 'All relevant data from journey'}

Already Generated Resources:
{existing_resources_summary}

{id_map_text}

{schema_context}

{resource_guidance}

CRITICAL REQUIREMENTS:
1. Generate a complete, valid FHIR {self.fhir_version} {resource_type} resource
2. Include all required fields for {resource_type} (see schema and guidance above)
3. Use proper FHIR data types and structures as defined in the schema
4. Reference other resources appropriately using the Resource IDs provided above (e.g., Patient/{{patient_id}})
5. ONLY use data that is EXPLICITLY mentioned in the journey stages, context, or key data points above
6. DO NOT add clinical information that is not in the journey
7. DO NOT make assumptions or add "typical" data for this resource type
8. DO NOT infer information - if a data point isn't mentioned, omit it or use a minimal placeholder
9. Use appropriate coding systems (LOINC, SNOMED CT, RxNorm, etc.) ONLY for items explicitly mentioned
10. Follow the property descriptions from the schema
11. IMPORTANT: Use the assigned ID "{assigned_id}" as the "id" field for this resource
12. Return ONLY the JSON for the {resource_type} resource, no explanations
13. Ensure ALL required fields have valid values according to FHIR spec
14. For CodeableConcept fields, always include at least a 'text' field even if you don't have a specific code
15. Use the minimal example from the guidance as a starting template

STAY FAITHFUL TO THE JOURNEY: If the journey doesn't mention specific details (like exact measurements, codes, dates), use minimal but valid FHIR structures. Don't invent clinical data.

Return the resource as a valid JSON object."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a FHIR expert who generates valid FHIR {self.fhir_version} resources. You always return valid JSON. You ONLY use data explicitly mentioned in the provided patient journey - you never add information not stated in the journey.",
                    },
                    {"role": "user", "content": generation_prompt},
                ],

                response_format={"type": "json_object"},
            )

            resource_json = response.choices[0].message.content
            resource = json.loads(resource_json)

            # Ensure resourceType is set
            resource["resourceType"] = resource_type

            # Ensure the assigned ID is used
            if assigned_id:
                resource["id"] = assigned_id

            return resource

        except Exception as e:
            print(f"  Error generating {resource_type}: {e}")
            return None

    async def _generate_single_resource_async(
        self,
        resource_spec: Dict[str, Any],
        journey: PatientJourney,
        existing_resources: List[Dict[str, Any]],
        patient_context: Optional[str] = None,
        resource_id_map: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Async version of _generate_single_resource for parallel execution.

        Args:
            resource_spec: Specification for the resource to generate
            journey: Original patient journey
            existing_resources: Already generated resources for reference
            patient_context: Optional additional context
            resource_id_map: Map of resourceType to assigned UUIDs

        Returns:
            Generated FHIR resource as dict, or None if generation failed
        """
        resource_type = resource_spec.get("resourceType")
        description = resource_spec.get("description", "")
        key_data = resource_spec.get("key_data", [])
        assigned_id = resource_spec.get("assigned_id")  # Get pre-assigned UUID

        journey_description = self._format_journey_for_prompt(journey)
        existing_resources_summary = self._format_existing_resources(
            existing_resources)

        # Format resource ID map for prompt
        id_map_text = self._format_resource_id_map(resource_id_map or {})

        # Get FHIR context for this resource type - use enhanced if available
        if self.use_enhanced_context and self.data_loader and self.data_loader.is_loaded():
            schema_context = self.data_loader.format_enhanced_context_for_prompt(
                resource_type)
        else:
            schema_context = self.schema_loader.format_schema_for_prompt(
                resource_type)

        # Get resource-specific guidance
        resource_guidance = self._get_resource_specific_guidance(resource_type)

        generation_prompt = f"""Generate a valid FHIR {self.fhir_version} {resource_type} resource.

Patient Journey:
{journey_description}

{f"Additional Context: {patient_context}" if patient_context else ""}

Resource to Generate: {resource_type}
Description: {description}
Key Data Points: {', '.join(key_data) if key_data else 'All relevant data from journey'}

Already Generated Resources:
{existing_resources_summary}

{id_map_text}

{schema_context}

{resource_guidance}

CRITICAL REQUIREMENTS:
1. Generate a complete, valid FHIR {self.fhir_version} {resource_type} resource
2. Include all required fields for {resource_type} (see schema and guidance above)
3. Use proper FHIR data types and structures as defined in the schema
4. Reference other resources appropriately using the Resource IDs provided above (e.g., Patient/{{patient_id}})
5. ONLY use data that is EXPLICITLY mentioned in the journey stages, context, or key data points above
6. DO NOT add clinical information that is not in the journey
7. DO NOT make assumptions or add "typical" data for this resource type
8. DO NOT infer information - if a data point isn't mentioned, omit it or use a minimal placeholder
9. Use appropriate coding systems (LOINC, SNOMED CT, RxNorm, etc.) ONLY for items explicitly mentioned
10. Follow the property descriptions from the schema
11. IMPORTANT: Use the assigned ID "{assigned_id}" as the "id" field for this resource
12. Return ONLY the JSON for the {resource_type} resource, no explanations
13. Ensure ALL required fields have valid values according to FHIR spec
14. For CodeableConcept fields, always include at least a 'text' field even if you don't have a specific code
15. Use the minimal example from the guidance as a starting template

STAY FAITHFUL TO THE JOURNEY: If the journey doesn't mention specific details (like exact measurements, codes, dates), use minimal but valid FHIR structures. Don't invent clinical data.

Return the resource as a valid JSON object."""

        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a FHIR expert who generates valid FHIR {self.fhir_version} resources. You always return valid JSON. You ONLY use data explicitly mentioned in the provided patient journey - you never add information not stated in the journey.",
                    },
                    {"role": "user", "content": generation_prompt},
                ],

                response_format={"type": "json_object"},
            )

            resource_json = response.choices[0].message.content
            resource = json.loads(resource_json)

            # Ensure resourceType is set
            resource["resourceType"] = resource_type

            # Ensure the assigned ID is used
            if assigned_id:
                resource["id"] = assigned_id

            return resource

        except Exception as e:
            print(f"  Error generating {resource_type}: {e}")
            return None

    async def _generate_resources_parallel(
        self,
        resource_specs: List[Dict[str, Any]],
        journey: PatientJourney,
        existing_resources: List[Dict[str, Any]],
        patient_context: Optional[str] = None,
        resource_id_map: Optional[Dict[str, str]] = None,
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Generate multiple FHIR resources in parallel using async API calls.

        Args:
            resource_specs: List of resource specifications to generate
            journey: Original patient journey
            existing_resources: Already generated resources for reference
            patient_context: Optional additional context
            resource_id_map: Map of resourceType to assigned UUIDs

        Returns:
            List of generated resources (same order as input specs)
        """
        tasks = [
            self._generate_single_resource_async(
                resource_spec, journey, existing_resources, patient_context, resource_id_map
            )
            for resource_spec in resource_specs
        ]

        return await asyncio.gather(*tasks)

    async def _fix_resources_parallel(
        self,
        validation_data: List[Dict[str, Any]],
        journey: PatientJourney,
        existing_resources: List[Dict[str, Any]],
        patient_context: Optional[str] = None,
        resource_id_map: Optional[Dict[str, str]] = None,
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Fix multiple invalid FHIR resources in parallel using async API calls.

        Args:
            validation_data: List of dicts with 'resource', 'validation', 'spec' keys
            journey: Original patient journey
            existing_resources: Already generated resources for reference
            patient_context: Optional additional context
            resource_id_map: Map of resourceType to assigned UUIDs

        Returns:
            List of fixed resources (same order as input)
        """
        tasks = [
            self._fix_invalid_resource_async(
                val_data['resource'],
                val_data['validation'],
                val_data['spec'],
                journey,
                existing_resources,
                patient_context,
                resource_id_map,
            )
            for val_data in validation_data
        ]

        return await asyncio.gather(*tasks)

    async def _fix_invalid_resource_async(
        self,
        invalid_resource: Dict[str, Any],
        validation_result: ValidationResult,
        resource_spec: Dict[str, Any],
        journey: PatientJourney,
        existing_resources: List[Dict[str, Any]],
        patient_context: Optional[str] = None,
        resource_id_map: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Async version of _fix_invalid_resource for parallel execution.

        Args:
            invalid_resource: The resource that failed validation
            validation_result: ValidationResult with error details
            resource_spec: Original specification for the resource
            journey: Original patient journey
            existing_resources: Already generated resources for reference
            patient_context: Optional additional context
            resource_id_map: Map of resourceType to assigned UUIDs

        Returns:
            Fixed FHIR resource as dict, or None if fixing failed
        """
        resource_type = invalid_resource.get("resourceType", "Unknown")
        assigned_id = resource_spec.get("assigned_id")

        # Format the errors for the AI
        errors_text = "\n".join(
            f"- {error}" for error in validation_result.errors)

        journey_description = self._format_journey_for_prompt(journey)
        existing_resources_summary = self._format_existing_resources(
            existing_resources)

        # Format resource ID map for prompt
        id_map_text = self._format_resource_id_map(resource_id_map or {})

        # Get FHIR context for this resource type - use enhanced if available
        if self.use_enhanced_context and self.data_loader and self.data_loader.is_loaded():
            schema_context = self.data_loader.format_enhanced_context_for_prompt(
                resource_type)
        else:
            schema_context = self.schema_loader.format_schema_for_prompt(
                resource_type)

        fix_prompt = f"""You are a FHIR expert. A {resource_type} resource was generated but failed validation.

Your task: Fix the validation errors while preserving the clinical meaning.

ORIGINAL RESOURCE (with errors):
{json.dumps(invalid_resource, indent=2)}

VALIDATION ERRORS:
{errors_text}

Patient Journey (for context):
{journey_description}

{f"Additional Context: {patient_context}" if patient_context else ""}

Already Generated Resources (for reference):
{existing_resources_summary}

{id_map_text}

{schema_context}

Requirements:
1. Fix ALL validation errors listed above
2. Maintain the clinical meaning and data from the original resource
3. Ensure all required fields for {resource_type} are present and correct (see schema above)
4. Use proper FHIR {self.fhir_version} data types and structures as defined in the schema
5. Reference other resources appropriately using the Resource IDs provided above (e.g., Patient/{assigned_id})
6. Use appropriate coding systems (LOINC, SNOMED CT, RxNorm, etc.)
7. Follow the property descriptions from the schema
8. IMPORTANT: Ensure the ID field is "{assigned_id}"
9. Return ONLY the corrected JSON for the {resource_type} resource

Return the fixed resource as a valid JSON object."""

        for attempt in range(1, self.max_fix_retries + 1):
            try:
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are a FHIR expert who fixes validation errors in FHIR {self.fhir_version} resources. You always return valid, corrected JSON.",
                        },
                        {"role": "user", "content": fix_prompt},
                    ],
                    response_format={"type": "json_object"},
                )

                fixed_resource = json.loads(
                    response.choices[0].message.content)

                # Ensure resourceType is preserved
                fixed_resource["resourceType"] = resource_type

                # Ensure the assigned ID is preserved
                if assigned_id:
                    fixed_resource["id"] = assigned_id

                # Validate the fixed resource
                fixed_validation = self.validator.validate(fixed_resource)

                if fixed_validation.is_valid:
                    return fixed_resource
                else:
                    # Update errors for next attempt
                    errors_text = "\n".join(
                        f"- {error}" for error in fixed_validation.errors)

                    # Update the prompt for the next iteration
                    fix_prompt = f"""The previous fix attempt still has validation errors. Try again.

RESOURCE (with remaining errors):
{json.dumps(fixed_resource, indent=2)}

REMAINING VALIDATION ERRORS:
{errors_text}

Fix these errors while maintaining the clinical meaning."""

            except Exception as e:
                if attempt == self.max_fix_retries:
                    return None
                continue

        return None

    def _fix_invalid_resource(
        self,
        invalid_resource: Dict[str, Any],
        validation_result: ValidationResult,
        resource_spec: Dict[str, Any],
        journey: PatientJourney,
        existing_resources: List[Dict[str, Any]],
        patient_context: Optional[str] = None,
        resource_id_map: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to fix an invalid FHIR resource using AI based on validation errors.

        Args:
            invalid_resource: The resource that failed validation
            validation_result: ValidationResult with error details
            resource_spec: Original specification for the resource
            journey: Original patient journey
            existing_resources: Already generated resources for reference
            patient_context: Optional additional context
            resource_id_map: Map of resourceType to assigned UUIDs

        Returns:
            Fixed FHIR resource as dict, or None if fixing failed
        """
        resource_type = invalid_resource.get("resourceType", "Unknown")
        assigned_id = resource_spec.get("assigned_id")  # Get pre-assigned UUID

        # Format the errors for the AI
        errors_text = "\n".join(
            f"- {error}" for error in validation_result.errors)

        journey_description = self._format_journey_for_prompt(journey)
        existing_resources_summary = self._format_existing_resources(
            existing_resources)

        # Format resource ID map for prompt
        id_map_text = self._format_resource_id_map(resource_id_map or {})

        # Get FHIR context for this resource type - use enhanced if available
        if self.use_enhanced_context and self.data_loader and self.data_loader.is_loaded():
            schema_context = self.data_loader.format_enhanced_context_for_prompt(
                resource_type)
        else:
            schema_context = self.schema_loader.format_schema_for_prompt(
                resource_type)

        fix_prompt = f"""You are a FHIR expert. A {resource_type} resource was generated but failed validation.

Your task: Fix the validation errors while preserving the clinical meaning.

ORIGINAL RESOURCE (with errors):
{json.dumps(invalid_resource, indent=2)}

VALIDATION ERRORS:
{errors_text}

Patient Journey (for context):
{journey_description}

{f"Additional Context: {patient_context}" if patient_context else ""}

Already Generated Resources (for reference):
{existing_resources_summary}

{id_map_text}

{schema_context}

Requirements:
1. Fix ALL validation errors listed above
2. Maintain the clinical meaning and data from the original resource
3. Ensure all required fields for {resource_type} are present and correct (see schema above)
4. Use proper FHIR {self.fhir_version} data types and structures as defined in the schema
5. Reference other resources appropriately using the Resource IDs provided above (e.g., Patient/{assigned_id})
6. Use appropriate coding systems (LOINC, SNOMED CT, RxNorm, etc.)
7. Follow the property descriptions from the schema
8. IMPORTANT: Ensure the ID field is "{assigned_id}"
9. Return ONLY the corrected JSON for the {resource_type} resource

Return the fixed resource as a valid JSON object."""

        for attempt in range(1, self.max_fix_retries + 1):
            try:
                print(
                    f"        🔄 Fix attempt {attempt}/{self.max_fix_retries}...")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are a FHIR expert who fixes validation errors in FHIR {self.fhir_version} resources. You always return valid, corrected JSON.",
                        },
                        {"role": "user", "content": fix_prompt},
                    ],

                    response_format={"type": "json_object"},
                )

                fixed_resource = json.loads(
                    response.choices[0].message.content)

                # Ensure resourceType is preserved
                fixed_resource["resourceType"] = resource_type

                # Ensure the assigned ID is preserved
                if assigned_id:
                    fixed_resource["id"] = assigned_id

                # Validate the fixed resource
                fixed_validation = self.validator.validate(fixed_resource)

                if fixed_validation.is_valid:
                    print(f"        ✓ Fix successful on attempt {attempt}!")
                    return fixed_resource
                else:
                    # Update errors for next attempt
                    errors_text = "\n".join(
                        f"- {error}" for error in fixed_validation.errors)
                    print(
                        f"        ⚠️  Still has {len(fixed_validation.errors)} error(s), retrying...")

                    # Update the prompt for the next iteration
                    fix_prompt = f"""The previous fix attempt still has validation errors. Try again.

RESOURCE (with remaining errors):
{json.dumps(fixed_resource, indent=2)}

REMAINING VALIDATION ERRORS:
{errors_text}

Fix these errors while maintaining the clinical meaning."""

            except Exception as e:
                print(f"        ❌ Error during fix attempt {attempt}: {e}")
                if attempt == self.max_fix_retries:
                    return None
                continue

        print(f"        ✗ Could not fix after {self.max_fix_retries} attempts")
        return None

    def _check_completeness(
        self,
        journey: PatientJourney,
        generated_resources: List[Dict[str, Any]],
        journey_description: str,
        patient_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check if the generated resources completely represent the patient journey.

        Args:
            journey: Original patient journey
            generated_resources: Resources generated so far
            journey_description: Formatted journey description
            patient_context: Optional additional context

        Returns:
            Dict with is_complete flag and any additional_resources needed
        """
        resources_summary = self._format_existing_resources(
            generated_resources)

        completeness_prompt = f"""You are a FHIR expert reviewing if generated resources completely represent a patient journey.

Patient Journey:
{journey_description}

{f"Additional Context: {patient_context}" if patient_context else ""}

Generated FHIR Resources:
{resources_summary}

Your task:
1. Review if the generated resources completely capture ALL events explicitly mentioned in the patient journey
2. Check if any explicitly mentioned clinical events, conditions, observations, procedures, or medications are missing
3. Determine if more resources are needed

CRITICAL RULES:
- ONLY request additional resources for items EXPLICITLY mentioned in the journey stages or context
- DO NOT request resources for "typical" events that aren't mentioned
- DO NOT infer missing resources based on clinical best practices
- If the journey mentions 2 medications, only those 2 should be in resources - don't add more
- Be conservative: when in doubt, mark as complete

Return a JSON object with this structure:
{{
    "is_complete": true or false,
    "reasoning": "Explanation of your assessment - cite specific journey stages for any missing resources",
    "additional_resources": [
        {{
            "resourceType": "Condition",
            "description": "Specific condition that needs to be documented (cite the journey stage that mentions it)",
            "key_data": ["relevant data points from the journey"]
        }}
        // Only if is_complete is false AND the resource is explicitly mentioned in the journey
    ]
}}

Remember: Only flag as incomplete if something explicitly mentioned in the journey is missing from resources."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a FHIR expert who assesses completeness of FHIR resource sets.",
                    },
                    {"role": "user", "content": completeness_prompt},
                ],

                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            print(f"\nCompleteness Check: {result.get('reasoning', '')}")

            return result

        except Exception as e:
            print(f"Error checking completeness: {e}")
            # Default to incomplete with no additional resources
            return {"is_complete": False, "additional_resources": []}

    def _print_generation_summary(
        self,
        initial_plan: GenerationPlan,
        generated_resources: List[Dict[str, Any]],
        validation_results: List[ValidationResult],
        success: bool,
        iterations: int,
    ):
        """
        Print a summary of the generation process.

        Args:
            initial_plan: The initial generation plan
            generated_resources: Resources that were successfully generated
            validation_results: All validation results
            success: Whether generation succeeded
            iterations: Number of iterations used
        """
        print("\n" + "=" * 70)
        print("GENERATION SUMMARY")
        print("=" * 70)

        # Overall status
        status_icon = "✓" if success else "✗"
        status_text = "SUCCESS" if success else "INCOMPLETE"
        print(f"\nStatus: {status_icon} {status_text}")
        print(f"Iterations Used: {iterations}")

        # Planned vs Built
        planned_count = len(initial_plan.resources_to_generate)
        built_count = len(generated_resources)
        print(f"\nResources Planned: {planned_count}")
        print(f"Resources Built: {built_count}")

        if planned_count > 0:
            success_rate = (built_count / planned_count) * 100
            print(f"Build Success Rate: {success_rate:.1f}%")

        # Show what was planned
        print(f"\nPlanned Resources:")
        for i, resource_spec in enumerate(initial_plan.resources_to_generate, 1):
            resource_type = resource_spec.get("resourceType")
            print(f"  {i}. {resource_type}")

        # Show what was built
        print(f"\nSuccessfully Built Resources:")
        if generated_resources:
            for i, resource in enumerate(generated_resources, 1):
                resource_type = resource.get("resourceType", "Unknown")
                resource_id = resource.get("id", "no-id")
                print(f"  {i}. {resource_type}/{resource_id}")
        else:
            print("  None")

        # Validation Summary
        total_validations = len(validation_results)
        valid_count = sum(1 for v in validation_results if v.is_valid)
        invalid_count = total_validations - valid_count

        print(f"\nValidation Results:")
        print(f"  Total Validations: {total_validations}")
        print(f"  ✓ Valid: {valid_count}")
        if invalid_count > 0:
            print(f"  ✗ Invalid/Fixed: {invalid_count}")

        # Show resources that needed fixing
        fixed_resources = []
        for i, validation in enumerate(validation_results):
            if not validation.is_valid:
                fixed_resources.append(validation.resource_type)

        if fixed_resources:
            print(f"\nResources That Needed Error Correction:")
            for resource_type in fixed_resources:
                print(f"  - {resource_type}")

        print("\n" + "=" * 70)

    def _format_journey_for_prompt(self, journey: PatientJourney) -> str:
        """Format a PatientJourney for inclusion in prompts."""
        lines = []
        if journey.patient_id:
            lines.append(f"Patient ID: {journey.patient_id}")
        if journey.summary:
            lines.append(f"Summary: {journey.summary}")

        lines.append(f"\nStages ({len(journey.stages)}):")
        for i, stage in enumerate(journey.stages, 1):
            lines.append(f"{i}. {stage.name}")
            if stage.description:
                lines.append(f"   Description: {stage.description}")
            if stage.metadata:
                lines.append(
                    f"   Metadata: {json.dumps(stage.metadata, indent=6)}")

        return "\n".join(lines)

    def _format_existing_resources(self, resources: List[Dict[str, Any]]) -> str:
        """Format existing resources for inclusion in prompts."""
        if not resources:
            return "None yet"

        lines = []
        for i, resource in enumerate(resources, 1):
            resource_type = resource.get("resourceType", "Unknown")
            resource_id = resource.get("id", "no-id")
            lines.append(f"{i}. {resource_type}/{resource_id}")

        return "\n".join(lines)

    def _format_resource_id_map(self, resource_id_map: Dict[str, str]) -> str:
        """Format resource ID map for inclusion in prompts."""
        if not resource_id_map:
            return ""

        lines = ["Resource IDs (use these when referencing other resources):"]
        for resource_type, resource_id in resource_id_map.items():
            lines.append(f"  - {resource_type}: {resource_id}")

        return "\n".join(lines)

    def _get_resource_specific_guidance(self, resource_type: str) -> str:
        """
        Get resource-specific guidance to help AI generate better resources.

        Args:
            resource_type: The FHIR resource type

        Returns:
            Formatted guidance string
        """
        guidance_map = {
            "Encounter": """
ENCOUNTER SPECIFIC GUIDANCE:
- status: REQUIRED. Must be one of: planned, arrived, triaged, in-progress, onleave, finished, cancelled, entered-in-error, unknown
- class: REQUIRED. Must be a LIST containing CodeableConcept objects (NOT just Coding)
  * Each CodeableConcept should have a 'coding' array
  * Use system "http://terminology.hl7.org/CodeSystem/v3-ActCode" with codes:
    - "EMER" for emergency encounters
    - "IMP" for inpatient encounters  
    - "AMB" for ambulatory/outpatient
- subject: REQUIRED. Reference to Patient resource
- CRITICAL: DO NOT include these fields (they cause validation errors):
  * period - Not supported in this library version
  * reasonCode - Not supported (use 'reason' if needed, but best to omit)

Example minimal Encounter (USE EXACTLY THIS STRUCTURE):
{
  "resourceType": "Encounter",
  "id": "example-id",
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
    "reference": "Patient/patient-id"
  }
}""",
            "Observation": """
OBSERVATION SPECIFIC GUIDANCE:
- status: REQUIRED. Must be one of: registered, preliminary, final, amended, corrected, cancelled, entered-in-error, unknown
- code: REQUIRED. Use CodeableConcept describing what was observed
- subject: REQUIRED. Reference to Patient resource
- component: For multi-component observations (like vital signs panel)
  * Each component needs: code (what was measured), and value[x] (the measurement)
  * Use valueQuantity for numeric measurements
  * DO NOT use "valueComponent" - this field doesn't exist
  * referenceRange: Must be a LIST (array), not a single object
- Use LOINC codes when possible (system: "http://loinc.org")

CRITICAL: If using referenceRange in components, it must be an array:
  "referenceRange": [{"text": "Normal range"}]  // CORRECT
  "referenceRange": {"text": "Normal range"}    // WRONG - causes validation error

Example minimal Observation:
{
  "resourceType": "Observation",
  "id": "example-id",
  "status": "final",
  "code": {
    "text": "Blood pressure"
  },
  "subject": {
    "reference": "Patient/patient-id"
  },
  "valueQuantity": {
    "value": 120,
    "unit": "mmHg",
    "system": "http://unitsofmeasure.org",
    "code": "mm[Hg]"
  }
}""",
            "Procedure": """
PROCEDURE SPECIFIC GUIDANCE:
- status: REQUIRED. Must be one of: preparation, in-progress, not-done, on-hold, stopped, completed, entered-in-error, unknown
- subject: REQUIRED. Reference to Patient resource
- code: REQUIRED. Use CodeableConcept with at least 'text' field describing the procedure
- encounter: Reference to Encounter if available
- Use SNOMED CT codes when possible (system: "http://snomed.info/sct")
- CRITICAL: DO NOT include performedDateTime or performedPeriod fields - they cause validation errors in this library version

Example minimal Procedure (USE EXACTLY THIS STRUCTURE):
{
  "resourceType": "Procedure",
  "id": "example-id",
  "status": "completed",
  "code": {
    "text": "Cardiac catheterization"
  },
  "subject": {
    "reference": "Patient/patient-id"
  }
}""",
            "MedicationRequest": """
MEDICATION REQUEST SPECIFIC GUIDANCE:
- status: REQUIRED. Must be one of: active, on-hold, cancelled, completed, entered-in-error, stopped, draft, unknown
- intent: REQUIRED. Must be one of: proposal, plan, order, original-order, reflex-order, filler-order, instance-order, option
- medication: REQUIRED. This is a CodeableReference type with structure:
  * Use "concept" subfield containing a CodeableConcept
  * The CodeableConcept should have at least a "text" field
- subject: REQUIRED. Reference to Patient resource
- authoredOn: When the prescription was written
- requester: Reference to Practitioner if available
- Use RxNorm codes when possible (system: "http://www.nlm.nih.gov/research/umls/rxnorm")

IMPORTANT: The field is named "medication" with a nested "concept" object

Example minimal MedicationRequest:
{
  "resourceType": "MedicationRequest",
  "id": "example-id",
  "status": "active",
  "intent": "order",
  "medication": {
    "concept": {
      "text": "Aspirin 325mg"
    }
  },
  "subject": {
    "reference": "Patient/patient-id"
  }
}""",
            "MedicationAdministration": """
MEDICATION ADMINISTRATION SPECIFIC GUIDANCE:
- status: REQUIRED. Must be one of: in-progress, not-done, on-hold, completed, entered-in-error, stopped, unknown
- medication: REQUIRED. This is a CodeableReference type with structure:
  * Use "concept" subfield containing a CodeableConcept
  * The CodeableConcept should have at least a "text" field
- subject: REQUIRED. Reference to Patient resource
- occurenceDateTime or occurencePeriod: When medication was given (use occurenceDateTime for single point in time)
- Use RxNorm codes when possible (system: "http://www.nlm.nih.gov/research/umls/rxnorm")

IMPORTANT: Field is named "medication" with nested "concept", and timing field is "occurenceDateTime"

Example minimal MedicationAdministration:
{
  "resourceType": "MedicationAdministration",
  "id": "example-id",
  "status": "completed",
  "medication": {
    "concept": {
      "text": "Aspirin 325mg"
    }
  },
  "subject": {
    "reference": "Patient/patient-id"
  },
  "occurenceDateTime": "2024-01-15T11:00:00Z"
}""",
            "Practitioner": """
PRACTITIONER SPECIFIC GUIDANCE:
- No fields are strictly required, but should include identifiable information
- active: Boolean indicating if the practitioner's record is in active use
- name: Use HumanName structure with family and given names
- identifier: Use to store professional identifiers (NPI, license numbers, etc.)
- qualification: Professional qualifications, certifications

Example minimal Practitioner:
{
  "resourceType": "Practitioner",
  "id": "example-id",
  "active": true,
  "name": [{
    "family": "Smith",
    "given": ["John"],
    "prefix": ["Dr."]
  }]
}""",
            "Organization": """
ORGANIZATION SPECIFIC GUIDANCE:
- No fields are strictly required, but should include identifiable information
- active: Boolean indicating if the organization's record is in active use
- name: Name of the organization
- type: Kind of organization (hospital, department, etc.)
- DO NOT include address field unless you have complete address information
- If you include address, ALL string fields (city, state, country, postalCode) must be non-empty and match pattern '[ \\r\\n\\t\\S]+'

Example minimal Organization (without address):
{
  "resourceType": "Organization",
  "id": "example-id",
  "active": true,
  "name": "Sample Hospital",
  "type": [{
    "text": "Healthcare Provider"
  }]
}""",
            "Location": """
LOCATION SPECIFIC GUIDANCE:
- status: Status of the location (active, suspended, inactive)
- name: Name of the location
- type: Type of location (e.g., Emergency Department, ICU)
- DO NOT include address field unless you have complete address information
- If you include address, ALL string fields (city, state, country, postalCode) must be non-empty and match pattern '[ \\r\\n\\t\\S]+'

Example minimal Location (without address):
{
  "resourceType": "Location",
  "id": "example-id",
  "status": "active",
  "name": "Emergency Department",
  "type": [{
    "coding": [{
      "system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode",
      "code": "EMD",
      "display": "Emergency Department"
    }]
  }]
}""",
            "DiagnosticReport": """
DIAGNOSTIC REPORT SPECIFIC GUIDANCE:
- status: REQUIRED. Must be one of: registered, partial, preliminary, final, amended, corrected, appended, cancelled, entered-in-error, unknown
- code: REQUIRED. Type of diagnostic report (use LOINC codes when possible)
- subject: REQUIRED. Reference to Patient
- encounter: Reference to Encounter if available
- effectiveDateTime or effectivePeriod: Time of report
- issued: REQUIRED. Date/time report was issued
- result: References to Observation resources
- Use LOINC codes when possible (system: "http://loinc.org")

Example minimal DiagnosticReport:
{
  "resourceType": "DiagnosticReport",
  "id": "example-id",
  "status": "final",
  "code": {
    "text": "ECG Report"
  },
  "subject": {
    "reference": "Patient/patient-id"
  },
  "issued": "2024-01-15T10:30:00Z"
}""",
            "Immunization": """
IMMUNIZATION SPECIFIC GUIDANCE:
- status: REQUIRED. Must be one of: completed, entered-in-error, not-done
- vaccineCode: REQUIRED. Vaccine product administered (use CVX codes when possible)
- patient: REQUIRED. Reference to Patient
- occurrenceDateTime or occurrenceString: REQUIRED. When immunization occurred
- primarySource: Boolean indicating if data came from primary source
- Use CVX codes for vaccines (system: "http://hl7.org/fhir/sid/cvx")

Example minimal Immunization:
{
  "resourceType": "Immunization",
  "id": "example-id",
  "status": "completed",
  "vaccineCode": {
    "text": "COVID-19 vaccine"
  },
  "patient": {
    "reference": "Patient/patient-id"
  },
  "occurrenceDateTime": "2024-01-15"
}""",
        }

        return guidance_map.get(resource_type, "")

    def _create_bundle(self, resources: List[Dict[str, Any]]) -> FHIRPatientData:
        """Create a FHIR Bundle from generated resources."""
        entries = []
        for resource in resources:
            entries.append({"resource": resource})

        return FHIRPatientData(
            resourceType="Bundle",
            entries=entries,
        )


# Convenience function
def generate_fhir_from_journey(
    journey: PatientJourney,
    patient_context: Optional[str] = None,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    fhir_version: Literal["R4", "R4B", "R5", "STU3"] = "R4",
    max_iterations: int = 5,
    max_fix_retries: int = 3,
    fhir_schema_path: Optional[str] = None,
    fhir_data_directory: Optional[str] = None,
    auto_save: bool = True,
    save_directory: str = "output",
    parallel_generation: bool = True,
    use_enhanced_context: bool = True,
) -> GenerationResult:
    """
    Convenience function to generate FHIR resources from a patient journey.

    Args:
        journey: PatientJourney to convert
        patient_context: Optional additional context about the patient
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        model: OpenAI model to use
        fhir_version: FHIR version to generate
        max_iterations: Maximum number of generation iterations
        max_fix_retries: Maximum number of attempts to fix validation errors per resource
        fhir_schema_path: Optional path to fhir.schema.json file (legacy)
        fhir_data_directory: Optional path to directory containing all FHIR data files (recommended)
        auto_save: Automatically save successful FHIR bundles to disk (default: True)
        save_directory: Directory to save generated bundles (default: "output")
        parallel_generation: Use parallel generation for faster results (default: True)
        use_enhanced_context: Use enhanced context with valuesets, profiles, etc. (default: True, recommended)

    Returns:
        GenerationResult with generated resources and validation status
    """
    agent = AIJourneyToFHIR(
        api_key=api_key,
        model=model,
        fhir_version=fhir_version,
        max_iterations=max_iterations,
        max_fix_retries=max_fix_retries,
        fhir_schema_path=fhir_schema_path,
        fhir_data_directory=fhir_data_directory,
        auto_save=auto_save,
        save_directory=save_directory,
        parallel_generation=parallel_generation,
        use_enhanced_context=use_enhanced_context,
    )
    return agent.generate_from_journey(journey, patient_context)
