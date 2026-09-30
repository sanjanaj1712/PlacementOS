import pytest

import app as app_module


@pytest.mark.parametrize("method,path", [
    ("PATCH", "/goals/not-a-uuid"),
    ("DELETE", "/goals/not-a-uuid"),
    ("PATCH", "/progress/not-a-uuid"),
    ("DELETE", "/progress/not-a-uuid"),
    ("PATCH", "/applications/not-a-uuid"),
    ("DELETE", "/applications/not-a-uuid"),
])
def test_malformed_ids_return_404(user_a, method, path):
    response = user_a.request(method, path, json={"status": "applied"})
    assert response.status_code == 404


def test_malformed_learning_path_id_does_not_leak_database_error(user_a):
    response = user_a.get("/learning-paths/abc/topics")
    assert response.status_code in (400, 404)
    assert "syntax" not in response.get_data(as_text=True)


def test_unexpected_errors_are_not_leaked(user_a, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("password=hunter2 host=db.internal")

    monkeypatch.setattr(app_module.psycopg, "connect", boom)

    response = user_a.get("/goals")
    assert response.status_code == 500
    assert response.get_json() == {"error": "Internal server error"}


def test_login_failure_does_not_leak_details(client, monkeypatch):
    def fail(credentials):
        raise RuntimeError("upstream detail that should stay private")

    monkeypatch.setattr(
        app_module.supabase.auth,
        "sign_in_with_password",
        fail
    )

    response = client.post(
        "/login",
        json={"email": "a@example.com", "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid email or password"}


def test_dates_are_serialized_as_iso_strings(user_a):
    created = user_a.post("/goals", json={
        "target_role": "SDE",
        "target_company_type": "Product-based",
        "target_date": "2027-06-30",
    })
    assert created.status_code == 201

    goal = user_a.get("/goals").get_json()[0]
    assert goal["target_date"] == "2027-06-30"
    assert goal["created_at"].startswith("20")
    assert "T" in goal["created_at"]
