from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from google.cloud import speech
import os
import io
import PyPDF2
import threading
import time
from plyer import notification  # For local notifications
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

# ---------------- Flask App ---------------- #
app = Flask(__name__)
CORS(app)

scheduler = BackgroundScheduler()
scheduler.start()

SMTP_USER = os.environ.get("EMAIL_USER")
SMTP_PASS = os.environ.get("EMAIL_PASS")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ---------------- Gemini Setup ---------------- #
GENAI_API_KEY = os.environ.get("GOOGLE_API_KEY")  # Use your direct Gemini API key
genai.configure(api_key=GENAI_API_KEY)
GENAI_MODEL_NAME = os.environ.get("GENAI_MODEL_NAME", "gemini-1.5-flash")

# ---------------- Speech-to-Text Setup ---------------- #
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"E:\GenAI\ai_career_mentor\aicareermentor-cad4b3fb19d5.json"

# ---------------- Reminder Scheduler ---------------- #
reminders = []

def reminder_checker():
    while True:
        now = time.strftime("%H:%M:%S")
        for r in reminders[:]:
            if r["time"] == now:
                # Send local notification (prototype)
                notification.notify(
                    title="Skill Reminder",
                    message=f"Today you need to learn: {r['task']}",
                    timeout=10
                )
                reminders.remove(r)
        time.sleep(1)

threading.Thread(target=reminder_checker, daemon=True).start()

# ---------------- Routes ---------------- #
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Backend running with all features (facial expression coming soon)!"})

# --- 1. Speech to Text ---
@app.route("/speech_to_text", methods=["POST"])
def speech_to_text():
    try:
        file = request.files['file']
        audio_content = file.read()
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        response = client.recognize(config=config, audio=audio)
        transcript = " ".join([r.alternatives[0].transcript for r in response.results])
        return jsonify({"text": transcript})
    except Exception as e:
        return jsonify({"error": str(e)})

# --- 2. Resume Evaluator ---
@app.route("/resume_eval", methods=["POST"])
def resume_eval():
    try:
        file = request.files['file']
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        model = genai.GenerativeModel(GENAI_MODEL_NAME)
        prompt = f"Act as a career consultant. Evaluate this resume and provide strengths, weaknesses, missing skills, and improvements:\n{text}"
        response = model.generate_content(prompt)
        return jsonify({"evaluation": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})

# --- 3. Career Advice ---
@app.route("/career_advice", methods=["POST"])
def career_advice():
    try:
        data = request.get_json()
        profile = data.get("profile", "")
        model = genai.GenerativeModel(GENAI_MODEL_NAME)
        response = model.generate_content(
            f"Act as a career advisor. The profile is: {profile}. Give career advice."
        )
        return jsonify({"advice": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})

# --- 4. Job Suggestor ---
# --- 4. Job Suggestor ---
@app.route("/job_suggestor", methods=["POST"])
def job_suggestor():
    data = request.get_json()
    profile = data.get("profile", "")

    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
    The user profile is: {profile}.
    Suggest 5 suitable job roles for this person.
    For each role:
    - Give a short description (2-3 lines).
    - List 3-4 companies that are a good fit.
    - Mention companies currently hiring for such roles (based on 2025 trends).
    Return ONLY valid JSON array (no markdown, no comments).
    Format:
    [
      {{
        "role": "Job Role",
        "description": "Short description",
        "companies": ["Company1", "Company2", "Company3"],
        "hiring_now": ["CompanyA", "CompanyB"]
      }},
      ...
    ]
    """

    response = model.generate_content(prompt)

    try:
        import json, re
        text = response.text.strip()

        # Remove Markdown formatting if Gemini adds ```json ... ```
        text = re.sub(r"^```(json)?", "", text)
        text = re.sub(r"```$", "", text).strip()

        jobs = json.loads(text)
    except Exception as e:
        jobs = {"error": f"Could not parse job suggestions: {e}", "raw_response": response.text}

    return jsonify({"jobs": jobs})

# --- 5. Mock Interview Questions Generation ---
@app.route("/mock_interview", methods=["POST"])
def mock_interview():
    data = request.get_json()
    role = data.get("role", "")

    if not role:
        return jsonify({"questions": []})

    prompt = f"""
    You are an HR expert. Generate 5 realistic interview questions for a candidate applying as {role}.
    Return ONLY a JSON array of strings. Example:
    ["Question 1", "Question 2", ...]
    """

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Ensure valid JSON
        if text.startswith("["):
            questions = json.loads(text)
        else:
            # fallback: split by lines if not JSON
            questions = [q.strip() for q in text.splitlines() if q.strip()]

    except Exception as e:
        print("Error generating questions:", e)
        # fallback questions
        questions = [
            f"What motivates you to apply for {role}?",
            f"Describe a challenging project you handled in {role}-related tasks.",
            f"How do you keep your skills updated for {role}?",
        ]

    return jsonify({"questions": questions})

@app.route("/mock/evaluate", methods=["POST"])
def evaluate_answer():
    data = request.get_json()
    question = data.get("question", "")
    transcript = data.get("transcript", "")
    resume_text = data.get("resume_text", "")

    if not transcript.strip():
        return jsonify({"error": "No answer provided"}), 400

    try:
        prompt = f"""
        You are an HR expert evaluating interview answers.
        Question: {question}
        Candidate's answer: {transcript}
        Resume context: {resume_text}

        Provide evaluation in JSON with fields:
        - clarity (0-10)
        - confidence (0-10)
        - score (0-10)
        - feedback (detailed text advice)
        """
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        # parse JSON output
        try:
            eval_json = json.loads(response.text)
        except:
            # fallback: simple text parsing if model returned plain text
            eval_json = {
                "clarity": 0,
                "confidence": 0,
                "score": 0,
                "feedback": response.text
            }
        return jsonify(eval_json)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 6. Set Reminder ---
@app.route("/set_reminder", methods=["POST"])
def set_reminder():
    data = request.get_json()
    text = data.get("text")
    email = data.get("email")
    time_str = data.get("time")  # ISO format

    if not text or not email or not time_str:
        return jsonify({"error": "Missing parameters"}), 400

    try:
        remind_time = datetime.fromisoformat(time_str)
    except Exception as e:
        return jsonify({"error": f"Invalid isoformat string: {time_str}"}), 400

    # Schedule email
    scheduler.add_job(send_email, 'date', run_date=remind_time, args=[email, "Reminder", text])
    return jsonify({"message": f"Reminder scheduled for {remind_time} to {email}"})

def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = to_email
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print("Email sending failed:", e)

def schedule_email_reminder(to_email, text, remind_time):
    """
    Schedule email at a specific datetime
    """
    scheduler.add_job(
        send_email,
        'date',
        run_date=remind_time,
        args=[to_email, "AI Career Mentor Reminder", text]
    )



# --- 7. Facial Expression Evaluator (Dummy) ---
@app.route("/facial_expression", methods=["POST"])
def facial_expression():
    return jsonify({"expression": "Feature coming soon: facial expression detection will work here."})

# ---------------- Run App ---------------- #
if __name__ == "__main__":
    app.run(debug=True)