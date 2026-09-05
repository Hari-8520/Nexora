import os
import secrets
import sqlite3
import smtplib
import hashlib
import json
import re
from google import genai
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing from .env"
    )

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "change-this-secret-key"
)

DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "learnadapt.db"
)

OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():

    conn = get_db()

    # --------------------------------------------------
    # USERS TABLE
    # --------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            department TEXT NOT NULL,
            year TEXT NOT NULL,
            profile_picture TEXT,
            created_at TEXT NOT NULL
        )
    """)


    # --------------------------------------------------
    # ADD PROFILE PICTURE TO EXISTING DATABASE
    # --------------------------------------------------

    try:

        conn.execute("""
            ALTER TABLE users
            ADD COLUMN profile_picture TEXT
        """)

    except sqlite3.OperationalError:

        # Column already exists
        pass


    # --------------------------------------------------
    # REGISTRATION OTP TABLE
    # --------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS registration_otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            otp_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)


    # --------------------------------------------------
    # PASSWORD RESET OTP TABLE
    # --------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            otp_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)


    # --------------------------------------------------
    # COURSE QUIZ RESULTS TABLE
    # --------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 15,
            completed INTEGER NOT NULL DEFAULT 0,
            completed_at TEXT NOT NULL,
            UNIQUE(user_id, course)
        )
    """)


    conn.commit()
    conn.close()
# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def current_time():
    return datetime.now(timezone.utc)


def normalize_email(email):
    return email.strip().lower()


def generate_otp():
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp(otp):
    return hashlib.sha256(
        otp.encode("utf-8")
    ).hexdigest()


# --------------------------------------------------
# SEND EMAIL
# --------------------------------------------------

def send_otp_email(email, otp):
    smtp_host = os.getenv(
        "SMTP_HOST",
        "smtp.gmail.com"
    )

    smtp_port = int(
        os.getenv("SMTP_PORT", "587")
    )

    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv(
        "SMTP_APP_PASSWORD"
    )

    if not smtp_user or not smtp_password:
        raise RuntimeError(
            "Gmail SMTP is not configured."
        )

    message = EmailMessage()

    message["From"] = smtp_user
    message["To"] = email
    message["Subject"] = "Nexora - Email Verification"

    message.set_content(f"""
Hello,

Welcome to Nexora.

Your email verification OTP is:

{otp}

This OTP will expire in {OTP_EXPIRY_MINUTES} minutes.

If you did not request this verification, please ignore this email.

Nexora
""")

    with smtplib.SMTP(
        smtp_host,
        smtp_port,
        timeout=20
    ) as server:

        server.starttls()

        server.login(
            smtp_user,
            smtp_password
        )

        server.send_message(message)


# --------------------------------------------------
# CREATE OTP
# --------------------------------------------------

def create_registration_otp(email):

    otp = generate_otp()

    created = current_time()

    expires = created + timedelta(
        minutes=OTP_EXPIRY_MINUTES
    )

    conn = get_db()

    # Remove previous OTP
    conn.execute(
        """
        DELETE FROM registration_otps
        WHERE email = ?
        """,
        (email,)
    )

    conn.execute(
        """
        INSERT INTO registration_otps
        (
            email,
            otp_hash,
            expires_at,
            attempts,
            created_at
        )
        VALUES (?, ?, ?, 0, ?)
        """,
        (
            email,
            hash_otp(otp),
            expires.isoformat(),
            created.isoformat()
        )
    )

    conn.commit()
    conn.close()

    send_otp_email(email, otp)


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/")
def home():

    user = require_login()

    if user:
        return redirect(url_for("dashboard"))

    session.clear()

    return render_template("index.html")
# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.post("/api/login")
def login():

    data = request.get_json(silent=True) or {}

    email = normalize_email(data.get("email", ""))
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "ok": False,
            "message": "Please enter your Gmail and password."
        }), 400

    conn = get_db()

    user = conn.execute(
        """
        SELECT
            id,
            email,
            password_hash,
            full_name,
            student_id,
            department,
            year
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    conn.close()

    if not user:
        return jsonify({
            "ok": False,
            "message": "Invalid Gmail or password."
        }), 401

    if not check_password_hash(
        user["password_hash"],
        password
    ):
        return jsonify({
            "ok": False,
            "message": "Invalid Gmail or password."
        }), 401

    # Create login session
    session.clear()

    session["user_id"] = user["id"]
    session["email"] = user["email"]

    return jsonify({
        "ok": True,
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "name": user["full_name"],
            "email": user["email"],
            "student_id": user["student_id"],
            "department": user["department"],
            "year": user["year"]
        }
    })


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

# --------------------------------------------------
# AI CHAT QUIZ CONTEXT
# --------------------------------------------------

def get_student_quiz_context(user_id):
    """
    Read the student's completed quiz results and convert
    them into a simple learning profile for the AI tutor.
    """
    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            course,
            score,
            total,
            completed,
            completed_at
        FROM quiz_results
        WHERE user_id = ?
        ORDER BY completed_at DESC
        """,
        (user_id,)
    ).fetchall()

    conn.close()

    course_names = {
        "data-structures": "Data Structures",
        "computer-architecture": "Computer Architecture"
    }

    results = []
    mastery = {}

    for row in rows:
        course = normalize_course_name(row["course"])
        name = course_names.get(
            course,
            course.replace("-", " ").title()
        )

        total = int(row["total"] or 0)
        score = int(row["score"] or 0)
        percentage = (
            round((score / total) * 100)
            if total > 0
            else 0
        )

        results.append({
            "course": name,
            "score": score,
            "total": total,
            "percentage": percentage,
            "completed": bool(row["completed"]),
            "completed_at": row["completed_at"]
        })

        if row["completed"]:
            mastery[name] = percentage

    # Only use real quiz data to determine the weakest course.
    completed_mastery = {
        course: score
        for course, score in mastery.items()
    }

    if completed_mastery:
        weakest_course = min(
            completed_mastery,
            key=completed_mastery.get
        )
        weakest_score = completed_mastery[weakest_course]
    else:
        weakest_course = None
        weakest_score = None

    return {
        "results": results,
        "mastery": mastery,
        "weakest_course": weakest_course,
        "weakest_score": weakest_score
    }


