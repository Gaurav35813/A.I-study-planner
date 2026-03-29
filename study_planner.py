"""
Smart Study Planner — Streamlit App
=====================================
A personalized study planner with AI plan generation via Ollama (llama3).

Run with:
    streamlit run study_planner.py
"""

import time
from datetime import datetime, date

import pandas as pd
import requests
import streamlit as st


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

OLLAMA_URL  = "http://127.0.0.1:11434/api/generate"
MODEL_NAME  = "llama3:latest"

st.set_page_config(
    page_title="Smart Study Planner",
    page_icon="📚",
    layout="wide",
)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_ai_response(prompt: str) -> str:
    """Send a prompt to local Ollama and return the text response."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=300,
        )
        if response.status_code != 200:
            return f"API Error {response.status_code}: {response.text}"

        data = response.json()
        return data.get("response", f"Unexpected response format: {data}")

    except requests.exceptions.ConnectionError:
        return (
            "Connection Error: Could not reach Ollama. "
            "Make sure Ollama is running with: `ollama serve`"
        )
    except requests.exceptions.Timeout:
        return "Timeout Error: Ollama took too long to respond. Try again."
    except Exception as e:
        return f"Error: {e}"


def classify_level(score: int) -> str:
    if score < 60:
        return "Weak"
    elif score < 80:
        return "Moderate"
    return "Strong"


def level_emoji(level: str) -> str:
    return {"Weak": "🔴", "Moderate": "🟡", "Strong": "🟢"}.get(level, "")


def fmt_time(decimal_hour: float) -> str:
    """Convert decimal hour (e.g. 9.5) to HH:MM string."""
    h = int(decimal_hour)
    m = int((decimal_hour - h) * 60)
    return f"{h:02d}:{m:02d}"


# ─────────────────────────────────────────────
# SIDEBAR — Timer & Calendar
# ─────────────────────────────────────────────

with st.sidebar:
    st.header("🛠 Tools")

    # ── Clock ──
    st.subheader("🕒 Current Time")
    st.write(datetime.now().strftime("%A, %d %b %Y  •  %H:%M:%S"))

    # ── Study Timer ──
    st.subheader("⏱ Study Timer")
    if "start_time" not in st.session_state:
        st.session_state.start_time = None

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("▶ Start", use_container_width=True):
            st.session_state.start_time = time.time()
            st.success("Timer started!")
    with col_b:
        if st.button("⏹ Stop", use_container_width=True):
            if st.session_state.start_time:
                elapsed = time.time() - st.session_state.start_time
                minutes = round(elapsed / 60, 2)
                st.success(f"Studied for **{minutes} min**")
                st.session_state.start_time = None
            else:
                st.warning("Timer not started.")

    if st.session_state.start_time:
        elapsed_now = time.time() - st.session_state.start_time
        st.info(f"Running: {round(elapsed_now / 60, 1)} min")

    # ── Calendar ──
    st.subheader("📅 Study Date")
    selected_date = st.date_input("Choose a date", date.today())
    st.write(f"Selected: **{selected_date.strftime('%d %B %Y')}**")


# ─────────────────────────────────────────────
# MAIN — Title
# ─────────────────────────────────────────────

st.title("📚 Smart Study Planner")
st.markdown("Track your subject scores, get a personalised timetable, and generate an AI study plan.")
st.divider()


# ─────────────────────────────────────────────
# SECTION 1 — Enter Scores
# ─────────────────────────────────────────────

st.header("1️⃣  Enter Your Scores")

col1, col2, col3 = st.columns(3)
with col1:
    math = st.slider("📘 Math", 0, 100, 50)
with col2:
    physics = st.slider("⚡ Physics", 0, 100, 50)
with col3:
    chemistry = st.slider("🧪 Chemistry", 0, 100, 50)

hours = st.slider("⏳ Study Hours per Day", 1, 12, 4)
start_hour = st.slider("🌅 Start Hour (24h)", 5, 12, 8)

st.divider()


# ─────────────────────────────────────────────
# DATA PROCESSING
# ─────────────────────────────────────────────

df = pd.DataFrame({
    "Subject" : ["Math", "Physics", "Chemistry"],
    "Score"   : [math, physics, chemistry],
})
df["Level"]    = df["Score"].apply(classify_level)
df["Priority"] = 100 - df["Score"]          # higher priority → lower score

df_sorted      = df.sort_values("Priority", ascending=False).reset_index(drop=True)
total_priority = df_sorted["Priority"].sum()

# Guard: if all scores are 100, avoid division by zero
if total_priority == 0:
    df_sorted["TimeAlloc"] = hours / len(df_sorted)
else:
    df_sorted["TimeAlloc"] = (df_sorted["Priority"] / total_priority) * hours


# ─────────────────────────────────────────────
# SECTION 2 — Performance Analysis
# ─────────────────────────────────────────────

st.header("2️⃣  Performance Analysis")

col_table, col_chart = st.columns([1, 1])

with col_table:
    display_df = df_sorted[["Subject", "Score", "Level"]].copy()
    display_df["Level"] = display_df.apply(
        lambda r: f"{level_emoji(r['Level'])} {r['Level']}", axis=1
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)

with col_chart:
    st.bar_chart(df.set_index("Subject")["Score"], use_container_width=True)

st.subheader("Progress Bars")
for _, row in df.iterrows():
    st.write(f"{level_emoji(classify_level(row['Score']))} **{row['Subject']}** — {row['Score']}%")
    st.progress(int(row["Score"]))

st.divider()


# ─────────────────────────────────────────────
# SECTION 3 — Daily Timetable
# ─────────────────────────────────────────────

st.header("3️⃣  Daily Timetable")

current_time = float(start_hour)

for _, row in df_sorted.iterrows():
    alloc      = row["TimeAlloc"]
    end_time   = current_time + alloc
    start_str  = fmt_time(current_time)
    end_str    = fmt_time(end_time)
    emoji      = level_emoji(row["Level"])

    st.info(
        f"**{start_str} – {end_str}**  •  {emoji} {row['Subject']}  "
        f"({row['Level']})  •  {round(alloc, 1)} hrs"
    )
    current_time = end_time

st.divider()


# ─────────────────────────────────────────────
# SECTION 4 — Recommendations
# ─────────────────────────────────────────────

st.header("4️⃣  Study Recommendations")

for _, row in df_sorted.iterrows():
    alloc = row["TimeAlloc"]
    emoji = level_emoji(row["Level"])
    tip   = {
        "Weak"    : "Focus on fundamentals and practice daily.",
        "Moderate": "Review key concepts and solve more problems.",
        "Strong"  : "Revise lightly and maintain with mock tests.",
    }.get(row["Level"], "")

    st.markdown(
        f"**{emoji} {row['Subject']}** — Study for **{round(alloc, 1)} hrs**  \n"
        f"_{tip}_"
    )

st.divider()


# ─────────────────────────────────────────────
# SECTION 5 — AI Study Planner
# ─────────────────────────────────────────────

st.header("5️⃣  AI Study Planner")
st.caption("Powered by Ollama (llama3) running locally on your machine.")

exam = st.text_input("🎯 Enter Exam Name (e.g., IIT JAM, GATE, UPSC, JEE)")

weak_subjects = df[df["Level"] == "Weak"]["Subject"].tolist()
weak_str = ", ".join(weak_subjects) if weak_subjects else "none identified"

if st.button("🚀 Generate AI Study Plan", type="primary"):
    if not exam.strip():
        st.warning("⚠️ Please enter an exam name first.")
    else:
        prompt = f"""
You are an expert academic coach. Create a concise, actionable study plan for a student
preparing for the {exam} exam.

Student profile:
- Math score    : {math}/100  ({classify_level(math)})
- Physics score : {physics}/100  ({classify_level(physics)})
- Chemistry score: {chemistry}/100  ({classify_level(chemistry)})
- Available study time: {hours} hours per day
- Weak subjects: {weak_str}

Provide:
1. A weekly study schedule (Mon–Sun)
2. Specific tips for weak subjects
3. Recommended resources (books / YouTube channels)
4. Revision and mock-test strategy

Keep it concise and practical.
"""

        with st.spinner("🤖 Generating your personalised study plan..."):
            result = get_ai_response(prompt)

        if any(result.startswith(e) for e in ("Error", "API Error", "Connection Error", "Timeout")):
            st.error(result)
            st.info(
                "💡 **Tip:** Make sure Ollama is running.\n"
                "Open a terminal and run: `ollama serve`\n"
                "Then pull the model if needed: `ollama pull llama3`"
            )
        else:
            st.success("✅ Study Plan Generated!")
            st.markdown(result)
