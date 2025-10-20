"""
Example demonstrating the error correction feature.

This example shows how the AI agent can automatically detect validation errors
and fix them by reading the error messages and generating corrected resources.

Run this example:
    python examples/error_correction_example.py
"""

import os
from open_compute import (
    PatientJourney,
    JourneyStage,
    AIJourneyToFHIR,
    generate_fhir_from_journey,
)


def example_with_error_correction():
    """
    Example showing error correction in action.

    The AI will:
    1. Generate FHIR resources from the journey
    2. If any validation errors occur, it will:
       - Read the error messages
       - Understand what's wrong
       - Generate a corrected version
       - Retry up to max_fix_retries times
    """
    print("=" * 70)
    print("Example: AI Error Correction")
    print("=" * 70)

    # Create a complex journey that might have validation challenges
    journey = PatientJourney(
        patient_id="patient-789",
        summary="Complex multi-day hospital admission",
        stages=[
            JourneyStage(
                name="Emergency Admission",
                description="Admitted via ER with severe pneumonia",
                metadata={
                    "timestamp": "2024-01-10T22:15:00Z",
                    "chief_complaint": "Shortness of breath, fever",
                    "severity": "severe",
                },
            ),
            JourneyStage(
                name="Initial Assessment",
                description="Vital signs and initial labs",
                metadata={
                    "vital_signs": {
                        "temperature": "39.2 C",
                        "heart_rate": "105 bpm",
                        "respiratory_rate": "24 breaths/min",
                        "oxygen_saturation": "89% on room air",
                        "blood_pressure": "135/88 mmHg",
                    },
                    "labs": {
                        "WBC": "15,000/μL",
                        "CRP": "185 mg/L",
                    },
                },
            ),
            JourneyStage(
                name="Diagnosis",
                description="Diagnosed with community-acquired pneumonia",
                metadata={
                    "diagnosis": "Community-acquired pneumonia",
                    "icd10": "J18.9",
                    "severity": "Severe",
                },
            ),
            JourneyStage(
                name="Imaging",
                description="Chest X-ray shows right lower lobe infiltrate",
                metadata={
                    "procedure": "Chest X-ray",
                    "findings": "Right lower lobe infiltrate, no effusion",
                    "impression": "Consistent with pneumonia",
                },
            ),
            JourneyStage(
                name="Treatment Started",
                description="Started on IV antibiotics and oxygen",
                metadata={
                    "medications": [
                        "Ceftriaxone 2g IV daily",
                        "Azithromycin 500mg IV daily",
                    ],
                    "oxygen": "2L nasal cannula",
                },
            ),
            JourneyStage(
                name="Day 2 - Improvement",
                description="Patient showing improvement",
                metadata={
                    "status": "Improved",
                    "oxygen_saturation": "94% on 2L",
                    "temperature": "37.8 C",
                },
            ),
            JourneyStage(
                name="Day 4 - Discharge",
                description="Discharged home on oral antibiotics",
                metadata={
                    "discharge_medications": ["Amoxicillin-clavulanate 875mg PO BID"],
                    "follow_up": "Primary care in 1 week",
                },
            ),
        ],
    )

    patient_context = """
    Patient is a 67-year-old male with history of:
    - COPD (chronic obstructive pulmonary disease)
    - Type 2 Diabetes
    - Hypertension
    - Former smoker (quit 5 years ago)
    
    Current medications before admission:
    - Metformin 1000mg BID
    - Lisinopril 10mg daily
    - Albuterol inhaler PRN
    """

    # Generate FHIR with error correction enabled
    print("\nGenerating FHIR resources with automatic error correction...\n")

    agent = AIJourneyToFHIR(
        model="gpt-5-mini",
        max_iterations=3,
        max_fix_retries=3,  # Will try up to 3 times to fix each resource
    )

    result = agent.generate_from_journey(journey, patient_context)

    # Display results
    print("\n" + "=" * 70)
    print("Results")
    print("=" * 70)
    print(f"Success: {result.success}")
    print(f"Total Iterations: {result.iterations}")
    print(f"Resources Generated: {len(result.generated_resources)}")

    print("\nGenerated Resources:")
    for i, resource in enumerate(result.generated_resources, 1):
        resource_type = resource.get("resourceType", "Unknown")
        resource_id = resource.get("id", "no-id")
        print(f"  {i}. {resource_type}/{resource_id}")

    print("\nValidation Summary:")
    validation_passed = sum(1 for v in result.validation_results if v.is_valid)
    validation_total = len(result.validation_results)
    print(f"  Passed: {validation_passed}/{validation_total}")

    # Show any resources that had errors but were fixed
    print("\nError Correction Summary:")
    fixed_count = 0
    for validation in result.validation_results:
        if not validation.is_valid:
            fixed_count += 1
            print(f"  - {validation.resource_type}: Had errors, attempted fix")

    if fixed_count == 0:
        print("  ✓ All resources generated correctly on first try!")

    if result.errors:
        print("\nRemaining Errors:")
        for error in result.errors:
            print(f"  - {error}")

    # Save the bundle
    if result.fhir_data:
        import json
        output_file = "corrected_fhir_bundle.json"
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": result.fhir_data.entries,
        }
        with open(output_file, "w") as f:
            json.dump(bundle, f, indent=2)
        print(f"\n✓ FHIR bundle saved to: {output_file}")

    return result


