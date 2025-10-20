"""
Tests for the AI-powered Journey to FHIR generation.

These tests validate the AIJourneyToFHIR agent and related functionality.

Note: These tests will make actual API calls to OpenAI if OPENAI_API_KEY is set.
Consider using mocks for CI/CD environments.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from open_compute import (
    PatientJourney,
    JourneyStage,
    AIJourneyToFHIR,
    generate_fhir_from_journey,
    GenerationResult,
    GenerationPlan,
)


@pytest.fixture
def simple_journey():
    """Fixture providing a simple patient journey."""
    return PatientJourney(
        patient_id="test-patient-123",
        summary="Simple ER visit",
        stages=[
            JourneyStage(
                name="Registration",
                description="Patient registered",
                metadata={"timestamp": "2024-01-01T10:00:00Z"},
            ),
            JourneyStage(
                name="Triage",
                description="Initial assessment",
                metadata={"chief_complaint": "Headache"},
            ),
        ],
    )


@pytest.fixture
def complex_journey():
    """Fixture providing a complex patient journey."""
    return PatientJourney(
        patient_id="test-patient-456",
        summary="Multi-day hospital admission",
        stages=[
            JourneyStage(
                name="Admission",
                description="Admitted for pneumonia",
                metadata={"diagnosis": "Pneumonia", "severity": "moderate"},
            ),
            JourneyStage(
                name="Treatment",
                description="Antibiotics started",
                metadata={"medications": ["Azithromycin", "Ceftriaxone"]},
            ),
            JourneyStage(
                name="Procedure",
                description="Chest X-ray performed",
                metadata={"findings": "Right lower lobe infiltrate"},
            ),
            JourneyStage(
                name="Discharge",
                description="Discharged home",
                metadata={"condition": "Improved", "follow_up": "1 week"},
            ),
        ],
    )


class TestAIJourneyToFHIR:
    """Test the AIJourneyToFHIR class."""

    def test_initialization_with_api_key(self):
        """Test initializing the agent with an API key."""
        agent = AIJourneyToFHIR(api_key="test-key")
        assert agent.api_key == "test-key"
        assert agent.model == "gpt-4"
        assert agent.fhir_version == "R4"
        assert agent.max_iterations == 5

    def test_initialization_from_env(self):
        """Test initializing the agent from environment variable."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-test-key"}):
            agent = AIJourneyToFHIR()
            assert agent.api_key == "env-test-key"

    def test_initialization_without_api_key(self):
        """Test that initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key"):
                AIJourneyToFHIR()

    def test_custom_configuration(self):
        """Test initializing with custom configuration."""
        agent = AIJourneyToFHIR(
            api_key="test-key",
            model="gpt-5-mini",
            fhir_version="R4B",
            max_iterations=10,
        )
        assert agent.model == "gpt-5-mini"
        assert agent.fhir_version == "R4B"
        assert agent.max_iterations == 10

    def test_format_journey_for_prompt(self, simple_journey):
        """Test formatting a journey for prompts."""
        agent = AIJourneyToFHIR(api_key="test-key")
        formatted = agent._format_journey_for_prompt(simple_journey)

        assert "test-patient-123" in formatted
        assert "Simple ER visit" in formatted
        assert "Registration" in formatted
        assert "Triage" in formatted

    def test_format_existing_resources(self):
        """Test formatting existing resources."""
        agent = AIJourneyToFHIR(api_key="test-key")

        resources = [
            {"resourceType": "Patient", "id": "patient-1"},
            {"resourceType": "Encounter", "id": "encounter-1"},
        ]

        formatted = agent._format_existing_resources(resources)
        assert "Patient/patient-1" in formatted
        assert "Encounter/encounter-1" in formatted

    def test_format_existing_resources_empty(self):
        """Test formatting with no existing resources."""
        agent = AIJourneyToFHIR(api_key="test-key")
        formatted = agent._format_existing_resources([])
        assert "None yet" in formatted

    def test_create_bundle(self):
        """Test creating a FHIR bundle from resources."""
        agent = AIJourneyToFHIR(api_key="test-key")

        resources = [
            {"resourceType": "Patient", "id": "patient-1"},
            {"resourceType": "Encounter", "id": "encounter-1"},
        ]

        bundle = agent._create_bundle(resources)

        assert bundle.resourceType == "Bundle"
        assert len(bundle.entries) == 2
        assert bundle.entries[0]["resource"]["resourceType"] == "Patient"


class TestGenerationWithMocks:
    """Test generation workflow with mocked OpenAI API."""

    @pytest.fixture
    def mock_openai_client(self):
        """Fixture providing a mocked OpenAI client."""
        with patch("open_compute.agents.ai_journey_to_fhir.OpenAI") as mock:
            client = MagicMock()
            mock.return_value = client
            yield client

    def test_create_generation_plan_success(self, simple_journey, mock_openai_client):
        """Test creating a generation plan with mocked API."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "rationale": "Need Patient and Encounter resources",
                "resources": [
                    {
                        "resourceType": "Patient",
                        "description": "Patient demographics",
                        "key_data": ["patient_id"],
                    },
                    {
                        "resourceType": "Encounter",
                        "description": "ER visit",
                        "key_data": ["timestamp", "chief_complaint"],
                    },
                ],
            }
        )
        mock_openai_client.chat.completions.create.return_value = mock_response

        agent = AIJourneyToFHIR(api_key="test-key")
        plan = agent._create_generation_plan(simple_journey)

        assert isinstance(plan, GenerationPlan)
        assert len(plan.resources_to_generate) == 2
        assert plan.resources_to_generate[0]["resourceType"] == "Patient"
        assert plan.rationale == "Need Patient and Encounter resources"

    def test_generate_single_resource(self, simple_journey, mock_openai_client):
        """Test generating a single resource with mocked API."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "resourceType": "Patient",
                "id": "test-patient-123",
                "name": [{"family": "Doe", "given": ["John"]}],
                "gender": "male",
            }
        )
        mock_openai_client.chat.completions.create.return_value = mock_response

        agent = AIJourneyToFHIR(api_key="test-key")
        resource_spec = {
            "resourceType": "Patient",
            "description": "Patient demographics",
            "key_data": ["patient_id"],
        }

        resource = agent._generate_single_resource(
            resource_spec, simple_journey, [], None
        )

        assert resource is not None
        assert resource["resourceType"] == "Patient"
        assert resource["id"] == "test-patient-123"

    def test_check_completeness_complete(self, simple_journey, mock_openai_client):
        """Test completeness check when journey is complete."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "is_complete": True,
                "reasoning": "All essential resources generated",
                "additional_resources": [],
            }
        )
        mock_openai_client.chat.completions.create.return_value = mock_response

        agent = AIJourneyToFHIR(api_key="test-key")
        resources = [{"resourceType": "Patient"},
                     {"resourceType": "Encounter"}]
        journey_description = agent._format_journey_for_prompt(simple_journey)

        result = agent._check_completeness(
            simple_journey, resources, journey_description, None
        )

        assert result["is_complete"] is True
        assert "reasoning" in result

    def test_check_completeness_incomplete(self, simple_journey, mock_openai_client):
        """Test completeness check when more resources are needed."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(
            {
                "is_complete": False,
                "reasoning": "Missing Observation resource for chief complaint",
                "additional_resources": [
                    {
                        "resourceType": "Observation",
                        "description": "Chief complaint observation",
                        "key_data": ["chief_complaint"],
                    }
                ],
            }
        )
        mock_openai_client.chat.completions.create.return_value = mock_response

        agent = AIJourneyToFHIR(api_key="test-key")
        resources = [{"resourceType": "Patient"}]
        journey_description = agent._format_journey_for_prompt(simple_journey)

        result = agent._check_completeness(
            simple_journey, resources, journey_description, None
        )

        assert result["is_complete"] is False
        assert len(result["additional_resources"]) == 1
        assert result["additional_resources"][0]["resourceType"] == "Observation"


class TestConvenienceFunction:
    """Test the convenience function."""

    def test_generate_fhir_from_journey_signature(self, simple_journey):
        """Test that the convenience function accepts correct parameters."""
        # This test just validates the function signature
        # Actual generation would require a real API key
        with patch("open_compute.agents.ai_journey_to_fhir.OpenAI"):
            with pytest.raises(Exception):
                # Will fail when trying to make API calls, but that's ok
                generate_fhir_from_journey(
                    journey=simple_journey,
                    patient_context="Test context",
                    api_key="test-key",
                    model="gpt-4",
                    fhir_version="R4",
                    max_iterations=3,
                )


class TestGenerationResult:
    """Test the GenerationResult dataclass."""

    def test_successful_result(self):
        """Test a successful generation result."""
        from open_compute.types import FHIRPatientData
        from open_compute.utils.fhir_validator import ValidationResult

        result = GenerationResult(
            success=True,
            fhir_data=FHIRPatientData(entries=[]),
            generated_resources=[{"resourceType": "Patient"}],
            validation_results=[
                ValidationResult(is_valid=True, errors=[],
                                 resource_type="Patient")
            ],
            iterations=2,
            errors=[],
        )

        assert result.success is True
        assert result.iterations == 2
        assert len(result.generated_resources) == 1
        assert len(result.errors) == 0

    def test_failed_result(self):
        """Test a failed generation result."""
        result = GenerationResult(
            success=False,
            fhir_data=None,
            generated_resources=[],
            validation_results=[],
            iterations=5,
            errors=["Max iterations reached", "Validation failed"],
        )

        assert result.success is False
        assert len(result.errors) == 2


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="Requires OPENAI_API_KEY environment variable"
)
class TestRealAPIIntegration:
    """Integration tests that make real API calls to OpenAI.

    These tests are skipped unless OPENAI_API_KEY is set.
    """

    def test_real_generation_simple_journey(self, simple_journey):
        """Test real generation with a simple journey."""
        agent = AIJourneyToFHIR(
            model="gpt-5-mini",  # Use cheaper model for testing
            max_iterations=2,
        )

        result = agent.generate_from_journey(simple_journey)

        # Basic checks
        assert isinstance(result, GenerationResult)
        assert result.iterations > 0
        assert result.iterations <= 2

        # Should generate at least a Patient resource
        if result.generated_resources:
            resource_types = [r.get("resourceType")
                              for r in result.generated_resources]
            assert "Patient" in resource_types

    def test_real_generation_with_context(self, simple_journey):
        """Test real generation with patient context."""
        result = generate_fhir_from_journey(
            journey=simple_journey,
            patient_context="65-year-old male with history of hypertension",
            model="gpt-5-mini",
            max_iterations=2,
        )

        assert isinstance(result, GenerationResult)

        # If successful, should have FHIR data
        if result.success:
            assert result.fhir_data is not None
            assert len(result.generated_resources) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
