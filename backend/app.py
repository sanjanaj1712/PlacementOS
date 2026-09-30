from collections import namedtuple
from datetime import date, datetime
from flask import Flask, jsonify, request
from flask.json.provider import DefaultJSONProvider
from dotenv import load_dotenv
from flask_cors import CORS
import os
import uuid
import jwt
import psycopg
from supabase import create_client


class JSONProvider(DefaultJSONProvider):
    """Serialize dates as ISO 8601 so the frontend can parse them."""

    @staticmethod
    def default(value):
        if isinstance(value, (datetime, date)):
            return value.isoformat()

        return DefaultJSONProvider.default(value)


app = Flask(__name__)
app.json = JSONProvider(app)


CORS(
    app,
    origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    supports_credentials=True
)

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL or SUPABASE_KEY is not set")


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# Supabase signs access tokens either with the legacy shared secret (HS256)
# or with asymmetric signing keys published at the project's JWKS endpoint.
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET") or None
SUPABASE_JWT_ISSUER = f"{SUPABASE_URL.rstrip('/')}/auth/v1"
SUPABASE_JWT_AUDIENCE = "authenticated"
ASYMMETRIC_JWT_ALGORITHMS = ["ES256", "RS256"]

jwks_client = jwt.PyJWKClient(
    f"{SUPABASE_JWT_ISSUER}/.well-known/jwks.json",
    cache_keys=True,
    lifespan=600
)

AuthUser = namedtuple("AuthUser", ["id", "email"])


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def verify_access_token(token):
    """Verify a Supabase access token locally and return its claims."""
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")

        if algorithm == "HS256" and SUPABASE_JWT_SECRET:
            key = SUPABASE_JWT_SECRET
        elif algorithm in ASYMMETRIC_JWT_ALGORITHMS:
            key = jwks_client.get_signing_key_from_jwt(token).key
        else:
            return None

        claims = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=SUPABASE_JWT_AUDIENCE,
            issuer=SUPABASE_JWT_ISSUER,
            options={"require": ["exp", "sub", "aud", "iss"]}
        )
    except (jwt.InvalidTokenError, jwt.PyJWKClientError) as e:
        app.logger.info("Rejected access token: %s", e)
        return None

    if claims.get("role") != "authenticated":
        return None

    try:
        uuid.UUID(claims["sub"])
    except (ValueError, TypeError, AttributeError):
        return None

    return claims


def get_current_user():
    """Validate the Supabase access token and return the user."""
    authorization = request.headers.get("Authorization")

    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()

    if not token:
        return None

    claims = verify_access_token(token)

    if not claims:
        return None

    return AuthUser(id=claims["sub"], email=claims.get("email"))



def require_user():
    """Return the authenticated user or a 401 response."""
    user = get_current_user()

    if not user:
        return None, jsonify({
            "error": "Authentication required"
        }), 401

    return user, None, None


def get_request_data():
    """Safely get a JSON request body."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None

    return data


def server_error(error):
    """Log an unexpected error and return a response without internals."""
    if isinstance(error, psycopg.DataError):
        return jsonify({
            "error": "Invalid input"
        }), 400

    app.logger.exception("Unhandled error: %s", error)

    return jsonify({
        "error": "Internal server error"
    }), 500


def is_valid_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def not_found(resource):
    return jsonify({
        "error": f"{resource} not found"
    }), 404


def rows_to_dicts(cursor, rows):
    """Convert database rows to dictionaries."""
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


ALLOWED_APPLICATION_STATUSES = [
    "saved",
    "applied",
    "interview",
    "offer",
    "rejected"
]

ALLOWED_PROGRESS_STATUSES = [
    "not_started",
    "in_progress",
    "completed"
]


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.route("/")
def home():
    return "Hello from PlacementOS"


# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------

@app.route("/login", methods=["POST"])
def login():
    data = get_request_data()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "error": "email and password are required"
        }), 400

    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if not response.session:
            return jsonify({
                "error": "Login failed"
            }), 401

        return jsonify({
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }), 200

    except Exception as e:
        app.logger.info("Login failed: %s", e)
        return jsonify({
            "error": "Invalid email or password"
        }), 401


@app.route("/me", methods=["GET"])
def me():
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    return jsonify({
        "user_id": user.id,
        "email": user.email
    }), 200


# ---------------------------------------------------------
# Goals
# ---------------------------------------------------------

@app.route("/goals", methods=["GET"])
def get_goals():
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM goals
                    WHERE user_id = %s
                    ORDER BY created_at DESC;
                    """,
                    (user.id,)
                )

                goals = rows_to_dicts(cursor, cursor.fetchall())

        return jsonify(goals), 200

    except Exception as e:
        return server_error(e)


