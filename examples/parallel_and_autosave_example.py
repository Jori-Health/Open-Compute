"""
Example demonstrating Parallel Generation and Auto-Save features.

This example shows how to:
1. Use parallel generation for 3-5x faster resource generation
2. Auto-save successful FHIR bundles to disk
3. Configure save directory and options

Run this example:
    python examples/parallel_and_autosave_example.py
"""

import os
import time
from pathlib import Path
from open_compute import (
    PatientJourney,
    JourneyStage,
    generate_fhir_from_journey,
    AIJourneyToFHIR,
)


def example_parallel_generation():
    """
    Example showing parallel generation in action.

    Parallel generation makes multiple API calls at once, significantly
    speeding up resource generation when you have multiple resources.
    """
    print("=" * 70)
    print("Example 1: Parallel Generation")
    print("=" * 70)

    journey = PatientJourney(
        patient_id="patient-parallel-test",
        summary="Multi-day hospital admission with multiple procedures",
        stages=[
            JourneyStage(
                name="ER Admission",
                description="Admitted with severe abdominal pain",
                metadata={
                    "timestamp": "2024-01-15T18:30:00Z",
                    "chief_complaint": "Severe abdominal pain",
                    "vital_signs": {"bp": "145/92", "hr": "102", "temp": "38.5 C"},
                },
            ),
            JourneyStage(
                name="Imaging",
                description="CT abdomen performed",
                metadata={
                    "procedure": "CT abdomen with contrast",
                    "findings": "Acute appendicitis with perforation",
                },
            ),
            JourneyStage(
                name="Lab Results",
                description="Blood work",
                metadata={
                    "WBC": "18,000",
                    "CRP": "195 mg/L",
                },
            ),
            JourneyStage(
                name="Diagnosis",
                description="Acute appendicitis with perforation",
                metadata={"diagnosis": "Appendicitis", "icd10": "K35.32"},
            ),
            JourneyStage(
                name="Surgery",
                description="Emergency appendectomy performed",
                metadata={
                    "procedure": "Laparoscopic appendectomy",
                    "timestamp": "2024-01-15T22:00:00Z",
                },
            ),
            JourneyStage(
                name="Post-op Medications",
                description="Pain management and antibiotics",
                metadata={
                    "medications": [
                        "Morphine 2mg IV PRN",
                        "Zosyn 4.5g IV q8h",
                        "Flagyl 500mg IV q8h",
                    ],
                },
            ),
        ],
    )

    patient_context = """
    Patient is a 42-year-old male, previously healthy.
    No significant medical history.
    No known drug allergies.
    """

    print("\n🚀 Generating with PARALLEL enabled (default)...")
    start_time = time.time()

    result_parallel = generate_fhir_from_journey(
        journey=journey,
        patient_context=patient_context,
        model="gpt-5-mini",
        max_iterations=2,
        parallel_generation=True,  # ← PARALLEL ON (default)
    )

    parallel_time = time.time() - start_time

    print(f"\n⏱️  Parallel generation time: {parallel_time:.2f} seconds")
    print(f"Resources generated: {len(result_parallel.generated_resources)}")

    # Compare with sequential for demonstration
    print("\n\n🐌 Generating with SEQUENTIAL (for comparison)...")
    start_time = time.time()

    result_sequential = generate_fhir_from_journey(
        journey=journey,
        patient_context=patient_context,
        model="gpt-5-mini",
        max_iterations=2,
        parallel_generation=False,  # ← PARALLEL OFF
        auto_save=False,  # Don't save the comparison run
    )

    sequential_time = time.time() - start_time

    print(f"\n⏱️  Sequential generation time: {sequential_time:.2f} seconds")
    print(f"Resources generated: {len(result_sequential.generated_resources)}")

    # Show speedup
    if sequential_time > 0:
        speedup = sequential_time / parallel_time
        print(f"\n🚀 Speedup: {speedup:.1f}x faster with parallel generation!")

    return result_parallel


def example_auto_save():
    """
    Example showing auto-save feature.

    Successful FHIR bundles are automatically saved to disk with
    timestamps and patient IDs in the filename.
    """
    print("\n\n" + "=" * 70)
    print("Example 2: Auto-Save Feature")
    print("=" * 70)

    journey = PatientJourney(
        patient_id="patient-autosave-demo",
        summary="Routine office visit",
        stages=[
            JourneyStage(
                name="Check-in",
                description="Annual physical exam",
                metadata={"appointment_type": "annual_physical"},
            ),
            JourneyStage(
                name="Vitals",
                description="Vital signs recorded",
                metadata={
                    "bp": "118/76 mmHg",
                    "hr": "68 bpm",
                    "weight": "165 lbs",
                },
            ),
        ],
    )

    print("\n💾 Auto-save is ENABLED by default")
    print("Successful bundles will be saved to: generated_fhir/")

    result = generate_fhir_from_journey(
        journey=journey,
        patient_context="45-year-old male, healthy",
        model="gpt-5-mini",
        max_iterations=2,
        auto_save=True,  # ← AUTO-SAVE ON (default)
        save_directory="generated_fhir",  # ← Where to save
    )

    if result.success:
        print("\nLook for the auto-saved file in:")
        print(
            "  generated_fhir/fhir_bundle_patient-autosave-demo_[timestamp].json")

    return result


