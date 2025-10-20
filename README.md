# Open Compute

**Open-source agentic AI for healthcare technology** 🏥🤖

Open Compute is a powerful Python library that uses AI agents to transform patient journeys into standards-compliant FHIR (Fast Healthcare Interoperability Resources) data. Built by [Jori Health](https://jorihealth.com), this tool enables healthcare developers to bridge the gap between narrative patient experiences and structured healthcare data.

## ✨ Key Features

- **🤖 AI-Powered FHIR Generation**: Use OpenAI models to intelligently generate comprehensive FHIR resources from patient journeys
- **✅ Automatic Validation**: Built-in FHIR schema validation with iterative error correction
- **📦 Multiple Output Formats**: Generate FHIR Bundles (JSON) and Bulk FHIR (JSONL) formats
- **🔄 Parallel Processing**: Fast resource generation with parallel API calls
- **📊 Enhanced Context**: Leverages FHIR profiles, value sets, and search parameters for accurate resource generation
- **💾 Auto-Save**: Automatically saves generated resources with organized file structure
- **🎯 FHIR Version Support**: Compatible with FHIR R4, R4B, R5, and STU3

## 🚀 Quick Start

### Installation

#### Option 1: Install from GitHub (Recommended)

```bash
pip install git+https://github.com/jori-health/open-compute.git
```

#### Option 2: Install from local clone (for development)

```bash
git clone https://github.com/jori-health/open-compute.git
cd open-compute
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .
```

> 📦 Once published to PyPI:
>
> ```bash
> pip install open-compute
> ```

### Prerequisites

- **Python 3.9+**
- **OpenAI API Key**: Set as environment variable
  ```bash
  export OPENAI_API_KEY='your-api-key-here'
  ```

## 📖 Usage

### Patient Journey to FHIR Conversion

The primary use case is converting narrative patient journeys into structured, validated FHIR resources:

```python
from open_compute import (
    PatientJourney,
    JourneyStage,
    generate_fhir_from_journey,
)

# 1. Define a patient journey with clinical narrative
journey = PatientJourney(
    patient_id="patient-123",
    summary="58 year old male presents to ER with chest pain, diagnosed with acute MI",
    stages=[
        JourneyStage(
            name="Registration",
            description="Patient registered in ER",
            metadata={
                "timestamp": "2024-01-15T10:30:00Z",
                "location": "Emergency Department"
            }
        ),
        JourneyStage(
            name="Triage",
            description="Initial assessment - chest pain, elevated BP",
            metadata={
                "vital_signs": {
                    "blood_pressure": "150/95 mmHg",
                    "heart_rate": "88 bpm"
                },
                "chief_complaint": "Chest pain"
            }
        ),
        JourneyStage(
            name="Diagnosis",
            description="Diagnosed with acute myocardial infarction",
            metadata={
                "condition": "Acute MI",
                "icd10_code": "I21.9"
            }
        ),
        JourneyStage(
            name="Treatment",
            description="Administered aspirin and nitroglycerin",
            metadata={
                "medications": ["Aspirin 325mg", "Nitroglycerin 0.4mg"]
            }
        ),
    ]
)

# 2. Generate FHIR resources using AI
result = generate_fhir_from_journey(
    journey=journey,
    patient_context="58 year old male named John Doe with history of hypertension",
    model="gpt-4o-mini",  # or "gpt-4", "gpt-3.5-turbo"
    fhir_version="R4",
    max_iterations=3,
    auto_save=True  # Saves to output/john_doe/
)

# 3. Check results
print(f"✅ Success: {result.success}")
print(f"📊 Generated {len(result.generated_resources)} FHIR resources")
print(f"🔄 Iterations: {result.iterations}")

# View generated resource types
for resource in result.generated_resources:
    print(f"  - {resource['resourceType']}/{resource.get('id', 'no-id')}")
```

### Output Structure

When `auto_save=True`, generated files are saved to `output/{firstname_lastname}/`:

```
output/john_doe/
├── patient_bundle.json    # Complete FHIR Bundle (all resources)
├── bulk_fhir.jsonl       # Bulk FHIR format (one resource per line)
└── README.txt            # Summary of generated resources
```

### Advanced Configuration

```python
from open_compute import AIJourneyToFHIR

# Create agent with custom configuration
agent = AIJourneyToFHIR(
    api_key="your-openai-key",  # or use env var OPENAI_API_KEY
    model="gpt-4o-mini",
    fhir_version="R4",
    max_iterations=5,
    max_fix_retries=3,
    auto_save=True,
    save_directory="output",
    parallel_generation=True,  # Faster generation
    use_enhanced_context=True  # Better accuracy with FHIR profiles
)

# Generate resources
result = agent.generate(journey, patient_context="...")
```

## 📚 Examples

We provide comprehensive examples to help you get started:

### Running the Examples

```bash
# Make sure you have your OpenAI API key set
export OPENAI_API_KEY='your-api-key-here'

# Run the main example
python examples/patient_journey_to_fhir_example.py
```

### Available Examples

| Example         | Description                                                      | File                                          |
| --------------- | ---------------------------------------------------------------- | --------------------------------------------- |
| **Basic Usage** | Complete patient journey with ER visit, diagnosis, and treatment | `examples/patient_journey_to_fhir_example.py` |

The example demonstrates:

- Creating a patient journey with multiple stages
- Generating FHIR resources (Patient, Encounter, Observation, Condition, MedicationStatement, Procedure)
- Validating generated resources
- Auto-saving to organized output directory

### Example Output

```
Patient Journey to FHIR Generation
============================================================

These examples will use the OpenAI API to generate FHIR resources.
This may take a minute or two...

============================================================
Example 1: Basic Usage
============================================================

============================================================
Generation Results
============================================================
Success: True
Iterations: 1
Resources Generated: 8

Generated Resources:
  1. Patient/pat-john-doe
  2. Encounter/enc-emergency-visit
  3. Observation/obs-blood-pressure
  4. Observation/obs-heart-rate
  5. Condition/cond-acute-mi
  6. MedicationStatement/med-aspirin
  7. MedicationStatement/med-nitroglycerin
  8. Procedure/proc-cardiac-cath

✅ Files saved to: output/john_doe/
```

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=src/open_compute tests/

# Run specific test file
pytest tests/test_ai_journey_to_fhir.py
```

## 🏗️ Architecture

Open Compute uses an **agentic AI architecture** with the following workflow:

1. **Planning**: AI analyzes the patient journey and determines which FHIR resources to generate
2. **Generation**: AI generates each FHIR resource with appropriate content and references
3. **Validation**: Each resource is validated against FHIR schemas
4. **Error Correction**: If validation fails, AI automatically corrects errors
5. **Completeness Check**: AI verifies all journey stages are represented
6. **Iteration**: Process repeats until complete or max iterations reached

## 🤝 Contributing

We welcome contributions! Open Compute is an open-source project and we'd love your help.

### Areas for Contribution

- Additional FHIR resource types
- Support for more FHIR versions
- Enhanced validation rules
- Performance optimizations
- Documentation improvements

### Getting Started

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- Built with ❤️ by [Jori Health](https://jorihealth.com)
- Powered by [OpenAI](https://openai.com)
- FHIR specifications by [HL7](https://www.hl7.org/fhir/)

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/jori-health/open-compute/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jori-health/open-compute/discussions)
- **Email**: support@jorihealth.com

---

**Made with 🏥 for better healthcare interoperability**
