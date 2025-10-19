from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class FHIRPatientData:
    resourceType: str = "Bundle"
    entries: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class JourneyStage:
    name: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatientJourney:
    patient_id: Optional[str]
    stages: List[JourneyStage] = field(default_factory=list)
    summary: Optional[str] = None
