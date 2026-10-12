import os

from dotenv import load_dotenv

from telegram import Update

from telegram.ext import (

    Application,

    CommandHandler,

    MessageHandler,

    ContextTypes,

    filters,

)

from backend.agent import (

    graph,

    get_eligibility_criteria,

    evaluate_eligibility,

)

from backend.session_store import (

    get_session,

    save_session,

    clear_session,

)

from backend.document_agent import (

    DOCUMENT_WORKFLOWS,

    start_document_session,

    get_next_question,

    save_document_answer,

    validate_document_answers,

    prepare_document_data,

)

from backend.pdf_generator import generate_document_pdf

# --------------------------------------------------

# Configuration

# --------------------------------------------------

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:

    raise RuntimeError("TELEGRAM_BOT_TOKEN not found in .env")

INCOME_CERTIFICATE_ID = "INC_001"

OFFICIAL_PORTAL = "https://edistrict.delhi.gov.in/"

# --------------------------------------------------

# Start and cancel commands

# --------------------------------------------------

async def start(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE,

):

    clear_session(update.effective_user.id)

    await update.message.reply_text(

        "Welcome to CivicBridge! 🇮🇳\n\n"

        "I can help you understand government services, "

        "check preliminary eligibility, and prepare draft documents.\n\n"

        "Try asking:\n"

        "• How can I get an income certificate?\n"

        "• Check my eligibility for an income certificate.\n"

        "• Help me prepare an Income Certificate document.\n"

        "• What documents are required for a driving licence?\n\n"

        "Use /cancel to stop your current workflow."

    )

async def cancel(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE,

):

    clear_session(update.effective_user.id)

    await update.message.reply_text(

        "Your current conversation has been reset. "

        "You can start a new request anytime."

    )

# --------------------------------------------------

# Request detection

# --------------------------------------------------

def is_eligibility_request(message: str) -> bool:

    text = message.lower()

    asks_eligibility = any(

        word in text

        for word in ("eligibility", "eligible", "qualify")

    )

    asks_income_certificate = (

        "income certificate" in text

        or "income cert" in text

    )

    return asks_eligibility and asks_income_certificate

def is_document_request(message: str) -> bool:
    """Detect an explicit request to prepare a draft document/PDF."""
    text = " ".join(message.lower().strip().split())

    mentions_income_certificate = any(
        phrase in text
        for phrase in (
            "income certificate",
            "income cert",
        )
    )

    # Support common ways users may request help with preparing a document.
    document_intents = (
        "prepare",
        "preparing",
        "draft",
        "generate a pdf",
        "generate pdf",
        "create a pdf",
        "create pdf",
        "make a pdf",
        "document assistance",
        "document for",
        "prepare an application",
        "prepare application",
        "help me with my application",
        "help with my application",
        "help me prepare",
        "fill my form",
        "fill a form",
        "fill out a form",
        "create an application",
        "make an application",
    )

    asks_for_document = any(intent in text for intent in document_intents)
    detected = mentions_income_certificate and asks_for_document

    print(f"[CivicBridge debug] document request detected={detected}; message={message!r}")
    return detected


# --------------------------------------------------

# Eligibility workflow

# --------------------------------------------------

async def start_eligibility(

    update: Update,

    user_id: int,

):

    try:

        criteria = get_eligibility_criteria(

            INCOME_CERTIFICATE_ID

        )

        if not criteria:

            await update.message.reply_text(

                "I couldn't retrieve the eligibility criteria.\n"

                f"Please check the official portal: {OFFICIAL_PORTAL}"

            )

            return

        session = {

            "flow": "eligibility",

            "service_id": INCOME_CERTIFICATE_ID,

            "step": 0,

            "criteria": criteria,

            "answers": {},

        }

        save_session(user_id, session)

        await update.message.reply_text(

            "Let's check your preliminary eligibility for an "

            "Income Certificate.\n\n"

            "Please answer Yes or No for each requirement.\n\n"

            f"Question 1 of {len(criteria)}:\n"

            "Do you meet this requirement?\n"

            f"{criteria[0]}\n\n"

            "Use /cancel to stop."

        )

    except Exception as error:

        print(f"Eligibility startup error: {error}")

        await update.message.reply_text(

            "I couldn't start the eligibility check. "

            "Please try again."

        )

