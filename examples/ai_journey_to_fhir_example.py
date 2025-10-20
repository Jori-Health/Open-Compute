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
        summary="Emergency room visit for chest pain",
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
    result = generate_fhir_from_journey(
        journey=journey,
        patient_context=patient_context,
        model="gpt-5-mini",
        fhir_version="R4",
        max_iterations=3,
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

    # Save the generated FHIR bundle
    if result.fhir_data:
        output_file = "generated_fhir_bundle.json"
        bundle_dict = {
            "resourceType": result.fhir_data.resourceType,
            "type": "collection",
            "entry": result.fhir_data.entries,
        }
        with open(output_file, "w") as f:
            json.dump(bundle_dict, f, indent=2)
        print(f"\n✓ FHIR bundle saved to: {output_file}")

    return result


def example_advanced_usage():
    """Advanced example with more control."""
    print("\n\n" + "=" * 60)
    print("Example 2: Advanced Usage with Custom Configuration")
    print("=" * 60)

    # Create a more complex patient journey
    journey = PatientJourney(
        patient_id="patient-456",
        summary="Type 2 Diabetes management and complications",
        stages=[
            JourneyStage(
                name="Initial Diagnosis",
                description="Type 2 Diabetes diagnosed during routine checkup",
                metadata={
                    "date": "2023-06-01",
                    "hba1c": "8.2%",
                    "fasting_glucose": "165 mg/dL",
                },
            ),
            JourneyStage(
                name="Medication Start",
                description="Started on Metformin",
                metadata={
                    "medication": "Metformin 500mg twice daily",
                    "prescriber": "Dr. Smith",
                },
            ),
            JourneyStage(
                name="Follow-up Visit",
                description="3-month follow-up, poor glucose control",
                metadata={
                    "date": "2023-09-01",
                    "hba1c": "7.8%",
                    "adherence": "reported missed doses",
                },
            ),
            JourneyStage(
                name="Complication",
                description="Developed diabetic neuropathy",
                metadata={
                    "complication": "Diabetic peripheral neuropathy",
                    "symptoms": "numbness and tingling in feet",
                },
            ),
            JourneyStage(
                name="Referral",
                description="Referred to endocrinologist and podiatrist",
                metadata={
                    "referrals": ["Endocrinology", "Podiatry"],
                },
            ),
        ],
    )

    patient_context = """
    Patient is a 62-year-old female.
    BMI: 32 (obese)
    History: Hypertension, hyperlipidemia
    Family history of diabetes (mother, sister)
    Sedentary lifestyle
    """

    # Use the class directly for more control
    agent = AIJourneyToFHIR(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-5-mini",
        fhir_version="R4",
        max_iterations=5,
    )

    result = agent.generate_from_journey(journey, patient_context)

    print(f"\nGeneration completed in {result.iterations} iterations")
    print(f"Generated {len(result.generated_resources)} resources")

    # You can access individual resources
    for resource in result.generated_resources:
        if resource.get("resourceType") == "Patient":
            print("\nPatient Resource Summary:")
            print(f"  ID: {resource.get('id')}")
            print(f"  Gender: {resource.get('gender', 'not specified')}")
            if "name" in resource:
                names = resource.get("name", [])
                if names:
                    print(f"  Name: {names[0].get('family', '')}")

    return result


def example_simple_journey():
    """Simple example with a short journey."""
    print("\n\n" + "=" * 60)
    print("Example 3: Simple Outpatient Visit")
    print("=" * 60)

    journey = PatientJourney(
        patient_id="patient-789",
        summary="Routine annual physical exam",
        stages=[
            JourneyStage(
                name="Check-in",
                description="Patient arrives for annual physical",
                metadata={"appointment_type": "annual_physical"},
            ),
            JourneyStage(
                name="Vitals",
                description="Vital signs recorded",
                metadata={
                    "blood_pressure": "120/80 mmHg",
                    "heart_rate": "72 bpm",
                    "weight": "165 lbs",
                    "height": "5'9\"",
                },
            ),
            JourneyStage(
                name="Exam",
                description="Physical examination completed",
                metadata={"findings": "All systems normal"},
            ),
            JourneyStage(
                name="Lab Orders",
                description="Ordered routine bloodwork",
                metadata={
                    "tests": ["CBC", "Lipid panel", "HbA1c", "TSH"],
                },
            ),
        ],
    )

    result = generate_fhir_from_journey(
        journey=journey,
        patient_context="Healthy 45-year-old male, no chronic conditions",
        model="gpt-5-mini",
        max_iterations=2,
    )

    print(f"\nGenerated {len(result.generated_resources)} FHIR resources")
    print(f"Success: {result.success}")

    return result


def main():
    """Run all examples."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Please set OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='your-api-key-here'")
        return

    print("AI-Powered Journey to FHIR Generation Examples")
    print("=" * 60)
    print("\nThese examples will use the OpenAI API to generate FHIR resources.")
    print("This may take a minute or two...")

    # Run examples
    try:
        example_basic_usage()
        # Uncomment to run additional examples:
        # example_advanced_usage()
        # example_simple_journey()

    except Exception as e:
        print(f"\n❌ Error running example: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
