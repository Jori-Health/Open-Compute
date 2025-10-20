"""
Example demonstrating enhanced FHIR context for improved generation quality.

This example shows how to use the enhanced context feature that loads:
- Value sets (valid coded values)
- Resource profiles (detailed constraints)
- Type profiles (data type definitions)
- Search parameters (important fields)

This provides much richer context to the AI, resulting in:
- More accurate coded values (status, priority, etc.)
- Better adherence to FHIR constraints
- Higher quality, more complete resources

Run this example:
    python examples/enhanced_context_example.py
"""

import os
from open_compute import (
    PatientJourney,
    JourneyStage,
    generate_fhir_from_journey,
    AIJourneyToFHIR,
)


def example_with_enhanced_context():
    """Example using enhanced FHIR context (RECOMMENDED)."""
    print("=" * 70)
    print("Example: Enhanced Context (RECOMMENDED)")
    print("=" * 70)
    print("\nThis example uses valuesets, profiles, and search parameters")
    print("to provide rich context for better FHIR generation.\n")

    # Create a patient journey
    journey = PatientJourney(
        patient_id="patient-enhanced-001",
        summary="Patient with hypertension and recent medication adjustment",
        stages=[
            JourneyStage(
                name="Initial Visit",
                description="Patient presents with elevated blood pressure",
                metadata={
                    "date": "2024-01-10",
                    "vital_signs": {
                        "blood_pressure": "160/95 mmHg",
                        "heart_rate": "82 bpm",
                    },
                },
            ),
            JourneyStage(
                name="Diagnosis",
                description="Diagnosed with Essential Hypertension",
                metadata={
                    "condition": "Essential (primary) hypertension",
                    "icd10_code": "I10",
                    "onset_date": "2024-01-10",
                },
            ),
            JourneyStage(
                name="Medication Prescribed",
                description="Started on Lisinopril for hypertension",
                metadata={
                    "medication": "Lisinopril 10mg",
                    "dosage": "10mg once daily",
                    "route": "oral",
                    "prescribed_date": "2024-01-10",
                },
            ),
            JourneyStage(
                name="Follow-up",
                description="2-week follow-up shows improvement",
                metadata={
                    "date": "2024-01-24",
                    "blood_pressure": "132/84 mmHg",
                    "adherence": "Good medication adherence reported",
                },
            ),
        ],
    )

    patient_context = """
    Patient is a 55-year-old female.
    History: No prior cardiac events, newly diagnosed hypertension.
    No allergies.
    Non-smoker.
    """

    # Generate FHIR with enhanced context (default)
    print("🚀 Generating FHIR with ENHANCED context...\n")

    result = generate_fhir_from_journey(
        journey=journey,
        patient_context=patient_context,
        model="gpt-5-mini",
        fhir_version="R4",
        max_iterations=3,
        use_enhanced_context=True,  # This is the default
    )

    print(f"\n{'='*70}")
    print("RESULTS WITH ENHANCED CONTEXT")
    print("=" * 70)
    print(f"Success: {result.success}")
    print(f"Resources Generated: {len(result.generated_resources)}")

    # Show examples of improved quality
    print("\n📊 Quality Improvements with Enhanced Context:")
    print("   ✓ Coded values use valid FHIR valuesets")
    print("   ✓ Status fields use correct enumerated values")
    print("   ✓ Important fields are populated based on search parameters")
    print("   ✓ Resource constraints from profiles are followed")

    for resource in result.generated_resources:
        resource_type = resource.get("resourceType", "Unknown")
        print(f"\n{resource_type}:")

        # Show key fields that benefit from enhanced context
        if "status" in resource:
            print(f"  ✓ status: '{resource['status']}' (from valueset)")
        if "priority" in resource:
            print(f"  ✓ priority: '{resource['priority']}' (from valueset)")
        if "intent" in resource:
            print(f"  ✓ intent: '{resource['intent']}' (from valueset)")
        if "category" in resource:
            print(f"  ✓ category: {resource['category']}")

    return result


def example_without_enhanced_context():
    """Example WITHOUT enhanced context (for comparison)."""
    print("\n\n" + "=" * 70)
    print("Example: Basic Context (for comparison)")
    print("=" * 70)
    print("\nThis example uses only basic schema without enhanced context.\n")

    # Same journey as before
    journey = PatientJourney(
        patient_id="patient-basic-001",
        summary="Patient with hypertension",
        stages=[
            JourneyStage(
                name="Visit",
                description="Hypertension diagnosis and treatment",
                metadata={"date": "2024-01-10"},
            ),
        ],
    )

    print("🚀 Generating FHIR with BASIC context only...\n")

    result = generate_fhir_from_journey(
        journey=journey,
        model="gpt-5-mini",
        fhir_version="R4",
        max_iterations=2,
        use_enhanced_context=False,  # Disable enhanced context
    )

    print(f"\n{'='*70}")
    print("RESULTS WITH BASIC CONTEXT")
    print("=" * 70)
    print(f"Success: {result.success}")
    print(f"Resources Generated: {len(result.generated_resources)}")
    print("\n⚠️  Note: May have less accurate coded values and field usage")

    return result


def example_custom_data_directory():
    """Example specifying a custom FHIR data directory."""
    print("\n\n" + "=" * 70)
    print("Example: Custom Data Directory")
    print("=" * 70)

    # You can explicitly specify where FHIR data files are located
    custom_data_dir = "/Users/bkyritz/Code/Jori/Open-Compute/data/fhir/STU6"

    journey = PatientJourney(
        patient_id="patient-custom-001",
        summary="Simple test",
        stages=[
            JourneyStage(
                name="Test",
                description="Test stage",
            ),
        ],
    )

    print(f"Using custom data directory: {custom_data_dir}\n")

    agent = AIJourneyToFHIR(
        model="gpt-5-mini",
        fhir_version="R4",
        fhir_data_directory=custom_data_dir,
        use_enhanced_context=True,
    )

    result = agent.generate_from_journey(journey)

    print(f"\nSuccess: {result.success}")
    return result


def main():
    """Run all examples."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Please set OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='your-api-key-here'")
        return

    print("Enhanced FHIR Context Examples")
    print("=" * 70)
    print("\nThese examples demonstrate the improved quality when using")
    print("enhanced context with valuesets, profiles, and other FHIR data.\n")

    try:
        # Run the enhanced context example (recommended approach)
        example_with_enhanced_context()

        # Uncomment to compare with basic context:
        # example_without_enhanced_context()

        # Uncomment to see custom data directory usage:
        # example_custom_data_directory()

    except Exception as e:
        print(f"\n❌ Error running example: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
