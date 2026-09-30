import psycopg
import pytest

GOAL = {
    "target_role": "SDE",
    "target_company_type": "Product-based",
    "target_date": "2027-06-30",
}


@pytest.fixture
def count_queries(monkeypatch):
    counter = {"count": 0}
    original = psycopg.Cursor.execute

    def counting_execute(self, *args, **kwargs):
        counter["count"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(psycopg.Cursor, "execute", counting_execute)
    return counter


def all_topic_ids(user):
    ids = []
    for path in user.get("/learning-paths").get_json():
        topics = user.get(f"/learning-paths/{path['id']}/topics").get_json()
        ids.extend(topic["id"] for topic in topics)
    return ids


def populate(user, goals, applications, completed_topics, in_progress_topics):
    for index in range(goals):
        user.post("/goals", json={**GOAL, "target_role": f"Role {index}"})

    statuses = ["interested", "applied", "oa", "interview", "offer", "rejected"]
    for index in range(applications):
        user.post("/applications", json={
            "company_name": f"Company {index}",
            "role": "SDE",
            "status": statuses[index % len(statuses)],
        })

    topic_ids = all_topic_ids(user)
    for topic_id in topic_ids[:completed_topics]:
        user.post("/progress", json={
            "path_topic_id": topic_id,
            "status": "completed",
            "progress_percentage": 100,
        })
    for topic_id in topic_ids[
        completed_topics:completed_topics + in_progress_topics
    ]:
        user.post("/progress", json={
            "path_topic_id": topic_id,
            "status": "in_progress",
            "progress_percentage": 50,
        })


def test_learning_paths_include_progress_summary(user_a):
    paths = user_a.get("/learning-paths").get_json()
    assert [path["title"] for path in paths] == [
        "Data Structures & Algorithms",
        "Operating Systems",
        "Computer Networks",
        "DBMS",
    ]

    first = paths[0]
    topics = user_a.get(f"/learning-paths/{first['id']}/topics").get_json()
    assert first["topic_count"] == len(topics)
    assert first["completed_count"] == 0

    for topic in topics[:2]:
        user_a.post("/progress", json={
            "path_topic_id": topic["id"],
            "status": "completed",
            "progress_percentage": 100,
        })

    first = user_a.get("/learning-paths").get_json()[0]
    assert first["completed_count"] == 2
    assert first["progress_percentage"] == round(200 / len(topics))


def test_topics_include_subtopics_and_progress_id(user_a):
    path = user_a.get("/learning-paths").get_json()[0]
    topics = user_a.get(f"/learning-paths/{path['id']}/topics").get_json()

    top_level = [topic for topic in topics if topic["parent_topic_id"] is None]
    subtopics = [topic for topic in topics if topic["parent_topic_id"]]
    assert top_level and subtopics
    assert {sub["parent_topic_id"] for sub in subtopics} <= {
        topic["id"] for topic in top_level
    }

    progress_id = user_a.post("/progress", json={
        "path_topic_id": topics[0]["id"],
        "status": "completed",
        "progress_percentage": 100,
    }).get_json()["id"]

    topics = user_a.get(f"/learning-paths/{path['id']}/topics").get_json()
    assert topics[0]["progress_id"] == progress_id
    assert topics[0]["status"] == "completed"


def test_unknown_learning_path_returns_404(user_a):
    assert user_a.get("/learning-paths/999999/topics").status_code == 404
    assert user_a.get("/learning-paths/abc/topics").status_code == 404


def test_dashboard_for_new_user(user_a):
    data = user_a.get("/dashboard").get_json()
    assert data["goals"]["total"] == 0
    assert data["goals"]["current"] is None
    assert data["applications"]["total"] == 0
    assert data["topics"]["completed"] == 0
    assert data["topics"]["progress_percentage"] == 0
    assert data["recent_activity"] == []


def test_dashboard_matches_database(user_a, user_b, db):
    populate(user_a, goals=3, applications=8, completed_topics=5,
             in_progress_topics=2)
    populate(user_b, goals=1, applications=2, completed_topics=1,
             in_progress_topics=0)

    data = user_a.get("/dashboard").get_json()

    def scalar(sql, *params):
        return db.execute(sql, params).fetchone()[0]

    assert data["goals"]["total"] == scalar(
        "SELECT count(*) FROM goals WHERE user_id = %s", user_a.id
    ) == 3

    assert data["applications"]["total"] == scalar(
        "SELECT count(*) FROM applications WHERE user_id = %s", user_a.id
    ) == 8

    for status, count in data["applications"]["by_status"].items():
        assert count == scalar(
            "SELECT count(*) FROM applications "
            "WHERE user_id = %s AND status = %s",
            user_a.id, status
        )

    assert data["applications"]["active"] == scalar(
        "SELECT count(*) FROM applications WHERE user_id = %s "
        "AND status NOT IN ('offer', 'rejected')",
        user_a.id
    )

    assert data["topics"]["total"] == scalar("SELECT count(*) FROM path_topics")
    assert data["topics"]["completed"] == scalar(
        "SELECT count(*) FROM user_topic_progress "
        "WHERE user_id = %s AND status = 'completed'",
        user_a.id
    ) == 5
    assert data["topics"]["in_progress"] == 2
    assert data["topics"]["progress_percentage"] == round(
        5 * 100 / data["topics"]["total"]
    )

    assert len(data["recent_activity"]) == 10
    assert all(
        item["type"] in ("goal", "application", "topic")
        for item in data["recent_activity"]
    )


def test_dashboard_current_goal_prefers_active_goals(user_a):
    achieved = user_a.post("/goals", json={
        **GOAL, "target_date": "2026-01-01"
    }).get_json()["id"]
    user_a.patch(f"/goals/{achieved}", json={"status": "achieved"})
    active = user_a.post("/goals", json=GOAL).get_json()["id"]

    current = user_a.get("/dashboard").get_json()["goals"]["current"]
    assert current["id"] == active


@pytest.mark.parametrize("path", ["/dashboard", "/learning-paths"])
def test_query_count_does_not_grow_with_data(user_a, count_queries, path):
    user_a.get(path)
    baseline = count_queries["count"]

    populate(user_a, goals=5, applications=12, completed_topics=10,
             in_progress_topics=5)

    count_queries["count"] = 0
    user_a.get(path)
    assert count_queries["count"] == baseline
