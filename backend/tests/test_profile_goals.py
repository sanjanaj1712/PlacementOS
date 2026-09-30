import uuid

from conftest import ApiUser

GOAL = {
    "target_role": "Software Engineer",
    "target_company_type": "Product-based",
    "target_date": "2027-06-30",
}


def test_profile_created_on_first_access(user_a, db):
    db.execute("DELETE FROM users WHERE id = %s", (user_a.id,))

    response = user_a.get("/profile")
    assert response.status_code == 200
    assert response.get_json()["id"] == user_a.id
    assert response.get_json()["email"] == user_a.email


def test_profile_update_round_trip(user_a):
    response = user_a.patch("/profile", json={
        "full_name": "Asha Rao",
        "education_level": "B.Tech",
        "college_name": "PES University",
        "graduation_year": 2027,
        "preferred_roles": ["SDE", " Data Engineer ", ""],
    })
    assert response.status_code == 200

    profile = user_a.get("/profile").get_json()
    assert profile["full_name"] == "Asha Rao"
    assert profile["graduation_year"] == 2027
    assert profile["preferred_roles"] == ["SDE", "Data Engineer"]


def test_profile_update_works_without_existing_row(user_a, db):
    db.execute("DELETE FROM users WHERE id = %s", (user_a.id,))
    assert user_a.patch("/profile", json={"full_name": "A"}).status_code == 200


def test_token_for_deleted_account_does_not_500(client, db):
    ghost = ApiUser(client, str(uuid.uuid4()), "ghost@example.com")
    assert ghost.get("/profile").status_code == 409
    assert ghost.post("/goals", json=GOAL).status_code == 409


def test_goal_defaults(user_a):
    assert user_a.post("/goals", json=GOAL).status_code == 201

    goal = user_a.get("/goals").get_json()[0]
    assert goal["status"] == "not_started"
    assert goal["progress_percentage"] == 0
    assert goal["target_companies"] == []


def test_goal_edit_status_progress_and_companies(user_a):
    goal_id = user_a.post("/goals", json={
        **GOAL,
        "target_companies": ["Google", "Microsoft"],
    }).get_json()["id"]

    response = user_a.patch(f"/goals/{goal_id}", json={
        "status": "in_progress",
        "progress_percentage": 40,
        "target_companies": ["Google", "Amazon"],
        "target_date": "2027-08-01",
    })
    assert response.status_code == 200

    goal = user_a.get("/goals").get_json()[0]
    assert goal["status"] == "in_progress"
    assert goal["progress_percentage"] == 40
    assert goal["target_companies"] == ["Google", "Amazon"]
    assert goal["target_date"] == "2027-08-01"


def test_goal_invalid_status_and_progress(user_a):
    goal_id = user_a.post("/goals", json=GOAL).get_json()["id"]

    assert user_a.patch(
        f"/goals/{goal_id}", json={"status": "done"}
    ).status_code == 400
    assert user_a.patch(
        f"/goals/{goal_id}", json={"progress_percentage": 150}
    ).status_code == 400


def test_goal_delete(user_a):
    goal_id = user_a.post("/goals", json=GOAL).get_json()["id"]

    assert user_a.delete(f"/goals/{goal_id}").status_code == 200
    assert user_a.get("/goals").get_json() == []
    assert user_a.delete(f"/goals/{goal_id}").status_code == 404