async def handle_eligibility_answer(

    update: Update,

    user_id: int,

    session: dict,

    user_message: str,

):

    answer = user_message.strip().lower()

    if answer not in {"yes", "no", "y", "n"}:

        await update.message.reply_text(

            "Please answer Yes or No. You can also use /cancel."

        )

        return

    answer = "yes" if answer in {"yes", "y"} else "no"

    criteria = session.get("criteria", [])

    answers = session.get("answers", {})

    step = session.get("step", 0)

    if not criteria or step >= len(criteria):

        clear_session(user_id)

        await update.message.reply_text(

            "Your eligibility session is invalid or expired. "

            "Please start a new eligibility check."

        )

        return

    answers[criteria[step]] = answer

    next_step = step + 1

    if next_step < len(criteria):

        session["answers"] = answers

        session["step"] = next_step

        save_session(user_id, session)

        await update.message.reply_text(

            f"Question {next_step + 1} of {len(criteria)}:\n"

            "Do you meet this requirement?\n"

            f"{criteria[next_step]}"

        )

        return

    try:

        result = evaluate_eligibility(

            session["service_id"],

            answers,

        )

        response = [

            "Preliminary Eligibility Assessment",

            "",

            result["message"],

        ]

        if result.get("met"):

            response.extend([

                "",

                "Criteria reported as met:",

                *[f"- {item}" for item in result["met"]],

            ])

        if result.get("not_met"):

            response.extend([

                "",

                "Criteria reported as not met:",

                *[f"- {item}" for item in result["not_met"]],

            ])

        if result.get("unanswered"):

            response.extend([

                "",

                "Criteria still needing answers:",

                *[f"- {item}" for item in result["unanswered"]],

            ])

        response.extend([

            "",

            "This is not an official eligibility decision.",

            f"Verify current requirements: {OFFICIAL_PORTAL}",

        ])

        clear_session(user_id)

        await update.message.reply_text("\n".join(response))

    except Exception as error:

        print(f"Eligibility evaluation error: {error}")

        # Keep the completed answers available for a retry.

        session["answers"] = answers

        session["step"] = step

        save_session(user_id, session)

        await update.message.reply_text(

            "I couldn't evaluate your answers right now. "

            "Your answers have been saved; please try again."

        )

# --------------------------------------------------

# Document assistance workflow

# --------------------------------------------------

async def start_document_assistance(

    update: Update,

    user_id: int,

):

    try:

        session = start_document_session(

            INCOME_CERTIFICATE_ID

        )

        save_session(user_id, session)

        question = get_next_question(session)

        if not question:

            clear_session(user_id)

            await update.message.reply_text(

                "I couldn't start the document workflow. "

                "Please try again."

            )

            return

        await update.message.reply_text(

            "Let's prepare your Income Certificate assistance document.\n\n"

            "I'll ask a few questions and show you a summary "

            "before generating the PDF.\n\n"

            "This is a draft summary, not an official government form.\n\n"

            f"Question 1:\n{question}\n\n"

            "Use /cancel to stop."

        )

    except Exception as error:

        print(f"Document startup error: {error}")

        await update.message.reply_text(

            "I couldn't start document assistance. "

            "Please try again."

        )

async def handle_document_answer(

    update: Update,

    user_id: int,

    session: dict,

    user_message: str,

):

    try:

        result = save_document_answer(

            session,

            user_message,

        )

        if result["status"] == "needs_answer":

            await update.message.reply_text(

                result["message"]

            )

            return

        session = result["session"]

        if result["status"] == "in_progress":

            save_session(user_id, session)

            total = len(

                DOCUMENT_WORKFLOWS[

                    session["service_id"]

                ]["fields"]

            )

            question_number = session["step"] + 1

            await update.message.reply_text(

                f"Question {question_number} of {total}:\n"

                f"{result['next_question']}\n\n"

                "Use /cancel to stop."

            )

            return

        validation = validate_document_answers(session)

        if not validation["valid"]:

            save_session(user_id, session)

            await update.message.reply_text(

                "Some required details are missing: "

                + ", ".join(validation["missing_fields"])

                + ". Please provide the missing details."

            )

            return

        # Wait for the user to confirm before generating the PDF.

        session["flow"] = "document_confirmation"

        save_session(user_id, session)

        data = session["answers"]

        summary = (

            "Please review your information:\n\n"

            f"Name: {data.get('applicant_name', '')}\n"

            f"Address: {data.get('residential_address', '')}\n"

            f"Annual family income (INR): "

            f"{data.get('annual_family_income', '')}\n"

            f"Purpose: {data.get('purpose', '')}\n\n"

            "If everything is correct, reply YES to generate the PDF.\n"

            "Reply NO to cancel PDF generation.\n"

            "Use /cancel to reset the entire workflow."

        )

        await update.message.reply_text(summary)

    except Exception as error:

        print(f"Document answer error: {error}")

        await update.message.reply_text(

            "I couldn't process that answer. "

            "Please try again or use /cancel."

        )

