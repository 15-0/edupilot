"""Train the academic performance model.

Run:  python -m app.ml.train

The baseline is trained on a *synthetic* dataset whose relationships mirror published
findings (prior scores, attendance, study time and coursework completion all correlate
with final results). Replace `generate_dataset()` with a real dataset - e.g. the UCI
"Student Performance" dataset (G1/G2 -> avg_score, absences -> attendance_rate,
studytime -> study_hours_per_week) - once you have one.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

FEATURES = [
    "avg_score",             # weighted average % so far
    "attendance_rate",       # 0..1
    "study_hours_per_week",  # last 4 weeks
    "completion_rate",       # share of due assignments completed, 0..1
    "score_trend",           # % points change per assessment (slope)
    "num_assessments",
]
TARGET = "final_score"
MODEL_VERSION = "gbr-synthetic-v1"
ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "ml_artifacts"
MODEL_PATH = ARTIFACT_DIR / "performance_model.joblib"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"


def generate_dataset(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    ability = rng.normal(70, 12, n)
    attendance = np.clip(rng.beta(8, 2, n) + 0.003 * (ability - 70), 0, 1)
    study = np.clip(rng.gamma(2.2, 2.6, n) + 0.05 * (ability - 70), 0, 35)
    completion = np.clip(rng.beta(6, 2, n) + 0.004 * (ability - 70), 0, 1)
    num = rng.integers(1, 13, n)
    # Observed average is ability + noise that shrinks as more assessments are recorded
    avg_score = np.clip(ability + rng.normal(0, 14, n) / np.sqrt(num), 0, 100)
    trend = rng.normal(0, 2.5, n)

    final = (
        0.50 * avg_score
        + 0.22 * ability
        + 16 * attendance
        + 1.0 * np.minimum(study, 14)
        - 0.15 * np.maximum(study - 25, 0)  # diminishing returns / burnout
        + 9 * completion
        + 1.4 * trend
        + rng.normal(0, 4, n)
    )
    return pd.DataFrame({
        "avg_score": avg_score,
        "attendance_rate": attendance,
        "study_hours_per_week": study,
        "completion_rate": completion,
        "score_trend": trend,
        "num_assessments": num,
        TARGET: np.clip(final, 0, 100),
    })


def train_and_save(verbose: bool = True) -> dict:
    df = generate_dataset()
    X, y = df[FEATURES], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=7)

    model = GradientBoostingRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9, random_state=7)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)

    baseline = X_test["avg_score"]  # naive baseline: "you'll finish where you are now"
    metrics = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "rows": len(df),
        "test_rows": len(X_test),
        "mae": round(float(mean_absolute_error(y_test, pred)), 3),
        "rmse": round(float(np.sqrt(mean_squared_error(y_test, pred))), 3),
        "r2": round(float(r2_score(y_test, pred)), 3),
        "baseline_mae": round(float(mean_absolute_error(y_test, baseline)), 3),
        "feature_importance": {
            f: round(float(v), 4) for f, v in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1])
        },
        "dataset": "synthetic",
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "metrics": metrics}, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    if verbose:
        print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    train_and_save()
