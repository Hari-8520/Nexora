import os
import secrets
import sqlite3
import smtplib
import hashlib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            department TEXT NOT NULL,
            year TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

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
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.post("/api/login")
def login():

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

    if not email or not password:
        return jsonify({
            "ok": False,
            "message":
                "Please enter your Gmail and password."
        }), 400

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

    # Account does not exist
    if not user:

        return jsonify({
            "ok": False,
            "account_exists": False,
            "message":
                "This Gmail is not registered. Please create an account."
        }), 404

    # Check password
    if not check_password_hash(
        user["password_hash"],
        password
    ):

        return jsonify({
            "ok": False,
            "account_exists": True,
            "message":
                "Incorrect password. Please try again."
        }), 401

    # Login successful
    session.clear()

    session["user_id"] = user["id"]
    session["email"] = user["email"]

    return jsonify({
        "ok": True,
        "message": "Login successful.",
        "user": {
            "name": user["full_name"],
            "email": user["email"],
            "student_id": user["student_id"]
        }
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
            year
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
# DASHBOARD DATA AND ROUTES
# --------------------------------------------------

student_defaults = {'name': 'Ashwin Kumaar', 'email': 'ashwinkumaar@gmail.com', 'student_id': '2501014', 'department': 'Computer Science and Engineering', 'year': '3rd Year', 'college': 'Sri Ramakrishna Engineering College', 'batch': '2029', 'learning_level': 'Intermediate', 'mastery': 74, 'quiz_accuracy': 89, 'streak': 15, 'active_days': 42, 'completed_topics': 28}

courses = [{'title': 'Python Programming', 'description': 'Learn Python from fundamentals to object-oriented programming.', 'category': 'Programming', 'progress': 82, 'lessons': 24, 'assessments': 5, 'duration': '18 Hours', 'status': 'In Progress'}, {'title': 'Java Programming', 'description': 'Master Java programming, OOP, inheritance and advanced concepts.', 'category': 'Programming', 'progress': 64, 'lessons': 30, 'assessments': 6, 'duration': '22 Hours', 'status': 'Continue'}, {'title': 'Data Structures', 'description': 'Build strong foundations in arrays, linked lists, trees and graphs.', 'category': 'Computer Science', 'progress': 48, 'lessons': 32, 'assessments': 7, 'duration': '25 Hours', 'status': 'Continue'}, {'title': 'Database Management', 'description': 'Understand SQL, relational databases and database design.', 'category': 'Database', 'progress': 36, 'lessons': 20, 'assessments': 4, 'duration': '14 Hours', 'status': 'Start Learning'}, {'title': 'Machine Learning', 'description': 'Learn machine learning fundamentals and predictive modeling.', 'category': 'AI / ML', 'progress': 21, 'lessons': 28, 'assessments': 5, 'duration': '20 Hours', 'status': 'Start Learning'}, {'title': 'Web Development', 'description': 'Build modern websites using HTML, CSS, JavaScript and Flask.', 'category': 'Development', 'progress': 55, 'lessons': 26, 'assessments': 5, 'duration': '19 Hours', 'status': 'Continue'}]

videos = [{'title': 'Introduction to Python', 'topic': 'Python', 'duration': '18 min', 'level': 'Beginner'}, {'title': 'Object Oriented Programming', 'topic': 'Java', 'duration': '26 min', 'level': 'Intermediate'}, {'title': 'Understanding Linked Lists', 'topic': 'Data Structures', 'duration': '21 min', 'level': 'Intermediate'}, {'title': 'SQL Joins Explained', 'topic': 'Database', 'duration': '15 min', 'level': 'Intermediate'}]

sources = [{'title': 'Python Documentation', 'type': 'Documentation', 'topic': 'Python', 'description': 'Official Python language documentation and reference.'}, {'title': 'Java OOP Guide', 'type': 'Article', 'topic': 'Java', 'description': 'Learn classes, objects, inheritance and polymorphism.'}, {'title': 'Data Structures Notes', 'type': 'PDF Notes', 'topic': 'DSA', 'description': 'Quick revision notes for common data structures.'}, {'title': 'SQL Practice Problems', 'type': 'Practice', 'topic': 'Database', 'description': 'Practice SQL queries and database concepts.'}]

certificates = [{'title': 'Python Programming Fundamentals', 'topic': 'Python', 'status': 'Earned', 'date': '20 Aug 2026'}, {'title': 'Object Oriented Programming', 'topic': 'Java', 'status': 'In Progress', 'date': '-'}, {'title': 'Data Structures Mastery', 'topic': 'DSA', 'status': 'Locked', 'date': '-'}]

def require_login():
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = get_db()
    user = conn.execute(
        "SELECT id, email, full_name, student_id, department, year FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
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
        "year": user["year"]
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