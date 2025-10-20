"""
AI-powered agent to generate FHIR resources from a patient journey.

This module uses OpenAI's API to intelligently generate FHIR resources
that represent a complete patient journey, with validation and iterative
refinement.
"""

import json
import os
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal
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


@dataclass
class GenerationPlan:
    """Plan for generating FHIR resources."""
    resources_to_generate: List[Dict[str, Any]] = field(default_factory=list)
    rationale: str = ""


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
        model: str = "gpt-5-mini",
        fhir_version: Literal["R4", "R4B", "R5", "STU3"] = "R4",
        max_iterations: int = 5,
        max_fix_retries: int = 3,
        fhir_schema_path: Optional[str] = None,
        auto_save: bool = True,
        save_directory: str = "generated_fhir",
        parallel_generation: bool = True,
    ):
        """
        Initialize the AI agent.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use
            fhir_version: FHIR version to generate
            max_iterations: Maximum number of generation iterations
            max_fix_retries: Maximum number of attempts to fix validation errors per resource
            fhir_schema_path: Optional path to fhir.schema.json file for enhanced context
            auto_save: Automatically save successful FHIR bundles to disk
            save_directory: Directory to save generated bundles (default: "generated_fhir")
            parallel_generation: Use parallel generation for faster results (recommended)
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
        self.schema_loader = get_schema_loader(fhir_schema_path)
        self.auto_save = auto_save
        self.save_directory = save_directory
        self.parallel_generation = parallel_generation

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

        # Step 2: Generate resources iteratively with validation
        print(
            f"\n⚙️  STEP 2: Generating Resources (max {self.max_iterations} iterations)...")
        result = self._iterative_generation(journey, plan, patient_context)

        # Step 3: Auto-save if enabled and successful
        if self.auto_save and result.success and result.fhir_data:
            print(f"\n💾 STEP 3: Auto-Saving Bundle...")
            saved_path = self._save_bundle(result.fhir_data, journey)
            if saved_path:
                print(f"✓ Auto-saved FHIR bundle to: {saved_path}")

        return result

    def _save_bundle(self, fhir_data: FHIRPatientData, journey: PatientJourney) -> Optional[str]:
        """
        Save a FHIR bundle to disk.

        Args:
            fhir_data: FHIR bundle to save
            journey: Original journey (for filename)

        Returns:
            Path to saved file, or None if save failed
        """
        try:
            # Create save directory if it doesn't exist
            save_dir = Path(self.save_directory)
            save_dir.mkdir(parents=True, exist_ok=True)

            # Create filename with timestamp and patient ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            patient_id = journey.patient_id or "unknown"
            filename = f"fhir_bundle_{patient_id}_{timestamp}.json"
            filepath = save_dir / filename

            # Create bundle structure
            bundle = {
                "resourceType": "Bundle",
                "type": "collection",
                "timestamp": datetime.now().isoformat(),
                "entry": fhir_data.entries,
            }

            # Save to file
            with open(filepath, 'w') as f:
                json.dump(bundle, f, indent=2)

            return str(filepath)

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
1. Identify ALL FHIR resources needed to represent this patient journey completely
2. For each resource, specify:
   - resourceType (e.g., Patient, Encounter, Condition, Observation, Procedure, MedicationRequest, etc.)
   - A brief description of what the resource should contain
   - Key data points from the journey that should be included

Return your response as a JSON object with this structure:
{{
    "rationale": "Brief explanation of your approach",
    "resources": [
        {{
            "resourceType": "Patient",
            "description": "Basic patient demographics and identifiers",
            "key_data": ["patient_id", "demographics if available"]
        }},
        {{
            "resourceType": "Encounter",
            "description": "Hospital admission encounter",
            "key_data": ["admission date", "reason for visit"]
        }}
        // ... more resources
    ]
}}

Be comprehensive - include all relevant resource types for a complete clinical picture."""

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

            return GenerationPlan(
                resources_to_generate=plan_data.get("resources", []),
                rationale=plan_data.get("rationale", ""),
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

                import time
                start_time = time.time()
                batch_results = asyncio.run(
                    self._generate_resources_parallel(
                        resources_to_generate, journey, generated_resources, patient_context
                    )
                )
                elapsed = time.time() - start_time
                print(f"   ✓ All API calls completed in {elapsed:.1f}s")

                # Process parallel results
                print(
                    f"\n📝 Processing and validating {len(batch_results)} generated resources...")
                for idx, (resource_spec, generated_resource) in enumerate(zip(resources_to_generate, batch_results)):
                    resource_type = resource_spec.get("resourceType")
                    print(
                        f"\n  [{idx+1}/{len(resources_to_generate)}] {resource_type}")

                    if not generated_resource:
                        errors.append(f"Failed to generate {resource_type}")
                        continue

                    # Validate the resource
                    print(f"     🔍 Validating...")
                    validation = self.validator.validate(generated_resource)
                    validation_results.append(validation)

                    if validation.is_valid:
                        print(f"     ✓ Validation passed")
                        generated_resources.append(generated_resource)
                        print(f"     ✅ {resource_type} completed!")
                    else:
                        print(f"     ✗ Validation failed:")
                        for error in validation.errors:
                            print(f"        • {error}")

                        # Try to fix the resource
                        print(
                            f"     🔧 Attempting to fix (max {self.max_fix_retries} attempts)...")
                        fixed_resource = self._fix_invalid_resource(
                            generated_resource,
                            validation,
                            resource_spec,
                            journey,
                            generated_resources,
                            patient_context,
                        )

                        if fixed_resource:
                            # Validate the fixed resource
                            print(f"     🔍 Re-validating fixed resource...")
                            fixed_validation = self.validator.validate(
                                fixed_resource)
                            validation_results.append(fixed_validation)

                            if fixed_validation.is_valid:
                                print(f"     ✓ Validation passed after fix!")
                                generated_resources.append(fixed_resource)
                                print(f"     ✅ {resource_type} completed!")
                            else:
                                print(
                                    f"     ✗ Still invalid after {self.max_fix_retries} attempts")
                                errors.append(
                                    f"Validation failed for {resource_type} after {self.max_fix_retries} attempts: {fixed_validation.errors}"
                                )
                        else:
                            errors.append(
                                f"Validation failed for {resource_type}: {validation.errors}"
                            )
            else:
                # Sequential generation (for single resource or when parallel disabled)
                for resource_spec in resources_to_generate:
                    resource_type = resource_spec.get("resourceType")
                    print(f"Generating {resource_type}...")

                    # Generate the resource
                    generated_resource = self._generate_single_resource(
                        resource_spec, journey, generated_resources, patient_context
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
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a single FHIR resource using AI.

        Args:
            resource_spec: Specification for the resource to generate
            journey: Original patient journey
            existing_resources: Already generated resources for reference
            patient_context: Optional additional context

        Returns:
            Generated FHIR resource as dict, or None if generation failed
        """
        resource_type = resource_spec.get("resourceType")
        description = resource_spec.get("description", "")
        key_data = resource_spec.get("key_data", [])

        journey_description = self._format_journey_for_prompt(journey)
        existing_resources_summary = self._format_existing_resources(
            existing_resources)

        # Get FHIR schema context for this resource type
        schema_context = self.schema_loader.format_schema_for_prompt(
            resource_type)

        generation_prompt = f"""Generate a valid FHIR {self.fhir_version} {resource_type} resource.

Patient Journey:
{journey_description}

{f"Additional Context: {patient_context}" if patient_context else ""}

Resource to Generate: {resource_type}
Description: {description}
Key Data Points: {', '.join(key_data) if key_data else 'All relevant data from journey'}

Already Generated Resources:
{existing_resources_summary}

{schema_context}

Requirements:
1. Generate a complete, valid FHIR {self.fhir_version} {resource_type} resource
2. Include all required fields for {resource_type} (see schema above)
3. Use proper FHIR data types and structures as defined in the schema
4. Reference other resources appropriately (e.g., Patient/{{id}})
5. Extract data from the journey stages and context
6. Use appropriate coding systems (LOINC, SNOMED CT, RxNorm, etc.)
7. Follow the property descriptions from the schema
8. Return ONLY the JSON for the {resource_type} resource, no explanations

Return the resource as a valid JSON object."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a FHIR expert who generates valid FHIR {self.fhir_version} resources. You always return valid JSON.",
                    },
                    {"role": "user", "content": generation_prompt},
                ],

                response_format={"type": "json_object"},
            )

            resource_json = response.choices[0].message.content
            resource = json.loads(resource_json)

            # Ensure resourceType is set
            resource["resourceType"] = resource_type

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
    ) -> Optional[Dict[str, Any]]:
        """
        Async version of _generate_single_resource for parallel execution.

        Args:
            resource_spec: Specification for the resource to generate
            journey: Original patient journey
            existing_resources: Already generated resources for reference
            patient_context: Optional additional context

        Returns:
            Generated FHIR resource as dict, or None if generation failed
        """
        resource_type = resource_spec.get("resourceType")
        description = resource_spec.get("description", "")
        key_data = resource_spec.get("key_data", [])

        journey_description = self._format_journey_for_prompt(journey)
        existing_resources_summary = self._format_existing_resources(
            existing_resources)

        # Get FHIR schema context for this resource type
        schema_context = self.schema_loader.format_schema_for_prompt(
            resource_type)

        generation_prompt = f"""Generate a valid FHIR {self.fhir_version} {resource_type} resource.

Patient Journey:
{journey_description}

{f"Additional Context: {patient_context}" if patient_context else ""}

Resource to Generate: {resource_type}
Description: {description}
Key Data Points: {', '.join(key_data) if key_data else 'All relevant data from journey'}

Already Generated Resources:
{existing_resources_summary}

{schema_context}

Requirements:
1. Generate a complete, valid FHIR {self.fhir_version} {resource_type} resource
2. Include all required fields for {resource_type} (see schema above)
3. Use proper FHIR data types and structures as defined in the schema
4. Reference other resources appropriately (e.g., Patient/{{id}})
5. Extract data from the journey stages and context
6. Use appropriate coding systems (LOINC, SNOMED CT, RxNorm, etc.)
7. Follow the property descriptions from the schema
8. Return ONLY the JSON for the {resource_type} resource, no explanations

Return the resource as a valid JSON object."""

        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a FHIR expert who generates valid FHIR {self.fhir_version} resources. You always return valid JSON.",
                    },
                    {"role": "user", "content": generation_prompt},
                ],

                response_format={"type": "json_object"},
            )

            resource_json = response.choices[0].message.content
            resource = json.loads(resource_json)

            # Ensure resourceType is set
            resource["resourceType"] = resource_type

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
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Generate multiple FHIR resources in parallel using async API calls.

        Args:
            resource_specs: List of resource specifications to generate
            journey: Original patient journey
            existing_resources: Already generated resources for reference
            patient_context: Optional additional context

        Returns:
            List of generated resources (same order as input specs)
        """
        tasks = [
            self._generate_single_resource_async(
                resource_spec, journey, existing_resources, patient_context
            )
            for resource_spec in resource_specs
        ]

        return await asyncio.gather(*tasks)

    def _fix_invalid_resource(
        self,
        invalid_resource: Dict[str, Any],
        validation_result: ValidationResult,
        resource_spec: Dict[str, Any],
        journey: PatientJourney,
        existing_resources: List[Dict[str, Any]],
        patient_context: Optional[str] = None,
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

        Returns:
            Fixed FHIR resource as dict, or None if fixing failed
        """
        resource_type = invalid_resource.get("resourceType", "Unknown")

        # Format the errors for the AI
        errors_text = "\n".join(
            f"- {error}" for error in validation_result.errors)

        journey_description = self._format_journey_for_prompt(journey)
        existing_resources_summary = self._format_existing_resources(
            existing_resources)

        # Get FHIR schema context for this resource type
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

