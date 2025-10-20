# Tests

This directory contains tests for the Open Compute package.

## Quick Start

### Run Quick Smoke Test (5 seconds)

```bash
python tests/quick_test.py
```

### Run Full Test Suite (30 seconds)

```bash
pytest tests/test_fhir_validator.py -v
```

## Test Files

- **`test_fhir_validator.py`** - Comprehensive test suite with 35+ test cases
- **`quick_test.py`** - Quick smoke tests (6 tests)

## Installation

```bash
pip install pytest pytest-cov fhir.resources
```

Or install with dev dependencies:

```bash
pip install -e ".[dev]"
```

## Documentation

See `TESTING_QUICK_START.md` and `docs/TESTING_GUIDE.md` for detailed testing documentation.
