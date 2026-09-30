import pytest

VALID_GOAL = {
    "target_role": "Software Engineer",
    "target_company_type": "Product-based",
    "target_date": "2027-06-30",
}

VALID_APPLICATION = {
    "company_name": "Acme",
    "role": "SDE Intern",
    "status": "applied",
}


def create(user, path, body):
    response = user.post(path, json=body)
    assert response.status_code == 201, response.get_json()
    return response.get_json()["id"]


@pytest.mark.parametrize("path", [
    "/goals", "/applications", "/progress"
])
def test_create_requires_json_object(user_a, path):
    assert user_a.post(path, json=["not", "an", "object"]).status_code == 400
    assert user_a.post(path, data="plain text").status_code == 400


@pytest.mark.parametrize("override,bad_field", [
    ({"target_role": ""}, "target_role"),
    ({"target_role": "   "}, "target_role"),
    ({"target_role": 123}, "target_role"),
    ({"target_role": "x" * 101}, "target_role"),
    ({"target_company_type": None}, "target_company_type"),
    ({"target_date": "banana"}, "target_date"),
    ({"target_date": "2027-02-30"}, "target_date"),
    ({"target_date": "1800-01-01"}, "target_date"),
])
def test_goal_create_validation(user_a, override, bad_field):
    response = user_a.post("/goals", json={**VALID_GOAL, **override})
    assert response.status_code == 400
    assert bad_field in response.get_json()["fields"]


def test_goal_create_strips_whitespace(user_a):
    create(user_a, "/goals", {**VALID_GOAL, "target_role": "  SDE  "})
    assert user_a.get("/goals").get_json()[0]["target_role"] == "SDE"


@pytest.mark.parametrize("body", [
    {"target_role": None},
    {"target_role": ""},
    {"target_date": "not-a-date"},
])
def test_goal_update_cannot_null_or_corrupt_fields(user_a, body):
    goal_id = create(user_a, "/goals", VALID_GOAL)
    response = user_a.patch(f"/goals/{goal_id}", json=body)
    assert response.status_code == 400


def test_goal_update_rejects_unknown_only_fields(user_a):
    goal_id = create(user_a, "/goals", VALID_GOAL)
    response = user_a.patch(f"/goals/{goal_id}", json={"user_id": "x"})
    assert response.status_code == 400


@pytest.mark.parametrize("body,bad_field", [
    ({"graduation_year": "2026"}, "graduation_year"),
    ({"graduation_year": 3000}, "graduation_year"),
    ({"graduation_year": True}, "graduation_year"),
    ({"preferred_roles": "SDE"}, "preferred_roles"),
    ({"preferred_roles": [1, 2]}, "preferred_roles"),
    ({"full_name": "x" * 101}, "full_name"),
])
def test_profile_update_validation(user_a, body, bad_field):
    response = user_a.patch("/profile", json=body)
    assert response.status_code == 400
    assert bad_field in response.get_json()["fields"]


@pytest.mark.parametrize("override,bad_field", [
    ({"company_name": ""}, "company_name"),
    ({"role": None}, "role"),
    ({"status": "hired"}, "status"),
    ({"job_url": "javascript:alert(1)"}, "job_url"),
    ({"job_url": "not a url"}, "job_url"),
    ({"application_date": "nope"}, "application_date"),
    ({"interview_date": 20270101}, "interview_date"),
    ({"notes": "x" * 5001}, "notes"),
])
def test_application_create_validation(user_a, override, bad_field):
    response = user_a.post(
        "/applications",
        json={**VALID_APPLICATION, **override}
    )
    assert response.status_code == 400
    assert bad_field in response.get_json()["fields"]


def test_application_optional_fields_can_be_cleared(user_a):
    application_id = create(user_a, "/applications", {
        **VALID_APPLICATION,
        "location": "Bengaluru",
        "job_url": "https://acme.example/jobs/1",
    })

    response = user_a.patch(
        f"/applications/{application_id}",
        json={"location": "", "job_url": None}
    )
    assert response.status_code == 200

    application = user_a.get("/applications").get_json()[0]
    assert application["location"] is None
    assert application["job_url"] is None


@pytest.mark.parametrize("body", [
    {"company_name": None},
    {"role": "  "},
    {"status": None},
])
def test_application_update_cannot_null_required_fields(user_a, body):
    application_id = create(user_a, "/applications", VALID_APPLICATION)
    response = user_a.patch(f"/applications/{application_id}", json=body)
    assert response.status_code == 400


@pytest.mark.parametrize("override,bad_field", [
    ({"path_topic_id": "abc"}, "path_topic_id"),
    ({"path_topic_id": 0}, "path_topic_id"),
    ({"status": "done"}, "status"),
    ({"progress_percentage": 101}, "progress_percentage"),
    ({"progress_percentage": -1}, "progress_percentage"),
    ({"progress_percentage": "50"}, "progress_percentage"),
    ({"progress_percentage": True}, "progress_percentage"),
])
def test_progress_create_validation(user_a, override, bad_field):
    body = {
        "path_topic_id": 1,
        "status": "in_progress",
        "progress_percentage": 50,
        **override,
    }
    response = user_a.post("/progress", json=body)
    assert response.status_code == 400
    assert bad_field in response.get_json()["fields"]
