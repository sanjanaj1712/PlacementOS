"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/useApi";

const statusLabels = {
  interested: "Interested",
  applied: "Applied",
  oa: "Online Assessment",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
};

// Must match APPLICATION_STATUS_TRANSITIONS in backend/app.py.
const nextStatuses = {
  interested: ["applied", "rejected"],
  applied: ["oa", "interview", "rejected"],
  oa: ["interview", "rejected"],
  interview: ["offer", "rejected"],
  offer: [],
  rejected: [],
};

const detailFields = [
  { name: "company_type", label: "Company type", type: "text" },
  { name: "location", label: "Location", type: "text" },
  { name: "job_url", label: "Job URL", type: "url" },
  { name: "application_date", label: "Applied on", type: "date" },
  { name: "interview_date", label: "Interview date", type: "date" },
];

const emptyApplication = {
  company_name: "",
  role: "",
  status: "interested",
  company_type: "",
  location: "",
  job_url: "",
  application_date: "",
  interview_date: "",
  notes: "",
};

const inputClass =
  "w-full rounded-lg border border-gray-200 px-4 py-3 text-gray-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100";

function toForm(application) {
  return Object.fromEntries(
    Object.keys(emptyApplication).map((field) => [
      field,
      application[field] ?? "",
    ])
  );
}

