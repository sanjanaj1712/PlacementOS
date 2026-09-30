from collections import namedtuple
from datetime import date, datetime
from flask import Flask, jsonify, request
from flask.json.provider import DefaultJSONProvider
from dotenv import load_dotenv
from flask_cors import CORS
import os
import uuid
from urllib.parse import urlparse
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

    if isinstance(error, psycopg.errors.ForeignKeyViolation):
        return jsonify({
            "error": "A referenced record does not exist"
        }), 409

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


def ensure_profile(cursor, user):
    """Create the user's profile row if the signup trigger did not."""
    cursor.execute(
        """
        INSERT INTO users (id, email)
        VALUES (%s, %s)
        ON CONFLICT (id) DO NOTHING;
        """,
        (user.id, user.email)
    )


def fetch_path_summaries(cursor, user_id):
    """Learning paths with the user's topic completion, in one query."""
    cursor.execute(
        """
        SELECT
            lp.id,
            lp.title,
            lp.description,
            lp.position,
            COUNT(pt.id) AS topic_count,
            COUNT(utp.id) FILTER (
                WHERE utp.status = 'completed'
            ) AS completed_count,
            COUNT(utp.id) FILTER (
                WHERE utp.status = 'in_progress'
            ) AS in_progress_count
        FROM learning_paths lp
        LEFT JOIN path_topics pt
            ON pt.learning_path_id = lp.id
        LEFT JOIN user_topic_progress utp
            ON utp.path_topic_id = pt.id
            AND utp.user_id = %s
        GROUP BY lp.id
        ORDER BY lp.position, lp.id;
        """,
        (user_id,)
    )

    paths = rows_to_dicts(cursor, cursor.fetchall())

    for path in paths:
        path["progress_percentage"] = percentage(
            path["completed_count"],
            path["topic_count"]
        )

    return paths


def percentage(part, whole):
    return round(part * 100 / whole) if whole else 0


def rows_to_dicts(cursor, rows):
    """Convert database rows to dictionaries."""
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


# Application pipeline: Interested -> Applied -> OA -> Interview -> Offer,
# with Rejected possible from any active stage. Offer and Rejected are final.
APPLICATION_STATUS_TRANSITIONS = {
    "interested": ["applied", "rejected"],
    "applied": ["oa", "interview", "rejected"],
    "oa": ["interview", "rejected"],
    "interview": ["offer", "rejected"],
    "offer": [],
    "rejected": []
}

ALLOWED_APPLICATION_STATUSES = list(APPLICATION_STATUS_TRANSITIONS)

ALLOWED_GOAL_STATUSES = [
    "not_started",
    "in_progress",
    "achieved",
    "abandoned"
]

ALLOWED_PROGRESS_STATUSES = [
    "not_started",
    "in_progress",
    "completed"
]


# ---------------------------------------------------------
# Input validation
# ---------------------------------------------------------

def text(max_length):
    def validate(value):
        if not isinstance(value, str):
            raise ValueError("must be a string")

        value = value.strip()

        if len(value) > max_length:
            raise ValueError(f"must be at most {max_length} characters")

        return value

    return validate


def integer(minimum, maximum):
    def validate(value):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")

        if not minimum <= value <= maximum:
            raise ValueError(f"must be between {minimum} and {maximum}")

        return value

    return validate


def choice(options):
    def validate(value):
        if value not in options:
            raise ValueError(f"must be one of: {', '.join(options)}")

        return value

    return validate


def iso_date(value):
    if not isinstance(value, str):
        raise ValueError("must be a date in YYYY-MM-DD format")

    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("must be a date in YYYY-MM-DD format")

    if not 1950 <= parsed.year <= 2100:
        raise ValueError("must be between 1950 and 2100")

    return parsed.isoformat()


def http_url(value):
    value = text(2000)(value)
    parsed = urlparse(value)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("must be an http or https URL")

    return value


