"""JSON-file-backed storage for user profiles."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROFILES_PATH = DATA_DIR / "user_profiles.json"
WORKOUT_LOGS_PATH = DATA_DIR / "workout_logs.json"
MEAL_LOGS_PATH = DATA_DIR / "meal_logs.json"
PROGRESS_LOGS_PATH = DATA_DIR / "progress_logs.json"


class JSONStore:
    """Loads/saves a list of records from a JSON file, keyed by id_field."""

    def __init__(self, path: Path, id_field: str):
        self.path = path
        self.id_field = id_field

    def load_all(self) -> list[dict]:
        with open(self.path) as f:
            return json.load(f)

    def get(self, record_id: str) -> dict | None:
        for record in self.load_all():
            if record[self.id_field] == record_id:
                return record
        return None

    def save(self, record: dict) -> None:
        """Insert or update a record (matched by id_field)."""
        records = self.load_all()
        for i, existing in enumerate(records):
            if existing[self.id_field] == record[self.id_field]:
                records[i] = record
                break
        else:
            records.append(record)
        with open(self.path, "w") as f:
            json.dump(records, f, indent=2)

    def delete(self, record_id: str) -> bool:
        records = self.load_all()
        remaining = [r for r in records if r[self.id_field] != record_id]
        if len(remaining) == len(records):
            return False
        with open(self.path, "w") as f:
            json.dump(remaining, f, indent=2)
        return True

    def query(self, field: str, value) -> list[dict]:
        return [r for r in self.load_all() if r.get(field) == value]


profiles = JSONStore(PROFILES_PATH, id_field="user_id")
workout_logs = JSONStore(WORKOUT_LOGS_PATH, id_field="log_id")
meal_logs = JSONStore(MEAL_LOGS_PATH, id_field="log_id")
progress_logs = JSONStore(PROGRESS_LOGS_PATH, id_field="log_id")
