import pytest


@pytest.fixture
def topic_id(user_a):
    path = user_a.get("/learning-paths").get_json()[0]
    return user_a.get(f"/learning-paths/{path['id']}/topics").get_json()[0]["id"]


def mark(user, topic_id, status="completed", percentage=100):
    return user.post("/progress", json={
        "path_topic_id": topic_id,
        "status": status,
        "progress_percentage": percentage,
    })


def test_marking_twice_updates_single_row(user_a, topic_id, db):
    first = mark(user_a, topic_id)
    assert first.status_code == 201

    second = mark(user_a, topic_id, "not_started", 0)
    assert second.status_code == 200
    assert second.get_json()["id"] == first.get_json()["id"]

    count = db.execute(
        "SELECT count(*) FROM user_topic_progress WHERE user_id = %s",
        (user_a.id,)
    ).fetchone()[0]
    assert count == 1

    record = user_a.get("/progress").get_json()[0]
    assert record["status"] == "not_started"
    assert record["progress_percentage"] == 0


def test_unknown_topic_returns_404(user_a):
    assert mark(user_a, 999999999).status_code == 404


@pytest.mark.parametrize("status,percentage", [
    ("not_started", 100),
    ("completed", 50),
    ("in_progress", 0),
    ("in_progress", 100),
])
def test_inconsistent_status_and_percentage_rejected(
    user_a, topic_id, status, percentage
):
    assert mark(user_a, topic_id, status, percentage).status_code == 400


@pytest.mark.parametrize("body,expected", [
    ({"progress_percentage": 100}, ("completed", 100)),
    ({"progress_percentage": 40}, ("in_progress", 40)),
    ({"status": "not_started"}, ("not_started", 0)),
    ({"status": "completed"}, ("completed", 100)),
])
def test_patch_derives_missing_field(user_a, topic_id, body, expected):
    progress_id = mark(user_a, topic_id, "in_progress", 10).get_json()["id"]

    response = user_a.patch(f"/progress/{progress_id}", json=body)
    assert response.status_code == 200

    record = user_a.get("/progress").get_json()[0]
    assert (record["status"], record["progress_percentage"]) == expected


def test_progress_survives_new_connection(user_a, topic_id, db):
    mark(user_a, topic_id)
    row = db.execute(
        "SELECT status FROM user_topic_progress WHERE user_id = %s",
        (user_a.id,)
    ).fetchone()
    assert row == ("completed",)


def test_delete_progress(user_a, topic_id):
    progress_id = mark(user_a, topic_id).get_json()["id"]
    assert user_a.delete(f"/progress/{progress_id}").status_code == 200
    assert user_a.get("/progress").get_json() == []