def text_list(max_items, max_length):
    def validate(value):
        if not isinstance(value, list):
            raise ValueError("must be a list of strings")

        items = [text(max_length)(item) for item in value]
        items = [item for item in items if item]

        if len(items) > max_items:
            raise ValueError(f"must have at most {max_items} items")

        return items

    return validate


def field(validator, required=False, empty=None):
    return {
        "validator": validator,
        "required": required,
        "empty": empty
    }


def validate_fields(data, specs, partial=False):
    """Validate request fields against specs.

    Returns (values, errors). Missing fields are skipped when partial is
    True (PATCH). Empty strings and null clear optional fields but are
    rejected for required ones.
    """
    values = {}
    errors = {}

    for name, spec in specs.items():
        if name not in data:
            if spec["required"] and not partial:
                errors[name] = "is required"
            continue

        value = data[name]

        if value is None or (isinstance(value, str) and not value.strip()):
            if spec["required"]:
                errors[name] = "is required"
            else:
                values[name] = spec["empty"]
            continue

        try:
            values[name] = spec["validator"](value)
        except ValueError as e:
            errors[name] = str(e)

    return values, errors


def validation_error(errors):
    return jsonify({
        "error": "Invalid input",
        "fields": errors
    }), 400


def reconcile_progress(values):
    """Keep progress status and percentage consistent with each other.

    not_started is 0%, completed is 100% and in_progress is anything in
    between. When only one of the two is given the other is derived.
    Returns an error message, or None.
    """
    status = values.get("status")
    percentage = values.get("progress_percentage")

    if percentage is not None and status is None:
        if percentage == 0:
            values["status"] = "not_started"
        elif percentage == 100:
            values["status"] = "completed"
        else:
            values["status"] = "in_progress"
        return None

    if status is not None and percentage is None:
        if status == "in_progress":
            return "progress_percentage is required for in_progress"

        values["progress_percentage"] = 100 if status == "completed" else 0
        return None

    if status == "not_started" and percentage != 0:
        return "not_started progress must be 0%"

    if status == "completed" and percentage != 100:
        return "completed progress must be 100%"

    if status == "in_progress" and not 0 < percentage < 100:
        return "in_progress progress must be between 1% and 99%"

    return None


PROFILE_FIELDS = {
    "full_name": field(text(100)),
    "education_level": field(text(100)),
    "college_name": field(text(200)),
    "graduation_year": field(integer(1950, 2100)),
    "preferred_roles": field(text_list(20, 100), empty=[])
}

GOAL_FIELDS = {
    "target_role": field(text(100), required=True),
    "target_company_type": field(text(100), required=True),
    "target_date": field(iso_date, required=True),
    "target_companies": field(text_list(30, 100), empty=[]),
    "status": field(choice(ALLOWED_GOAL_STATUSES), empty="not_started"),
    "progress_percentage": field(integer(0, 100), empty=0)
}

APPLICATION_FIELDS = {
    "company_name": field(text(200), required=True),
    "role": field(text(200), required=True),
    "company_type": field(text(100)),
    "status": field(choice(ALLOWED_APPLICATION_STATUSES)),
    "application_date": field(iso_date),
    "job_url": field(http_url),
    "location": field(text(200)),
    "notes": field(text(5000)),
    "interview_date": field(iso_date)
}

