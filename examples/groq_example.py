"""
Example demonstrating Groq integration with Open-Compute.

This example shows how to use Groq for fast FHIR generation.

Requirements:
- Set GROQ_API_KEY environment variable
- Optionally set LLM_PROVIDER=groq (will be used explicitly in this example)

Run this example:
    export GROQ_API_KEY='your-groq-api-key'
    python examples/groq_example.py
"""

import os
from open_compute import (
    PatientJourney,
    JourneyStage,
    generate_fhir_from_journey,
)


def main():
    """Example using Groq for FHIR generation."""

    # Check for Groq API key
    if not os.getenv("GROQ_API_KEY"):
        print("❌ ERROR: Please set GROQ_API_KEY environment variable")
        print("Get your key at: https://console.groq.com/keys")
        print("\nExample: export GROQ_API_KEY='your-api-key-here'")
        return

    print("=" * 70)
    print("GROQ FHIR GENERATION EXAMPLE")
    print("=" * 70)
    print("\n🚀 Using Groq for ultra-fast FHIR generation!")
    print("Model: openai/gpt-oss-120b (120B parameter model)\n")

    # Create a simple patient journey
    journey = PatientJourney(
        patient_id="groq-test-patient",
        summary="65 year old female presents to primary care with fever and cough",
        stages=[
            JourneyStage(
                name="Chief Complaint",
                description="Patient reports fever (101°F) and productive cough for 3 days",
                metadata={
                    "timestamp": "2024-01-20T14:00:00Z",
                    "location": "Primary Care Clinic"
                }
            ),
            JourneyStage(
                name="Physical Examination",
                description="Lung auscultation reveals crackles in right lower lobe",
                metadata={
                    "vital_signs": {
                        "temperature": "101°F",
                        "heart_rate": "92 bpm",
                        "respiratory_rate": "20 breaths/min"
                    }
                }
            ),
            JourneyStage(
                name="Diagnosis",
                description="Diagnosed with community-acquired pneumonia",
                metadata={
                    "condition": "Community-acquired pneumonia",
                    "icd10_code": "J18.9"
                }
            ),
            JourneyStage(
                name="Treatment",
                description="Prescribed amoxicillin 500mg three times daily for 7 days",
                metadata={
                    "medications": ["Amoxicillin 500mg TID x 7 days"]
                }
            )
        ]
    )

    # Patient context
    patient_context = """
    Patient is named Jane Smith, a 65-year-old female.
    Medical history: Type 2 diabetes mellitus, well-controlled.
    No known drug allergies.
    Non-smoker.
    """

    print("📋 Patient Journey Created")
    print(f"   - Patient: {journey.patient_id}")
    print(f"   - Stages: {len(journey.stages)}")
    print(f"   - Summary: {journey.summary}\n")

    print("⚡ Generating FHIR resources with Groq...")
    print("   (This should be very fast!)\n")

    # Generate FHIR resources using Groq
    result = generate_fhir_from_journey(
        journey=journey,
        patient_context=patient_context,
        model="openai/gpt-oss-120b",  # Groq's 120B parameter model
        llm_provider="groq",  # Explicitly use Groq
        fhir_version="R4",
        max_iterations=3,
        auto_save=True,
    )

    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    if result.success:
        print("✅ FHIR Generation Successful!")
    else:
        print("⚠️  FHIR Generation Incomplete")

    print(f"\nIterations: {result.iterations}")
    print(f"Resources Generated: {len(result.generated_resources)}")

    if result.planning_details:
        print(f"\n📝 Planning Rationale:")
        print(f"   {result.planning_details.rationale}")

    print("\n📦 Generated Resources:")
    for i, resource in enumerate(result.generated_resources, 1):
        resource_type = resource.get("resourceType", "Unknown")
        resource_id = resource.get("id", "no-id")
        print(f"   {i}. {resource_type}/{resource_id}")

    print("\n✓ Validation Summary:")
    valid_count = sum(1 for v in result.validation_results if v.is_valid)
    print(f"   Valid: {valid_count}/{len(result.validation_results)}")

    if result.errors:
        print("\n⚠️  Errors:")
        for error in result.errors:
            print(f"   - {error}")

    print("\n💾 Files saved to: output/jane_smith/")
    print("   - patient_bundle.json (FHIR Bundle)")
    print("   - bulk_fhir.jsonl (NDJSON format)")
    print("   - README.txt (Summary)")

    print("\n" + "=" * 70)
    print("🎉 Example Complete!")
    print("=" * 70)
    print("\n💡 Tip: Try comparing the speed with OpenAI by setting:")
    print("   LLM_PROVIDER=openai and running the basic example")


if __name__ == "__main__":
    main()
