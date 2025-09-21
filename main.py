import streamlit as st
import os
import json
import time
from io import BytesIO
import datetime
import google.generativeai as genai
from google.cloud import speech
import PyPDF2

# -------------------------
# Config
# -------------------------
st.set_page_config(page_title="AI Career Mentor", page_icon="🎓", layout="wide")

# -------------------------
# Small CSS to make UI nicer
# -------------------------
st.markdown(
    """
    <style>
    .card { border: 1px solid #e6e9ee; border-radius: 10px; padding: 16px; box-shadow: 0 2px 6px rgba(32,33,36,0.06); background: #ffffff; }
    .card h3 { margin-bottom: 8px; }
    .primary-btn { background-color: #0f62fe; color: white; padding: 8px 14px; border-radius: 8px; border: none; }
    .small-muted { color: #6b7280; font-size: 13px; }
    .result-block { background: #f7fbff; padding: 12px; border-radius: 8px; }
    .progress-bar { background-color: #0f62fe; height: 12px; border-radius: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Sidebar: user info + nav
# -------------------------
with st.sidebar:
    st.header("Welcome")
    user_name = st.text_input("Your name (optional)", value="")
    st.markdown("### Navigate")
    page = st.radio("", [
        "Dashboard",
        "Career Advice",
        "Job Suggestor",
        "Resume Evaluator",
        "Mock Interview",
        "Speech-to-Text",
        "Notifier",
        "Facial Analysis"
    ])
    st.markdown("---")
    st.write("Tip: Try the Mock Interview for quick practice.")
    st.markdown("")

if user_name.strip():
    st.sidebar.success(f"Hi {user_name.split()[0]} — ready to upskill? 👋")
else:
    st.sidebar.info("Hi there — tell me your name for a personal touch 👆")

# -------------------------
# Utility helpers
# -------------------------
def download_text_button(text, filename="output.txt", label="Download"):
    b = text.encode("utf-8")
    st.download_button(label, b, file_name=filename, mime="text/plain")

# -------------------------
# Gemini Setup
# -------------------------
GENAI_API_KEY = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
GENAI_MODEL_NAME = os.environ.get("GENAI_MODEL_NAME", "gemini-1.5-flash")

# -------------------------
# Backend Logic (Functions)
# -------------------------
# --- 1. Speech to Text ---
def speech_to_text(audio_file):
    try:
        audio_content = audio_file.read()
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        response = client.recognize(config=config, audio=audio)
        transcript = " ".join([r.alternatives[0].transcript for r in response.results])
        return {"text": transcript}
    except Exception as e:
        return {"error": str(e)}

# --- 2. Resume Evaluator ---
def resume_eval(file):
    try:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        model = genai.GenerativeModel(GENAI_MODEL_NAME)
        prompt = f"Act as a career consultant. Evaluate this resume and provide strengths, weaknesses, missing skills, and improvements:\n{text}"
        response = model.generate_content(prompt)
        return {"evaluation": response.text}
    except Exception as e:
        return {"error": str(e)}

# --- 3. Career Advice ---
def career_advice(profile):
    try:
        model = genai.GenerativeModel(GENAI_MODEL_NAME)
        response = model.generate_content(
            f"Act as a career advisor. The profile is: {profile}. Give career advice along with skills that should be learned."
        )
        return {"advice": response.text}
    except Exception as e:
        return {"error": str(e)}

# --- 4. Job Suggestor ---
def job_suggestor(profile, location):
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
        import re
        text = response.text.strip()
        text = re.sub(r"^```(json)?", "", text)
        text = re.sub(r"```$", "", text).strip()
        jobs = json.loads(text)
    except Exception as e:
        jobs = {"error": f"Could not parse job suggestions: {e}", "raw_response": response.text}
    return {"jobs": jobs}

# --- 5. Mock Interview Questions Generation ---
def mock_interview(role):
    if not role.strip():
        return {"error": "Role required"}
    try:
        prompt = f"""
        Generate 5 realistic interview questions for the role of {role}.
        Return ONLY a valid JSON array of strings.
        Example: ["Question 1", "Question 2", "Question 3"]
        """
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        try:
            questions = json.loads(raw_text)
        except Exception:
            questions = [q.strip("-• ").strip() for q in raw_text.split("\n") if q.strip()]
        questions = [q for q in questions if isinstance(q, str) and q.strip()]
        return {"questions": questions}
    except Exception as e:
        return {"error": str(e)}

def evaluate_answer(question, transcript, resume_text=""):
    if not transcript.strip():
        return {"error": "No answer provided"}
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
        try:
            eval_json = json.loads(response.text)
        except:
            eval_json = {
                "clarity": 0,
                "confidence": 0,
                "score": 0,
                "feedback": response.text
            }
        return eval_json
    except Exception as e:
        return {"error": str(e)}

# -------------------------
# Streamlit UI & Logic
# -------------------------
if page == "Dashboard":
    st.title("🎓 AI Career Mentor — Dashboard")
    greeting = f"Welcome back, {user_name.split()[0]}!" if user_name.strip() else "Welcome to your Career Mentor"
    st.markdown(f"#### {greeting}")
    st.markdown("This dashboard helps with career choices, resume review, interview practice, and daily learning nudges.")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="card"><h3>Career Advice</h3><p class="small-muted">Personalized career paths & 30-day roadmap</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card"><h3>Mock Interview</h3><p class="small-muted">Practice Q&A + feedback on clarity & confidence</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="card"><h3>Resume Evaluator</h3><p class="small-muted">Get strengths, weaknesses & improvement tips</p></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("Quick actions:")
    a1, a2, a3 = st.columns(3)
    if a1.button("Get Career Advice"):
        st.experimental_rerun()
    if a2.button("Start Mock Interview"):
        st.experimental_rerun()
    if a3.button("Upload Resume"):
        st.experimental_rerun()

if page == "Career Advice":
    st.header("🧭 Personalized Career Advice")
    profile = st.text_area("Describe your profile (education, skills, interests, goals):", height=180)
    if st.button("Get Advice", key="get_advice"):
        if not profile.strip():
            st.warning("Please enter your profile so I can give tailored advice.")
        else:
            with st.spinner("Generating personalized career advice..."):
                resp = career_advice(profile)
                if "error" in resp:
                    st.error(f"Backend error: {resp['error']}")
                else:
                    advice = resp.get("advice", "")
                    st.markdown("### Results")
                    st.markdown(f"<div class='result-block'>{advice}</div>", unsafe_allow_html=True)
                    download_text_button(advice, filename="career_advice.txt", label="Download Advice")
                    st.button("Copy to Clipboard", key="copy_advice", help="Copy advice text for later use")

if page == "Job Suggestor":
    st.header("💼 Job Suggestor")
    profile = st.text_area("Enter your profile (skills, domain, interests):", height=140)
    location = st.text_input("Preferred location (optional)")
    if st.button("Suggest Jobs", key="suggest_jobs"):
        if not profile.strip():
            st.warning("Please provide at least a short profile or skills.")
        else:
            with st.spinner("Finding best-fit job roles..."):
                resp = job_suggestor(profile, location)
                if "error" in resp:
                    st.error(f"Backend error: {resp['error']}")
                else:
                    jobs = resp.get("jobs", [])
                    if isinstance(jobs, list):
                        progress = st.progress(0)
                        for i, j in enumerate(jobs):
                            st.markdown(f"### 🔹 {j.get('role')}")
                            st.markdown(j.get("description", ""))
                            if j.get("skills"):
                                st.markdown("**Top skills:** " + ", ".join(j.get("skills")))
                            companies = j.get("companies", [])
                            if companies:
                                st.markdown("**Recommended companies:**")
                                for c in companies:
                                    if isinstance(c, dict):
                                        name = c.get("name")
                                        url = c.get("careers_url")
                                        if url:
                                            st.markdown(f"- [{name}]({url})")
                                        else:
                                            st.markdown(f"- {c}")
                                    else:
                                        st.markdown(f"- {c}")
                            hiring = j.get("hiring_now", [])
                            if hiring:
                                st.success("📌 Companies hiring now: " + ", ".join([h.get("name") if isinstance(h, dict) else h for h in hiring]))
                            st.divider()
                            progress.progress((i + 1)/len(jobs))
                    else:
                        st.markdown("**Suggestions (raw):**")
                        st.text(jobs)
                        download_text_button(str(jobs), filename="job_suggestions_raw.txt", label="Download Raw")

if page == "Resume Evaluator":
    st.header("📄 Resume Evaluator")
    st.markdown("Upload your resume (PDF). The system will extract text and provide strengths, weaknesses, missing skills and concrete improvements.")
    resume_file = st.file_uploader("Upload PDF resume", type=["pdf"])
    if resume_file:
        if st.button("Evaluate Resume", key="eval_resume"):
            with st.spinner("Extracting and evaluating resume..."):
                resp = resume_eval(resume_file)
                if "error" in resp:
                    st.error(f"Error evaluating resume: {resp['error']}")
                else:
                    ev = resp.get("evaluation", "")
                    st.markdown("### Resume Evaluation")
                    with st.expander("Full Evaluation (expand)"):
                        st.markdown(ev if ev else "No evaluation text returned.")
                    st.success("Evaluation complete.")
                    download_text_button(ev, filename="resume_evaluation.txt", label="Download Evaluation")

if page == "Mock Interview":
    st.header("🎤 Mock Interview")
    role = st.text_input("Role to prepare for (e.g., Embedded Systems Engineer):")
    start = st.button("Start Mock Interview", key="start_mock")
    if "mi_questions" not in st.session_state:
        st.session_state.mi_questions = []
    if "mi_idx" not in st.session_state:
        st.session_state.mi_idx = 0
    if "mi_results" not in st.session_state:
        st.session_state.mi_results = []
    if start:
        if not role.strip():
            st.warning("Please enter the role.")
        else:
            with st.spinner("Generating interview questions..."):
                resp = mock_interview(role)
                if "error" in resp:
                    st.error(f"Error generating questions: {resp['error']}")
                else:
                    questions = resp.get("questions", [])
                    if isinstance(questions, list) and questions:
                        st.session_state.mi_questions = questions
                        st.session_state.mi_idx = 0
                        st.session_state.mi_results = []
                    else:
                        st.warning("No questions generated. Try again.")
    if st.session_state.mi_questions:
        idx = st.session_state.mi_idx
        current_question = st.session_state.mi_questions[idx]
        st.subheader(f"Question {idx + 1} of {len(st.session_state.mi_questions)}")
        st.markdown(f"**{current_question}**")
        answer = st.text_area(
            "Type your answer here (or use Speech-to-Text tab and paste text):",
            key=f"ans_{idx}",
            height=150
        )
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("Submit Answer", key=f"submit_{idx}"):
                if not answer.strip():
                    st.warning("Please type an answer or use speech-to-text.")
                else:
                    with st.spinner("Evaluating answer..."):
                        res = evaluate_answer(current_question, answer)
                        if "error" in res:
                            st.error(f"Evaluation error: {res['error']}")
                        else:
                            st.session_state.mi_results.append(res)
                            st.success("Answer evaluated.")
                            if idx + 1 < len(st.session_state.mi_questions):
                                st.session_state.mi_idx += 1
                            else:
                                st.info("All questions completed.")
        with col2:
            if st.button("Skip / Next", key=f"next_{idx}"):
                st.session_state.mi_idx = min(idx + 1, len(st.session_state.mi_questions) - 1)
        with col3:
            if st.button("Finish Interview", key="finish_mock"):
                st.session_state.mi_idx = 0
                st.session_state.mi_questions = []
                st.session_state.mi_results = []
                st.success("Mock interview ended.")
        if st.session_state.mi_results:
            st.markdown("### Previous Answers & Feedback")
            for i, r in enumerate(st.session_state.mi_results):
                st.markdown(f"**Q{i+1}:** {st.session_state.mi_questions[i]}")
                st.markdown(f"- **Clarity:** {r.get('clarity','N/A')}")
                st.markdown(f"- **Confidence:** {r.get('confidence','N/A')}")
                st.markdown(f"- **Score:** {r.get('score','N/A')}")
                st.markdown(f"- **Feedback:** {r.get('feedback','')}")
                st.divider()

if page == "Speech-to-Text":
    st.header("🗣️ Speech to Text")
    st.markdown("Record audio elsewhere and upload a WAV/MP3 file.")
    audio_file = st.file_uploader("Upload audio file (wav/mp3)", type=["wav", "mp3"])
    if audio_file and st.button("Transcribe Audio"):
        with st.spinner("Transcribing..."):
            resp = speech_to_text(audio_file)
            if "error" in resp:
                st.error(f"Error transcribing audio: {resp['error']}")
            else:
                text = resp.get("text") or ""
                st.success("Transcription complete")
                st.markdown("**Transcript:**")
                st.write(text)
                download_text_button(text, filename="transcript.txt", label="Download Transcript")

if page == "Notifier":
    st.header("🔔 Notifier (Reminders via Email)")
    st.warning("Note: This feature requires an external scheduling service like a Cron job to run on a continuous basis. It will not work on Streamlit Cloud due to its session-based architecture.")
    reminder_text = st.text_input("What should I remind you about?")
    reminder_email = st.text_input("Your email address")
    remind_time = st.time_input("Remind me at (time, local):")
    if st.button("Set Reminder"):
        st.info("You can't schedule reminders on Streamlit Cloud. This feature is for a dedicated backend service.")

if page == "Facial Analysis":
    st.header("📹 Facial Expression Evaluator (Mock Interview)")
    st.markdown("This feature uses webcam frames to detect emotions and provide feedback on non-verbal cues.")
    st.info("💡 Prototype only — actual facial analysis coming soon!")
    st.markdown("Expected feedback will be like:")
    st.markdown("😊 😐 😞  (Happy, Neutral, Concerned) — Feature coming soon.")

st.markdown("---")
st.markdown("<div class='small-muted'>Tip: Keep your backend running. Use download buttons to save outputs.</div>", unsafe_allow_html=True)