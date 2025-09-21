import streamlit as st
import requests
import json
import time
from io import BytesIO
import datetime

# -------------------------
# Config
# -------------------------
BACKEND_URL = "http://localhost:8000"  # change if your backend lives elsewhere
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
def safe_post_json(endpoint, payload, timeout=30):
    try:
        r = requests.post(f"{BACKEND_URL}{endpoint}", json=payload, timeout=timeout)
        return r
    except Exception as e:
        return None

def safe_post_files(endpoint, files, timeout=60):
    try:
        r = requests.post(f"{BACKEND_URL}{endpoint}", files=files, timeout=timeout)
        return r
    except Exception as e:
        return None

def download_text_button(text, filename="output.txt", label="Download"):
    b = text.encode("utf-8")
    st.download_button(label, b, file_name=filename, mime="text/plain")

# -------------------------
# Dashboard
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

# -------------------------
# Career Advice
# -------------------------
if page == "Career Advice":
    st.header("🧭 Personalized Career Advice")
    profile = st.text_area("Describe your profile (education, skills, interests, goals):", height=180)
    if st.button("Get Advice", key="get_advice"):
        if not profile.strip():
            st.warning("Please enter your profile so I can give tailored advice.")
        else:
            with st.spinner("Generating personalized career advice..."):
                resp = safe_post_json("/career_advice", {"profile": profile})
                if resp is None:
                    st.error("Could not connect to the backend. Is it running?")
                elif resp.status_code != 200:
                    st.error(f"Backend error: {resp.text}")
                else:
                    advice = resp.json().get("advice", "")
                    st.markdown("### Results")
                    st.markdown(f"<div class='result-block'>{advice}</div>", unsafe_allow_html=True)
                    download_text_button(advice, filename="career_advice.txt", label="Download Advice")
                    st.button("Copy to Clipboard", key="copy_advice", help="Copy advice text for later use")

# -------------------------
# Job Suggestor
# -------------------------
if page == "Job Suggestor":
    st.header("💼 Job Suggestor")
    profile = st.text_area("Enter your profile (skills, domain, interests):", height=140)
    location = st.text_input("Preferred location (optional)")
    if st.button("Suggest Jobs", key="suggest_jobs"):
        if not profile.strip():
            st.warning("Please provide at least a short profile or skills.")
        else:
            with st.spinner("Finding best-fit job roles..."):
                payload = {"profile": profile, "location": location}
                resp = safe_post_json("/job_suggestor", payload)
                if resp is None:
                    st.error("Backend not reachable.")
                elif resp.status_code != 200:
                    st.error(f"Backend error: {resp.text}")
                else:
                    jobs = resp.json().get("jobs", [])
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
                                            st.markdown(f"- {name}")
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

# -------------------------
# Resume Evaluator
# -------------------------
if page == "Resume Evaluator":
    st.header("📄 Resume Evaluator")
    st.markdown("Upload your resume (PDF). The system will extract text and provide strengths, weaknesses, missing skills and concrete improvements.")
    resume_file = st.file_uploader("Upload PDF resume", type=["pdf"])
    if resume_file:
        if st.button("Evaluate Resume", key="eval_resume"):
            with st.spinner("Extracting and evaluating resume..."):
                files = {"file": ("resume.pdf", resume_file.getvalue(), "application/pdf")}
                resp = safe_post_files("/resume_eval", files)
                if resp is None:
                    st.error("Could not reach backend.")
                elif resp.status_code != 200:
                    st.error(f"Backend error: {resp.text}")
                else:
                    ev = resp.json().get("evaluation", "")
                    st.markdown("### Resume Evaluation")
                    with st.expander("Full Evaluation (expand)"):
                        st.markdown(ev if ev else "No evaluation text returned.")
                    st.success("Evaluation complete.")
                    download_text_button(ev, filename="resume_evaluation.txt", label="Download Evaluation")

