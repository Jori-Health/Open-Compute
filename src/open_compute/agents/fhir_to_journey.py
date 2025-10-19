from typing import Iterable

from ..types import FHIRPatientData, PatientJourney, JourneyStage


def fhir_to_journey(data: FHIRPatientData) -> PatientJourney:
    patient_id = None
    stages: list[JourneyStage] = []

    for entry in data.entries:
        resource = entry.get("resource", {})
        r_type = resource.get("resourceType")

        if r_type == "Patient":
            patient_id = resource.get("id") or patient_id
            stages.append(
                JourneyStage(
                    name="Registration",
                    description="Patient resource found",
                    metadata={"patient_id": patient_id},
                )
            )
        elif r_type == "Encounter":
            stages.append(
                JourneyStage(
                    name="Encounter",
                    description=resource.get("reasonCode", [{}])[
                        0].get("text"),
                    metadata={"status": resource.get("status")},
                )
            )
        elif r_type == "Observation":
            stages.append(
                JourneyStage(
                    name="Observation",
                    description=resource.get("code", {}).get("text"),
                    metadata={"value": resource.get("valueString")},
                )
            )

    summary = f"Journey with {len(stages)} stages"
    return PatientJourney(patient_id=patient_id, stages=stages, summary=summary)