def clean_ai_response(text):
    """Return clean student-facing text without Markdown clutter."""
    text = str(text or "").strip()
    text = re.sub(r"```[A-Za-z0-9_+-]*", "", text)
    text = text.replace("```", "")
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*]\s+", "• ", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"__([^_\n]+)__", r"\1", text)
    text = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@app.post("/api/chat")
def chat():

    # ---------------------------------------------
    # Check login
    # ---------------------------------------------

    user = require_login()

    if not user:
        return jsonify({
            "ok": False,
            "message": "Please login first."
        }), 401

    # ---------------------------------------------
    # Get message
    # ---------------------------------------------

    data = request.get_json(silent=True) or {}

    message = str(
        data.get("message", "")
    ).strip()

    if not message:
        return jsonify({
            "ok": False,
            "message": "Please enter a message."
        }), 400

    user_id = user["id"]

    # ---------------------------------------------
    # Get REAL quiz performance
    # ---------------------------------------------

    quiz_context = get_student_quiz_context(user_id)

    quiz_results = quiz_context["results"]
    mastery = quiz_context["mastery"]
    weakest_course = quiz_context["weakest_course"]
    weakest_score = quiz_context["weakest_score"]

    if mastery:
        mastery_text = "\n".join(
            f"- {course}: {score}%"
            for course, score in mastery.items()
        )
    else:
        mastery_text = "- No course quiz has been completed yet."

    if weakest_course:
        weakest_text = (
            f"{weakest_course}: {weakest_score}%"
        )
    else:
        weakest_text = (
            "No weak course can be determined yet. "
            "Ask the student to complete a course quiz first."
        )

    # ---------------------------------------------
    # Short conversation memory
    # This allows messages like "A" to be understood
    # as an answer to the previous chatbot question.
    # ---------------------------------------------

    chat_history = session.get("nexora_chat_history", [])

    if not isinstance(chat_history, list):
        chat_history = []

    history_text = "\n".join(
        f"{item.get('role', 'user').upper()}: {item.get('content', '')}"
        for item in chat_history[-6:]
    )

    if not history_text:
        history_text = "No previous conversation."

    # ---------------------------------------------
    # NEXORA AI Tutor prompt
    # ---------------------------------------------

    system_prompt = f"""
You are NEXORA AI Tutor.

You are a personalized learning assistant, not a generic chatbot.

STUDENT
-------
Name: {user["full_name"]}
Student ID: {user["student_id"]}
Department: {user["department"]}
Year: {user["year"]}

REAL QUIZ PERFORMANCE
---------------------
{mastery_text}

WEAKEST COMPLETED COURSE
------------------------
{weakest_text}

IMPORTANT:
- The quiz percentages above come from the student's actual
  completed quizzes stored by NEXORA.
- Do NOT invent quiz scores.
- Do NOT claim a topic is weak unless the available quiz data
  supports it.
- A course score below 60% should normally be treated as an
  area needing improvement.
- A score of 60-79% means the student has a developing
  understanding.
- A score of 80% or above means the student is performing well,
  but do not claim mastery unless there is enough evidence.

TEACHING BEHAVIOR
-----------------
1. Use the student's quiz performance to personalize answers.
2. If the student asks about weak areas, identify the lowest
   completed quiz score and explain why it needs attention.
3. If the student asks about a course, use that course's quiz
   performance when deciding how deeply to explain it.
4. If the student has not completed a quiz, say that clearly
   instead of inventing a score.
5. Teach step-by-step.
6. Keep normal answers concise and useful.
7. Use examples when helpful.
8. After teaching an important concept, ask one short check
   question when appropriate.
9. If the student answers a previous question with a short
   response such as A, B, C, or D, use the conversation history
   to understand what they are answering.
10. If the student's answer is wrong, explain the mistake simply
    and give the next practice question.
11. If the student's answer is correct, gradually increase the
    difficulty.
12. Encourage active learning.
13. Never claim mastery without evidence.

OUTPUT RULES
------------
- Return ONLY the final answer for the student.
- Never output "Draft:", "Final:", "Analysis:", "Reasoning:",
  or similar internal labels.
- Never reveal internal reasoning.
- Never mention prompts, APIs, models, Gemini, or implementation
  details.
- Do not repeat the student's question unnecessarily.
- Do not give multiple alternative answers.
- Use plain text only. Do not use Markdown bold, italic, or headings.
- Do not use * symbols for formatting.
- Keep responses focused and reasonably short.

RECENT CONVERSATION
-------------------
{history_text}

CURRENT STUDENT MESSAGE
-----------------------
{message}
"""

    # ---------------------------------------------
    # FAST GEMINI REQUEST
    # ---------------------------------------------
    # gemini-2.5-flash-lite is no longer available to
    # new users. The API recommends gemini-3.5-flash-lite.
    # Use Chat.send_message to avoid the AFC warning.

    model_name = "gemini-3.5-flash-lite"

    try:
        print(f"Trying Gemini model: {model_name}")

        chat = gemini_client.chats.create(
            model=model_name,
            config={
                "system_instruction": system_prompt,
                "temperature": 0.3,
                "max_output_tokens": 450
            }
        )

        result = chat.send_message(message)

        ai_response = (
            getattr(result, "text", None) or ""
        ).strip()

        if not ai_response:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        print(f"Gemini SUCCESS: {model_name}")

    except Exception as error:
        app.logger.exception(
            "Gemini request failed: %r",
            error
        )

        return jsonify({
            "ok": False,
            "message": (
                "NEXORA AI is temporarily unavailable. "
                "Please try again in a few seconds."
            )
        }), 503

    ai_response = clean_ai_response(ai_response)

    # ---------------------------------------------
    # Save short conversation history
    # ---------------------------------------------

    chat_history.append({
        "role": "user",
        "content": message
    })

    chat_history.append({
        "role": "assistant",
        "content": ai_response
    })

    # Keep the Flask session small.
    session["nexora_chat_history"] = chat_history[-6:]
    session.modified = True

    # ---------------------------------------------
    # Send response to frontend
    # ---------------------------------------------

    return jsonify({
        "ok": True,
        "response": ai_response,
        "weakest_topic": weakest_course,
        "weakest_score": weakest_score,
        "mastery": mastery,
        "quiz_results": quiz_results
    })


