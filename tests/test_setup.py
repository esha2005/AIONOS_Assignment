import os
import json

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_policies_file_exists():
    path = os.path.join(DATA_DIR, "policies.json")
    assert os.path.isfile(path), "policies.json must exist in data/"


def test_policies_loadable():
    path = os.path.join(DATA_DIR, "policies.json")
    data = _load_json(path)
    assert isinstance(data, list), "policies.json must contain a JSON list"
    assert len(data) > 0, "policies.json must contain at least one policy"
    for entry in data:
        assert "policy_id" in entry
        assert "title" in entry
        assert "content" in entry


def test_employee_requests_file_exists():
    path = os.path.join(DATA_DIR, "employee_requests.json")
    assert os.path.isfile(path), "employee_requests.json must exist in data/"


def test_employee_requests_loadable():
    path = os.path.join(DATA_DIR, "employee_requests.json")
    data = _load_json(path)
    assert isinstance(data, list), "employee_requests.json must contain a JSON list"
    assert len(data) > 0, "employee_requests.json must contain at least one request"
    for entry in data:
        assert "request_id" in entry
        assert "employee_name" in entry
        assert "employee_email" in entry
        assert "request" in entry


def test_tickets_file_exists():
    path = os.path.join(DATA_DIR, "tickets.json")
    assert os.path.isfile(path), "tickets.json must exist in data/"


def test_tickets_loadable():
    path = os.path.join(DATA_DIR, "tickets.json")
    data = _load_json(path)
    assert isinstance(data, list), "tickets.json must contain a JSON list"
    assert len(data) > 0, "tickets.json must contain at least one ticket"
    for entry in data:
        assert "ticket_id" in entry
        assert "employee" in entry
        assert "issue_summary" in entry
        assert "status" in entry


def test_fastapi_app_importable():
    from backend.main import app
    assert app is not None, "FastAPI app must be importable from backend.main"
