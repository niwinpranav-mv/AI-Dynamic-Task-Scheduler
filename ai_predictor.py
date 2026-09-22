from scheduler import simulate
from metrics import summarize


CONFIGS = [
    ("EDF", True),
    ("EDF", False),
    ("RM", True),
    ("RM", False),
]


def score_metrics(m):
    # Lower is better.
    # Deadline misses dominate the decision because meeting deadlines
    # is the primary real-time scheduling objective.
    miss = m["deadline_misses"] * 100
    miss_rate = m["miss_rate"] * 100
    wait = m["avg_waiting"] * 2
    switches = m["context_switches"] * 0.5

    return miss + miss_rate + wait + switches


def predict_best(tasks, duration=20):
    results = []

    for algorithm, preemptive in CONFIGS:
        events, jobs = simulate(
            tasks,
            algorithm,
            preemptive,
            int(duration),
        )
        metrics = summarize(jobs, events, tasks)
        score = score_metrics(metrics)

        results.append({
            "algorithm": algorithm,
            "preemptive": preemptive,
            "score": score,
            "metrics": metrics,
        })

    results.sort(key=lambda x: x["score"])

    best = results[0]
    second = results[1]

    gap = max(0.0, second["score"] - best["score"])

    confidence = min(
        0.99,
        0.55 + gap / max(second["score"], 1.0) * 0.45,
    )

    return best, confidence, results