@app.route("/goals", methods=["POST"])
def create_goal():
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    data = get_request_data()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    required_fields = [
        "target_role",
        "target_company_type",
        "target_date"
    ]

    missing_fields = [
        field for field in required_fields
        if not data.get(field)
    ]

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "fields": missing_fields
        }), 400

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO goals
                    (
                        user_id,
                        target_role,
                        target_company_type,
                        target_date
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        user.id,
                        data["target_role"],
                        data["target_company_type"],
                        data["target_date"]
                    )
                )

                goal_id = cursor.fetchone()[0]
                connection.commit()

        return jsonify({
            "status": "goal created",
            "id": str(goal_id)
        }), 201

    except Exception as e:
        return server_error(e)


@app.route("/goals/<goal_id>", methods=["PATCH"])
def update_goal(goal_id):
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    if not is_valid_uuid(goal_id):
        return not_found("Goal")

    data = get_request_data()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    allowed_fields = [
        "target_role",
        "target_company_type",
        "target_date"
    ]

    updates = {
        field: data[field]
        for field in allowed_fields
        if field in data
    }

    if not updates:
        return jsonify({
            "error": "No fields provided for update"
        }), 400

    set_clause = ", ".join(
        f"{field} = %s"
        for field in updates
    )

    values = list(updates.values())
    values.extend([goal_id, user.id])

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE goals
                    SET
                        {set_clause},
                        updated_at = NOW()
                    WHERE id = %s
                    AND user_id = %s;
                    """,
                    values
                )

                updated = cursor.rowcount
                connection.commit()

        if updated == 0:
            return jsonify({
                "error": "Goal not found"
            }), 404

        return jsonify({
            "status": "goal updated"
        }), 200

    except Exception as e:
        return server_error(e)


@app.route("/goals/<goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    if not is_valid_uuid(goal_id):
        return not_found("Goal")

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM goals
                    WHERE id = %s
                    AND user_id = %s;
                    """,
                    (goal_id, user.id)
                )

                deleted = cursor.rowcount
                connection.commit()

        if deleted == 0:
            return jsonify({
                "error": "Goal not found"
            }), 404

        return jsonify({
            "status": "goal deleted"
        }), 200

    except Exception as e:
        return server_error(e)


# ---------------------------------------------------------
# Profile
# ---------------------------------------------------------

@app.route("/profile", methods=["GET"])
def profile():
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE id = %s;
                    """,
                    (user.id,)
                )

                result = cursor.fetchone()

                if result is None:
                    return jsonify({
                        "error": "Profile not found"
                    }), 404

                columns = [
                    description[0]
                    for description in cursor.description
                ]

                profile_data = dict(zip(columns, result))

        return jsonify(profile_data), 200

    except Exception as e:
        return server_error(e)


@app.route("/profile", methods=["PATCH"])
def update_profile():
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    data = get_request_data()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    allowed_fields = [
        "full_name",
        "education_level",
        "college_name",
        "graduation_year",
        "preferred_roles"
    ]

    updates = {
        field: data[field]
        for field in allowed_fields
        if field in data
    }

    if not updates:
        return jsonify({
            "error": "No fields provided for update"
        }), 400

    set_clause = ", ".join(
        f"{field} = %s"
        for field in updates
    )

    values = list(updates.values())
    values.append(user.id)

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE users
                    SET
                        {set_clause},
                        updated_at = NOW()
                    WHERE id = %s;
                    """,
                    values
                )

                updated = cursor.rowcount
                connection.commit()

        if updated == 0:
            return jsonify({
                "error": "Profile not found"
            }), 404

        return jsonify({
            "status": "profile updated"
        }), 200

    except Exception as e:
        return server_error(e)


# ---------------------------------------------------------
# Learning paths
# ---------------------------------------------------------

