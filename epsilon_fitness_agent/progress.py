"""Local (non-LLM) progress assessment computed from logged data."""

from collections import Counter
from datetime import date

from epsilon_fitness_agent.storage import meal_logs, progress_logs, workout_logs

RECENT_ENTRIES_LIMIT = 3


def _trend(delta: float, flat_threshold: float = 0.1) -> str:
    if delta <= -flat_threshold:
        return "decreasing"
    if delta >= flat_threshold:
        return "increasing"
    return "stable"


def _summarize_workouts(workouts: list[dict]) -> dict:
    if not workouts:
        return {"total_logged": 0}

    first_date = date.fromisoformat(workouts[0]["date"])
    last_date = date.fromisoformat(workouts[-1]["date"])
    weeks_span = max((last_date - first_date).days / 7, 1)

    return {
        "total_logged": len(workouts),
        "date_range": {"first": workouts[0]["date"], "last": workouts[-1]["date"]},
        "sessions_per_week_avg": round(len(workouts) / weeks_span, 1),
        "by_type": dict(Counter(w["workout_type"] for w in workouts)),
        "total_calories_burned": sum(w.get("calories_burned") or 0 for w in workouts),
    }


def _summarize_meals(meals: list[dict]) -> dict:
    if not meals:
        return {"total_logged": 0}

    distinct_days = sorted({m["date"] for m in meals})
    calories = [m["calories"] for m in meals if m.get("calories") is not None]
    protein = [m["macros"]["protein_g"] for m in meals if m.get("macros")]
    carbs = [m["macros"]["carbs_g"] for m in meals if m.get("macros")]
    fat = [m["macros"]["fat_g"] for m in meals if m.get("macros")]

    def avg(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 1) if values else None

    return {
        "total_logged": len(meals),
        "distinct_days_logged": len(distinct_days),
        "date_range": {"first": meals[0]["date"], "last": meals[-1]["date"]},
        "avg_calories_per_meal": avg(calories),
        "avg_protein_g_per_meal": avg(protein),
        "avg_carbs_g_per_meal": avg(carbs),
        "avg_fat_g_per_meal": avg(fat),
    }


def _summarize_measurements(entries: list[dict]) -> dict:
    if not entries:
        return {"total_logged": 0}

    first, last = entries[0], entries[-1]
    weight_delta = round(last["weight_kg"] - first["weight_kg"], 2)

    summary = {
        "total_logged": len(entries),
        "date_range": {"first": first["date"], "last": last["date"]},
        "weight_kg": {
            "first": first["weight_kg"],
            "latest": last["weight_kg"],
            "delta": weight_delta,
            "trend": _trend(weight_delta),
        },
    }

    if first.get("body_fat_pct") is not None and last.get("body_fat_pct") is not None:
        bf_delta = round(last["body_fat_pct"] - first["body_fat_pct"], 2)
        summary["body_fat_pct"] = {
            "first": first["body_fat_pct"],
            "latest": last["body_fat_pct"],
            "delta": bf_delta,
            "trend": _trend(bf_delta),
        }

    return summary


def summarize_progress(user_id: str) -> dict:
    """Compute deterministic trend stats from a user's logs - no model call involved."""
    workouts = sorted(workout_logs.query("user_id", user_id), key=lambda w: w["date"])
    meals = sorted(meal_logs.query("user_id", user_id), key=lambda m: m["date"])
    measurements = sorted(progress_logs.query("user_id", user_id), key=lambda p: p["date"])

    return {
        "workouts": _summarize_workouts(workouts),
        "meals": _summarize_meals(meals),
        "measurements": _summarize_measurements(measurements),
        "recent_workouts": workouts[-RECENT_ENTRIES_LIMIT:],
        "recent_meals": meals[-RECENT_ENTRIES_LIMIT:],
    }