def example_custom_save_directory():
    """
    Example with custom save directory.
    """
    print("\n\n" + "=" * 70)
    print("Example 3: Custom Save Directory")
    print("=" * 70)

    journey = PatientJourney(
        patient_id="patient-custom-dir",
        summary="Quick visit",
        stages=[
            JourneyStage(name="Visit", description="Brief consultation"),
        ],
    )

    result = generate_fhir_from_journey(
        journey=journey,
        model="gpt-5-mini",
        max_iterations=1,
        auto_save=True,
        save_directory="my_fhir_outputs",  # ← Custom directory
    )

    if result.success:
        print("\n💾 Check your custom directory:")
        print(
            "  my_fhir_outputs/fhir_bundle_patient-custom-dir_[timestamp].json")

    return result


def example_disable_auto_save():
    """
    Example with auto-save disabled (manual save).
    """
    print("\n\n" + "=" * 70)
    print("Example 4: Manual Save (auto-save disabled)")
    print("=" * 70)

    journey = PatientJourney(
        patient_id="patient-manual-save",
        summary="Visit",
        stages=[
            JourneyStage(name="Visit", description="Check-up"),
        ],
    )

    result = generate_fhir_from_journey(
        journey=journey,
        model="gpt-5-mini",
        max_iterations=1,
        auto_save=False,  # ← AUTO-SAVE OFF
    )

    # Manual save with custom logic
    if result.success and result.fhir_data:
        import json
        custom_filename = "my_custom_bundle.json"
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": result.fhir_data.entries,
        }
        with open(custom_filename, "w") as f:
            json.dump(bundle, f, indent=2)
        print(f"\n💾 Manually saved to: {custom_filename}")

    return result


def example_parallel_vs_sequential_performance():
    """
    Example comparing parallel vs sequential generation performance.
    """
    print("\n\n" + "=" * 70)
    print("Example 5: Performance Comparison")
    print("=" * 70)

    # Create a complex journey that will generate many resources
    journey = PatientJourney(
        patient_id="patient-perf-test",
        summary="Complex multi-system illness",
        stages=[
            JourneyStage(name="Admission", description="ICU admission"),
            JourneyStage(name="Diagnosis 1", description="Sepsis"),
            JourneyStage(name="Diagnosis 2",
                         description="Respiratory failure"),
            JourneyStage(name="Lab 1", description="Blood culture"),
            JourneyStage(name="Lab 2", description="ABG"),
            JourneyStage(name="Imaging", description="Chest X-ray"),
            JourneyStage(name="Procedure", description="Intubation"),
            JourneyStage(name="Medications", description="Multiple drugs"),
        ],
    )

    print("\n🚀 Testing PARALLEL generation...")
    start = time.time()
    result_parallel = generate_fhir_from_journey(
        journey=journey,
        model="gpt-5-mini",
        max_iterations=1,
        parallel_generation=True,
        auto_save=False,
    )
    parallel_time = time.time() - start

    print("\n\n🐌 Testing SEQUENTIAL generation...")
    start = time.time()
    result_sequential = generate_fhir_from_journey(
        journey=journey,
        model="gpt-5-mini",
        max_iterations=1,
        parallel_generation=False,
        auto_save=False,
    )
    sequential_time = time.time() - start

    print("\n" + "=" * 70)
    print("PERFORMANCE RESULTS")
    print("=" * 70)
    print(f"Parallel time:   {parallel_time:.2f}s")
    print(f"Sequential time: {sequential_time:.2f}s")
    print(f"Speedup:         {sequential_time / parallel_time:.1f}x faster!")
    print(f"Time saved:      {sequential_time - parallel_time:.2f}s")
    print("=" * 70)


def main():
    """Run all examples."""
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Please set OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='your-api-key-here'")
        return

    print("Parallel Generation and Auto-Save Examples")
    print("=" * 70)
    print("\nThese examples demonstrate:")
    print("  1. Parallel generation for 3-5x faster results")
    print("  2. Auto-save of successful FHIR bundles")
    print("  3. Custom save directories")
    print("  4. Performance comparisons")
    print("=" * 70)

    try:
        # Run examples
        example_parallel_generation()
        example_auto_save()

        # Uncomment to run additional examples:
        # example_custom_save_directory()
        # example_disable_auto_save()
        # example_parallel_vs_sequential_performance()

    except Exception as e:
        print(f"\n❌ Error running example: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
