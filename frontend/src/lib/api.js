import { supabase } from "@/lib/supabase";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:5000";

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export async function getAccessToken() {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  return session?.access_token ?? null;
}

// Calls the Flask API with the current Supabase access token.
// getSession() refreshes the token when it has expired, so requests keep
// working for as long as the user stays signed in.
export async function apiFetch(path, { method = "GET", body } = {}) {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    redirectToLogin();
    throw new ApiError("Please sign in again.", 401);
  }

  const headers = {
    Authorization: `Bearer ${session.access_token}`,
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  let response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      "Could not reach the PlacementOS API. Is the backend running?",
      0
    );
  }

  const data = await response.json().catch(() => null);

  if (response.status === 401) {
    await supabase.auth.signOut();
    redirectToLogin();
    throw new ApiError("Your session has expired. Please sign in again.", 401);
  }

  if (!response.ok) {
    throw new ApiError(errorMessage(data), response.status, data);
  }

  return data;
}

function errorMessage(data) {
  if (!data || !data.error) {
    return "Something went wrong. Please try again.";
  }

  if (data.fields) {
    const details = Object.entries(data.fields)
      .map(([field, problem]) => `${field.replaceAll("_", " ")} ${problem}`)
      .join("; ");

    return `${data.error}: ${details}`;
  }

  return data.error;
}

function redirectToLogin() {
  if (typeof window !== "undefined" && window.location.pathname !== "/") {
    window.location.replace("/");
  }
}
