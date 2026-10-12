
from backend.document_agent import (
    start_document_session,
    get_next_question,
    save_document_answer,
    validate_document_answers,
    prepare_document_data,
)

session = start_document_session("INC_001")

print("First question:", get_next_question(session))

answers = [
    "Test User",
    "New Delhi",
    "300000",
    "Government scheme application",
]

for answer in answers:
    result = save_document_answer(session, answer)

print("Validation:", validate_document_answers(session))
print("Document data:", prepare_document_data(session))