@app.route("/learning-paths", methods=["GET"])
def learning_paths():
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM learning_paths
                    ORDER BY id;
                    """
                )

                paths = rows_to_dicts(cursor, cursor.fetchall())

        return jsonify(paths), 200

    except Exception as e:
        return server_error(e)


@app.route("/learning-paths/<learning_path_id>/topics", methods=["GET"])
def get_path_topics(learning_path_id):
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        pt.id,
                        pt.learning_path_id,
                        pt.title,
                        pt.description,
                        pt.resource_url,
                        pt.position,
                        COALESCE(
                            utp.progress_percentage,
                            0
                        ) AS progress_percentage,
                        COALESCE(
                            utp.status,
                            'not_started'
                        ) AS status
                    FROM path_topics pt
                    LEFT JOIN user_topic_progress utp
                        ON pt.id = utp.path_topic_id
                        AND utp.user_id = %s
                    WHERE pt.learning_path_id = %s
                    ORDER BY pt.position;
                    """,
                    (user.id, learning_path_id)
                )

                topics = rows_to_dicts(cursor, cursor.fetchall())

        return jsonify(topics), 200

    except Exception as e:
        return server_error(e)


# ---------------------------------------------------------
# Progress
# ---------------------------------------------------------

@app.route("/progress", methods=["POST"])
def create_progress():
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    data = get_request_data()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    required_fields = [
        "path_topic_id",
        "status",
        "progress_percentage"
    ]

    missing_fields = [
        field for field in required_fields
        if field not in data
    ]

    if missing_fields:
        return jsonify({
            "error": "Missing required fields",
            "fields": missing_fields
        }), 400

    progress_percentage = data["progress_percentage"]

    if (
        not isinstance(progress_percentage, (int, float))
        or isinstance(progress_percentage, bool)
        or not 0 <= progress_percentage <= 100
    ):
        return jsonify({
            "error": "progress_percentage must be a number between 0 and 100"
        }), 400

    if data["status"] not in ALLOWED_PROGRESS_STATUSES:
        return jsonify({
            "error": "Invalid progress status"
        }), 400

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO user_topic_progress
                    (
                        user_id,
                        path_topic_id,
                        status,
                        progress_percentage
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        user.id,
                        data["path_topic_id"],
                        data["status"],
                        progress_percentage
                    )
                )

                progress_id = cursor.fetchone()[0]
                connection.commit()

        return jsonify({
            "status": "progress created",
            "id": str(progress_id)
        }), 201

    except Exception as e:
        return server_error(e)


@app.route("/progress", methods=["GET"])
def get_progress():
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM user_topic_progress
                    WHERE user_id = %s
                    ORDER BY updated_at DESC;
                    """,
                    (user.id,)
                )

                progress = rows_to_dicts(cursor, cursor.fetchall())

        return jsonify(progress), 200

    except Exception as e:
        return server_error(e)


@app.route("/progress/<progress_id>", methods=["PATCH"])
def update_progress(progress_id):
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    if not is_valid_uuid(progress_id):
        return not_found("Progress record")

    data = get_request_data()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    allowed_fields = [
        "progress_percentage",
        "status"
    ]

    updates = {
        field: data[field]
        for field in allowed_fields
        if field in data
    }

    if not updates:
        return jsonify({
            "error": "No fields provided for update"
        }), 400

    if "progress_percentage" in updates:
        progress_percentage = updates["progress_percentage"]

        if (
            not isinstance(progress_percentage, (int, float))
            or isinstance(progress_percentage, bool)
            or not 0 <= progress_percentage <= 100
        ):
            return jsonify({
                "error": "progress_percentage must be a number between 0 and 100"
            }), 400

    if (
        "status" in updates
        and updates["status"] not in ALLOWED_PROGRESS_STATUSES
    ):
        return jsonify({
            "error": "Invalid progress status"
        }), 400

    set_clause = ", ".join(
        f"{field} = %s"
        for field in updates
    )

    values = list(updates.values())
    values.extend([progress_id, user.id])

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE user_topic_progress
                    SET
                        {set_clause},
                        updated_at = NOW()
                    WHERE id = %s
                    AND user_id = %s;
                    """,
                    values
                )

                updated = cursor.rowcount
                connection.commit()

        if updated == 0:
            return jsonify({
                "error": "Progress record not found"
            }), 404

        return jsonify({
            "status": "progress updated"
        }), 200

    except Exception as e:
        return server_error(e)


