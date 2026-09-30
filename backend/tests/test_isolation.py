"""User B must never read, change or delete user A's data."""

GOAL = {
    "target_role": "SDE",
    "target_company_type": "Product-based",
    "target_date": "2027-06-30",
}


def a_topic(user):
    path = user.get("/learning-paths").get_json()[0]
    return user.get(f"/learning-paths/{path['id']}/topics").get_json()[0]


def test_goals_are_isolated(user_a, user_b):
    goal_id = user_a.post("/goals", json=GOAL).get_json()["id"]

    assert user_b.get("/goals").get_json() == []
    assert user_b.patch(
        f"/goals/{goal_id}", json={"target_role": "hacked"}
    ).status_code == 404
    assert user_b.delete(f"/goals/{goal_id}").status_code == 404

    goal = user_a.get("/goals").get_json()[0]
    assert goal["target_role"] == "SDE"


def test_applications_are_isolated(user_a, user_b):
    application_id = user_a.post("/applications", json={
        "company_name": "Acme", "role": "SDE"
    }).get_json()["id"]

    assert user_b.get("/applications").get_json() == []
    assert user_b.patch(
        f"/applications/{application_id}", json={"status": "applied"}
    ).status_code == 404
    assert user_b.delete(
        f"/applications/{application_id}"
    ).status_code == 404

    assert user_a.get("/applications").get_json()[0]["status"] == "interested"


def test_progress_is_isolated(user_a, user_b):
    topic = a_topic(user_a)
    progress_id = user_a.post("/progress", json={
        "path_topic_id": topic["id"],
        "status": "completed",
        "progress_percentage": 100,
    }).get_json()["id"]

    assert user_b.get("/progress").get_json() == []
    assert user_b.patch(
        f"/progress/{progress_id}", json={"status": "not_started"}
    ).status_code == 404
    assert user_b.delete(f"/progress/{progress_id}").status_code == 404

    b_topic = a_topic(user_b)
    assert b_topic["status"] == "not_started"
    assert b_topic["progress_id"] is None

    # B marking the same topic creates B's own row, leaving A's untouched.
    user_b.post("/progress", json={
        "path_topic_id": topic["id"],
        "status": "not_started",
        "progress_percentage": 0,
    })
    assert user_a.get("/progress").get_json()[0]["status"] == "completed"


def test_profiles_are_isolated(user_a, user_b):
    user_a.patch("/profile", json={"full_name": "Alice"})
    user_b.patch("/profile", json={"full_name": "Bob"})

    assert user_a.get("/profile").get_json()["full_name"] == "Alice"
    assert user_b.get("/profile").get_json()["full_name"] == "Bob"
    assert user_b.get("/profile").get_json()["id"] == user_b.id


def test_dashboards_are_isolated(user_a, user_b):
    user_a.post("/goals", json=GOAL)
    user_a.post("/applications", json={"company_name": "A", "role": "SDE"})

    data = user_b.get("/dashboard").get_json()
    assert data["goals"]["total"] == 0
    assert data["applications"]["total"] == 0
    assert data["recent_activity"] == []


def test_deleting_account_cascades_without_orphans(user_a, user_b, db):
    topic = a_topic(user_a)
    user_a.post("/goals", json=GOAL)
    user_a.post("/applications", json={"company_name": "A", "role": "SDE"})
    user_a.post("/progress", json={
        "path_topic_id": topic["id"],
        "status": "completed",
        "progress_percentage": 100,
    })
    user_a.get("/profile")
    user_b.post("/goals", json=GOAL)

    db.execute("DELETE FROM auth.users WHERE id = %s", (user_a.id,))

    for table, column in [
        ("users", "id"),
        ("goals", "user_id"),
        ("applications", "user_id"),
        ("user_topic_progress", "user_id"),
    ]:
        count = db.execute(
            f"SELECT count(*) FROM {table} WHERE {column} = %s",
            (user_a.id,)
        ).fetchone()[0]
        assert count == 0, table

    assert len(user_b.get("/goals").get_json()) == 1


def test_deleting_a_topic_cascades_progress(user_a, db):
    with db.transaction(force_rollback=True):
        path_id = db.execute(
            "INSERT INTO learning_paths (title) VALUES ('Temp path') "
            "RETURNING id"
        ).fetchone()[0]
        topic_id = db.execute(
            "INSERT INTO path_topics (learning_path_id, title) "
            "VALUES (%s, 'Temp topic') RETURNING id",
            (path_id,)
        ).fetchone()[0]
        db.execute(
            "INSERT INTO user_topic_progress "
            "(user_id, path_topic_id, status, progress_percentage) "
            "VALUES (%s, %s, 'completed', 100)",
            (user_a.id, topic_id)
        )

        db.execute("DELETE FROM learning_paths WHERE id = %s", (path_id,))

        orphans = db.execute(
            "SELECT count(*) FROM user_topic_progress "
            "WHERE path_topic_id = %s",
            (topic_id,)
        ).fetchone()[0]
        assert orphans == 0
