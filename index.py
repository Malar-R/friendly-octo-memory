"""
Eco-Themed Student Details Web App (single file Flask)
-----------------------------------------------------
Features
- Friendly eco UI (TailwindCSS via CDN)
- Collects: name, department, email, phone, area of interest, short/long-term goals
- Preview page for validation before final submit
- On final submit: emails the details to OWNER_EMAIL and appends to a CSV file
- Basic server-side validation + simple bot honeypot

How to run
1) Ensure Python 3.9+
2) Install Flask:  pip install Flask python-dotenv
3) (Optional) Create a .env with these keys or set environment variables:
   - MAIL_USER="your_gmail_username@gmail.com"
   - MAIL_PASS="your_gmail_app_password"   # Use a Gmail App Password
   - OWNER_EMAIL="suryasingam49@gmail.com" # Where submissions are sent
4) Start the server:  python app.py
5) Open http://127.0.0.1:5000 in your browser

Notes on Gmail
- If using Gmail, create an App Password under Google Account > Security > 2‑Step Verification > App passwords.
- Put that password in MAIL_PASS.

"""
from flask import Flask, request, render_template_string, redirect, url_for, session, flash
import re
import os
import csv
import smtplib
from email.message import EmailMessage
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret-key")

MAIL_USER = os.environ.get("MAIL_USER")
MAIL_PASS = os.environ.get("MAIL_PASS")
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "suryasingam49@gmail.com")

SUBMISSIONS_CSV = Path("submissions.csv")

# ---------- Shared HTML (Tailwind + base) ----------
BASE_HEAD = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title }}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <meta name="description" content="Eco-friendly student details form with preview & email." />
  <style>
    .leaf-bg { background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); }
    .card { box-shadow: 0 10px 25px rgba(16,185,129,0.15); }
    .soft { border-radius: 1.25rem; }
  </style>
</head>
<body class="leaf-bg min-h-screen">
  <header class="max-w-5xl mx-auto px-4 py-6">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 flex items-center justify-center bg-green-600 text-white rounded-2xl">🌿</div>
      <div>
        <h1 class="text-2xl font-bold text-green-800">{{ heading }}</h1>
        <p class="text-green-700">A clean, eco-themed form for student details.</p>
      </div>
    </div>
  </header>
  <main class="max-w-3xl mx-auto px-4 pb-16">{% block content %}{% endblock %}</main>
  <footer class="max-w-5xl mx-auto px-4 pb-10 text-sm text-green-700">
    <div class="flex items-center gap-2">Made with <span>🌱</span> using Flask.</div>
  </footer>
