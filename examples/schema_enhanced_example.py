"""
Example showing FHIR Schema-Enhanced Generation.

This example demonstrates how to use the fhir.schema.json file to provide
enhanced context for FHIR resource generation, improving accuracy and compliance.

Run this example:
    python examples/schema_enhanced_example.py
"""

import os
from pathlib import Path
from open_compute import (
    PatientJourney,
    JourneyStage,
    generate_fhir_from_journey,
    AIJourneyToFHIR,
)


def example_with_schema():
    """Example using FHIR schema for enhanced generation."""
    print("=" * 70)
    print("Example: Schema-Enhanced FHIR Generation")
    print("=" * 70)

    # Create a patient journey
    journey = PatientJourney(
        patient_id="patient-schema-test",
        summary="Hospital admission for pneumonia with complications",
        stages=[
            JourneyStage(
                name="ER Admission",
                description="Patient presented to ER with respiratory distress",
                metadata={
                    "timestamp": "2024-01-20T14:30:00Z",
                    "chief_complaint": "Shortness of breath, fever",
                    "vital_signs": {
                        "temperature": "39.5 C",
                        "respiratory_rate": "28 breaths/min",
                        "oxygen_saturation": "88% on room air",
                    },
                },
            ),
            JourneyStage(
                name="Diagnostic Imaging",
                description="Chest X-ray performed",
                metadata={
                    "procedure": "Chest X-ray, two views",
                    "findings": "Bilateral infiltrates, right lower lobe consolidation",
                    "impression": "Pneumonia, possible sepsis",
                },
            ),
            JourneyStage(
                name="Lab Results",
                description="Blood work completed",
                metadata={
                    "labs": {
                        "WBC": "18,500/μL",
                        "CRP": "245 mg/L",
                        "Procalcitonin": "4.2 ng/mL",
                        "Lactate": "3.1 mmol/L",
                    },
                },
            ),
            JourneyStage(
                name="Diagnosis",
                description="Severe community-acquired pneumonia with sepsis",
                metadata={
                    "primary_diagnosis": "Severe pneumonia",
                    "secondary_diagnosis": "Sepsis",
                    "icd10": ["J18.9", "A41.9"],
                },
            ),
            JourneyStage(
                name="Treatment Initiated",
                description="IV antibiotics and fluids started",
                metadata={
                    "medications": [
                        "Ceftriaxone 2g IV q24h",
                        "Azithromycin 500mg IV q24h",
                        "Normal saline 1L IV bolus",
                    ],
                    "oxygen": "High-flow nasal cannula 6L",
                },
            ),
            JourneyStage(
                name="ICU Transfer",
                description="Transferred to ICU due to deterioration",
                metadata={
                    "reason": "Worsening respiratory status",
                    "location": "Medical ICU",
                },
            ),
        ],
    )

    patient_context = """
    Patient is a 72-year-old female with medical history including:
    - COPD (on home oxygen at baseline)
    - Type 2 Diabetes (on metformin)
    - Hypertension (on lisinopril)
    - 30 pack-year smoking history (quit 10 years ago)
    
    Living situation: Lives alone, daughter nearby
    """

    # Path to the FHIR schema file
    # Update this path to where your fhir.schema.json is located
    schema_path = str(Path.home() / "Desktop" /
                      "definitions.json" / "fhir.schema.json")

    print(f"\nUsing FHIR schema from: {schema_path}")
    print("\nGenerating FHIR resources with schema context...")
    print("This provides the AI with:")
    print("  - Required fields for each resource type")
    print("  - Property descriptions and data types")
    print("  - Coding system requirements")
    print("  - Structural guidance")
    print("")

    # Generate with schema context
    result = generate_fhir_from_journey(
        journey=journey,
        patient_context=patient_context,
        model="gpt-5-mini",
        fhir_version="R4",
        max_iterations=3,
        fhir_schema_path=schema_path,  # ← Schema path here
    )

    # The summary is automatically printed by the generator
    # Results are in the result object

    if result.fhir_data:
        import json
        output_file = "schema_enhanced_bundle.json"
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": result.fhir_data.entries,
        }
        with open(output_file, "w") as f:
            json.dump(bundle, f, indent=2)
        print(f"\n✓ FHIR bundle saved to: {output_file}")

    return result


def example_with_custom_schema_path():
    """Example with explicit schema path configuration."""
    print("\n\n" + "=" * 70)
    print("Example: Using Agent with Custom Schema Path")
    print("=" * 70)

    journey = PatientJourney(
        patient_id="patient-custom-schema",
        summary="Outpatient diabetes management",
        stages=[
            JourneyStage(
                name="Office Visit",
                description="Follow-up for diabetes management",
                metadata={
                    "hba1c": "7.8%",
                    "fasting_glucose": "152 mg/dL",
                },
            ),
        ],
    )

    # Custom schema path
    schema_path = "/Users/bkyritz/Desktop/definitions.json/fhir.schema.json"

    # Create agent with schema path
    agent = AIJourneyToFHIR(
        model="gpt-5-mini",
        fhir_schema_path=schema_path,  # ← Specify schema here
        max_iterations=2,
    )

    result = agent.generate_from_journey(
        journey,
        patient_context="65-year-old male with Type 2 Diabetes"
    )

    print(f"\nGeneration completed: {result.success}")

    return result


def example_without_schema():
    """Example without schema for comparison."""
    print("\n\n" + "=" * 70)
    print("Example: Generation WITHOUT Schema (for comparison)")
    print("=" * 70)
    print("\nNote: Still works, but may have more validation errors")
    print("      and require more iterations to get right.\n")

    journey = PatientJourney(
        patient_id="patient-no-schema",
        summary="Simple checkup",
        stages=[
            JourneyStage(
                name="Annual Physical",
                description="Routine annual exam",
            ),
        ],
    )

    # Generate without schema (fhir_schema_path not provided)
    result = generate_fhir_from_journey(
        journey=journey,
        model="gpt-5-mini",
        max_iterations=2,
        # fhir_schema_path=None  # ← No schema
    )

    return result


def main():
    """Run examples."""
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Please set OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='your-api-key-here'")
        return

    print("Schema-Enhanced FHIR Generation Examples")
    print("=" * 70)
    print("\nThese examples show how using fhir.schema.json improves")
    print("FHIR resource generation quality and compliance.")
    print("=" * 70)

    try:
        # Run the main example
        example_with_schema()

        # Uncomment to run additional examples:
        # example_with_custom_schema_path()
        # example_without_schema()

    except Exception as e:
        print(f"\n❌ Error running example: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
