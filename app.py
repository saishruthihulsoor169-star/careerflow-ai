from flask import Flask, render_template, jsonify, request
import json
from pathlib import Path

app = Flask(__name__)

DATA_FILE = Path("data/sample_applications.json")


def load_dataset():
    """Load the application dataset from the JSON file."""
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def validate_dataset(data):
    """Validate jobs, drafts, IDs, and relationships."""
    errors = []

    if not isinstance(data, dict):
        return ["Dataset must be a JSON object."]

    jobs = data.get("jobs", [])
    drafts = data.get("drafts", [])

    if not isinstance(jobs, list):
        errors.append("'jobs' must be a list.")

    if not isinstance(drafts, list):
        errors.append("'drafts' must be a list.")

    if errors:
        return errors

    job_ids = set()
    draft_ids = set()

    # Validate jobs
    for job in jobs:

        if not isinstance(job, dict):
            errors.append("Each job must be an object.")
            continue

        job_id = job.get("id")

        if not job_id:
            errors.append("Job is missing an id.")
            continue

        if job_id in job_ids:
            errors.append(f"Duplicate job id: {job_id}")

        job_ids.add(job_id)

        required_fields = [
            "from",
            "to",
            "type",
            "description"
        ]

        for field in required_fields:
            if not job.get(field):
                errors.append(
                    f"Job {job_id} is missing '{field}'."
                )

    # Validate drafts
    for draft in drafts:

        if not isinstance(draft, dict):
            errors.append("Each draft must be an object.")
            continue

        draft_id = draft.get("id")
        job_id = draft.get("jobId")

        if not draft_id:
            errors.append("Draft is missing an id.")
        elif draft_id in draft_ids:
            errors.append(
                f"Duplicate draft id: {draft_id}"
            )
        else:
            draft_ids.add(draft_id)

        if not job_id:
            errors.append(
                f"Draft {draft_id or 'unknown'} is missing jobId."
            )

        elif job_id not in job_ids:
            errors.append(
                f"Draft {draft_id or 'unknown'} "
                f"references unknown job {job_id}."
            )

        if not draft.get("type"):
            errors.append(
                f"Draft {draft_id or 'unknown'} is missing type."
            )

        if not draft.get("contents"):
            errors.append(
                f"Draft {draft_id or 'unknown'} "
                f"is missing contents."
            )

    return errors


def build_applications(data):
    """Convert jobs and drafts into linked application records."""

    jobs = data.get("jobs", [])
    drafts = data.get("drafts", [])

    applications = []

    for job in jobs:

        linked_drafts = [
            draft
            for draft in drafts
            if draft.get("jobId") == job.get("id")
        ]

        applications.append({
            "id": job["id"],
            "description": job["description"],
            "type": job["type"],
            "from": job["from"],
            "to": job["to"],
            "status": "Applied",
            "drafts": linked_drafts
        })

    return applications


@app.route("/")
def home():
    """Render the CareerFlow dashboard."""
    return render_template("index.html")


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "CareerFlow AI"
    })


@app.route("/api/import", methods=["POST"])
def import_applications():
    """Load, validate, and process application data."""

    try:

        data = request.get_json(silent=True)

        # If no JSON body is provided,
        # use the sample dataset.
        if data is None:
            data = load_dataset()

        errors = validate_dataset(data)

        if errors:
            return jsonify({
                "success": False,
                "errors": errors
            }), 400

        applications = build_applications(data)

        return jsonify({
            "success": True,
            "count": len(applications),
            "applications": applications
        })

    except FileNotFoundError:

        return jsonify({
            "success": False,
            "error": "Application dataset not found."
        }), 500

    except json.JSONDecodeError:

        return jsonify({
            "success": False,
            "error": "Application dataset contains invalid JSON."
        }), 500

    except Exception:

        return jsonify({
            "success": False,
            "error": "Unable to process application dataset."
        }), 500


@app.route("/api/applications/<job_id>", methods=["GET"])
def get_application(job_id):
    """Return one application and its linked drafts."""

    try:

        data = load_dataset()

        errors = validate_dataset(data)

        if errors:
            return jsonify({
                "success": False,
                "errors": errors
            }), 400

        applications = build_applications(data)

        application = next(
            (
                app
                for app in applications
                if app.get("id") == job_id
            ),
            None
        )

        if application is None:
            return jsonify({
                "success": False,
                "error": "Application not found."
            }), 404

        return jsonify({
            "success": True,
            "application": application
        })

    except FileNotFoundError:

        return jsonify({
            "success": False,
            "error": "Application dataset not found."
        }), 500

    except Exception:

        return jsonify({
            "success": False,
            "error": "Unable to retrieve application."
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=True
    )