function ApplicationFields({ form, onChange, includeStatus }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <input
        type="text"
        placeholder="Company name"
        value={form.company_name}
        onChange={(e) => onChange("company_name", e.target.value)}
        maxLength={200}
        className={inputClass}
      />

      <input
        type="text"
        placeholder="Role"
        value={form.role}
        onChange={(e) => onChange("role", e.target.value)}
        maxLength={200}
        className={inputClass}
      />

      {includeStatus && (
        <select
          value={form.status}
          onChange={(e) => onChange("status", e.target.value)}
          className={inputClass}
        >
          {Object.entries(statusLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      )}

      {detailFields.map((field) => (
        <label key={field.name} className="text-sm text-gray-600">
          {field.label}
          <input
            type={field.type}
            value={form[field.name]}
            onChange={(e) => onChange(field.name, e.target.value)}
            className={`mt-1 ${inputClass}`}
          />
        </label>
      ))}

      <textarea
        placeholder="Notes"
        value={form.notes}
        onChange={(e) => onChange("notes", e.target.value)}
        maxLength={5000}
        rows={3}
        className={`md:col-span-2 ${inputClass}`}
      />
    </div>
  );
}

export default function Applications() {
  const { data, loading, error: loadError, reload } = useApi("/applications");
  const applications = data || [];

  const [newApplication, setNewApplication] = useState(emptyApplication);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState(emptyApplication);
  const [error, setError] = useState("");

  const run = async (action) => {
    try {
      setError("");
      await action();
      reload();
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  };

  const addApplication = async () => {
    if (!newApplication.company_name.trim() || !newApplication.role.trim()) {
      setError("Company name and role are required.");
      return;
    }

    const added = await run(() =>
      apiFetch("/applications", { method: "POST", body: newApplication })
    );

    if (added) {
      setNewApplication(emptyApplication);
    }
  };

  const updateStatus = (application, status) =>
    run(() =>
      apiFetch(`/applications/${application.id}`, {
        method: "PATCH",
        body: { status },
      })
    );

  const startEditing = (application) => {
    setEditingId(application.id);
    setEditForm(toForm(application));
  };

  const saveDetails = async () => {
    // Status changes go through the status dropdown.
    const details = { ...editForm };
    delete details.status;

    const saved = await run(() =>
      apiFetch(`/applications/${editingId}`, {
        method: "PATCH",
        body: details,
      })
    );

    if (saved) {
      setEditingId(null);
    }
  };

  const deleteApplication = (application) => {
    if (
      !window.confirm(
        `Delete your application to ${application.company_name}?`
      )
    ) {
      return;
    }

    run(() =>
      apiFetch(`/applications/${application.id}`, { method: "DELETE" })
    );
  };

  const countByStatus = (status) =>
    applications.filter((application) => application.status === status)
      .length;

  const stats = [
    { label: "Total Applications", value: applications.length },
    { label: "Online Assessments", value: countByStatus("oa") },
    { label: "Interviews", value: countByStatus("interview") },
    { label: "Offers", value: countByStatus("offer") },
  ];

  return (
    <main className="flex-1 p-8">
      <h1 className="text-3xl font-bold text-gray-900">
        Applications
      </h1>

      <p className="mt-2 text-gray-600">
        Track your placement applications and interview progress.
      </p>

      {(error || loadError) && (
        <div className="mt-6 rounded-xl bg-red-50 p-4 text-sm text-red-600">
          {error || loadError}
        </div>
      )}

      {/* Statistics */}
      <div className="mt-8 grid gap-4 md:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="rounded-2xl bg-white p-6 shadow-sm">
            <p className="text-sm text-gray-500">{stat.label}</p>

            <p className="mt-2 text-3xl font-bold text-gray-900">
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      {/* Add Application */}
      <div className="mt-6 max-w-3xl rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">
          Add Application
        </h2>

        <div className="mt-4">
          <ApplicationFields
            form={newApplication}
            includeStatus
            onChange={(field, value) =>
              setNewApplication((current) => ({ ...current, [field]: value }))
            }
          />
        </div>

        <button
          onClick={addApplication}
          className="mt-4 rounded-lg bg-violet-600 px-5 py-3 font-medium text-white transition hover:bg-violet-700"
        >
          Add Application
        </button>
      </div>

      {/* Applications List */}
      <div className="mt-6 max-w-3xl space-y-4">
        {loading ? (
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <p className="text-sm text-gray-500">
              Loading applications...
            </p>
          </div>
        ) : applications.length === 0 ? (
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <p className="text-sm text-gray-500">
              No applications yet.
            </p>
          </div>
        ) : (
          applications.map((application) => (
            <div
              key={application.id}
              className="rounded-2xl bg-white p-6 shadow-sm"
            >
              {editingId === application.id ? (
                <>
                  <ApplicationFields
                    form={editForm}
                    onChange={(field, value) =>
                      setEditForm((current) => ({
                        ...current,
                        [field]: value,
                      }))
                    }
                  />

                  <div className="mt-4 flex gap-3">
                    <button
                      onClick={saveDetails}
                      className="rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-violet-700"
                    >
                      Save
                    </button>

                    <button
                      onClick={() => setEditingId(null)}
                      className="rounded-lg px-5 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-100"
                    >
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h2 className="text-lg font-semibold text-gray-900">
                        {application.company_name}
                      </h2>

                      <p className="mt-1 text-sm text-gray-500">
                        {[
                          application.role,
                          application.company_type,
                          application.location,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                    </div>

                    <select
                      value={application.status}
                      disabled={nextStatuses[application.status]?.length === 0}
                      onChange={(e) =>
                        updateStatus(application, e.target.value)
                      }
                      className="w-fit rounded-full border border-violet-100 bg-violet-50 px-3 py-2 text-sm font-medium text-violet-700 outline-none disabled:opacity-70"
                    >
                      {[
                        application.status,
                        ...(nextStatuses[application.status] || []),
                      ].map((option) => (
                        <option key={option} value={option}>
                          {statusLabels[option] || option}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="mt-3 space-y-1 text-sm text-gray-600">
                    {application.application_date && (
                      <p>Applied on {application.application_date}</p>
                    )}

                    {application.interview_date && (
                      <p>Interview on {application.interview_date}</p>
                    )}

                    {/^https?:\/\//i.test(application.job_url || "") && (
                      <a
                        href={application.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-violet-600 hover:underline"
                      >
                        Job posting
                      </a>
                    )}

                    {application.notes && (
                      <p className="whitespace-pre-line">
                        {application.notes}
                      </p>
                    )}
                  </div>

                  <div className="mt-4 flex gap-3 text-sm">
                    <button
                      onClick={() => startEditing(application)}
                      className="font-medium text-violet-600 hover:underline"
                    >
                      Edit
                    </button>

                    <button
                      onClick={() => deleteApplication(application)}
                      className="font-medium text-red-600 hover:underline"
                    >
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </main>
  );
}
