def cpu_demand(tasks):
    """Theoretical task-set CPU demand/utilization.

    This is workload demand, not physical CPU usage.
    """
    return sum(
        float(row["execution"]) / float(row["period"])
        for _, row in tasks.iterrows()
    )


def cpu_utilization(tasks):
    return cpu_demand(tasks)


def summarize(job_records, events, tasks):
    jobs = len(job_records)

    misses = 0
    rows = []

    for j in job_records:
        finish = j["finish"]

        if finish is None:
            status = "MISSED / INCOMPLETE"
            misses += 1
        elif finish > j["deadline"]:
            status = "MISSED"
            misses += 1
        else:
            status = "MET"

        response = None
        waiting = None

        if j["start"] is not None:
            response = j["start"] - j["release"]
            waiting = response

        rows.append({
            "Job": j["job_id"],
            "Task": j["task"],
            "Release": j["release"],
            "Start": j["start"] if j["start"] is not None else "—",
            "Finish": j["finish"] if j["finish"] is not None else "—",
            "Deadline": j["deadline"],
            "Response Time": response if response is not None else "—",
            "Waiting Time": waiting if waiting is not None else "—",
            "Status": status,
        })

    busy = sum(
        max(0, e["end"] - e["start"])
        for e in events
        if e["task"] != "IDLE"
    )

    total_time = 0
    if events:
        total_time = max(e["end"] for e in events)

    context_switches = 0
    previous = None

    for e in events:
        task = e["task"]
        if task != "IDLE":
            if previous is not None and task != previous:
                context_switches += 1
            previous = task

    completed_waits = [
        r["Waiting Time"] for r in rows
        if isinstance(r["Waiting Time"], (int, float))
    ]

    completed_responses = [
        r["Response Time"] for r in rows
        if isinstance(r["Response Time"], (int, float))
    ]

    return {
        "deadline_misses": misses,
        "jobs": jobs,
        "miss_rate": misses / jobs if jobs else 0.0,
        "context_switches": context_switches,
        "avg_waiting": (
            sum(completed_waits) / len(completed_waits)
            if completed_waits else 0.0
        ),
        "avg_response": (
            sum(completed_responses) / len(completed_responses)
            if completed_responses else 0.0
        ),
        "actual_busy_ratio": (
            busy / total_time if total_time else 0.0
        ),
        "cpu_demand": cpu_demand(tasks),
        "job_table": rows,
    }
