
from backend.session_store import (
    get_session,
    save_session,
    clear_session
)

# Use a test ID, not your real Telegram user ID
test_user_id = 999999999

clear_session(test_user_id)

session = {
    "flow": "eligibility",
    "step": "residence",
    "answers": {
        "citizenship": "yes"
    }
}

save_session(test_user_id, session)

saved_session = get_session(test_user_id)

print("Saved session:", saved_session)

assert saved_session["step"] == "residence"
assert saved_session["answers"]["citizenship"] == "yes"

clear_session(test_user_id)

print("Redis session test successful!")