# --------------------------------------------------
# START REGISTRATION
# --------------------------------------------------

@app.post("/api/register")
def register():

    data = request.get_json(
        silent=True
    ) or {}

    email = normalize_email(
        data.get("email", "")
    )

    password = data.get(
        "password",
        ""
    )

    confirm_password = data.get(
        "confirm_password",
        ""
    )

    full_name = data.get(
        "full_name",
        ""
    ).strip()

    student_id = data.get(
        "student_id",
        ""
    ).strip()

    department = data.get(
        "department",
        ""
    ).strip()

    year = data.get(
        "year",
        ""
    ).strip()

    # Check fields
    if not all([
        email,
        password,
        confirm_password,
        full_name,
        student_id,
        year
    ]):

        return jsonify({
            "ok": False,
            "message":
                "Please complete all fields."
        }), 400

    # Check password
    if len(password) < 8:

        return jsonify({
            "ok": False,
            "message":
                "Password must contain at least 8 characters."
        }), 400

    if password != confirm_password:

        return jsonify({
            "ok": False,
            "message":
                "Passwords do not match."
        }), 400

    conn = get_db()

    existing = conn.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    conn.close()

    # Existing account
    if existing:

        return jsonify({
            "ok": False,
            "account_exists": True,
            "message":
                "This Gmail is already registered. Please login instead."
        }), 409

    # Store registration details temporarily in session
    session["registration_data"] = {
        "email": email,
        "password_hash":
            generate_password_hash(password),
        "full_name": full_name,
        "student_id": student_id,
        "department": department,
        "year": year
    }

    try:

        create_registration_otp(email)

        return jsonify({
            "ok": True,
            "message":
                "OTP sent to your Gmail."
        })

    except Exception as e:
        print("================================")
        print("OTP EMAIL ERROR:", repr(e))
        print("================================")

        session.pop(
            "registration_data",
            None
        )

        return jsonify({
            "ok": False,
            "message":
                "Could not send OTP. Check your Gmail SMTP settings."
        }), 500


# --------------------------------------------------
# VERIFY REGISTRATION OTP
# --------------------------------------------------

@app.post("/api/verify-registration-otp")
def verify_registration_otp():

    data = request.get_json(
        silent=True
    ) or {}

    otp = str(
        data.get("otp", "")
    ).strip()

    registration = session.get(
        "registration_data"
    )

    if not registration:

        return jsonify({
            "ok": False,
            "message":
                "Registration session expired. Please register again."
        }), 400

    email = registration["email"]

    if len(otp) != 6 or not otp.isdigit():

        return jsonify({
            "ok": False,
            "message":
                "Enter the complete 6-digit OTP."
        }), 400

    conn = get_db()

    record = conn.execute(
        """
        SELECT *
        FROM registration_otps
        WHERE email = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (email,)
    ).fetchone()

    if not record:

        conn.close()

        return jsonify({
            "ok": False,
            "message":
                "OTP not found. Please request a new OTP."
        }), 400

    # Maximum attempts
    if record["attempts"] >= MAX_OTP_ATTEMPTS:

        conn.close()

        return jsonify({
            "ok": False,
            "message":
                "Too many incorrect attempts. Please request a new OTP."
        }), 429

    # Expiration
    expires_at = datetime.fromisoformat(
        record["expires_at"]
    )

    if current_time() > expires_at:

        conn.execute(
            """
            DELETE FROM registration_otps
            WHERE id = ?
            """,
            (record["id"],)
        )

        conn.commit()
        conn.close()

        return jsonify({
            "ok": False,
            "message":
                "OTP expired. Please request a new OTP."
        }), 400

    # Verify OTP
    if not secrets.compare_digest(
        record["otp_hash"],
        hash_otp(otp)
    ):

        conn.execute(
            """
            UPDATE registration_otps
            SET attempts = attempts + 1
            WHERE id = ?
            """,
            (record["id"],)
        )

        conn.commit()
        conn.close()

        return jsonify({
            "ok": False,
            "message":
                "Incorrect OTP."
        }), 400

    # OTP correct
    try:

        conn.execute(
            """
            INSERT INTO users
            (
                email,
                password_hash,
                full_name,
                student_id,
                department,
                year,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                registration["email"],
                registration["password_hash"],
                registration["full_name"],
                registration["student_id"],
                registration["department"],
                registration["year"],
                current_time().isoformat()
            )
        )

        conn.execute(
            """
            DELETE FROM registration_otps
            WHERE email = ?
            """,
            (email,)
        )

        conn.commit()

    except sqlite3.IntegrityError:

        conn.close()

        session.pop(
            "registration_data",
            None
        )

        return jsonify({
            "ok": False,
            "message":
                "This Gmail is already registered."
        }), 409

    conn.close()

    # Login immediately after registration
    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    conn.close()

    session.pop(
        "registration_data",
        None
    )

    session.clear()

    session["user_id"] = user["id"]
    session["email"] = user["email"]

    return jsonify({
        "ok": True,
        "message":
            "Account created successfully.",
        "user": {
            "name": user["full_name"],
            "email": user["email"],
            "student_id": user["student_id"]
        }
    })