async def handle_document_confirmation(

    update: Update,

    user_id: int,

    session: dict,

    user_message: str,

):

    answer = user_message.strip().lower()

    if answer not in {"yes", "y", "no", "n"}:

        await update.message.reply_text(

            "Please reply YES to generate the PDF or NO to cancel."

        )

        return

    if answer in {"no", "n"}:

        clear_session(user_id)

        await update.message.reply_text(

            "PDF generation cancelled. "

            "You can start a new request anytime."

        )

        return

    try:

        document_data = prepare_document_data(session)

        pdf_path = generate_document_pdf(document_data)

        with open(pdf_path, "rb") as pdf_file:

            await update.message.reply_document(

                document=pdf_file,

                filename="income_certificate_draft.pdf",

                caption=(

                    "Your CivicBridge draft PDF is ready.\n\n"

                    "This is not an official government form or "

                    "issued certificate.\n"

                    f"Official portal: {OFFICIAL_PORTAL}"

                ),

            )

        clear_session(user_id)

    except Exception as error:

        print(f"PDF generation or delivery error: {error}")

        await update.message.reply_text(

            "I couldn't generate or send the PDF. "

            "Your answers are still saved. Please reply YES to retry "

            "or use /cancel to reset."

        )

# --------------------------------------------------

# General Telegram message handler

# --------------------------------------------------

async def handle_message(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE,

):

    if not update.message or not update.message.text:

        return

    user_id = update.effective_user.id

    user_message = update.message.text.strip()

    try:

        session = get_session(user_id)

    except Exception as error:

        print(f"Redis session error: {error}")

        await update.message.reply_text(

            "I couldn't access your conversation session. "

            "Please try again."

        )

        return

    # Continue active workflows first.

    if session.get("flow") == "eligibility":

        await handle_eligibility_answer(

            update, user_id, session, user_message

        )

        return

    if session.get("flow") == "document":

        await handle_document_answer(

            update, user_id, session, user_message

        )

        return

    if session.get("flow") == "document_confirmation":

        await handle_document_confirmation(

            update, user_id, session, user_message

        )

        return

    # Debug routing: check which workflow should handle this message.
    print("Incoming message:", repr(user_message))
    print("Eligibility detected:", is_eligibility_request(user_message))
    print("Document detected:", is_document_request(user_message))

    # Start a new workflow.

    if is_eligibility_request(user_message):

        await start_eligibility(update, user_id)

        return

    if is_document_request(user_message):

        await start_document_assistance(update, user_id)

        return

    # Existing LangGraph service discovery.

    try:

        result = graph.invoke({

            "user_message": user_message,

            "service_id": "",

            "service_data": {},

            "final_response": "",

        })

        response = result.get(

            "final_response",

            "Sorry, I couldn't generate a response.",

        )

        await update.message.reply_text(response)

    except Exception as error:

        print(f"Message processing error: {error}")

        await update.message.reply_text(

            "Something went wrong while processing your request. "

            "Please try again."

        )

# --------------------------------------------------

# Register handlers and run bot

# --------------------------------------------------

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(CommandHandler("cancel", cancel))

app.add_handler(

    MessageHandler(

        filters.TEXT & ~filters.COMMAND,

        handle_message,

    )

)

print("CivicBridge Telegram Bot is running...")

app.run_polling()
