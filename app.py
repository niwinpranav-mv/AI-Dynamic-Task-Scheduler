import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from task_generator import generate_tasks, load_tasks
from scheduler import simulate
from metrics import summarize, cpu_demand
from ai_predictor import predict_best

st.set_page_config(page_title="AI Dynamic Task Scheduler", layout="wide")
st.title("AI-Based Dynamic Real-Time Task Scheduler")
st.caption("Pure-software prototype: RM ↔ EDF and Preemptive ↔ Non-Preemptive")

# -----------------------------
# Session state
# -----------------------------
if "tasks" not in st.session_state:
    st.session_state.tasks = generate_tasks(seed=42)

# -----------------------------
# 1. TASK INPUT
# -----------------------------
st.header("1. Task Input")

left, right = st.columns([5, 1])

with left:
    edited = st.data_editor(
        st.session_state.tasks,
        num_rows="dynamic",
        use_container_width=True,
        key="task_editor",
    )
    st.session_state.tasks = edited

with right:
    st.write("**Actions**")
    if st.button("Generate Sample"):
        st.session_state.tasks = generate_tasks(seed=42)
        st.rerun()
    if st.button("Load CSV"):
        st.session_state.tasks = load_tasks()
        st.rerun()

tasks = st.session_state.tasks.copy()

required = ["task", "execution", "period", "deadline", "priority"]
missing = [c for c in required if c not in tasks.columns]

if missing:
    st.error(f"Missing columns: {', '.join(missing)}")
    st.stop()

try:
    for c in ["execution", "period", "deadline", "priority"]:
        tasks[c] = pd.to_numeric(tasks[c], errors="raise").astype(int)
except Exception:
    st.error("Execution, period, deadline and priority must contain valid integers.")
    st.stop()

if tasks.empty:
    st.warning("Add at least one task.")
    st.stop()

if (tasks[["execution", "period", "deadline"]] <= 0).any().any():
    st.error("Execution time, period and deadline must be greater than zero.")
    st.stop()

# -----------------------------
# 2. CPU DEMAND
# -----------------------------
st.header("2. CPU Demand")

demand = cpu_demand(tasks)
c1, c2 = st.columns(2)

with c1:
    st.metric("Task-set CPU Demand", f"{demand * 100:.1f}%")

with c2:
    if demand > 1.0:
        st.error("🔴 OVERLOADED — CPU demand exceeds 100%.")
    elif demand > 0.8:
        st.warning("🟠 HIGH DEMAND — CPU demand is above 80%.")
    else:
        st.success("🟢 WITHIN CAPACITY — CPU demand is at or below 100%.")

st.caption(
    "CPU Demand = Σ(Execution Time / Period). This is workload demand, "
    "not the physical CPU usage of your computer."
)

# -----------------------------
# 3. SCHEDULING CONFIGURATION
# -----------------------------
st.header("3. Scheduling Configuration")

c1, c2 = st.columns(2)
with c1:
    algorithm = st.radio("Initial Algorithm", ["RM", "EDF"], horizontal=True)
with c2:
    mode = st.radio(
        "Initial Mode",
        ["Non-Preemptive", "Preemptive"],
        horizontal=True,
    )

preemptive = mode == "Preemptive"

# -----------------------------
# 4. SIMULATION SETTINGS
# -----------------------------
st.header("4. Simulation Settings")

c1, c2 = st.columns(2)
with c1:
    duration = st.number_input(
        "Simulation Duration (time units)",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
        help="Total simulated CPU time. 100 gives multiple releases of the periodic tasks.",
    )
with c2:
    window = st.number_input(
        "Scheduling Window (time units)",
        min_value=5,
        max_value=100,
        value=20,
        step=5,
        help="Analysis interval used by the dynamic scheduler. 20 matches the largest period in the default workload.",
    )

# -----------------------------
# 5. AI SETTINGS
# -----------------------------
st.header("5. AI Settings")

c1, c2 = st.columns(2)
with c1:
    confidence_threshold = st.slider(
        "AI Confidence Threshold",
        min_value=0.50,
        max_value=0.99,
        value=0.80,
        step=0.01,
        format="%.0f%%",
        help="AI must be at least this confident before it can switch configuration.",
    )
with c2:
    improvement_threshold = st.slider(
        "Switch Improvement Threshold",
        min_value=1,
        max_value=30,
        value=10,
        step=1,
        format="%d%%",
        help="The alternative configuration must improve the score by at least this percentage.",
    )

st.info(
    "Prototype defaults: 100 time units, 20-unit scheduling window, "
    "80% AI confidence, and 10% minimum improvement."
)