# --------------------------------------------------
# RESEND REGISTRATION OTP
# --------------------------------------------------

@app.post("/api/resend-registration-otp")
def resend_registration_otp():

    registration = session.get(
        "registration_data"
    )

    if not registration:

        return jsonify({
            "ok": False,
            "message":
                "Registration session expired."
        }), 400

    email = registration["email"]

    try:

        create_registration_otp(email)

        return jsonify({
            "ok": True,
            "message":
                "A new OTP has been sent."
        })

    except Exception:

        app.logger.exception(
            "Could not resend OTP"
        )

        return jsonify({
            "ok": False,
            "message":
                "Could not resend OTP."
        }), 500

# --------------------------------------------------
# FORGOT PASSWORD
# --------------------------------------------------

@app.post("/api/forgot-password")
def forgot_password():

    data = request.get_json(silent=True) or {}

    email = normalize_email(
        data.get("email", "")
    )

    if not email:
        return jsonify({
            "ok": False,
            "message": "Please enter your Gmail."
        }), 400

    conn = get_db()

    user = conn.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    conn.close()

    if not user:
        return jsonify({
            "ok": False,
            "message": "This Gmail is not registered."
        }), 404

    otp = generate_otp()

    created = current_time()

    expires = created + timedelta(
        minutes=OTP_EXPIRY_MINUTES
    )

    conn = get_db()

    conn.execute(
        """
        DELETE FROM password_reset_otps
        WHERE email = ?
        """,
        (email,)
    )

    conn.execute(
        """
        INSERT INTO password_reset_otps
        (
            email,
            otp_hash,
            expires_at,
            attempts,
            created_at
        )
        VALUES (?, ?, ?, 0, ?)
        """,
        (
            email,
            hash_otp(otp),
            expires.isoformat(),
            created.isoformat()
        )
    )

    conn.commit()
    conn.close()

    try:

        smtp_host = os.getenv(
            "SMTP_HOST",
            "smtp.gmail.com"
        )

        smtp_port = int(
            os.getenv("SMTP_PORT", "587")
        )

        smtp_user = os.getenv("SMTP_USER")

        smtp_password = os.getenv(
            "SMTP_APP_PASSWORD"
        )

        if not smtp_user or not smtp_password:
            raise RuntimeError(
                "Gmail SMTP is not configured."
            )

        message = EmailMessage()

        message["From"] = smtp_user
        message["To"] = email
        message["Subject"] = "Nexora - Password Reset OTP"

        message.set_content(f"""
Hello,

You requested to reset your Nexora password.

Your password reset OTP is:

{otp}

This OTP will expire in {OTP_EXPIRY_MINUTES} minutes.

If you did not request this password reset,
please ignore this email.

Nexora
""")

        with smtplib.SMTP(
            smtp_host,
            smtp_port,
            timeout=20
        ) as server:

            server.starttls()

            server.login(
                smtp_user,
                smtp_password
            )

            server.send_message(message)

        return jsonify({
            "ok": True,
            "message":
                "Password reset OTP sent to your Gmail."
        })

    except Exception as e:

        print(
            "PASSWORD RESET EMAIL ERROR:",
            repr(e)
        )

        return jsonify({
            "ok": False,
            "message":
                "Could not send password reset OTP."
        }), 500
    # --------------------------------------------------
# VERIFY PASSWORD RESET OTP
# --------------------------------------------------