def example_custom_fix_retries():
    """
    Example showing how to configure the number of fix attempts.
    """
    print("\n\n" + "=" * 70)
    print("Example: Custom Fix Retry Configuration")
    print("=" * 70)

    journey = PatientJourney(
        patient_id="patient-simple",
        summary="Simple outpatient visit",
        stages=[
            JourneyStage(
                name="Visit",
                description="Routine checkup",
                metadata={"blood_pressure": "120/80 mmHg"},
            ),
        ],
    )

    # You can configure how many times to retry fixes
    result = generate_fhir_from_journey(
        journey=journey,
        patient_context="Healthy 45-year-old",
        model="gpt-5-mini",
        max_iterations=2,
        max_fix_retries=5,  # Try up to 5 times to fix validation errors
    )

    print(f"\nGenerated {len(result.generated_resources)} resources")
    print(f"Success: {result.success}")


def example_understanding_output():
    """
    Example explaining what you'll see in the output.
    """
    print("\n\n" + "=" * 70)
    print("Example: Understanding Error Correction Output")
    print("=" * 70)
    print("""
When error correction happens, you'll see output like:

=== Iteration 1/3 ===
Generating Patient...
  ✓ Patient validated successfully

Generating MedicationRequest...
  ✗ MedicationRequest validation failed:
    - Field required [type=missing, input_value=..., input_type=dict]
  → Attempting to fix MedicationRequest...
    Attempt 1/3...
    ✓ Fixed successfully on attempt 1
  ✓ MedicationRequest fixed and validated successfully!

This shows:
1. Initial generation failed validation
2. System detected the error
3. AI read the error message
4. AI generated a corrected version
5. Correction was successful!

If fixing fails after max_fix_retries attempts:
  → Attempting to fix MedicationRequest...
    Attempt 1/3...
    Still has errors, trying again...
    Attempt 2/3...
    Still has errors, trying again...
    Attempt 3/3...
    ✗ Could not fix after 3 attempts
  ✗ MedicationRequest still invalid after fixes

The resource will be skipped, but generation continues.
    """)


def main():
    """Run all examples."""
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Please set OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='your-api-key-here'")
        return

    print("AI Error Correction Examples")
    print("=" * 70)
    print("\nThese examples show how the AI automatically detects and fixes")
    print("validation errors in generated FHIR resources.")
    print("=" * 70)

    try:
        # Run the main example
        example_with_error_correction()

        # Show understanding
        example_understanding_output()

        # Uncomment to run additional examples:
        # example_custom_fix_retries()

    except Exception as e:
        print(f"\n❌ Error running example: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
