#!/usr/bin/env python3
"""Run the example Flask API."""

from example_api.app import app

if __name__ == "__main__":
    app.run(debug=True, port=5000)
