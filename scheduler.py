from dataclasses import dataclass


@dataclass
class Job:
    job_id: str
    task: str
    release: int
    remaining: int
    execution: int
    deadline: int
    period: int
    priority: int
    start: int | None = None
    finish: int | None = None


def choose_job(ready, algorithm):
    if not ready:
        return None

    if algorithm == "EDF":
        return min(ready, key=lambda j: (j.deadline, j.task, j.job_id))

    # Rate Monotonic: shorter period = higher priority.
    return min(ready, key=lambda j: (j.period, j.task, j.job_id))


def simulate(tasks, algorithm="EDF", preemptive=True, duration=100):
    """Simulate one independent scheduling window.

    Returns:
        events: CPU execution segments
        jobs: per-job release/start/finish/deadline information
    """
    jobs = []

    for _, row in tasks.iterrows():
        period = int(row["period"])
        execution = int(row["execution"])
        deadline = int(row["deadline"])
        priority = int(row["priority"])

        release = 0
        instance = 1

        while release < duration:
            jobs.append(
                Job(
                    job_id=f"{row['task']}_{instance}",
                    task=str(row["task"]),
                    release=release,
                    remaining=execution,
                    execution=execution,
                    deadline=release + deadline,
                    period=period,
                    priority=priority,
                )
            )
            release += period
            instance += 1

    ready = []
    events = []
    current = None

    for t in range(duration):
        # Release jobs at this time.
        for j in jobs:
            if j.release == t and j.remaining > 0:
                ready.append(j)

        # Preemptive mode chooses the highest-priority job every time unit.
        # Non-preemptive mode keeps the current job until it finishes.
        if current is None:
            current = choose_job(ready, algorithm)
            if current is not None:
                ready.remove(current)
                if current.start is None:
                    current.start = t

        elif preemptive:
            candidate = choose_job(ready + [current], algorithm)
            if candidate is not current:
                ready.append(current)
                current = candidate
                ready.remove(current)
                if current.start is None:
                    current.start = t

        if current is None:
            events.append({
                "task": "IDLE",
                "job_id": "IDLE",
                "start": t,
                "end": t + 1,
            })
            continue

        current.remaining -= 1

        if current.remaining == 0:
            current.finish = t + 1
            events.append({
                "task": current.task,
                "job_id": current.job_id,
                "start": t,
                "end": t + 1,
            })
            current = None
        else:
            events.append({
                "task": current.task,
                "job_id": current.job_id,
                "start": t,
                "end": t + 1,
            })

    # Merge adjacent segments belonging to the same job.
    merged = []
    for e in events:
        if (
            merged
            and merged[-1]["job_id"] == e["job_id"]
            and merged[-1]["end"] == e["start"]
        ):
            merged[-1]["end"] = e["end"]
        else:
            merged.append(dict(e))

    job_records = []
    for j in jobs:
        job_records.append({
            "job_id": j.job_id,
            "task": j.task,
            "release": j.release,
            "execution": j.execution,
            "deadline": j.deadline,
            "start": j.start,
            "finish": j.finish,
        })

    return merged, job_records