@app.post("/api/verify-password-reset-otp")
def verify_password_reset_otp():

    data = request.get_json(
        silent=True
    ) or {}

    email = normalize_email(
        data.get("email", "")
    )

    otp = str(
        data.get("otp", "")
    ).strip()

    if not email or len(otp) != 6 or not otp.isdigit():

        return jsonify({
            "ok": False,
            "message":
                "Enter the complete 6-digit OTP."
        }), 400

    conn = get_db()

    record = conn.execute(
        """
        SELECT *
        FROM password_reset_otps
        WHERE email = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (email,)
    ).fetchone()

    if not record:

        conn.close()

        return jsonify({
            "ok": False,
            "message":
                "OTP not found. Please request a new OTP."
        }), 400

    if record["attempts"] >= MAX_OTP_ATTEMPTS:

        conn.close()

        return jsonify({
            "ok": False,
            "message":
                "Too many incorrect attempts."
        }), 429

    expires_at = datetime.fromisoformat(
        record["expires_at"]
    )

    if current_time() > expires_at:

        conn.execute(
            """
            DELETE FROM password_reset_otps
            WHERE id = ?
            """,
            (record["id"],)
        )

        conn.commit()
        conn.close()

        return jsonify({
            "ok": False,
            "message":
                "OTP expired. Please request a new OTP."
        }), 400

    if not secrets.compare_digest(
        record["otp_hash"],
        hash_otp(otp)
    ):

        conn.execute(
            """
            UPDATE password_reset_otps
            SET attempts = attempts + 1
            WHERE id = ?
            """,
            (record["id"],)
        )

        conn.commit()
        conn.close()

        return jsonify({
            "ok": False,
            "message":
                "Incorrect OTP."
        }), 400

    conn.close()

    session["password_reset_email"] = email

    return jsonify({
        "ok": True,
        "message":
            "OTP verified successfully."
    })
# --------------------------------------------------
# RESET PASSWORD
# --------------------------------------------------

@app.post("/api/reset-password")
def reset_password():

    data = request.get_json(
        silent=True
    ) or {}

    email = session.get(
        "password_reset_email"
    )

    password = data.get(
        "password",
        ""
    )

    confirm_password = data.get(
        "confirm_password",
        ""
    )

    if not email:

        return jsonify({
            "ok": False,
            "message":
                "Password reset session expired."
        }), 400

    if len(password) < 8:

        return jsonify({
            "ok": False,
            "message":
                "Password must contain at least 8 characters."
        }), 400

    if password != confirm_password:

        return jsonify({
            "ok": False,
            "message":
                "Passwords do not match."
        }), 400

    conn = get_db()

    user = conn.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    if not user:

        conn.close()

        return jsonify({
            "ok": False,
            "message":
                "Account not found."
        }), 404

    conn.execute(
        """
        UPDATE users
        SET password_hash = ?
        WHERE email = ?
        """,
        (
            generate_password_hash(password),
            email
        )
    )

    conn.execute(
        """
        DELETE FROM password_reset_otps
        WHERE email = ?
        """,
        (email,)
    )

    conn.commit()
    conn.close()

    session.pop(
        "password_reset_email",
        None
    )

    return jsonify({
        "ok": True,
        "message":
            "Password changed successfully. Please login."
    })
# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.post("/api/logout")
def logout():

    session.clear()

    return jsonify({
        "ok": True,
        "message":
            "Logged out successfully."
    })
# --------------------------------------------------
# UPDATE PROFILE
# --------------------------------------------------

@app.post("/api/profile/update")
def update_profile():

    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "ok": False,
            "message": "You are not logged in."
        }), 401

    data = request.get_json(silent=True) or {}

    full_name = data.get("full_name", "").strip()
    student_id = data.get("student_id", "").strip()
    year = data.get("year", "").strip()
    email = normalize_email(
        data.get("email", "")
    )

    profile_picture = data.get(
        "profile_picture"
    )


    # -----------------------------------------------
    # VALIDATION
    # -----------------------------------------------

    if not full_name:
        return jsonify({
            "ok": False,
            "message": "Full name is required."
        }), 400

    if not student_id:
        return jsonify({
            "ok": False,
            "message": "Student ID is required."
        }), 400

    if not year:
        return jsonify({
            "ok": False,
            "message": "Year is required."
        }), 400

    if not email:
        return jsonify({
            "ok": False,
            "message": "Email is required."
        }), 400


    conn = get_db()

    try:

        # -------------------------------------------
        # CHECK DUPLICATE EMAIL
        # -------------------------------------------

        existing_user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            AND id != ?
            """,
            (
                email,
                user_id
            )
        ).fetchone()


        if existing_user:

            conn.close()

            return jsonify({
                "ok": False,
                "message":
                    "That email is already registered."
            }), 400


        # -------------------------------------------
        # UPDATE PROFILE
        # -------------------------------------------

        conn.execute(
            """
            UPDATE users
            SET
                full_name = ?,
                student_id = ?,
                year = ?,
                email = ?,
                profile_picture =
                    COALESCE(?, profile_picture)
            WHERE id = ?
            """,
            (
                full_name,
                student_id,
                year,
                email,
                profile_picture,
                user_id
            )
        )


        conn.commit()


        # Update session email
        session["email"] = email


    except Exception as error:

        conn.rollback()
        conn.close()

        app.logger.exception(
            "Profile update failed"
        )

        return jsonify({
            "ok": False,
            "message":
                f"Could not update profile: {error}"
        }), 500


    conn.close()


    return jsonify({
        "ok": True,
        "message":
            "Profile updated successfully."
    })
# --------------------------------------------------
# CURRENT USER
# --------------------------------------------------

