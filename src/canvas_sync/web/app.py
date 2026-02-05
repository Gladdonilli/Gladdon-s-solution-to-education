"""Flask web application for Canvas Sync."""

import json
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from canvas_sync.api.auth import get_api_token, set_api_token
from canvas_sync.api.courses import get_all_courses
from canvas_sync.config import DEFAULT_CANVAS_URL, DEFAULT_VAULT_PATH
from canvas_sync.db.models import (
    get_config,
    get_db,
    get_selected_courses,
    get_sync_time_from_config,
    get_vault_path_from_config,
    set_config,
    set_selected_courses,
)
from canvas_sync.sync.assignments import sync_assignments
from canvas_sync.sync.calendar import sync_calendar_events


def create_app(testing: bool = False) -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    app.secret_key = "canvas-sync-secret-key"
    app.config["TESTING"] = testing

    @app.route("/")
    def index():
        token = get_api_token(require=False)
        if token is None:
            return redirect(url_for("setup"))
        return redirect(url_for("status"))

    @app.route("/setup", methods=["GET", "POST"])
    def setup():
        if request.method == "POST":
            canvas_url = request.form.get("canvas_url", DEFAULT_CANVAS_URL)
            api_token = request.form.get("api_token", "")

            if not api_token:
                flash("API token is required", "error")
                return render_template("setup.html", default_url=DEFAULT_CANVAS_URL)

            set_api_token(api_token)

            conn = get_db(str(DEFAULT_VAULT_PATH))
            set_config(conn, "canvas_url", canvas_url)
            set_config(conn, "vault_path", str(DEFAULT_VAULT_PATH))
            conn.close()

            flash("Setup complete!", "success")
            return redirect(url_for("courses"))

        return render_template("setup.html", default_url=DEFAULT_CANVAS_URL)

    @app.route("/courses", methods=["GET", "POST"])
    def courses():
        token = get_api_token(require=False)
        if token is None:
            return redirect(url_for("setup"))

        conn = get_db(str(DEFAULT_VAULT_PATH))
        vault_path = get_vault_path_from_config(conn)

        if request.method == "POST":
            course_ids = request.form.getlist("course_ids")
            course_ids = [int(cid) for cid in course_ids]

            all_courses = get_all_courses(vault_path)
            selected = [
                {"course_id": c.id, "course_name": c.name}
                for c in all_courses
                if c.id in course_ids
            ]
            set_selected_courses(conn, selected)
            conn.close()

            flash(f"Selected {len(selected)} courses", "success")
            return redirect(url_for("status"))

        all_courses = get_all_courses(vault_path)
        selected = get_selected_courses(conn)
        selected_ids = {c["course_id"] for c in selected}
        conn.close()

        return render_template(
            "courses.html", courses=all_courses, selected_ids=selected_ids
        )

    @app.route("/sync", methods=["GET", "POST"])
    def sync():
        token = get_api_token(require=False)
        if token is None:
            return redirect(url_for("setup"))

        conn = get_db(str(DEFAULT_VAULT_PATH))
        vault_path = get_vault_path_from_config(conn)
        selected = get_selected_courses(conn)

        if not selected:
            conn.close()
            flash("No courses selected. Go to Courses to select some.", "warning")
            return redirect(url_for("courses"))

        results = run_sync(vault_path, selected)

        set_config(conn, "last_sync_at", datetime.now().isoformat())
        set_config(conn, "last_sync_status", json.dumps(results))
        conn.close()

        return render_template("sync_results.html", results=results)

    @app.route("/status")
    def status():
        token = get_api_token(require=False)
        if token is None:
            return redirect(url_for("setup"))

        conn = get_db(str(DEFAULT_VAULT_PATH))
        last_sync_at = get_config(conn, "last_sync_at")
        last_sync_status = get_config(conn, "last_sync_status")
        conn.close()

        status_data = None
        if last_sync_status:
            status_data = json.loads(last_sync_status)

        return render_template(
            "status.html", last_sync_at=last_sync_at, status=status_data
        )

    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        token = get_api_token(require=False)
        if token is None:
            return redirect(url_for("setup"))

        conn = get_db(str(DEFAULT_VAULT_PATH))

        if request.method == "POST":
            sync_time = request.form.get("sync_time", "06:00")
            set_config(conn, "sync_time", sync_time)
            flash("Settings saved", "success")

        vault_path = get_vault_path_from_config(conn)
        canvas_url = get_config(conn, "canvas_url") or DEFAULT_CANVAS_URL
        sync_time = get_sync_time_from_config(conn)
        conn.close()

        return render_template(
            "settings.html",
            vault_path=vault_path,
            canvas_url=canvas_url,
            sync_time=sync_time,
        )

    return app


def run_sync(vault_path: str, courses: list[dict]) -> dict:
    """Run sync for given courses."""
    results = {
        "started_at": datetime.now().isoformat(),
        "assignments_synced": 0,
        "events_synced": 0,
        "skipped": 0,
        "errors": [],
        "courses_synced": [],
    }

    for course in courses:
        try:
            a_count, a_skipped = sync_assignments(course["course_id"], vault_path)
            results["assignments_synced"] += a_count
            results["skipped"] += a_skipped
            results["courses_synced"].append(course["course_name"])
        except (OSError, ValueError) as e:
            results["errors"].append(f"Assignments for {course['course_name']}: {e}")

    try:
        course_ids = [c["course_id"] for c in courses]
        e_count, e_skipped = sync_calendar_events(course_ids, vault_path)
        results["events_synced"] += e_count
        results["skipped"] += e_skipped
    except (OSError, ValueError) as e:
        results["errors"].append(f"Calendar events: {e}")

    results["completed_at"] = datetime.now().isoformat()
    return results
