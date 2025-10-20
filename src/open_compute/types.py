from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal, Mapping


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


# US Core STU versions and canonical docs roots
USCoreSTU = Literal[
    "STU1",
    "STU2",
    "STU3",
    "STU4",
    "STU5",
    "STU6",
    "STU7",
    "STU8",
]

US_CORE_STU_TO_URL: Mapping[USCoreSTU, str] = {
    "STU1": "https://hl7.org/fhir/us/core/STU1/",
    "STU2": "https://hl7.org/fhir/us/core/STU2/",
    "STU3": "https://hl7.org/fhir/us/core/STU3/",
    "STU4": "https://hl7.org/fhir/us/core/STU4/",
    "STU5": "https://hl7.org/fhir/us/core/STU5/",
    "STU6": "https://hl7.org/fhir/us/core/STU6/",
    "STU7": "https://hl7.org/fhir/us/core/STU7/",
    "STU8": "https://hl7.org/fhir/us/core/STU8/",
}
