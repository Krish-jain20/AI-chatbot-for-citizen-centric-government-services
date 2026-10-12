
from typing import Any


# Initial document workflow for CivicBridge.
# Start with Income Certificate and extend to other services later.

DOCUMENT_WORKFLOWS = {
    "INC_001": {
        "service_name": "Income Certificate",
        "jurisdiction": "Delhi",
        "fields": [
            {
                "key": "applicant_name",
                "question": "What is your full name?",
                "required": True,
            },
            {
                "key": "residential_address",
                "question": "What is your residential address?",
                "required": True,
            },
            {
                "key": "annual_family_income",
                "question": "What is your approximate annual family income in INR?",
                "required": True,
            },
            {
                "key": "purpose",
                "question": "Why do you need the Income Certificate?",
                "required": True,
            },
        ],
        "official_url": "https://edistrict.delhi.gov.in/",
    }
}


def get_document_workflow(service_id: str) -> dict[str, Any] | None:
    """Return the document workflow for a service."""
    return DOCUMENT_WORKFLOWS.get(service_id)


def start_document_session(service_id: str) -> dict[str, Any]:
    """Create a new document-assistance session."""
    workflow = get_document_workflow(service_id)

    if workflow is None:
        raise ValueError(
            f"Document assistance is not configured for service: {service_id}"
        )

    return {
        "flow": "document",
        "service_id": service_id,
        "step": 0,
        "answers": {},
    }


def get_next_question(session: dict[str, Any]) -> str | None:
    """Return the next unanswered question."""
    workflow = get_document_workflow(session["service_id"])
    if workflow is None:
        return None

    fields = workflow["fields"]
    step = session.get("step", 0)

    if step >= len(fields):
        return None

    return fields[step]["question"]


def save_document_answer(
    session: dict[str, Any],
    answer: str,
) -> dict[str, Any]:
    """Save an answer and move to the next field."""
    workflow = get_document_workflow(session["service_id"])

    if workflow is None:
        raise ValueError("Unknown document workflow.")

    fields = workflow["fields"]
    step = session.get("step", 0)

    if step >= len(fields):
        return {
            "status": "complete",
            "session": session,
            "message": "All configured fields have been collected.",
        }

    answer = answer.strip()

    if not answer:
        return {
            "status": "needs_answer",
            "session": session,
            "message": "Please provide an answer before continuing.",
        }

    field = fields[step]
    session["answers"][field["key"]] = answer
    session["step"] = step + 1

    if session["step"] < len(fields):
        return {
            "status": "in_progress",
            "session": session,
            "next_question": get_next_question(session),
        }

    return {
        "status": "complete",
        "session": session,
        "message": "All configured fields have been collected.",
    }


def validate_document_answers(
    session: dict[str, Any],
) -> dict[str, Any]:
    """Check that all required fields have been answered."""
    workflow = get_document_workflow(session["service_id"])

    if workflow is None:
        return {
            "valid": False,
            "missing_fields": [],
            "message": "Unknown document workflow.",
        }

    answers = session.get("answers", {})
    missing_fields = [
        field["key"]
        for field in workflow["fields"]
        if field["required"]
        and not str(answers.get(field["key"], "")).strip()
    ]

    return {
        "valid": not missing_fields,
        "missing_fields": missing_fields,
        "message": (
            "All required fields have been collected."
            if not missing_fields
            else "Some required fields are missing."
        ),
    }


def prepare_document_data(session: dict[str, Any]) -> dict[str, Any]:
    """Prepare validated data for the PDF generator."""
    validation = validate_document_answers(session)

    if not validation["valid"]:
        raise ValueError(
            f"Missing required fields: {validation['missing_fields']}"
        )

    workflow = get_document_workflow(session["service_id"])

    return {
        "service_name": workflow["service_name"],
        "jurisdiction": workflow["jurisdiction"],
        "answers": session["answers"],
        "official_url": workflow["official_url"],
        "document_status": "DRAFT - NOT AN OFFICIAL GOVERNMENT FORM",
    }