@app.get("/api/me")
def current_user():

    user_id = session.get(
        "user_id"
    )

    if not user_id:

        return jsonify({
            "authenticated": False
        })

    conn = get_db()

    user = conn.execute(
        """
        SELECT
            id,
            email,
            full_name,
            student_id,
            department,
            year,
            profile_picture
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    if not user:

        session.clear()

        return jsonify({
            "authenticated": False
        })

    return jsonify({
        "authenticated": True,
        "user": dict(user)
    })


# --------------------------------------------------


# --------------------------------------------------
# COURSE QUIZ DATA
# --------------------------------------------------

QUIZ_QUESTIONS = {
    "data-structures": [
        {
            "id": 1,
            "question": "In a singly linked list, what does the next pointer of the last node normally contain?",
            "options": ["The first node", "NULL", "The previous node", "The list size"],
            "answer": 1
        },
        {
            "id": 2,
            "question": "What is the main purpose of the head pointer in a singly linked list?",
            "options": ["It stores the last node", "It stores the number of nodes", "It points to the first node", "It points to NULL only"],
            "answer": 2
        },
        {
            "id": 3,
            "question": "What is the usual time complexity for inserting a node at the beginning of a singly linked list when the head is known?",
            "options": ["O(1)", "O(log n)", "O(n)", "O(n²)"],
            "answer": 0
        },
        {
            "id": 4,
            "question": "During traversal of a singly linked list, when should traversal normally stop?",
            "options": ["When the current node is NULL", "After the first node", "When the list becomes sorted", "After two nodes"],
            "answer": 0
        },
        {
            "id": 5,
            "question": "Which additional pointer is present in a doubly linked list compared with a singly linked list?",
            "options": ["Root", "Previous", "Tail only", "Index"],
            "answer": 1
        },
        {
            "id": 6,
            "question": "In a doubly linked list, what should the previous pointer of the first node normally contain?",
            "options": ["The last node", "The second node", "NULL", "The list size"],
            "answer": 2
        },
        {
            "id": 7,
            "question": "Which operation is generally easier in a doubly linked list because each node stores both previous and next links?",
            "options": ["Backward traversal", "Creating an array", "Changing the data type", "Sorting without comparisons"],
            "answer": 0
        },
        {
            "id": 8,
            "question": "When inserting a node at a position in a linked list, what must be updated to preserve the list links?",
            "options": ["Only the new node's data", "The relevant node pointers", "Only the list name", "Only the first node's data"],
            "answer": 1
        },
        {
            "id": 9,
            "question": "What makes a circular linked list different from a standard singly linked list?",
            "options": ["It has no nodes", "The last node points back to the first node", "Every node has two previous pointers", "It can store only integers"],
            "answer": 1
        },
        {
            "id": 10,
            "question": "In a circular linked list, what happens if traversal continues without a stopping condition?",
            "options": ["The list is automatically deleted", "Traversal can continue indefinitely", "The head becomes NULL", "The nodes become sorted"],
            "answer": 1
        },
        {
            "id": 11,
            "question": "Which operation removes a node from a linked list?",
            "options": ["Traversal", "Deletion", "Insertion", "Initialization"],
            "answer": 1
        },
        {
            "id": 12,
            "question": "What is a common way to delete the first node of a singly linked list?",
            "options": ["Move head to head.next", "Set every node to NULL", "Move head to the last node", "Sort the list first"],
            "answer": 0
        },
        {
            "id": 13,
            "question": "If a node is deleted from the middle of a singly linked list, what generally needs to happen to the previous node's next pointer?",
            "options": ["It points to the deleted node", "It points to the node after the deleted node", "It becomes the list size", "It points to itself"],
            "answer": 1
        },
        {
            "id": 14,
            "question": "Which linked-list operation visits nodes one by one to process or display their contents?",
            "options": ["Traversal", "Compilation", "Casting", "Hashing"],
            "answer": 0
        },
        {
            "id": 15,
            "question": "For insertion at the end of a linked list when only the head pointer is available, what may be required?",
            "options": ["Traverse to the last node", "Delete the head", "Reverse every node first", "Convert the list to an array"],
            "answer": 0
        }
    ],

    "computer-architecture": [
        {
            "id": 1,
            "question": "Which unit of a computer performs arithmetic and logical operations?",
            "options": ["ALU", "Cache", "DMA controller", "I/O port"],
            "answer": 0
        },
        {
            "id": 2,
            "question": "Which component controls and coordinates the operations of the CPU?",
            "options": ["Control Unit", "Cache", "RAM chip only", "Keyboard"],
            "answer": 0
        },
        {
            "id": 3,
            "question": "Which number system uses only 0 and 1?",
            "options": ["Decimal", "Octal", "Binary", "Hexadecimal"],
            "answer": 2
        },
        {
            "id": 4,
            "question": "What is the decimal value of binary 1010?",
            "options": ["8", "10", "12", "14"],
            "answer": 1
        },
        {
            "id": 5,
            "question": "Which representation is commonly used to represent negative integers in modern computers?",
            "options": ["Two's complement", "BCD only", "Gray code only", "ASCII only"],
            "answer": 0
        },
        {
            "id": 6,
            "question": "Which CPU component temporarily stores operands and intermediate values for fast access?",
            "options": ["Registers", "Hard disk", "Printer", "Keyboard"],
            "answer": 0
        },
        {
            "id": 7,
            "question": "What is the correct general order of the basic instruction cycle?",
            "options": ["Execute → Decode → Fetch", "Fetch → Decode → Execute", "Decode → Execute → Fetch", "Fetch → Execute → Decode"],
            "answer": 1
        },
        {
            "id": 8,
            "question": "Which ISA component specifies the operation that an instruction should perform?",
            "options": ["Opcode", "Cache line", "Memory address bus", "Clock battery"],
            "answer": 0
        },
        {
            "id": 9,
            "question": "What is the main purpose of pipelining in a processor?",
            "options": ["Increase instruction throughput", "Eliminate all memory", "Remove registers", "Reduce the number of instructions to zero"],
            "answer": 0
        },
        {
            "id": 10,
            "question": "Which type of pipeline hazard occurs when an instruction depends on the result of an earlier instruction?",
            "options": ["Data hazard", "Structural hazard", "Control hazard", "Power hazard"],
            "answer": 0
        },
        {
            "id": 11,
            "question": "Which memory is generally faster and smaller than main memory and is placed close to the CPU?",
            "options": ["Cache", "Secondary storage", "Optical disk", "Tape"],
            "answer": 0
        },
        {
            "id": 12,
            "question": "What is virtual memory mainly used for?",
            "options": ["Providing the illusion of a larger memory space", "Increasing keyboard speed", "Replacing the CPU", "Removing all caches"],
            "answer": 0
        },
        {
            "id": 13,
            "question": "What does DMA allow in an I/O system?",
            "options": ["Data transfer between I/O and memory with reduced CPU involvement", "The CPU to stop executing forever", "Memory to become read-only", "The cache to become permanent storage"],
            "answer": 0
        },
        {
            "id": 14,
            "question": "Which instruction type changes the normal sequential flow of program execution?",
            "options": ["Branch instruction", "Load instruction only", "Store instruction only", "NOP only"],
            "answer": 0
        },
        {
            "id": 15,
            "question": "What is the main idea of parallel processing?",
            "options": ["Perform multiple operations concurrently", "Use only one instruction for every program", "Remove all processors", "Store every value on a keyboard"],
            "answer": 0
        }
    ]
}


def normalize_course_name(course):
    course = str(course or "").strip().lower()

    aliases = {
        "data structures": "data-structures",
        "data-structure": "data-structures",
        "data_structures": "data-structures",
        "computer architecture": "computer-architecture",
        "computer-architecture": "computer-architecture",
        "computer_architecture": "computer-architecture"
    }

    return aliases.get(course, course)


def quiz_is_completed(user_id, course):
    course = normalize_course_name(course)

    conn = get_db()

    result = conn.execute(
        """
        SELECT completed
        FROM quiz_results
        WHERE user_id = ? AND course = ?
        """,
        (user_id, course)
    ).fetchone()

    conn.close()

    return bool(result and result["completed"] == 1)


# --------------------------------------------------
# QUIZ PAGE
# --------------------------------------------------

@app.route("/quiz")
def quiz_page():
    student = dashboard_student()

    if not student:
        return redirect(url_for("home"))

    course = normalize_course_name(request.args.get("course", ""))

    return render_template(
        "page.html",
        page="quiz",
        student=student,
        courses=courses,
        videos=videos,
        sources=sources,
        certificates=certificates,
        quiz_course=course
    )


# --------------------------------------------------
# GET QUIZ
# --------------------------------------------------

@app.get("/api/quiz/<course>")
def get_quiz(course):

    user = require_login()

    if not user:
        return jsonify({
            "ok": False,
            "message": "Please login first."
        }), 401

    course = normalize_course_name(course)
    question_bank = QUIZ_QUESTIONS.get(course)

    if not question_bank:
        return jsonify({
            "ok": False,
            "message": "Quiz not found."
        }), 404

    # Always select exactly 15 questions.
    if len(question_bank) < 15:
        return jsonify({
            "ok": False,
            "message": "This quiz does not contain 15 questions."
        }), 500

    selected_questions = secrets.SystemRandom().sample(
        question_bank,
        15
    )

    # Save the exact questions shown to the student.
    # Submission will use these same 15 questions.
    session[f"quiz_questions_{course}"] = [
        question["id"]
        for question in selected_questions
    ]

    safe_questions = [
        {
            "id": question["id"],
            "question": question["question"],
            "options": question["options"]
        }
        for question in selected_questions
    ]

    return jsonify({
        "ok": True,
        "course": course,
        "total": 15,
        "completed": quiz_is_completed(user["id"], course),
        "questions": safe_questions
    })


# --------------------------------------------------
# SUBMIT QUIZ
# --------------------------------------------------

@app.post("/api/quiz/submit")
def submit_quiz():

    user = require_login()

    if not user:
        return jsonify({
            "ok": False,
            "message": "Please login first."
        }), 401

    data = request.get_json(silent=True) or {}

    course = normalize_course_name(data.get("course"))
    answers = data.get("answers")

    question_bank = QUIZ_QUESTIONS.get(course)

    if not question_bank:
        return jsonify({
            "ok": False,
            "message": "Quiz not found."
        }), 404

    if not isinstance(answers, dict):
        return jsonify({
            "ok": False,
            "message": "Please submit your quiz answers."
        }), 400

    selected_ids = session.get(
        f"quiz_questions_{course}"
    )

    if (
        not isinstance(selected_ids, list)
        or len(selected_ids) != 15
    ):
        return jsonify({
            "ok": False,
            "message": "Quiz session expired. Please reload the quiz."
        }), 400

    questions_by_id = {
        str(question["id"]): question
        for question in question_bank
    }

    questions = []

    for question_id in selected_ids:
        question = questions_by_id.get(str(question_id))

        if question is None:
            return jsonify({
                "ok": False,
                "message": "Quiz questions could not be restored."
            }), 500

        questions.append(question)

    if len(answers) != 15:
        return jsonify({
            "ok": False,
            "message": "Please answer all 15 questions before submitting."
        }), 400

    score = 0
    correct_answers = {}

    for question in questions:

        question_id = str(question["id"])

        submitted_answer = answers.get(question_id)

        try:
            submitted_answer = int(submitted_answer)
        except (TypeError, ValueError):
            submitted_answer = -1

        correct_answers[question_id] = question["answer"]

        if submitted_answer == question["answer"]:
            score += 1

    total = 15
    completed_at = current_time().isoformat()

    conn = get_db()

    try:

        conn.execute(
            """
            INSERT INTO quiz_results
            (
                user_id,
                course,
                score,
                total,
                completed,
                completed_at
            )
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(user_id, course)
            DO UPDATE SET
                score = excluded.score,
                total = excluded.total,
                completed = 1,
                completed_at = excluded.completed_at
            """,
            (
                user["id"],
                course,
                score,
                total,
                completed_at
            )
        )

        conn.commit()

    except Exception as error:

        conn.rollback()

        app.logger.exception(
            "Quiz submission failed"
        )

        conn.close()

        return jsonify({
            "ok": False,
            "message": f"Could not save quiz result: {error}"
        }), 500

    conn.close()

    # Correct answers are returned only after submission.
    return jsonify({
        "ok": True,
        "message": "Quiz completed successfully. Course unlocked.",
        "course": course,
        "score": score,
        "total": total,
        "percentage": round((score / total) * 100),
        "completed": True,
        "correct_answers": correct_answers
    })


# --------------------------------------------------
# QUIZ RESULT
# --------------------------------------------------

@app.get("/api/quiz/result/<course>")
def quiz_result(course):

    user = require_login()

    if not user:
        return jsonify({
            "ok": False,
            "message": "Please login first."
        }), 401

    course = normalize_course_name(course)

    if course not in QUIZ_QUESTIONS:
        return jsonify({
            "ok": False,
            "message": "Quiz not found."
        }), 404

    conn = get_db()

    result = conn.execute(
        """
        SELECT
            course,
            score,
            total,
            completed,
            completed_at
        FROM quiz_results
        WHERE user_id = ? AND course = ?
        """,
        (user["id"], course)
    ).fetchone()

    conn.close()

    if not result:
        return jsonify({
            "ok": True,
            "completed": False,
            "course": course
        })

    return jsonify({
        "ok": True,
        "completed": bool(result["completed"]),
        "course": result["course"],
        "score": result["score"],
        "total": result["total"],
        "percentage": round((result["score"] / result["total"]) * 100) if result["total"] else 0,
        "completed_at": result["completed_at"]
    })


# --------------------------------------------------
# DASHBOARD DATA AND ROUTES
# --------------------------------------------------

student_defaults = {'name': 'Ashwin Kumaar', 'email': 'ashwinkumaar@gmail.com', 'student_id': '2501014', 'department': 'Computer Science and Engineering', 'year': '3rd Year', 'college': 'Sri Ramakrishna Engineering College', 'batch': '2029', 'learning_level': 'Intermediate', 'mastery': 74, 'quiz_accuracy': 89, 'streak': 15, 'active_days': 42, 'completed_topics': 28}

courses = [
    {
        'title': 'Data Structures',
        'description': 'Build strong foundations in arrays, linked lists, trees and graphs.',
        'category': 'Computer Science',
        'progress': 48,
        'lessons': 32,
        'assessments': 7,
        'duration': '25 Hours',
        'status': 'Continue'
    },
   
    {
        'title': 'Computer Architecture',
        'description': 'Learn computer organization, CPU, memory, registers and system architecture.',
        'category': 'Computer Science',
        'progress': 0,
        'lessons': 30,
        'assessments': 5,
        'duration': '20 Hours',
        'status': 'Start Learning'
    }
]

videos = [
    {'title': 'Understanding Linked Lists', 'topic': 'Data Structures', 'duration': '', 'level': '', 'reference': 'nptel_linked_list', 'subtopics': [
        {'title': 'Introduction to Linked List in C', 'videoUrl': ''},
        {'title': 'Insertion at the Beginning in Singly Linked List', 'videoUrl': ''},
        {'title': 'Insertion at a Position in Singly Linked List', 'videoUrl': ''},
        {'title': 'Insertion at the End in Singly Linked List', 'videoUrl': ''},
        {'title': 'Traversal of a Linked List in Singly Linked List', 'videoUrl': ''},
        {'title': 'Deletion at the Beginning in Singly Linked List', 'videoUrl': ''},
        {'title': 'Deletion at a Position in Singly Linked List', 'videoUrl': ''},
        {'title': 'Deletion at the End in Singly Linked List', 'videoUrl': ''}
    ]},

    {'title': 'Understanding Doubly Linked List', 'topic': 'Data Structures', 'duration': '', 'level': '', 'reference': 'nptel_doubly_linked_list', 'subtopics': [
        {'title': 'Insertion at the Beginning in Doubly Linked List', 'videoUrl': ''},
        {'title': 'Insertion at a Position in Doubly Linked List', 'videoUrl': ''},
        {'title': 'Insertion at the End in Doubly Linked List', 'videoUrl': ''},
        {'title': 'Deletion at the Beginning in Doubly Linked List', 'videoUrl': ''}
    ]},

    {'title': 'Circular Linked List', 'topic': 'Data Structures', 'duration': '', 'level': '', 'reference': None, 'subtopics': [
        {'title': 'Deletion at the End in Circular Linked List', 'videoUrl': ''},
        {'title': 'Insertion at the End in Circular Linked List', 'videoUrl': ''}
    ]}
]
sources = [{'title': 'Python Documentation', 'type': 'Documentation', 'topic': 'Python', 'description': 'Official Python language documentation and reference.'}, {'title': 'Java OOP Guide', 'type': 'Article', 'topic': 'Java', 'description': 'Learn classes, objects, inheritance and polymorphism.'}, {'title': 'Data Structures Notes', 'type': 'PDF Notes', 'topic': 'DSA', 'description': 'Quick revision notes for common data structures.'}, {'title': 'SQL Practice Problems', 'type': 'Practice', 'topic': 'Database', 'description': 'Practice SQL queries and database concepts.'}]

certificates = [
    {
        'title': 'Data Structures',
        'topic': 'Data Structures',
        'status': 'Earned',
        'date': '-'
    },
    {
        'title': 'Computer Architecture',
        'topic': 'Computer Architecture',
        'status': 'Earned',
        'date': '-'
    }
]
def require_login():

    user_id = session.get("user_id")

    if not user_id:
        return None

    conn = get_db()

    user = conn.execute(
        """
             SELECT
            id,
            email,
            full_name,
            student_id,
            department,
            year,
            profile_picture
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    if not user:

        session.clear()

        return None

    return user
def dashboard_student():
    user = require_login()
    if not user:
        return None
    data = dict(student_defaults)
    data.update({
    "name": user["full_name"],
    "email": user["email"],
    "student_id": user["student_id"],
    "department": user["department"],
    "year": user["year"],
    "profile_picture": user["profile_picture"]
})
    return data


def render_dashboard_page(page_name):
    student = dashboard_student()
    if not student:
        return redirect(url_for("home"))
    return render_template(
        "page.html",
        page=page_name,
        student=student,
        courses=courses,
        videos=videos,
        sources=sources,
        certificates=certificates
    )


@app.route("/dashboard")
def dashboard():
    return render_dashboard_page("dashboard")


@app.route("/courses")
def course_page():
    return render_dashboard_page("courses")
@app.route("/data-structures")
def data_structures():
    user = require_login()

    if not user:
        return redirect(url_for("home"))

    if not quiz_is_completed(user["id"], "data-structures"):
        return redirect(url_for("quiz_page", course="data-structures"))

    return render_template("datastructure.html")
@app.route("/linked-list-simulation")
def linked_list_simulation():
    return render_template("linklist.html")


@app.route("/computer-architecture")
def computer_architecture():
    user = require_login()

    if not user:
        return redirect(url_for("home"))

    if not quiz_is_completed(user["id"], "computer-architecture"):
        return redirect(url_for("quiz_page", course="computer-architecture"))

    return render_template("computer_architecture.html")


@app.route("/videos")
def video_page():
    return render_dashboard_page("videos")


@app.route("/chatbot")
def chatbot():
    return render_dashboard_page("chatbot")


@app.route("/sources")
def source_page():
    return render_dashboard_page("sources")

@app.route("/simulation")
def simulation():
    return render_dashboard_page("simulation")

@app.route("/certificate")
def certificate_page():
    return render_dashboard_page("certificate")


@app.route("/profile")
def profile():
    return render_dashboard_page("profile")


@app.get("/logout")
def dashboard_logout():
    session.clear()
    return redirect(url_for("home"))


# RUN
# --------------------------------------------------

if __name__ == "__main__":

    init_db()

    app.run( 
        debug=True
    )
    # Add profile_picture column to existing databases
