import random
import pandas as pd


def generate_tasks(n=5, seed=42):
    random.seed(seed)

    rows = []
    for i in range(1, n + 1):
        execution = random.randint(1, 3)
        period = random.choice([5, 8, 10, 12, 15, 20])
        deadline = random.choice([
            period,
            max(execution, period - 1),
        ])
        priority = i

        rows.append({
            "task": f"T{i}",
            "execution": execution,
            "period": period,
            "deadline": deadline,
            "priority": priority,
        })

    return pd.DataFrame(rows)


def load_tasks(path="data/sample_tasks.csv"):
    return pd.read_csv(path)
