"""Example Flask API for testing aitest-guard."""

from flask import Flask, jsonify, request

from example_api.calculator import calculate_total
from example_api.validator import validate_email

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/total", methods=["POST"])
def total():
    """Calculate total from request body items."""
    data = request.get_json() or {}
    items = data.get("items", [])
    result = calculate_total(items)
    return jsonify({"total": result})


@app.route("/validate-email", methods=["POST"])
def validate_email_route():
    """Validate email from request body."""
    data = request.get_json() or {}
    email = data.get("email", "")
    valid = validate_email(email)
    return jsonify({"valid": valid})