@app.route("/progress/<progress_id>", methods=["DELETE"])
def delete_progress(progress_id):
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    if not is_valid_uuid(progress_id):
        return not_found("Progress record")

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM user_topic_progress
                    WHERE id = %s
                    AND user_id = %s;
                    """,
                    (progress_id, user.id)
                )

                deleted = cursor.rowcount
                connection.commit()

        if deleted == 0:
            return jsonify({
                "error": "Progress record not found"
            }), 404

        return jsonify({
            "status": "progress deleted"
        }), 200

    except Exception as e:
        return server_error(e)


# ---------------------------------------------------------
# Applications
# ---------------------------------------------------------

@app.route("/applications", methods=["POST"])
def create_application():
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    data = get_request_data()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    if not data.get("company_name"):
        return jsonify({
            "error": "company_name is required"
        }), 400

    if not data.get("role"):
        return jsonify({
            "error": "role is required"
        }), 400

    if (
        data.get("status")
        and data["status"] not in ALLOWED_APPLICATION_STATUSES
    ):
        return jsonify({
            "error": "Invalid application status"
        }), 400

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO applications
                    (
                        user_id,
                        company_name,
                        role,
                        company_type,
                        status,
                        application_date,
                        job_url,
                        location,
                        notes,
                        interview_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        user.id,
                        data["company_name"],
                        data["role"],
                        data.get("company_type"),
                        data.get("status", "saved"),
                        data.get("application_date"),
                        data.get("job_url"),
                        data.get("location"),
                        data.get("notes"),
                        data.get("interview_date")
                    )
                )

                application_id = cursor.fetchone()[0]
                connection.commit()

        return jsonify({
            "status": "application created",
            "id": str(application_id)
        }), 201

    except Exception as e:
        return server_error(e)


@app.route("/applications", methods=["GET"])
def get_applications():
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM applications
                    WHERE user_id = %s
                    ORDER BY created_at DESC;
                    """,
                    (user.id,)
                )

                applications = rows_to_dicts(
                    cursor,
                    cursor.fetchall()
                )

        return jsonify(applications), 200

    except Exception as e:
        return server_error(e)


@app.route("/applications/<application_id>", methods=["PATCH"])
def update_application(application_id):
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    if not is_valid_uuid(application_id):
        return not_found("Application")

    data = get_request_data()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    allowed_fields = [
        "company_name",
        "role",
        "company_type",
        "status",
        "application_date",
        "job_url",
        "location",
        "notes",
        "interview_date"
    ]

    updates = {
        field: data[field]
        for field in allowed_fields
        if field in data
    }

    if not updates:
        return jsonify({
            "error": "No fields provided for update"
        }), 400

    if (
        "status" in updates
        and updates["status"] not in ALLOWED_APPLICATION_STATUSES
    ):
        return jsonify({
            "error": "Invalid application status"
        }), 400

    set_clause = ", ".join(
        f"{field} = %s"
        for field in updates
    )

    values = list(updates.values())
    values.extend([application_id, user.id])

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE applications
                    SET
                        {set_clause},
                        updated_at = NOW()
                    WHERE id = %s
                    AND user_id = %s;
                    """,
                    values
                )

                updated = cursor.rowcount
                connection.commit()

        if updated == 0:
            return jsonify({
                "error": "Application not found"
            }), 404

        return jsonify({
            "status": "application updated"
        }), 200

    except Exception as e:
        return server_error(e)


@app.route("/applications/<application_id>", methods=["DELETE"])
def delete_application(application_id):
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    if not is_valid_uuid(application_id):
        return not_found("Application")

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM applications
                    WHERE id = %s
                    AND user_id = %s;
                    """,
                    (application_id, user.id)
                )

                deleted = cursor.rowcount
                connection.commit()

        if deleted == 0:
            return jsonify({
                "error": "Application not found"
            }), 404

        return jsonify({
            "status": "application deleted"
        }), 200

    except Exception as e:
        return server_error(e)


# ---------------------------------------------------------
# Run locally
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)