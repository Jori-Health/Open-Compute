"""
Test the save structure functionality for FHIR bundles.
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from open_compute.agents.ai_journey_to_fhir import AIJourneyToFHIR
from open_compute.types import FHIRPatientData


def test_extract_patient_name():
    """Test patient name extraction from FHIR resources."""
    # Create a mock API key for testing (we won't make actual API calls)
    agent = AIJourneyToFHIR(api_key="test-key", auto_save=False)
    
    # Test case 1: Valid patient resource
    fhir_data = FHIRPatientData(
        entries=[
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-123",
                    "name": [
                        {
                            "given": ["John", "Michael"],
                            "family": "Doe"
                        }
                    ]
                }
            }
        ]
    )
    
    first_name, last_name = agent._extract_patient_name(fhir_data)
    assert first_name == "john", f"Expected 'john', got '{first_name}'"
    assert last_name == "doe", f"Expected 'doe', got '{last_name}'"
    print("✓ Test 1 passed: Basic name extraction")
    
    # Test case 2: Special characters in name
    fhir_data = FHIRPatientData(
        entries=[
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-456",
                    "name": [
                        {
                            "given": ["María-José"],
                            "family": "O'Brien"
                        }
                    ]
                }
            }
        ]
    )
    
    first_name, last_name = agent._extract_patient_name(fhir_data)
    # Note: isalnum() preserves international characters like á, é, etc.
    assert first_name == "maría_josé", f"Expected 'maría_josé', got '{first_name}'"
    assert last_name == "o_brien", f"Expected 'o_brien', got '{last_name}'"
    print("✓ Test 2 passed: Special character sanitization")
    
    # Test case 3: Missing patient resource
    fhir_data = FHIRPatientData(
        entries=[
            {
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-123"
                }
            }
        ]
    )
    
    first_name, last_name = agent._extract_patient_name(fhir_data)
    assert first_name == "unknown", f"Expected 'unknown', got '{first_name}'"
    assert last_name == "patient", f"Expected 'patient', got '{last_name}'"
    print("✓ Test 3 passed: Missing patient fallback")
    
    # Test case 4: Missing name fields
    fhir_data = FHIRPatientData(
        entries=[
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-789",
                    "name": [{}]
                }
            }
        ]
    )
    
    first_name, last_name = agent._extract_patient_name(fhir_data)
    assert first_name == "unknown", f"Expected 'unknown', got '{first_name}'"
    assert last_name == "patient", f"Expected 'patient', got '{last_name}'"
    print("✓ Test 4 passed: Empty name object fallback")


def test_save_bundle_structure():
    """Test that bundle is saved with correct structure."""
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    
    try:
        agent = AIJourneyToFHIR(
            api_key="test-key",
            auto_save=False,
            save_directory=temp_dir
        )
        
        # Create test FHIR data
        fhir_data = FHIRPatientData(
            entries=[
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "patient-123",
                        "name": [{"given": ["John"], "family": "Doe"}]
                    }
                },
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "obs-456",
                        "status": "final"
                    }
                }
            ]
        )
        
        # Mock journey object
        class MockJourney:
            patient_id = "patient-123"
        
        journey = MockJourney()
        
        # Save the bundle
        save_path = agent._save_bundle(fhir_data, journey)
        
        # Verify the path
        assert save_path is not None, "Save path should not be None"
        expected_path = Path(temp_dir) / "john_doe"
        assert Path(save_path) == expected_path, f"Expected path {expected_path}, got {save_path}"
        print(f"✓ Saved to: {save_path}")
        
        # Verify files exist
        patient_bundle_path = expected_path / "patient_bundle.json"
        bulk_fhir_path = expected_path / "bulk_fhir.jsonl"
        readme_path = expected_path / "README.txt"
        
        assert patient_bundle_path.exists(), "patient_bundle.json should exist"
        assert bulk_fhir_path.exists(), "bulk_fhir.jsonl should exist"
        assert readme_path.exists(), "README.txt should exist"
        print("✓ All expected files created")
        
        # Verify patient_bundle.json structure
        with open(patient_bundle_path, 'r') as f:
            bundle = json.load(f)
        
        assert bundle["resourceType"] == "Bundle", "Bundle should have resourceType"
        assert bundle["type"] == "collection", "Bundle type should be 'collection'"
        assert "entry" in bundle, "Bundle should have entries"
        assert len(bundle["entry"]) == 2, "Bundle should have 2 entries"
        print("✓ patient_bundle.json has correct structure")
        
        # Verify bulk_fhir.jsonl structure
        with open(bulk_fhir_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 2, "JSONL should have 2 lines"
        
        # Parse each line to verify it's valid JSON
        for i, line in enumerate(lines):
            resource = json.loads(line.strip())
            assert "resourceType" in resource, f"Line {i+1} should have resourceType"
        
        print("✓ bulk_fhir.jsonl has correct structure")
        
        # Verify README.txt content
        with open(readme_path, 'r') as f:
            readme_content = f.read()
        
        assert "John Doe" in readme_content, "README should contain patient name"
        assert "patient-123" in readme_content, "README should contain patient ID"
        assert "Patient: 1" in readme_content, "README should list Patient resources"
        assert "Observation: 1" in readme_content, "README should list Observation resources"
        print("✓ README.txt has correct content")
        
        print("\n✓ All save structure tests passed!")
        
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    print("Testing Save Structure Functionality")
    print("=" * 60)
    
    print("\n1. Testing patient name extraction...")
    test_extract_patient_name()
    
    print("\n2. Testing save bundle structure...")
    test_save_bundle_structure()
    
    print("\n" + "=" * 60)
    print("All tests completed successfully! ✓")

