# AI-Based Dynamic Real-Time Task Scheduler

A pure-software Streamlit prototype for demonstrating:

- Rate Monotonic (RM)
- Earliest Deadline First (EDF)
- Preemptive scheduling
- Non-preemptive scheduling
- Task-set CPU demand
- Automatic overload detection
- Deadline-miss analysis
- Gantt-style CPU timeline
- Lightweight AI configuration prediction
- Dynamic switching between scheduling configurations

## UI design

The project intentionally uses a single main-page flow rather than a sidebar.

### Parameters

**Simulation Settings**
- Simulation Duration: 100 time units
- Scheduling Window: 20 time units

**AI Settings**
- AI Confidence Threshold: 80%
- Switch Improvement Threshold: 10%

These are prototype parameters, not universal real-time scheduling constants.

## CPU Demand

The displayed value is task-set CPU demand:

U = Σ(Ci / Ti)

It is NOT the physical CPU usage of the computer running Streamlit.

If U > 100%, the application displays:

OVERLOADED — CPU demand exceeds 100%.

For the included sample workload:

T1 = 3/5
T2 = 3/10
T3 = 1/8
T4 = 3/20
T5 = 3/12

U = 142.5%

## Deadline analysis

Every generated job is tracked separately.

The dashboard reports:
- release time
- start time
- finish time
- deadline
- response time
- waiting time
- MET / MISSED status
- total deadline misses
- miss rate

A job that has not completed by the end of the simulation is treated as incomplete/missed.

## AI behavior

The AI evaluates four configurations:

1. EDF + Preemptive
2. EDF + Non-Preemptive
3. RM + Preemptive
4. RM + Non-Preemptive

The lightweight predictor uses an interpretable score based primarily on deadline misses, then waiting time and context switches.

A dynamic switch occurs only when:
- the recommended configuration differs from the current one,
- AI confidence >= configured confidence threshold, and
- predicted improvement >= configured improvement threshold.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local Streamlit URL shown in the terminal.