</body>
</html>
"""

# ---------- Form Page ----------
FORM_TPL = """
{% extends base %}
{% block content %}
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <div class="mb-4 p-4 bg-red-50 text-red-700 rounded-xl">{{ messages[0] }}</div>
    {% endif %}
  {% endwith %}
  <div class="card soft bg-white p-6">
    <h2 class="text-xl font-semibold text-green-800 mb-4">Student Details</h2>
    <form method="post" action="{{ url_for('preview') }}" class="grid gap-5">
      <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
      <!-- Honeypot field (hidden from humans) -->
      <div class="hidden">
        <label>Do not fill this</label>
        <input type="text" name="website" autocomplete="off" />
      </div>

      <div class="grid md:grid-cols-2 gap-5">
        <div>
          <label class="block text-sm font-medium text-green-900">Full Name</label>
          <input required name="name" value="{{ data.name or '' }}" class="mt-1 w-full p-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500" placeholder="e.g., Malar R" />
        </div>
        <div>
          <label class="block text-sm font-medium text-green-900">Department</label>
          <select required name="department" class="mt-1 w-full p-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500">
            <option value="">Select department</option>
            {% for d in departments %}
              <option value="{{ d }}" {% if data.department==d %}selected{% endif %}>{{ d }}</option>
            {% endfor %}
          </select>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-5">
        <div>
          <label class="block text-sm font-medium text-green-900">Email</label>
          <input required type="email" name="email" value="{{ data.email or '' }}" class="mt-1 w-full p-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500" placeholder="name@example.com" />
        </div>
        <div>
          <label class="block text-sm font-medium text-green-900">Phone</label>
          <input required name="phone" value="{{ data.phone or '' }}" class="mt-1 w-full p-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500" placeholder="10-15 digits" />
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-green-900">Area of Interest</label>
        <textarea required name="interest" rows="3" class="mt-1 w-full p-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500" placeholder="e.g., Web Development, AI, Data Science">{{ data.interest or '' }}</textarea>
      </div>

      <div class="grid md:grid-cols-2 gap-5">
        <div>
          <label class="block text-sm font-medium text-green-900">Short-Term Goal</label>
          <textarea required name="short_goal" rows="3" class="mt-1 w-full p-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500" placeholder="Your 6–12 month goal">{{ data.short_goal or '' }}</textarea>
        </div>
        <div>
          <label class="block text-sm font-medium text-green-900">Long-Term Goal</label>
          <textarea required name="long_goal" rows="3" class="mt-1 w-full p-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500" placeholder="Your 2–5 year goal">{{ data.long_goal or '' }}</textarea>
        </div>
      </div>

      <div class="flex items-center justify-between">
        <p class="text-sm text-green-700">You can review your details on the next page before final submission.</p>
        <button class="px-5 py-3 bg-green-600 hover:bg-green-700 text-white rounded-2xl">Preview ➜</button>
      </div>
    </form>
  </div>
{% endblock %}
"""

# ---------- Preview Page ----------
PREVIEW_TPL = """
{% extends base %}
{% block content %}
  <div class="card soft bg-white p-6">
    <h2 class="text-xl font-semibold text-green-800 mb-4">Review & Confirm</h2>
    <div class="grid gap-3 text-green-900">
      <div class="grid grid-cols-3 gap-2"><span class="font-medium">Name</span><span class="col-span-2">{{ data.name }}</span></div>
      <div class="grid grid-cols-3 gap-2"><span class="font-medium">Department</span><span class="col-span-2">{{ data.department }}</span></div>
      <div class="grid grid-cols-3 gap-2"><span class="font-medium">Email</span><span class="col-span-2">{{ data.email }}</span></div>
      <div class="grid grid-cols-3 gap-2"><span class="font-medium">Phone</span><span class="col-span-2">{{ data.phone }}</span></div>
      <div class="grid grid-cols-3 gap-2"><span class="font-medium">Area of Interest</span><span class="col-span-2">{{ data.interest }}</span></div>
      <div class="grid grid-cols-3 gap-2"><span class="font-medium">Short-Term Goal</span><span class="col-span-2">{{ data.short_goal }}</span></div>
      <div class="grid grid-cols-3 gap-2"><span class="font-medium">Long-Term Goal</span><span class="col-span-2">{{ data.long_goal }}</span></div>
    </div>
    <form method="post" action="{{ url_for('submit') }}" class="mt-6 flex gap-3">
      <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
      <button name="action" value="edit" class="px-5 py-3 bg-white border border-green-600 text-green-700 rounded-2xl">⟵ Edit</button>
      <button name="action" value="confirm" class="px-5 py-3 bg-green-600 hover:bg-green-700 text-white rounded-2xl">Confirm & Submit</button>
    </form>
  </div>
{% endblock %}
"""

# ---------- Success Page ----------
SUCCESS_TPL = """
{% extends base %}
{% block content %}
  <div class="card soft bg-white p-8 text-center">
    <div class="text-5xl mb-3">✅</div>
    <h2 class="text-2xl font-semibold text-green-800 mb-2">Submission Received</h2>
    <p class="text-green-700">Thank you! A copy has been emailed to the organizer and saved locally.</p>
    <a href="{{ url_for('index') }}" class="inline-block mt-6 px-5 py-3 bg-green-600 hover:bg-green-700 text-white rounded-2xl">Submit another response</a>
  </div>
{% endblock %}
"""

# ---------- Utility Functions ----------
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_REGEX = re.compile(r"^[0-9]{10,15}$")
NAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,49}$")

DEPARTMENTS = [
    "BCA", "BSc CS", "BSc IT", "MCA", "MSc CS", "ECE", "EEE", "CSE", "AIML", "Data Science"
]


def new_csrf_token():
    token = os.urandom(16).hex()
    session['csrf_token'] = token
    return token


def validate_csrf(token: str) -> bool:
    return token and session.get('csrf_token') == token


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def validate_payload(form):
    # Basic bot block: honeypot field should be empty
    if form.get('website'):
        return False, "Bot detected."

    name = clean_text(form.get('name'))
    dept = clean_text(form.get('department'))
    email = clean_text(form.get('email'))
    phone = re.sub(r"\D", "", form.get('phone') or "")
    interest = clean_text(form.get('interest'))
    sgoal = clean_text(form.get('short_goal'))
    lgoal = clean_text(form.get('long_goal'))

    # Validation rules
    if not NAME_REGEX.match(name):
        return False, "Please enter a valid full name."
    if dept not in DEPARTMENTS:
        return False, "Please select a valid department."
    if not EMAIL_REGEX.match(email):
        return False, "Please enter a valid email address."
    if not PHONE_REGEX.match(phone):
        return False, "Phone must be 10-15 digits."
    if len(interest) < 3 or len(interest) > 300:
        return False, "Area of interest must be between 3 and 300 characters."
    if len(sgoal) < 3 or len(sgoal) > 600:
        return False, "Short-term goal must be between 3 and 600 characters."
    if len(lgoal) < 3 or len(lgoal) > 800:
        return False, "Long-term goal must be between 3 and 800 characters."

    data = {
        "name": name,
        "department": dept,
        "email": email,
        "phone": phone,
        "interest": interest,
        "short_goal": sgoal,
        "long_goal": lgoal,
    }
    return True, data


def send_email(data: dict):
    if not (MAIL_USER and MAIL_PASS):
        print("[WARN] MAIL_USER/MAIL_PASS not set; skipping email send.")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"New Student Submission • {data['name']} ({data['department']})"
    msg["From"] = MAIL_USER
    msg["To"] = OWNER_EMAIL

    body_lines = [
        "A new student detail submission has been received:\n",
        f"Name: {data['name']}",
        f"Department: {data['department']}",
        f"Email: {data['email']}",
        f"Phone: {data['phone']}",
        f"Area of Interest: {data['interest']}",
        f"Short-Term Goal: {data['short_goal']}",
        f"Long-Term Goal: {data['long_goal']}",
        "",
        f"Submitted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ]
    msg.set_content("\n".join(body_lines))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(MAIL_USER, MAIL_PASS)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False


def save_to_csv(data: dict):
    new_file = not SUBMISSIONS_CSV.exists()
    with open(SUBMISSIONS_CSV, "a", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "name", "department", "email", "phone", "interest", "short_goal", "long_goal"
        ])
        if new_file:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec='seconds'),
            **data
        })

# ---------- Routes ----------
@app.route("/", methods=["GET"])
def index():
    csrf_token = new_csrf_token()
    data = session.get('form_data', {})
    return render_template_string(
        FORM_TPL,
        base=BASE_HEAD,
        title="Eco Student Form",
        heading="Student Details Collection",
        csrf_token=csrf_token,
        data=data,
        departments=DEPARTMENTS,
    )


@app.route("/preview", methods=["POST"])
def preview():
    if not validate_csrf(request.form.get('csrf_token')):
        flash("Invalid session. Please try again.")
        return redirect(url_for('index'))

    ok, result = validate_payload(request.form)
    if not ok:
        flash(result)
        session['form_data'] = {
            'name': request.form.get('name'),
            'department': request.form.get('department'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'interest': request.form.get('interest'),
            'short_goal': request.form.get('short_goal'),
            'long_goal': request.form.get('long_goal'),
        }
        return redirect(url_for('index'))

    session['form_data'] = result
    csrf_token = new_csrf_token()
    return render_template_string(
        PREVIEW_TPL,
        base=BASE_HEAD,
        title="Preview Details",
        heading="Please confirm your details",
        csrf_token=csrf_token,
        data=result,
    )


@app.route("/submit", methods=["POST"])
def submit():
    if not validate_csrf(request.form.get('csrf_token')):
        flash("Invalid session. Please try again.")
        return redirect(url_for('index'))

    action = request.form.get('action')
    if action == 'edit':
        # Go back to form with same data
        return redirect(url_for('index'))

    data = session.get('form_data')
    if not data:
        flash("Session expired. Please re-enter your details.")
        return redirect(url_for('index'))

    # Save locally
    save_to_csv(data)
    # Email owner
    send_email(data)

    # Clear session data used for form
    session.pop('form_data', None)

    csrf_token = new_csrf_token()
    return render_template_string(
        SUCCESS_TPL,
        base=BASE_HEAD,
        title="Submission Success",
        heading="All set!",
        csrf_token=csrf_token,
    )


if __name__ == "__main__":
    app.run(debug=True)


