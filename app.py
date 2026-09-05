import os
import json
import secrets
import sqlite3
import smtplib
import hashlib
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

# Keep the login session alive for 30 days instead of expiring the moment
# the browser closes. Without this, a user who closes their browser and
# comes back "the next day" would get bounced back to the login page,
# which looked identical to (and was easy to confuse with) courses being
# re-locked. Active Days / streaks are still computed from real calendar
# dates in the database, so this only affects how long someone stays
# signed in - not how activity is counted.
app.permanent_session_lifetime = timedelta(days=30)

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


    # --------------------------------------------------
    # USER ACTIVITY TABLE (per-user active days / streak)
    # --------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activity_date TEXT NOT NULL,
            UNIQUE(user_id, activity_date)
        )
    """)

    # Stores the questions/answers from each quiz attempt so the roadmap can
    # identify weak concepts instead of only looking at the overall score.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            wrong_question_ids TEXT NOT NULL DEFAULT '[]',
            completed_at TEXT NOT NULL
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

    session.permanent = True
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

@app.post("/api/chat")
def chat():

    # ---------------------------------------------
    # Check login
    # ---------------------------------------------

    if not session.get("user_id"):
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

    # ---------------------------------------------
    # Get logged-in student
    # ---------------------------------------------

    user_id = session.get("user_id")

    conn = get_db()

    user = conn.execute("""
        SELECT
            full_name,
            student_id,
            department,
            year
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    conn.close()

    if not user:
        return jsonify({
            "ok": False,
            "message": "Student not found."
        }), 404

    student = dict(user)

    # ---------------------------------------------
    # Real per-user mastery profile
    # ---------------------------------------------

    user_results = get_user_quiz_results(user_id)
    mastery = {}

    for course in courses:
        course_key = normalize_course_name(course["title"])
        result = user_results.get(course_key)
        if result and result["total"]:
            mastery[course["title"]] = round(
                (result["score"] / result["total"]) * 100
            )
        else:
            mastery[course["title"]] = 0

    weakest_topic = min(mastery, key=mastery.get) if mastery else "Data Structures"

    # ---------------------------------------------
    # NEXORA AI Tutor
    # ---------------------------------------------

    system_prompt = f"""
You are NEXORA AI Tutor.

You are NOT a generic chatbot.

Your purpose is to help a student learn
through personalized and adaptive teaching.

STUDENT PROFILE
----------------
Name: {student['full_name']}
Student ID: {student['student_id']}
Department: {student['department']}
Year: {student['year']}

CURRENT MASTERY
----------------
{chr(10).join(f"{topic}: {score}%" for topic, score in mastery.items())}

WEAKEST TOPIC
----------------
{weakest_topic}: {mastery[weakest_topic]}%

YOUR TEACHING RULES
----------------

1. Adapt explanations to the student's level.

2. Do not simply dump a long answer.

3. Teach step-by-step.

4. If the student asks about a topic they
   struggle with, explain it more carefully.

5. Detect possible misconceptions.

6. After explaining an important concept,
   ask a short question to check understanding.

7. If the student answers correctly,
   gradually increase difficulty.

8. If the student struggles,
   simplify the explanation.

9. Recommend the student's weak topic
   when appropriate.

10. When recommending a topic, explain WHY
    you recommended it.

11. Encourage active learning.

12. Keep responses clear and reasonably concise.

13. Use examples whenever they improve understanding.

14. Never claim that the student mastered
    something unless there is evidence.
IMPORTANT OUTPUT RULES
----------------------

- Return ONLY the final response intended for the student.
- Never output words such as "Draft:", "Draft*:", "Final:", "Analysis:", or "Reasoning:".
- Never describe your internal thinking or reasoning.
- Do not generate multiple alternative answers.
- Do not repeat the student's question.
- Do not mention system prompts, instructions, models, APIs, or Gemini.

NEXORA SHOULD FEEL LIKE:

Student
   ↓
Understand
   ↓
Teach
   ↓
Check understanding
   ↓
Adapt
   ↓
Practice
   ↓
Improve

The student's current question is:

{message}
"""

    # ---------------------------------------------
    # Call Gemini
    # ---------------------------------------------
    models_to_try = [
        "gemini-3.7-flash",
        "gemini-3.6-flash"
]

    ai_response = None

    for model_name in models_to_try:
        try:
            print(f"Trying Gemini model: {model_name}")

            result = gemini_client.models.generate_content(
                model=model_name,
                contents=system_prompt
            )

            ai_response = result.text

            if ai_response:
                print(f"Gemini SUCCESS: {model_name}")
                break

        except Exception as e:
            print(f"GEMINI ERROR: {model_name}")
            print(repr(e))
            print("================================")

    if not ai_response:
        return jsonify({
            "ok": False,
            "message": "NEXORA AI could not connect to Gemini."
        }), 500

    
    # ---------------------------------------------
    # If all models failed
    # ---------------------------------------------

    if not ai_response:

        return jsonify({
            "ok": False,
            "message": (
                "NEXORA AI is temporarily unavailable. "
                "Please try again in a few seconds."
            )
        }), 503

    # ---------------------------------------------
    # Send response to frontend
    # ---------------------------------------------

    return jsonify({
        "ok": True,
        "response": ai_response,
        "weakest_topic": weakest_topic,
        "mastery": mastery
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

    session.permanent = True
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

# Question-to-topic mapping used by the adaptive Today's Roadmap.
# Each quiz question belongs to the concept it tests, so wrong answers can
# point the learner toward a concrete topic to study.
QUIZ_TOPIC_MAP = {
    "data-structures": {
        1: "Singly Linked List", 2: "Singly Linked List", 3: "Singly Linked List",
        4: "Singly Linked List", 5: "Doubly Linked List", 6: "Doubly Linked List",
        7: "Doubly Linked List", 8: "Doubly Linked List", 9: "Circular Linked List",
        10: "Circular Linked List", 11: "Linked List Operations",
        12: "Linked List Operations", 13: "Linked List Operations",
        14: "Linked List Operations", 15: "Linked List Operations"
    },
    "computer-architecture": {
        1: "Computer Organization Basics", 2: "Computer Organization Basics",
        3: "Number Systems & Data Representation", 4: "Number Systems & Data Representation",
        5: "Number Systems & Data Representation", 6: "Registers & Instruction Register",
        7: "Instruction Cycle", 8: "Instruction Cycle", 9: "CPU Organization",
        10: "CPU Organization", 11: "Cache Memory", 12: "Memory Hierarchy",
        13: "I/O Techniques", 14: "Instruction Cycle", 15: "CPU Organization"
    }
}

ROADMAP_TOPIC_PLAN = {
    "Data Structures": [
        "Arrays & Array Operations", "Singly Linked List", "Doubly Linked List",
        "Circular Linked List", "Stacks", "Queues", "Trees", "Binary Search Tree",
        "Graphs", "Hashing", "Searching & Sorting"
    ],
    "Computer Architecture": [
        "Computer Organization Basics", "Number Systems & Data Representation",
        "Instruction Cycle", "Registers & Instruction Register", "Addressing Modes",
        "CPU Organization", "Memory Hierarchy", "RAM & ROM", "Cache Memory",
        "I/O Techniques", "Interrupts & Polling"
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
    wrong_question_ids = []

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
        else:
            wrong_question_ids.append(int(question["id"]))

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

        conn.execute(
            """
            INSERT INTO quiz_attempts
            (user_id, course, score, total, wrong_question_ids, completed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"], course, score, total,
                json.dumps(wrong_question_ids), completed_at
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

    # Completing a quiz is genuine learning activity for this user.
    record_user_activity(user["id"])

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

# NOTE: these are only used as *fallback/cosmetic* defaults (things we don't
# actually track per-user, like college/batch/learning_level). The progress
# numbers (mastery, quiz_accuracy, streak, active_days, completed_topics)
# are always recomputed per logged-in user from real DB data below -
# they must never be served as-is to every user.
student_defaults = {'name': 'Student', 'email': '', 'student_id': '', 'department': '', 'year': '', 'college': 'Sri Ramakrishna Engineering College', 'batch': '2029', 'learning_level': 'Intermediate', 'mastery': 0, 'quiz_accuracy': 0, 'streak': 0, 'active_days': 0, 'completed_topics': 0}


def record_user_activity(user_id):
    """Log that this user was active *today* (for streak / active-days).

    This is what makes "Active Days" behave like a login-based day
    counter: the very first time a user reaches an authenticated page
    (dashboard, courses, quiz, etc.) on a given calendar date, one row
    is written for that date. INSERT OR IGNORE + the UNIQUE(user_id,
    activity_date) constraint on the table guarantees a single date is
    only ever counted once, no matter how many times the user logs in,
    refreshes, or navigates around during that same day.
    """
    conn = get_db()
    try:
        today = current_time().date().isoformat()
        conn.execute(
            """
            INSERT OR IGNORE INTO user_activity (user_id, activity_date)
            VALUES (?, ?)
            """,
            (user_id, today)
        )
        conn.commit()
    finally:
        conn.close()


def get_active_days(user_id):
    """Count the distinct calendar days this user has logged in / been
    active on. Driven by user_activity (recorded on every authenticated
    request), NOT by quiz completion - so day 1 shows 1 active day as
    soon as the user reaches the dashboard, and each new calendar day
    the user logs back in bumps the count by exactly 1, whether or not
    they take a quiz that day."""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT DISTINCT activity_date
        FROM user_activity
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return len(rows)


def get_user_activity_dates(user_id):
    """Return every calendar date this user was active (logged in), used
    to color in the Learning Activity heatmap."""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT DISTINCT activity_date
        FROM user_activity
        WHERE user_id = ?
        ORDER BY activity_date
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return [row["activity_date"] for row in rows if row["activity_date"]]


def get_learning_streak(user_id):
    """Consecutive-day login streak, computed from user_activity (login
    days) rather than quiz completion days."""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT DISTINCT activity_date
        FROM user_activity
        WHERE user_id = ?
        ORDER BY activity_date DESC
        """,
        (user_id,)
    ).fetchall()
    conn.close()

    if not rows:
        return 0

    dates = sorted(
        {datetime.strptime(r["activity_date"], "%Y-%m-%d").date() for r in rows},
        reverse=True
    )

    today = current_time().date()
    if dates[0] not in (today, today - timedelta(days=1)):
        return 0

    streak = 1
    start_date = dates[0]
    for date_value in dates[1:]:
        if date_value == start_date - timedelta(days=1):
            streak += 1
            start_date = date_value
        else:
            break
    return streak

def get_user_quiz_results(user_id):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT course, score, total, completed, completed_at
        FROM quiz_results
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return {row["course"]: dict(row) for row in rows}


def get_user_learning_stats(user_id):
    """Compute this user's real progress from their own quiz results -
    never shared with, or copied from, any other user."""

    results = get_user_quiz_results(user_id)
    completed_results = [
        r for r in results.values() if r["completed"]
    ]

    total_courses = len(courses) or 1
    total_possible_marks = total_courses * 15

    marks_earned = sum(r["score"] for r in completed_results)
    mastery = round((marks_earned / total_possible_marks) * 100) if total_possible_marks else 0

    if completed_results:
        quiz_accuracy = round(
            sum((r["score"] / r["total"]) * 100 for r in completed_results if r["total"])
            / len(completed_results)
        )
    else:
        quiz_accuracy = 0

    # "completed topics" = lessons from courses the user has actually
    # finished the quiz for (real, per-user - not a shared constant).
    completed_topics = 0
    for course in courses:
        course_key = normalize_course_name(course["title"])
        result = results.get(course_key)
        if result and result["completed"]:
            completed_topics += course.get("lessons", 0)

    return {
        "mastery": mastery,
        "quiz_accuracy": quiz_accuracy,
        "completed_topics": completed_topics,
        "active_days": get_active_days(user_id),
        "streak": get_learning_streak(user_id),
        "quiz_results": results,
    }


def get_user_courses(user_id):
    """Return the course catalog with each course's progress/status
    computed from THIS user's quiz results, instead of the shared
    static defaults."""

    results = get_user_quiz_results(user_id)
    personalized = []

    for course in courses:
        course_copy = dict(course)
        course_key = normalize_course_name(course["title"])
        result = results.get(course_key)

        if result and result["completed"]:
            percentage = round((result["score"] / result["total"]) * 100) if result["total"] else 0
            course_copy["progress"] = percentage
            course_copy["status"] = "Completed"
        else:
            course_copy["progress"] = 0
            course_copy["status"] = "Start Learning"

        personalized.append(course_copy)

    return personalized


def get_next_learning_course(user_id):
    """Choose the user's next/recommended course from their real results.

    Unfinished courses are preferred. If all courses are completed, recommend
    the course with the lowest score for review.
    """
    results = get_user_quiz_results(user_id)
    candidates = []

    for course in courses:
        key = normalize_course_name(course["title"])
        result = results.get(key)
        percentage = 0
        completed = False
        completed_at = ""
        if result:
            completed = bool(result["completed"])
            if result["total"]:
                percentage = round((result["score"] / result["total"]) * 100)
            completed_at = result.get("completed_at", "") or ""
        candidates.append({
            "key": key,
            "title": course["title"],
            "progress": percentage,
            "completed": completed,
            "completed_at": completed_at,
        })

    unfinished = [c for c in candidates if not c["completed"]]
    if unfinished:
        # Keep the catalog order for predictable recommendations.
        return unfinished[0]

    # Everything is complete: review the weakest subject. If scores tie,
    # use the most recently completed quiz as the tie-breaker.
    lowest = min(c["progress"] for c in candidates)
    tied = [c for c in candidates if c["progress"] == lowest]
    return max(tied, key=lambda c: c["completed_at"] or "")


def get_daily_learning_topics():
    """Return the fixed syllabus order used when there is no quiz weakness yet."""
    return ROADMAP_TOPIC_PLAN


def get_latest_quiz_attempt(user_id, course):
    conn = get_db()
    row = conn.execute(
        """
        SELECT score, total, wrong_question_ids, completed_at
        FROM quiz_attempts
        WHERE user_id = ? AND course = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id, normalize_course_name(course))
    ).fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    try:
        data["wrong_question_ids"] = json.loads(data.get("wrong_question_ids") or "[]")
    except (TypeError, ValueError):
        data["wrong_question_ids"] = []
    return data


def get_adaptive_topic(user_id, course_title):
    """Choose the weakest learning topic from the user's latest quiz."""
    course_key = normalize_course_name(course_title)
    plan = ROADMAP_TOPIC_PLAN.get(course_title, [])
    attempt = get_latest_quiz_attempt(user_id, course_key)

    if attempt and attempt["wrong_question_ids"]:
        topic_map = QUIZ_TOPIC_MAP.get(course_key, {})
        counts = {}
        for qid in attempt["wrong_question_ids"]:
            topic = topic_map.get(int(qid))
            if topic:
                counts[topic] = counts.get(topic, 0) + 1

        if counts:
            max_mistakes = max(counts.values())
            weak_topics = {t for t, n in counts.items() if n == max_mistakes}
            topic = next(
                (t for t in plan if t in weak_topics),
                next(iter(weak_topics))
            )
        else:
            topic = plan[0] if plan else "Core concepts"
    else:
        topic = plan[0] if plan else "Core concepts"

    return {
        "topic": topic,
        "quiz_score": (
            round((attempt["score"] / attempt["total"]) * 100)
            if attempt and attempt["total"] else None
        ),
        "reason": (
            "Based on the topic where you made the most mistakes in your latest quiz."
            if attempt and attempt["wrong_question_ids"]
            else "Start with this topic; quiz results will personalize the next focus."
        )
    }


def get_today_roadmap(user_id):
    """Build Today's Roadmap from the user's weakest quiz topic."""
    user_courses = get_user_courses(user_id)
    results = get_user_quiz_results(user_id)

    scored = []
    for course in user_courses:
        result = results.get(normalize_course_name(course["title"]))
        pct = round((result["score"] / result["total"]) * 100) if result and result["total"] else 0
        completed_at = result.get("completed_at", "") if result else ""
        scored.append((course, pct, completed_at, bool(result and result["completed"])))

    # Score is the primary priority. If scores tie, the latest completed
    # quiz gets priority.
    lowest = min((x[1] for x in scored), default=0)
    tied = [x for x in scored if x[1] == lowest]
    focus_course = max(tied, key=lambda x: x[2] or "")[0] if tied else None

    roadmap = []
    if focus_course:
        adaptive = get_adaptive_topic(user_id, focus_course["title"])
        roadmap.append({
            "title": focus_course["title"],
            "topic": adaptive["topic"],
            "reason": adaptive["reason"],
            "score": adaptive["quiz_score"],
            "status": "Today's Focus",
            "icon": "★",
            "class": "active-road",
            "progress": focus_course["progress"]
        })

    # Keep the second course as a simple review topic. No mini quiz or
    # additional learning phases are shown because the app has no mini quiz.
    for course, pct, completed_at, completed in scored:
        if focus_course and course["title"] == focus_course["title"]:
            continue
        adaptive = get_adaptive_topic(user_id, course["title"])
        roadmap.append({
            "title": course["title"],
            "topic": adaptive["topic"],
            "reason": "Review this topic to keep the course active.",
            "score": pct if completed else None,
            "status": "Quick Review",
            "icon": "○",
            "class": "",
            "progress": pct
        })

    return roadmap

def get_user_ai_insights(user_id):
    """Build dashboard insight text from this user's actual quiz results."""
    results = get_user_quiz_results(user_id)
    course_scores = []
    for course in courses:
        key = normalize_course_name(course["title"])
        result = results.get(key)
        if result and result["completed"] and result["total"]:
            pct = round((result["score"] / result["total"]) * 100)
            completed_at = result.get("completed_at", "") or ""
            course_scores.append((course["title"], pct, completed_at))

    if not course_scores:
        return [
            "You have not completed a course quiz yet, so NEXORA will personalize your path as you learn.",
            "Complete a quiz to create your first course-specific mastery signal.",
            "Your next learning activity will be chosen from the courses you have not completed."
        ]

    # Score is the primary priority. When scores are tied, the most
    # recently completed quiz wins the tie so the dashboard does not always
    # default to the first course in the catalog.
    weakest_score = min(x[1] for x in course_scores)
    weakest_tied = [x for x in course_scores if x[1] == weakest_score]
    weakest_title, weakest_score, _ = max(weakest_tied, key=lambda x: x[2] or "")

    strongest_score = max(x[1] for x in course_scores)
    strongest_tied = [x for x in course_scores if x[1] == strongest_score]
    strongest_title, strongest_score, _ = max(strongest_tied, key=lambda x: x[2] or "")

    if len(course_scores) == 1:
        return [
            f"Your {strongest_title} quiz score is {strongest_score}%, so NEXORA is using that result as your current learning signal.",
            f"Your next focus is {weakest_title} because it is the only course with a recorded quiz result so far.",
            "Continue Learning opens the course NEXORA currently recommends for your account."
        ]

    if weakest_title == strongest_title:
        return [
            f"Your completed quiz results currently show {strongest_score}% mastery across the tracked courses.",
            f"NEXORA will keep {weakest_title} as the review focus while you build more learning activity.",
            "Continue Learning opens the recommended course for your current results."
        ]

    return [
        f"Your strongest recorded result is {strongest_title} at {strongest_score}%.",
        f"Your current focus is {weakest_title} at {weakest_score}%, so NEXORA recommends strengthening it.",
        "Continue Learning opens the course selected from your current quiz performance."
    ]

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
sources = [{'title': 'Python Documentation', 'type': 'Documentation', 'topic': 'Python', 'description': 'Official Python language documentation and reference.'}, {'title': 'Java Programming Guide', 'type': 'Article', 'topic': 'Java', 'description': 'Learn classes, objects, inheritance and polymorphism.'}, {'title': 'Data Structures Notes', 'type': 'PDF Notes', 'topic': 'DSA', 'description': 'Quick revision notes for common data structures.'}, {'title': 'SQL Practice Problems', 'type': 'Practice', 'topic': 'Database', 'description': 'Practice SQL queries and database concepts.'}]

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

    # Every authenticated page hit counts as "the user logged in today".
    # This is what makes Active Days / the learning streak / the heatmap
    # advance immediately on login, on their own calendar day, instead of
    # only when a quiz is completed.
    record_user_activity(user["id"])

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
        "profile_picture": user["profile_picture"],
        "active_dates": get_user_activity_dates(user["id"])
    })

    # Overwrite the shared placeholder progress numbers with this user's
    # own, real, per-user progress.
    data.update(get_user_learning_stats(user["id"]))

    next_course = get_next_learning_course(user["id"])
    data["next_course"] = next_course
    data["today_roadmap"] = get_today_roadmap(user["id"])
    data["ai_insights"] = get_user_ai_insights(user["id"])

    return data


def render_dashboard_page(page_name):
    user = require_login()
    if not user:
        return redirect(url_for("home"))

    student = dashboard_student()
    if not student:
        return redirect(url_for("home"))

    return render_template(
        "page.html",
        page=page_name,
        student=student,
        courses=get_user_courses(user["id"]),
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
@app.route("/continue-learning")
def continue_learning():
    """Open the user's next learning page based on their own quiz progress."""
    user = require_login()
    if not user:
        return redirect(url_for("home"))

    next_course = get_next_learning_course(user["id"])
    route_name = next_course["key"].replace("-", "_")
    return redirect(url_for(route_name))


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

@app.route("/computer-architecture-simulation")
def computer_architecture_simulation():
    return render_template("ca_sim.html")

@app.route("/data-structures-videos")
def data_structures_videos():
    return render_template("ds video.html")

@app.route("/video-learning/<video_slug>")
def video_learning(video_slug):

    student = dashboard_student()

    if not student:
        return redirect(url_for("home"))

    if video_slug == "computer-architecture":
        return render_template("CA video.html")

    selected_video = None

    for video in videos:
        if video.get("slug") == video_slug:
            selected_video = video
            break

    if not selected_video:
        return redirect(url_for("video_page"))

    return render_template(
        "page.html",
        page="video-learning",
        student=student,
        courses=courses,
        videos=videos,
        sources=sources,
        certificates=certificates,
        video=selected_video
    )


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
