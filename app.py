from flask import Flask, render_template, jsonify, request
import json
from pathlib import Path

app = Flask(__name__)

DATA_FILE = Path("data/sample_applications.json")


def load_dataset():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def validate_dataset(data):
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

    for job in jobs:
        if "id" not in job:
            errors.append("Job is missing an id.")
            continue

        if job["id"] in job_ids:
            errors.append(f"Duplicate job id: {job['id']}")

        job_ids.add(job["id"])

        for field in ["from", "to", "type", "description"]:
            if not job.get(field):
                errors.append(
                    f"Job {job['id']} is missing '{field}'."
                )

    for draft in drafts:
        if not draft.get("id"):
            errors.append("Draft is missing an id.")

        if not draft.get("jobId"):
            errors.append(
                f"Draft {draft.get('id', 'unknown')} is missing jobId."
            )

        elif draft["jobId"] not in job_ids:
            errors.append(
                f"Draft {draft.get('id', 'unknown')} "
                f"references unknown job {draft['jobId']}."
            )

    return errors


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "CareerFlow AI"
    })


@app.route("/api/import", methods=["POST"])
def import_applications():
    try:
        data = request.get_json(silent=True)

        if data is None:
            data = load_dataset()

        errors = validate_dataset(data)

        if errors:
            return jsonify({
                "success": False,
                "errors": errors
            }), 400

        jobs = data.get("jobs", [])
        drafts = data.get("drafts", [])

        applications = []

        for job in jobs:
            linked_drafts = [
                draft for draft in drafts
                if draft.get("jobId") == job["id"]
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

        return jsonify({
            "success": True,
            "count": len(applications),
            "applications": applications
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "error": "Unable to process application dataset."
        }), 500

@app.route("/api/applications/<job_id>", methods=["GET"])
def get_application(job_id):
    try:
        data = load_dataset()

        errors = validate_dataset(data)

        if errors:
            return jsonify({
                "success": False,
                "errors": errors
            }), 400

        jobs = data.get("jobs", [])
        drafts = data.get("drafts", [])

        job = next(
            (job for job in jobs if job.get("id") == job_id),
            None
        )

        if job is None:
            return jsonify({
                "success": False,
                "error": "Application not found."
            }), 404

        linked_drafts = [
            draft for draft in drafts
            if draft.get("jobId") == job_id
        ]

        application = {
            "id": job["id"],
            "description": job["description"],
            "type": job["type"],
            "from": job["from"],
            "to": job["to"],
            "status": "Applied",
            "drafts": linked_drafts
        }

        return jsonify({
            "success": True,
            "application": application
        })

    except Exception:
        return jsonify({
            "success": False,
            "error": "Unable to retrieve application."
        }), 500
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
