import pytest

import app as app_module


def create_application(user, **fields):
    body = {"company_name": "Acme", "role": "SDE", **fields}
    response = user.post("/applications", json=body)
    assert response.status_code == 201, response.get_json()
    return response.get_json()["id"]


def set_status(user, application_id, status):
    return user.patch(
        f"/applications/{application_id}",
        json={"status": status}
    )


def test_new_application_defaults_to_interested(user_a):
    create_application(user_a)
    assert user_a.get("/applications").get_json()[0]["status"] == "interested"


def test_full_pipeline_to_offer(user_a):
    application_id = create_application(user_a)

    for status in ["applied", "oa", "interview", "offer"]:
        response = set_status(user_a, application_id, status)
        assert response.status_code == 200, (status, response.get_json())

    assert user_a.get("/applications").get_json()[0]["status"] == "offer"


def test_applied_can_skip_oa(user_a):
    application_id = create_application(user_a, status="applied")
    assert set_status(user_a, application_id, "interview").status_code == 200


@pytest.mark.parametrize("start", ["interested", "applied", "oa", "interview"])
def test_active_stages_can_be_rejected(user_a, start):
    application_id = create_application(user_a, status=start)
    assert set_status(user_a, application_id, "rejected").status_code == 200


def all_transitions():
    statuses = app_module.ALLOWED_APPLICATION_STATUSES
    allowed = app_module.APPLICATION_STATUS_TRANSITIONS

    return [
        (current, new)
        for current in statuses
        for new in statuses
        if new != current and new not in allowed[current]
    ]


@pytest.mark.parametrize("current,new", all_transitions())
def test_invalid_transitions_are_rejected(user_a, current, new):
    application_id = create_application(user_a, status=current)

    response = set_status(user_a, application_id, new)
    assert response.status_code == 409
    assert user_a.get("/applications").get_json()[0]["status"] == current


def test_invalid_transition_does_not_apply_other_fields(user_a):
    application_id = create_application(user_a, status="rejected")

    response = user_a.patch(
        f"/applications/{application_id}",
        json={"status": "offer", "notes": "should not be saved"}
    )
    assert response.status_code == 409
    assert user_a.get("/applications").get_json()[0]["notes"] is None


def test_same_status_update_is_allowed(user_a):
    application_id = create_application(user_a, status="offer")

    response = user_a.patch(
        f"/applications/{application_id}",
        json={"status": "offer", "notes": "Joining in July"}
    )
    assert response.status_code == 200


def test_application_details_round_trip(user_a):
    application_id = create_application(
        user_a,
        company_type="Product-based",
        application_date="2026-09-01",
        job_url="https://acme.example/careers/42",
        location="Bengaluru",
        notes="Referral from alumni",
        interview_date="2026-10-15",
    )

    response = user_a.patch(
        f"/applications/{application_id}",
        json={"role": "SDE 1", "location": "Remote"}
    )
    assert response.status_code == 200

    application = user_a.get("/applications").get_json()[0]
    assert application["role"] == "SDE 1"
    assert application["location"] == "Remote"
    assert application["job_url"] == "https://acme.example/careers/42"
    assert application["application_date"] == "2026-09-01"
    assert application["interview_date"] == "2026-10-15"


def test_delete_application(user_a):
    application_id = create_application(user_a)

    assert user_a.delete(f"/applications/{application_id}").status_code == 200
    assert user_a.get("/applications").get_json() == []
    assert user_a.delete(f"/applications/{application_id}").status_code == 404
