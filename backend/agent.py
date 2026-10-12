
import os
from typing import TypedDict

from dotenv import load_dotenv
from google import genai
from supabase import create_client
from langgraph.graph import StateGraph, START, END

# --------------------------------------------------
# 1. Environment setup
# --------------------------------------------------

load_dotenv(override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials not found in .env")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini = genai.Client(api_key=GEMINI_API_KEY)

MODEL = "gemini-3.5-flash-lite"


# --------------------------------------------------
# 2. Government services
# --------------------------------------------------

VALID_SERVICES = {
    "driving_licence": "Driving Licence",
    "vehicle_registration": "Vehicle Registration",
    "passport": "Passport",
    "voter_id": "Voter ID",
    "pan": "PAN Card",
    "birth_certificate": "Birth Certificate",
    "income_certificate": "Income Certificate",
    "caste_certificate": "Caste Certificate",
}

SERVICE_KEYWORDS = {
    "driving_licence": [
        "driving licence", "driving license",
        "learner licence", "learner license",
        "sarathi",
    ],
    "vehicle_registration": [
        "vehicle registration", "registration certificate",
        "rc book", "vehicle rc", "vahan",
    ],
    "passport": ["passport", "passport seva"],
    "voter_id": [
        "voter id", "voter card", "voter registration",
        "voting card", "election card",
    ],
    "pan": [
        "pan card", "pan number", "permanent account number",
    ],
    "birth_certificate": [
        "birth certificate", "birth registration",
    ],
    "income_certificate": [
        "income certificate", "income proof",
    ],
    "caste_certificate": [
        "caste certificate", "sc certificate",
        "st certificate", "obc certificate",
    ],
}


# --------------------------------------------------
# 3. LangGraph state
# --------------------------------------------------

class CivicState(TypedDict):
    user_message: str
    service_id: str
    service_data: dict
    final_response: str


# --------------------------------------------------
# 4. Identify service or conversational message
# --------------------------------------------------

def identify_service(state: CivicState):
    message = state["user_message"].strip().lower()
    normalized = " ".join(message.split())

    greetings = {
        "hi", "hii", "hiii", "hello", "hey",
        "good morning", "good afternoon",
        "good evening", "howdy",
    }

    if normalized in greetings:
        return {"service_id": "GREETING"}

    if normalized in {
        "thanks", "thank you", "thankyou", "thx",
    }:
        return {"service_id": "THANKS"}

    if normalized in {"bye", "goodbye", "see you"}:
        return {"service_id": "GOODBYE"}

    # Keyword matching first
    for service_id, keywords in SERVICE_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            print(f"Keyword matching identified: {service_id}")
            return {"service_id": service_id}

    # Gemini fallback
    try:
        available_services = "\n".join(
            f"{service_id}: {name}"
            for service_id, name in VALID_SERVICES.items()
        )

        response = gemini.models.generate_content(
            model=MODEL,
            contents=f"""
Identify the government service requested by the user.

Available services:
{available_services}

User message: {state["user_message"]}

Return only the exact service_id from the list.
If none matches, return UNKNOWN.
"""
        )

        result = (response.text or "").strip()
        result = result.replace("`", "").lower()

        if result in VALID_SERVICES:
            print(f"Gemini identified: {result}")
            return {"service_id": result}

        return {"service_id": "UNKNOWN"}

    except Exception as error:
        print(f"Service identification error: {error}")
        return {"service_id": "UNKNOWN"}


# --------------------------------------------------
# 5. Validate service
# --------------------------------------------------

def validate_service(state: CivicState):
    service_id = state["service_id"]

    conversation_states = {
        "GREETING", "THANKS", "GOODBYE",
    }

    if service_id in conversation_states:
        return {"service_id": service_id}

    if service_id not in VALID_SERVICES:
        return {"service_id": "UNKNOWN"}

    return {"service_id": service_id}


# --------------------------------------------------
# 6. Retrieve service from Supabase
# --------------------------------------------------

def retrieve_service(state: CivicState):
    service_id = state["service_id"]

    if service_id in {
        "GREETING", "THANKS", "GOODBYE", "UNKNOWN",
    }:
        return {"service_data": {}}

    try:
        print(f"Looking up service ID: {service_id}")

        response = (
            supabase.table("services")
            .select("*")
            .eq("service_id", service_id)
            .execute()
        )

        if not response.data:
            print("Service record not found.")
            return {"service_data": {}}

        print(f"Retrieved service: {response.data[0]['service_name']}")
        return {"service_data": response.data[0]}

    except Exception as error:
        print(f"Supabase retrieval error: {error}")
        return {"service_data": {}}


# --------------------------------------------------
# 7. Generate a friendly, detailed answer
# --------------------------------------------------

def generate_answer(state: CivicState):
    service_id = state["service_id"]

    if service_id == "GREETING":
        return {
            "final_response": (
                "Hello! Welcome to CivicBridge. 👋\n\n"
                "I'm here to help you understand government services "
                "and their application processes.\n\n"
                "Here are the services I can help you with:\n"
                "1. Driving Licence\n"
                "2. Vehicle Registration\n"
                "3. Passport\n"
                "4. Voter ID\n"
                "5. PAN Card\n"
                "6. Birth Certificate\n"
                "7. Income Certificate\n"
                "8. Caste Certificate\n\n"
                "Which service would you like help with?"
            )
        }

    if service_id == "THANKS":
        return {
            "final_response": (
                "You're welcome! 😊 I'm happy to help.\n\n"
                "If you need information about another government "
                "service, just tell me which one."
            )
        }

    if service_id == "GOODBYE":
        return {
            "final_response": (
                "Goodbye! 👋 Thank you for using CivicBridge. "
                "Feel free to return whenever you need help "
                "with a government service."
            )
        }

    if service_id == "UNKNOWN":
        return {
            "final_response": (
                "I'd be happy to help! 😊\n\n"
                "I currently support these government services:\n"
                "1. Driving Licence\n"
                "2. Vehicle Registration\n"
                "3. Passport\n"
                "4. Voter ID\n"
                "5. PAN Card\n"
                "6. Birth Certificate\n"
                "7. Income Certificate\n"
                "8. Caste Certificate\n\n"
                "Please tell me which service you need information about."
            )
        }

    service_data = state["service_data"]

    if not service_data:
        return {
            "final_response": (
                "Sorry, I couldn't retrieve the information for this "
                "service right now. Please try again in a little while."
            )
        }

    try:
        response = gemini.models.generate_content(
            model=MODEL,
            contents=f"""
You are CivicBridge, a friendly citizen-centric government
services assistant.

USER QUESTION:
{state["user_message"]}

SERVICE RECORD FROM SUPABASE:
{service_data}

Write a helpful, natural, conversational answer.

RESPONSE STYLE:
1. Start by acknowledging the user's request naturally.
2. Give a short introduction explaining what you can help with.
3. Use simple headings when useful, such as:
   Application Procedure, Eligibility, Required Documents,
   Fees and Processing Time, Important Information.
4. Use numbered steps for procedures and simple bullet points
   for lists.
5. Explain available information in sufficient detail without
   being repetitive.
6. Use plain text only. Do not use Markdown formatting,
   asterisks, hash symbols, or Markdown link syntax.
7. Include the official URL only once, at the end, under
   the heading "Official Portal".
8. Do not repeat the URL elsewhere in the answer.
9. If a field is empty, null, or an empty list, explain politely
   that the information is not currently available in the database.
10. Do not invent eligibility criteria, required documents,
    fees, processing times, or official procedures.
11. Use application procedures only when supported by the record.
12. Government requirements may vary by state. Mention this
    when relevant and supported by the context.
13. Never claim that an application has been submitted.

Return only the response intended for the citizen.
"""
        )

        answer = (response.text or "").strip()

        if not answer:
            raise ValueError("Gemini returned an empty response")

        return {"final_response": answer}

    except Exception as error:
        print(f"Answer generation error: {error}")

        service_name = service_data.get(
            "service_name", "this service"
        )
        official_url = service_data.get("official_url")

        answer = (
            f"Hello! I can help you find information about "
            f"{service_name}.\n\n"
            "I couldn't generate a detailed response right now. "
            "Please try again shortly."
        )

        if official_url:
            answer += f"\n\nOfficial Portal:\n{official_url}"

        return {"final_response": answer}


# --------------------------------------------------
# 8. Build the LangGraph workflow
# --------------------------------------------------

builder = StateGraph(CivicState)

builder.add_node("identify_service", identify_service)
builder.add_node("validate_service", validate_service)
builder.add_node("retrieve_service", retrieve_service)
builder.add_node("generate_answer", generate_answer)

builder.add_edge(START, "identify_service")
builder.add_edge("identify_service", "validate_service")
builder.add_edge("validate_service", "retrieve_service")
builder.add_edge("retrieve_service", "generate_answer")
builder.add_edge("generate_answer", END)

graph = builder.compile()


# --------------------------------------------------
# 9. Eligibility checking helpers
# --------------------------------------------------

# Map the service identifiers used by the bot to
# the actual service IDs stored in Supabase.
ELIGIBILITY_SERVICE_IDS = {
    "income_certificate": "INC_001",
    "driving_licence": "DL_001",
    "vehicle_registration": "VR_001",
    "caste_certificate": "CASTE_SC_001",
    "domicile_certificate": "DOM_001",
}


def get_eligibility_criteria(service_id: str) -> list:
    """
    Retrieve eligibility criteria from Supabase.
    Returns a list of criteria or an empty list.
    """
    database_service_id = ELIGIBILITY_SERVICE_IDS.get(
        service_id, service_id
    )

    response = (
        supabase.table("services")
        .select("service_id, service_name, eligibility, official_url")
        .eq("service_id", database_service_id)
        .execute()
    )

    if not response.data:
        return []

    service = response.data[0]
    criteria = service.get("eligibility", [])

    if not isinstance(criteria, list):
        return []

    # Return the criteria as stored in the database.
    return [
        criterion.strip()
        for criterion in criteria
        if isinstance(criterion, str) and criterion.strip()
    ]


def evaluate_eligibility(
    service_id: str,
    answers: dict,
) -> dict:
    """
    Produce a preliminary result from the user's answers.

    Each answer must be keyed by the exact criterion
    returned by get_eligibility_criteria().
    """
    criteria = get_eligibility_criteria(service_id)

    if not criteria:
        return {
            "status": "unknown",
            "message": (
                "I couldn't retrieve eligibility criteria "
                "for this service. Please check the official portal."
            ),
            "met": [],
            "not_met": [],
            "unanswered": [],
        }

    met = []
    not_met = []
    unanswered = []

    for criterion in criteria:
        answer = answers.get(criterion)

        if answer == "yes":
            met.append(criterion)
        elif answer == "no":
            not_met.append(criterion)
        else:
            unanswered.append(criterion)

    if unanswered:
        status = "incomplete"
        message = (
            "I still need answers to all eligibility questions "
            "before providing a preliminary assessment."
        )
    elif not_met:
        status = "not_all_criteria_met"
        message = (
            "Based on your answers, at least one listed criterion "
            "was not met. This is not an official decision."
        )
    else:
        status = "criteria_met"
        message = (
            "Based on your answers, all listed criteria were "
            "reported as met. This is a preliminary assessment, "
            "not confirmation of official eligibility."
        )

    return {
        "status": status,
        "message": message,
        "met": met,
        "not_met": not_met,
        "unanswered": unanswered,
    }
