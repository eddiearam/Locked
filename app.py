"""Locked deployment skeleton: frontend → Flask → PostgreSQL."""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# Placeholder defaults for columns the skeleton form does not collect.
PLACEHOLDER_OS = "Android"
PLACEHOLDER_AGE = 25
PLACEHOLDER_APPS_INSTALLED = 20

app = Flask(__name__)


def database_url() -> str:
    url = (os.environ.get("DATABASE_URL") or "").strip().strip("'").strip('"')
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


def get_connection():
    return psycopg2.connect(database_url())


def init_schema(conn) -> None:
    """Create Locked tables if they do not already exist. Same design as schema.sql."""
    sql = (ROOT / "schema.sql").read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def placeholder_behavior_class(screen_on_time_hours: float) -> int:
    """Temporary classification for the deployment assignment only."""
    if screen_on_time_hours <= 2:
        return 1
    if screen_on_time_hours <= 4:
        return 2
    if screen_on_time_hours <= 6:
        return 3
    if screen_on_time_hours <= 8:
        return 4
    return 5


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/check-goal")
def check_goal():
    payload = request.get_json(silent=True) or {}

    try:
        user_id = int(payload.get("user_id"))
        screen_on_time_hours = float(payload.get("screen_on_time_hours"))
        target_hours = float(payload.get("target_hours", 4))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "user_id, screen_on_time_hours, and target_hours must be numbers"}), 400

    if user_id <= 0:
        return jsonify({"success": False, "error": "user_id must be a positive integer"}), 400
    if screen_on_time_hours < 0:
        return jsonify({"success": False, "error": "screen_on_time_hours must be zero or greater"}), 400
    if target_hours <= 0:
        return jsonify({"success": False, "error": "target_hours must be greater than zero"}), 400

    # Skeleton goal logic (not the full Locked product).
    goal_completed = screen_on_time_hours <= target_hours
    message = "Goal completed" if goal_completed else "Goal not completed"

    # Placeholder fields required by screen_time_observations.
    app_usage_time_min = int(round(screen_on_time_hours * 60))
    user_behavior_class = placeholder_behavior_class(screen_on_time_hours)

    try:
        conn = get_connection()
        try:
            init_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                if cur.fetchone() is None:
                    cur.execute(
                        """
                        INSERT INTO users (user_id, operating_system, age)
                        VALUES (%s, %s, %s)
                        """,
                        (user_id, PLACEHOLDER_OS, PLACEHOLDER_AGE),
                    )

                cur.execute(
                    """
                    INSERT INTO screen_time_observations (
                        user_id,
                        app_usage_time_min,
                        screen_on_time_hours,
                        number_of_apps_installed,
                        user_behavior_class
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING observation_id
                    """,
                    (
                        user_id,
                        app_usage_time_min,
                        screen_on_time_hours,
                        PLACEHOLDER_APPS_INSTALLED,
                        user_behavior_class,
                    ),
                )
                observation = cur.fetchone()
            conn.commit()
        finally:
            conn.close()
    except Exception:
        return jsonify({"success": False, "error": "database error"}), 500

    return jsonify(
        {
            "success": True,
            "goal_completed": goal_completed,
            "message": message,
            "observation_saved": True,
            "observation_id": observation["observation_id"],
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
