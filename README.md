# open-compute

Utilities by Jori Health. Provides a simple AI facade exposed at the Python import path `jori_health.ai`.

## Requirements
- Python 3.9+

## Install

### Option A: Install directly from GitHub
```bash
pip install git+https://github.com/jori-health/open-compute.git
```

### Option B: Install from a local clone (editable)
```bash
git clone https://github.com/jori-health/open-compute.git
cd open-compute
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

> Once published to PyPI you will be able to run:
```bash
pip install open-compute
```

## Quickstart

### Import the default instance
```python
from jori_health.ai import joriai

print(joriai.ask("hello"))            # -> "world"
print(joriai.ask("How are you?"))     # -> "Echo: How are you?"
```

### Or create your own instance
```python
from jori_health.ai import JoriAI

ai = JoriAI()
print(ai.ask("hello"))  # -> "world"
```

## Testing locally (optional)
```bash
pytest -q
```

## License
MIT