# -----------------------------
# Run simulation
# -----------------------------
if st.button("🚀 Run Dynamic Simulation", type="primary", use_container_width=True):

    current_algorithm = algorithm
    current_preemptive = preemptive
    all_events = []
    all_job_records = []
    switch_log = []

    current_time = 0

    # Windowed dynamic simulation. Each window is evaluated independently,
    # while event timestamps are shifted into the global simulation timeline.
    while current_time < duration:
        end = min(current_time + int(window), int(duration))
        window_duration = end - current_time

        events, jobs = simulate(
            tasks,
            current_algorithm,
            current_preemptive,
            window_duration,
        )

        for e in events:
            shifted = dict(e)
            shifted["start"] += current_time
            shifted["end"] += current_time
            shifted["window"] = f"{current_time}-{end}"
            all_events.append(shifted)

        for j in jobs:
            shifted_job = dict(j)
            shifted_job["release"] += current_time
            shifted_job["deadline"] += current_time
            if shifted_job["start"] is not None:
                shifted_job["start"] += current_time
            if shifted_job["finish"] is not None:
                shifted_job["finish"] += current_time
            all_job_records.append(shifted_job)

        best, confidence, alternatives = predict_best(tasks, window_duration)

        current_label = (current_algorithm, current_preemptive)
        best_label = (best["algorithm"], best["preemptive"])

        current_result = next(
            x for x in alternatives
            if (x["algorithm"], x["preemptive"]) == current_label
        )

        current_score = current_result["score"]
        best_score = best["score"]

        if current_score > 0:
            improvement = max(
                0.0,
                ((current_score - best_score) / current_score) * 100
            )
        else:
            improvement = 0.0

        if (
            best_label != current_label
            and confidence >= confidence_threshold
            and improvement >= improvement_threshold
        ):
            switch_log.append({
                "Time": end,
                "From": f"{current_algorithm} + {'Preemptive' if current_preemptive else 'Non-Preemptive'}",
                "To": f"{best['algorithm']} + {'Preemptive' if best['preemptive'] else 'Non-Preemptive'}",
                "AI Confidence": f"{confidence * 100:.1f}%",
                "Predicted Improvement": f"{improvement:.1f}%",
            })
            current_algorithm, current_preemptive = best_label

        current_time = end

    final_metrics = summarize(all_job_records, all_events, tasks)

    # -----------------------------
    # 6. RESULTS
    # -----------------------------
    st.header("6. Simulation Results")

    if demand > 1:
        st.error(
            f"⚠️ OVERLOADED: task-set CPU demand is {demand * 100:.1f}%, "
            "which exceeds the 100% capacity of a single CPU."
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Deadline Misses", final_metrics["deadline_misses"])
    c2.metric("Jobs Simulated", final_metrics["jobs"])
    c3.metric("Miss Rate", f"{final_metrics['miss_rate'] * 100:.1f}%")
    c4.metric("CPU Busy", f"{final_metrics['actual_busy_ratio'] * 100:.1f}%")

    st.subheader("Deadline-Miss Analysis")

    if final_metrics["job_table"]:
        job_df = pd.DataFrame(final_metrics["job_table"])
        st.dataframe(job_df, use_container_width=True, hide_index=True)

        if final_metrics["deadline_misses"] > 0:
            st.warning(
                f"{final_metrics['deadline_misses']} of {final_metrics['jobs']} "
                "simulated jobs missed their deadlines."
            )
        else:
            st.success("All simulated jobs met their deadlines.")
    else:
        st.info("No completed jobs were available for deadline analysis.")

    # -----------------------------
    # Gantt chart
    # -----------------------------
    st.subheader("CPU Execution Timeline")

    fig, ax = plt.subplots(figsize=(14, 3.2))
    for e in all_events:
        if e["task"] == "IDLE":
            continue
        ax.barh(
            0,
            e["end"] - e["start"],
            left=e["start"],
            height=0.5,
        )
        ax.text(
            (e["start"] + e["end"]) / 2,
            0,
            e["task"],
            ha="center",
            va="center",
        )

    ax.set_xlabel("Time")
    ax.set_yticks([])
    ax.set_xlim(0, int(duration))
    ax.set_title("CPU Execution Timeline")
    st.pyplot(fig)

    # -----------------------------
    # AI switching history
    # -----------------------------
    st.subheader("AI Dynamic Switching")

    if switch_log:
        st.dataframe(
            pd.DataFrame(switch_log),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No switch was made. The AI either preferred the current configuration "
            "or the confidence/improvement requirements were not satisfied."
        )

    # -----------------------------
    # Final AI recommendation
    # -----------------------------
    st.subheader("AI Recommendation")

    best, confidence, alternatives = predict_best(tasks, int(window))

    recommendation = (
        f"{best['algorithm']} + "
        f"{'Preemptive' if best['preemptive'] else 'Non-Preemptive'}"
    )

    st.write(
        f"Recommended configuration: **{recommendation}**  \n"
        f"AI confidence: **{confidence * 100:.1f}%**"
    )

    comparison = pd.DataFrame([
        {
            "Configuration": (
                f"{x['algorithm']} + "
                f"{'Preemptive' if x['preemptive'] else 'Non-Preemptive'}"
            ),
            "Score": round(x["score"], 2),
            "Deadline Misses": x["metrics"]["deadline_misses"],
            "Miss Rate": f"{x['metrics']['miss_rate'] * 100:.1f}%",
            "Context Switches": x["metrics"]["context_switches"],
        }
        for x in alternatives
    ])

    st.dataframe(comparison, use_container_width=True, hide_index=True)

    st.subheader("Final Configuration")
    st.success(
        f"Final scheduler: **{current_algorithm} + "
        f"{'Preemptive' if current_preemptive else 'Non-Preemptive'}**"
    )
