"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/useApi";

const inputClass =
  "mt-1 w-full rounded-lg border border-gray-200 px-4 py-3 text-gray-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100";

function toForm(profile) {
  return {
    full_name: profile.full_name || "",
    education_level: profile.education_level || "",
    college_name: profile.college_name || "",
    graduation_year: profile.graduation_year ?? "",
    preferred_roles: (profile.preferred_roles || []).join(", "),
  };
}

export default function Profile() {
  const { data: profile, loading, error: loadError, reload } =
    useApi("/profile");

  // null means "not edited yet": show the saved profile.
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const form = draft ?? (profile ? toForm(profile) : null);

  const updateForm = (field, value) => {
    setDraft({ ...form, [field]: value });
    setMessage("");
  };

  const saveProfile = async () => {
    const year = String(form.graduation_year).trim();

    if (year && !/^\d{4}$/.test(year)) {
      setError("Graduation year must be a four-digit year.");
      return;
    }

    try {
      setSaving(true);
      setError("");

      await apiFetch("/profile", {
        method: "PATCH",
        body: {
          full_name: form.full_name,
          education_level: form.education_level,
          college_name: form.college_name,
          graduation_year: year ? Number(year) : null,
          preferred_roles: form.preferred_roles
            .split(",")
            .map((role) => role.trim())
            .filter(Boolean),
        },
      });

      setDraft(null);
      setMessage("Profile saved.");
      reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="flex-1 p-8">
      <h1 className="text-3xl font-bold text-gray-900">Profile</h1>

      <p className="mt-2 text-gray-600">
        Your placement details.
      </p>

      {(error || loadError) && (
        <div className="mt-6 max-w-2xl rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
          {error || loadError}
        </div>
      )}

      {loading || !form ? (
        <p className="mt-8 text-sm text-gray-500">
          {loading ? "Loading profile..." : ""}
        </p>
      ) : (
        <div className="mt-8 max-w-2xl rounded-2xl bg-white p-6 shadow-sm">
          <p className="text-sm text-gray-500">{profile.email}</p>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <label className="text-sm text-gray-600 md:col-span-2">
              Full name
              <input
                type="text"
                value={form.full_name}
                onChange={(e) => updateForm("full_name", e.target.value)}
                maxLength={100}
                className={inputClass}
              />
            </label>

            <label className="text-sm text-gray-600">
              Education level
              <input
                type="text"
                value={form.education_level}
                onChange={(e) =>
                  updateForm("education_level", e.target.value)
                }
                placeholder="B.Tech, M.Tech, MCA..."
                maxLength={100}
                className={inputClass}
              />
            </label>

            <label className="text-sm text-gray-600">
              Graduation year
              <input
                type="number"
                value={form.graduation_year}
                onChange={(e) =>
                  updateForm("graduation_year", e.target.value)
                }
                min={1950}
                max={2100}
                className={inputClass}
              />
            </label>

            <label className="text-sm text-gray-600 md:col-span-2">
              College
              <input
                type="text"
                value={form.college_name}
                onChange={(e) => updateForm("college_name", e.target.value)}
                maxLength={200}
                className={inputClass}
              />
            </label>

            <label className="text-sm text-gray-600 md:col-span-2">
              Preferred roles (comma separated)
              <input
                type="text"
                value={form.preferred_roles}
                onChange={(e) =>
                  updateForm("preferred_roles", e.target.value)
                }
                placeholder="SDE, Data Engineer"
                className={inputClass}
              />
            </label>
          </div>

          <div className="mt-6 flex items-center gap-4">
            <button
              onClick={saveProfile}
              disabled={saving}
              className="rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-violet-700 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Profile"}
            </button>

            {message && (
              <p className="text-sm text-gray-600">{message}</p>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