{schema_context}

Requirements:
1. Fix ALL validation errors listed above
2. Maintain the clinical meaning and data from the original resource
3. Ensure all required fields for {resource_type} are present and correct (see schema above)
4. Use proper FHIR {self.fhir_version} data types and structures as defined in the schema
5. Reference other resources appropriately (e.g., Patient/{{id}})
6. Use appropriate coding systems (LOINC, SNOMED CT, RxNorm, etc.)
7. Follow the property descriptions from the schema
8. Return ONLY the corrected JSON for the {resource_type} resource

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
1. Review if the generated resources completely capture the patient journey
2. Check if any important clinical events, conditions, observations, procedures, medications, etc. are missing
3. Determine if more resources are needed

Return a JSON object with this structure:
{{
    "is_complete": true or false,
    "reasoning": "Explanation of your assessment",
    "additional_resources": [
        {{
            "resourceType": "Condition",
            "description": "Specific condition that needs to be documented",
            "key_data": ["relevant data points"]
        }}
        // Only if is_complete is false
    ]
}}"""

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
    model: str = "gpt-5-mini",
    fhir_version: Literal["R4", "R4B", "R5", "STU3"] = "R4",
    max_iterations: int = 5,
    max_fix_retries: int = 3,
    fhir_schema_path: Optional[str] = None,
    auto_save: bool = True,
    save_directory: str = "generated_fhir",
    parallel_generation: bool = True,
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
        fhir_schema_path: Optional path to fhir.schema.json file for enhanced context
        auto_save: Automatically save successful FHIR bundles to disk (default: True)
        save_directory: Directory to save generated bundles (default: "generated_fhir")
        parallel_generation: Use parallel generation for faster results (default: True)

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
        auto_save=auto_save,
        save_directory=save_directory,
        parallel_generation=parallel_generation,
    )
    return agent.generate_from_journey(journey, patient_context)
