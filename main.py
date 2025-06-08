import os
import pathlib
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Text, DateTime, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from data_processing import get_ai_response
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# Load environment variables
load_dotenv()

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Cloud SQL (PostgreSQL) configuration via environment variables
CLOUDSQL_USER            = os.getenv("CLOUDSQL_USER")
CLOUDSQL_PASS            = os.getenv("CLOUDSQL_PASS")
CLOUDSQL_DB              = os.getenv("CLOUDSQL_DB")
CLOUDSQL_CONNECTION_NAME = os.getenv("CLOUDSQL_CONNECTION_NAME")
if not (CLOUDSQL_USER and CLOUDSQL_PASS and CLOUDSQL_DB and CLOUDSQL_CONNECTION_NAME):
    raise RuntimeError("Missing one of CLOUDSQL_USER / CLOUDSQL_PASS / CLOUDSQL_DB / CLOUDSQL_CONNECTION_NAME")

DATABASE_URI = (
    f"postgresql+psycopg2://{CLOUDSQL_USER}:{CLOUDSQL_PASS}"
    f"@/{CLOUDSQL_DB}?host=/cloudsql/{CLOUDSQL_CONNECTION_NAME}"
)

# ─────────────────────────────────────────────────────────────────────────────
# SQLAlchemy setup
engine = create_engine(DATABASE_URI, connect_args={"sslmode": "disable"})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"
    id          = Column(Integer, primary_key=True, index=True)

    # Track which “user” (by IP address) this row belongs to:
    user_id     = Column(String, nullable=False, index=True)

    user_input  = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    timestamp   = Column(DateTime, nullable=False)

def init_db():
    """Create or update the 'messages' table if it doesn't exist."""
    Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────────────────────────────────────
# Filesystem base for storing conversation transcripts
# ─────────────────────────────────────────────────────────────────────────────

BASE_PATH = pathlib.Path(__file__).parent.resolve() / "conversations"
BASE_PATH.mkdir(parents=True, exist_ok=True)

def store_turn_on_disk(user_id: str, user_text: str, ai_text: str, timestamp: datetime):
    """
    Create a folder ./conversations/<user_id>/turn_<YYYYMMDD_HHMMSSfff>/ 
    and write two files: user.txt and ai.txt.
    """
    safe_user_id = user_id.replace(":", "_").replace(".", "_")
    user_folder = BASE_PATH / safe_user_id
    user_folder.mkdir(parents=True, exist_ok=True)

    turn_name = timestamp.strftime("turn_%Y%m%d_%H%M%S_%f")
    turn_folder = user_folder / turn_name
    turn_folder.mkdir(parents=True, exist_ok=True)

    (turn_folder / "user.txt").write_text(user_text, encoding="utf-8")
    (turn_folder / "ai.txt").write_text(ai_text, encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Flask endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def index():
    init_db()
    user_id = request.remote_addr
    db = SessionLocal()

    # 1) If “Restart Conversation” was clicked (form name="reset"), clear this IP’s rows, then redirect to a clean GET.
    if request.method == "POST" and "reset" in request.form:
        db.query(Message).filter(Message.user_id == user_id).delete()
        db.commit()
        db.close()
        return redirect(url_for("index"))

    # 2) If “Send” was clicked, process the new user_input.
    if request.method == "POST" and "send" in request.form:
        user_input = request.form.get("user_input", "").strip()
        if user_input:
            # Fetch all prior conversation rows for this IP (to build context)
            prior_rows = (
                db.query(Message)
                  .filter(Message.user_id == user_id)
                  .order_by(Message.id)
                  .all()
            )

            # Build the conversation_history string used as input to get_ai_response
            conversation_history = ""
            for row in prior_rows:
                conversation_history += f"User: {row.user_input}\n"
                conversation_history += f"AI:   {row.ai_response}\n"
            conversation_history += f"User: {user_input}\n"
            conversation_history += "AI:   "  # cue for the model to respond

            # Call the GenAI function (streaming or non‐streaming) to get AI’s reply
            ai_response = get_ai_response(conversation_history)

            # Save this turn in the DB
            now = datetime.utcnow()
            new_msg = Message(
                user_id=user_id,
                user_input=user_input,
                ai_response=ai_response,
                timestamp=now
            )
            db.add(new_msg)
            db.commit()

            # Also write the turn to disk for persistence
            store_turn_on_disk(user_id, user_input, ai_response, now)

            # Build full_display to render everything so far (prior + new)
            full_display = ""
            for row in prior_rows:
                full_display += f"User: {row.user_input}\n"
                full_display += f"AI:   {row.ai_response}\n"
            full_display += f"User: {user_input}\n"
            full_display += f"AI:   {ai_response}"

            db.close()
            return render_template("index.html", conversation_history=full_display)

    # 3) On a GET (or a POST without user_input), we show no history at all:
    db.close()
    return render_template("index.html", conversation_history="")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)