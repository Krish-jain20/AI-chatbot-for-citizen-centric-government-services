
from backend.document_agent import (
    start_document_session,
    save_document_answer,
    prepare_document_data,
)
from backend.pdf_generator import generate_document_pdf

session = start_document_session("INC_001")

answers = [
    "Test User",
    "New Delhi",
    "300000",
    "Government scheme application",
]

for answer in answers:
    save_document_answer(session, answer)

document_data = prepare_document_data(session)
pdf_path = generate_document_pdf(document_data)

print("PDF generated successfully!")
print("Location:", pdf_path)
