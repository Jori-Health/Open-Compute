from ..types import PatientJourney, FHIRPatientData


def journey_to_fhir(journey: PatientJourney) -> FHIRPatientData:
    entries = []

    if journey.patient_id:
        entries.append(
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": journey.patient_id,
                }
            }
        )

    for stage in journey.stages:
        if stage.name == "Encounter":
            entries.append(
                {
                    "resource": {
                        "resourceType": "Encounter",
                        "status": stage.metadata.get("status", "finished"),
                        "reasonCode": [
                            {"text": stage.description or "Encounter"}
                        ],
                    }
                }
            )
        elif stage.name == "Observation":
            entries.append(
                {
                    "resource": {
                        "resourceType": "Observation",
                        "code": {"text": stage.description or "Observation"},
                        "valueString": stage.metadata.get("value"),
                    }
                }
            )

    return FHIRPatientData(entries=entries)