PROGRESS_FIELDS = {
    "path_topic_id": field(integer(1, 2**63 - 1), required=True),
    "status": field(choice(ALLOWED_PROGRESS_STATUSES), required=True),
    "progress_percentage": field(integer(0, 100), required=True)
}


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

    values, errors = validate_fields(data, GOAL_FIELDS)

    if errors:
        return validation_error(errors)

    columns = ["user_id", *values]
    placeholders = ", ".join(["%s"] * len(columns))

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO goals ({", ".join(columns)})
                    VALUES ({placeholders})
                    RETURNING id;
                    """,
                    [user.id, *values.values()]
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

    updates, errors = validate_fields(data, GOAL_FIELDS, partial=True)

    if errors:
        return validation_error(errors)

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
                ensure_profile(cursor, user)

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

    updates, errors = validate_fields(data, PROFILE_FIELDS, partial=True)

    if errors:
        return validation_error(errors)

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
                ensure_profile(cursor, user)

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
                paths = fetch_path_summaries(cursor, user.id)

        return jsonify(paths), 200

    except Exception as e:
        return server_error(e)


@app.route("/learning-paths/<learning_path_id>/topics", methods=["GET"])
def get_path_topics(learning_path_id):
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    if not (learning_path_id.isdigit() or is_valid_uuid(learning_path_id)):
        return not_found("Learning path")

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1
                    FROM learning_paths
                    WHERE id = %s;
                    """,
                    (learning_path_id,)
                )

                if cursor.fetchone() is None:
                    return not_found("Learning path")

                cursor.execute(
                    """
                    SELECT
                        pt.id,
                        pt.learning_path_id,
                        pt.parent_topic_id,
                        pt.title,
                        pt.description,
                        pt.resource_url,
                        pt.position,
                        utp.id AS progress_id,
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
                    ORDER BY pt.position, pt.id;
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

    values, errors = validate_fields(data, PROGRESS_FIELDS)

    if errors:
        return validation_error(errors)

    mismatch = reconcile_progress(values)

    if mismatch:
        return validation_error({"status": mismatch})

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                # One row per user and topic: marking a topic again updates
                # the existing record instead of failing on a duplicate.
                cursor.execute(
                    """
                    INSERT INTO user_topic_progress
                    (
                        user_id,
                        path_topic_id,
                        status,
                        progress_percentage
                    )
                    SELECT %s, pt.id, %s, %s
                    FROM path_topics pt
                    WHERE pt.id = %s
                    ON CONFLICT (user_id, path_topic_id)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        progress_percentage = EXCLUDED.progress_percentage,
                        updated_at = NOW()
                    RETURNING id, (xmax = 0) AS created;
                    """,
                    (
                        user.id,
                        values["status"],
                        values["progress_percentage"],
                        values["path_topic_id"]
                    )
                )

                row = cursor.fetchone()
                connection.commit()

        if row is None:
            return not_found("Topic")

        progress_id, created = row

        return jsonify({
            "status": "progress created" if created else "progress updated",
            "id": str(progress_id)
        }), 201 if created else 200

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

    progress_update_fields = {
        name: spec
        for name, spec in PROGRESS_FIELDS.items()
        if name != "path_topic_id"
    }

    updates, errors = validate_fields(
        data,
        progress_update_fields,
        partial=True
    )

    if errors:
        return validation_error(errors)

    if not updates:
        return jsonify({
            "error": "No fields provided for update"
        }), 400

    mismatch = reconcile_progress(updates)

    if mismatch:
        return validation_error({"status": mismatch})

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

    values, errors = validate_fields(data, APPLICATION_FIELDS)

    if errors:
        return validation_error(errors)

    if not values.get("status"):
        values["status"] = ALLOWED_APPLICATION_STATUSES[0]

    columns = ["user_id", *values]
    placeholders = ", ".join(["%s"] * len(columns))

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO applications ({", ".join(columns)})
                    VALUES ({placeholders})
                    RETURNING id;
                    """,
                    [user.id, *values.values()]
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

    updates, errors = validate_fields(
        data,
        APPLICATION_FIELDS,
        partial=True
    )

    if errors:
        return validation_error(errors)

    if "status" in updates and not updates["status"]:
        return validation_error({"status": "is required"})

    if not updates:
        return jsonify({
            "error": "No fields provided for update"
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
                    """
                    SELECT status
                    FROM applications
                    WHERE id = %s
                    AND user_id = %s
                    FOR UPDATE;
                    """,
                    (application_id, user.id)
                )

                row = cursor.fetchone()

                if row is None:
                    return not_found("Application")

                current_status = row[0]
                new_status = updates.get("status", current_status)

                if (
                    new_status != current_status
                    and new_status not in APPLICATION_STATUS_TRANSITIONS.get(
                        current_status, []
                    )
                ):
                    return jsonify({
                        "error": (
                            f"Cannot move application from "
                            f"{current_status} to {new_status}"
                        ),
                        "allowed_statuses": APPLICATION_STATUS_TRANSITIONS.get(
                            current_status, []
                        )
                    }), 409

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

                connection.commit()

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
# Dashboard
# ---------------------------------------------------------

@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Everything the dashboard shows, in a fixed number of queries."""
    user, error_response, status_code = require_user()

    if error_response:
        return error_response, status_code

    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT status, COUNT(*)
                    FROM goals
                    WHERE user_id = %s
                    GROUP BY status;
                    """,
                    (user.id,)
                )

                goal_counts = dict(cursor.fetchall())

                cursor.execute(
                    """
                    SELECT *
                    FROM goals
                    WHERE user_id = %s
                    ORDER BY
                        status IN ('achieved', 'abandoned'),
                        target_date,
                        created_at DESC
                    LIMIT 1;
                    """,
                    (user.id,)
                )

                current_goal = rows_to_dicts(cursor, cursor.fetchall())

                paths = fetch_path_summaries(cursor, user.id)

                cursor.execute(
                    """
                    SELECT status, COUNT(*)
                    FROM applications
                    WHERE user_id = %s
                    GROUP BY status;
                    """,
                    (user.id,)
                )

                application_counts = dict(cursor.fetchall())

                cursor.execute(
                    """
                    SELECT *
                    FROM (
                        SELECT
                            'goal' AS type,
                            g.id::text AS id,
                            g.target_role AS title,
                            g.status,
                            g.updated_at
                        FROM goals g
                        WHERE g.user_id = %(user_id)s

                        UNION ALL

                        SELECT
                            'application',
                            a.id::text,
                            a.company_name || ' - ' || a.role,
                            a.status,
                            a.updated_at
                        FROM applications a
                        WHERE a.user_id = %(user_id)s

                        UNION ALL

                        SELECT
                            'topic',
                            utp.id::text,
                            pt.title,
                            utp.status,
                            utp.updated_at
                        FROM user_topic_progress utp
                        JOIN path_topics pt
                            ON pt.id = utp.path_topic_id
                        WHERE utp.user_id = %(user_id)s
                    ) activity
                    ORDER BY updated_at DESC
                    LIMIT 10;
                    """,
                    {"user_id": user.id}
                )

                recent_activity = rows_to_dicts(cursor, cursor.fetchall())

        total_topics = sum(path["topic_count"] for path in paths)
        completed_topics = sum(path["completed_count"] for path in paths)
        in_progress_topics = sum(path["in_progress_count"] for path in paths)

        return jsonify({
            "goals": {
                "total": sum(goal_counts.values()),
                "by_status": {
                    status: goal_counts.get(status, 0)
                    for status in ALLOWED_GOAL_STATUSES
                },
                "current": current_goal[0] if current_goal else None
            },
            "topics": {
                "total": total_topics,
                "completed": completed_topics,
                "in_progress": in_progress_topics,
                "progress_percentage": percentage(
                    completed_topics,
                    total_topics
                ),
                "paths": paths
            },
            "applications": {
                "total": sum(application_counts.values()),
                "active": sum(
                    count
                    for status, count in application_counts.items()
                    if status not in ("offer", "rejected")
                ),
                "by_status": {
                    status: application_counts.get(status, 0)
                    for status in ALLOWED_APPLICATION_STATUSES
                }
            },
            "recent_activity": recent_activity
        }), 200

    except Exception as e:
        return server_error(e)


# ---------------------------------------------------------
# Run locally
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)