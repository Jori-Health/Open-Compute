"""
Example usage of AI-powered Journey to FHIR generation.

This example demonstrates how to:
1. Create a patient journey
2. Use AI to generate comprehensive FHIR resources
3. Validate the resources
4. Iteratively refine until complete

Requirements:
- Set your OpenAI API key as an environment variable: OPENAI_API_KEY
- Or pass it directly to the function

Run this example:
    python examples/ai_journey_to_fhir_example.py
"""

import os
import json
from open_compute import (
    PatientJourney,
    JourneyStage,
    generate_fhir_from_journey,
    AIJourneyToFHIR,
)


def example_basic_usage():
    """Basic example of generating FHIR from a journey."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    # Create a patient journey
    journey = PatientJourney(
        patient_id="patient-123",
        summary="58 year old male presents to ER with chest pain and is diagnosed with acute myocardial infarction",
        stages=[
            JourneyStage(
                name="Registration",
                description="Patient registered in ER",
                metadata={
                    "timestamp": "2024-01-15T10:30:00Z",
                    "location": "Emergency Department",
                },
            ),
            JourneyStage(
                name="Triage",
                description="Initial assessment - chest pain, elevated BP",
                metadata={
                    "vital_signs": {
                        "blood_pressure": "150/95 mmHg",
                        "heart_rate": "88 bpm",
                        "temperature": "98.6 F",
                    },
                    "chief_complaint": "Chest pain",
                },
            ),
            JourneyStage(
                name="Diagnosis",
                description="Diagnosed with acute myocardial infarction",
                metadata={
                    "condition": "Acute myocardial infarction",
                    "icd10_code": "I21.9",
                },
            ),
            JourneyStage(
                name="Treatment",
                description="Administered aspirin and nitroglycerin",
                metadata={
                    "medications": ["Aspirin 325mg", "Nitroglycerin 0.4mg"],
                },
            ),
            JourneyStage(
                name="Procedure",
                description="Emergency cardiac catheterization performed",
                metadata={
                    "procedure": "Cardiac catheterization",
                    "timestamp": "2024-01-15T12:00:00Z",
                },
            ),
        ],
    )

    # Additional context about the patient
    patient_context = """
    Patient is a 58-year-old male with history of hypertension.
    No prior cardiac events.
    Non-smoker, occasional alcohol use.
    """

    # Generate FHIR resources using AI
    # Make sure OPENAI_API_KEY is set in your environment
    # Note: auto_save is enabled by default, so resources will be saved to output/firstname_lastname/
    result = generate_fhir_from_journey(
        journey=journey,
        patient_context=patient_context,
        model="gpt-4o-mini",
        fhir_version="R4",
        max_iterations=1,
        auto_save=True,  # Automatically saves to output/firstname_lastname/ folder
    )

    # Check results
    print(f"\n{'='*60}")
    print("Generation Results")
    print("=" * 60)
    print(f"Success: {result.success}")
    print(f"Iterations: {result.iterations}")
    print(f"Resources Generated: {len(result.generated_resources)}")

    if result.planning_details:
        print(f"\nPlanning Rationale: {result.planning_details.rationale}")

    print("\nGenerated Resources:")
    for i, resource in enumerate(result.generated_resources, 1):
        resource_type = resource.get("resourceType", "Unknown")
        resource_id = resource.get("id", "no-id")
        print(f"  {i}. {resource_type}/{resource_id}")

    print("\nValidation Results:")
    for i, validation in enumerate(result.validation_results, 1):
        status = "✓ Valid" if validation.is_valid else "✗ Invalid"
        print(f"  {i}. {validation.resource_type}: {status}")
        if not validation.is_valid:
            for error in validation.errors:
                print(f"     - {error}")

    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  - {error}")

    # Files are automatically saved to output/firstname_lastname/ folder with:
    # - patient_bundle.json: Complete FHIR Bundle
    # - bulk_fhir.jsonl: All resources in JSONL format (one resource per line)
    # - README.txt: Summary of generated resources

    return result


def main():
    """Run all examples."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Please set OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='your-api-key-here'")
        return

    print("Patient Journey to FHIR Generation")
    print("=" * 60)
    print("\nThese examples will use the OpenAI API to generate FHIR resources.")
    print("This may take a minute or two...")

    # Run examples
    try:
        example_basic_usage()

    except Exception as e:
        print(f"\n❌ Error running example: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