# -------------------------
# Page: Mock Interview
# -------------------------
if page == "Mock Interview":
    st.header("🎤 Mock Interview")
    role = st.text_input("Role to prepare for (e.g., Embedded Systems Engineer):")
    start = st.button("Start Mock Interview", key="start_mock")

    # session state for questions, index, and results
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
                resp = safe_post_json("/mock_interview", {"role": role})
                if resp is None:
                    st.error("Backend unreachable.")
                elif resp.status_code != 200:
                    st.error("Backend error: " + resp.text)
                else:
                    questions = resp.json().get("questions", [])
                    # Ensure it's a list
                    if isinstance(questions, list) and questions:
                        st.session_state.mi_questions = questions
                        st.session_state.mi_idx = 0
                        st.session_state.mi_results = []
                    else:
                        st.warning("No questions generated. Try again.")

    # Display current question
    if st.session_state.mi_questions:
        idx = st.session_state.mi_idx
        current_question = st.session_state.mi_questions[idx]

        st.subheader(f"Question {idx + 1} of {len(st.session_state.mi_questions)}")
        st.markdown(f"**{current_question}**")

        # Input area
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
                        payload = {
                            "question": current_question,
                            "transcript": answer,
                            "resume_text": ""
                        }
                        resp = safe_post_json("/mock/evaluate", payload)
                        if resp is None:
                            st.error("Backend unreachable.")
                        elif resp.status_code != 200:
                            st.error("Backend error: " + resp.text)
                        else:
                            res = resp.json()
                            st.session_state.mi_results.append(res)
                            st.success("Answer evaluated.")
                            # move to next question automatically
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

        # show past results
        if st.session_state.mi_results:
            st.markdown("### Previous Answers & Feedback")
            for i, r in enumerate(st.session_state.mi_results):
                st.markdown(f"**Q{i+1}:** {st.session_state.mi_questions[i]}")
                st.markdown(f"- **Clarity:** {r.get('clarity','N/A')}")
                st.markdown(f"- **Confidence:** {r.get('confidence','N/A')}")
                st.markdown(f"- **Score:** {r.get('score','N/A')}")
                st.markdown(f"- **Feedback:** {r.get('feedback','')}")
                st.divider()

# -------------------------
# Speech-to-Text
# -------------------------
if page == "Speech-to-Text":
    st.header("🗣️ Speech to Text")
    st.markdown("Record audio elsewhere and upload a WAV/MP3 file.")
    audio_file = st.file_uploader("Upload audio file (wav/mp3)", type=["wav", "mp3"])
    if audio_file and st.button("Transcribe Audio"):
        with st.spinner("Transcribing..."):
            files = {"file": ("audio", audio_file.getvalue(), "audio/wav")}
            resp = safe_post_files("/speech_to_text", files, timeout=90)
            if resp and resp.status_code == 200:
                text = resp.json().get("transcript") or resp.json().get("text") or ""
                st.success("Transcription complete")
                st.markdown("**Transcript:**")
                st.write(text)
                download_text_button(text, filename="transcript.txt", label="Download Transcript")
            else:
                st.error("Backend unreachable or error.")

if page == "Notifier":
    st.header("🔔 Notifier (Reminders via Email)")
    reminder_text = st.text_input("What should I remind you about?")
    reminder_email = st.text_input("Your email address")
    remind_time = st.time_input("Remind me at (time, local):")

    if st.button("Set Reminder"):
        if not reminder_text.strip() or not reminder_email.strip():
            st.warning("Please enter both reminder text and email.")
        else:
            # Combine today's date with selected time
            now = datetime.datetime.now()
            remind_datetime = datetime.datetime.combine(now.date(), remind_time)
            payload = {
                "text": reminder_text,
                "email": reminder_email,
                "time": remind_datetime.isoformat()
            }
            resp = safe_post_json("/set_reminder", payload)
            if resp is None:
                st.error("Backend unreachable.")
            elif resp.status_code != 200:
                st.error(f"Backend error: {resp.text}")
            else:
                st.success(f"Reminder scheduled: '{reminder_text}' at {remind_datetime.strftime('%H:%M:%S')}")


# -------------------------
# Facial Analysis (placeholder)
# -------------------------
if page == "Facial Analysis":
    st.header("📹 Facial Expression Evaluator (Mock Interview)")
    st.markdown("This feature uses webcam frames to detect emotions and provide feedback on non-verbal cues.")
    st.info("💡 Prototype only — actual facial analysis coming soon!")
    st.markdown("Expected feedback will be like:")
    st.markdown("😊 😐 😞  (Happy, Neutral, Concerned) — Feature coming soon.")

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.markdown("<div class='small-muted'>Tip: Keep your backend running. Use download buttons to save outputs.</div>", unsafe_allow_html=True)