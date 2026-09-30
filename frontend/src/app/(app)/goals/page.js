"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/useApi";

const companyTypes = ["Product-based", "Service-based", "Startup", "Any"];

const goalStatuses = [
  { value: "not_started", label: "Not started" },
  { value: "in_progress", label: "In progress" },
  { value: "achieved", label: "Achieved" },
  { value: "abandoned", label: "Abandoned" },
];

const emptyForm = {
  target_role: "Software Engineer",
  target_company_type: "Product-based",
  target_companies: [],
  target_date: "",
  status: "not_started",
  progress_percentage: 0,
};

const inputClass =
  "w-full rounded-lg border border-gray-200 px-4 py-3 text-gray-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100";

export default function Goals() {
  const { data, loading, error: loadError, reload } = useApi("/goals");
  const goals = data || [];
  const [actionError, setError] = useState("");
  const error = actionError || loadError;

  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [company, setCompany] = useState("");
  const [saving, setSaving] = useState(false);

  const updateForm = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const addCompany = () => {
    const name = company.trim();

    if (!name || form.target_companies.includes(name)) {
      setCompany("");
      return;
    }

    updateForm("target_companies", [...form.target_companies, name]);
    setCompany("");
  };

  const removeCompany = (name) => {
    updateForm(
      "target_companies",
      form.target_companies.filter((item) => item !== name)
    );
  };

  const resetForm = () => {
    setForm(emptyForm);
    setEditingId(null);
    setCompany("");
  };

  const saveGoal = async () => {
    if (!form.target_role.trim()) {
      setError("Please enter a target role.");
      return;
    }

    if (!form.target_date) {
      setError("Please select a target date.");
      return;
    }

    try {
      setSaving(true);
      setError("");

      await apiFetch(editingId ? `/goals/${editingId}` : "/goals", {
        method: editingId ? "PATCH" : "POST",
        body: {
          ...form,
          target_role: form.target_role.trim(),
          progress_percentage: Number(form.progress_percentage),
        },
      });

      resetForm();
      reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const editGoal = (goal) => {
    setEditingId(goal.id);
    setForm({
      target_role: goal.target_role,
      target_company_type: goal.target_company_type,
      target_companies: goal.target_companies || [],
      target_date: goal.target_date,
      status: goal.status,
      progress_percentage: goal.progress_percentage,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const deleteGoal = async (goal) => {
    if (!window.confirm(`Delete the goal "${goal.target_role}"?`)) {
      return;
    }

    try {
      setError("");
      await apiFetch(`/goals/${goal.id}`, { method: "DELETE" });

      if (editingId === goal.id) {
        resetForm();
      }

      reload();
    } catch (err) {
      setError(err.message);
    }
  };

  const statusLabel = (value) =>
    goalStatuses.find((status) => status.value === value)?.label || value;

  return (
    <main className="flex-1 p-8">
      <h1 className="text-3xl font-bold text-gray-900">
        Your Goals
      </h1>

      <p className="mt-2 text-gray-600">
        Set your placement goals and track your progress.
      </p>

      {error && (
        <div className="mt-6 max-w-2xl rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Goal form */}
      <div className="mt-8 max-w-2xl rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">
          {editingId ? "Edit Goal" : "New Goal"}
        </h2>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <label className="text-sm text-gray-600 md:col-span-2">
            Target role
            <input
              type="text"
              value={form.target_role}
              onChange={(e) => updateForm("target_role", e.target.value)}
              maxLength={100}
              className={`mt-1 ${inputClass}`}
            />
          </label>

          <label className="text-sm text-gray-600">
            Company type
            <select
              value={form.target_company_type}
              onChange={(e) =>
                updateForm("target_company_type", e.target.value)
              }
              className={`mt-1 ${inputClass}`}
            >
              {companyTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm text-gray-600">
            Target date
            <input
              type="date"
              value={form.target_date}
              onChange={(e) => updateForm("target_date", e.target.value)}
              className={`mt-1 ${inputClass}`}
            />
          </label>

          <label className="text-sm text-gray-600">
            Status
            <select
              value={form.status}
              onChange={(e) => updateForm("status", e.target.value)}
              className={`mt-1 ${inputClass}`}
            >
              {goalStatuses.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm text-gray-600">
            Progress: {form.progress_percentage}%
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={form.progress_percentage}
              onChange={(e) =>
                updateForm("progress_percentage", Number(e.target.value))
              }
              className="mt-4 w-full accent-violet-600"
            />
          </label>

          <div className="text-sm text-gray-600 md:col-span-2">
            Target companies
            <div className="mt-1 flex gap-3">
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addCompany();
                  }
                }}
                placeholder="Company name"
                maxLength={100}
                className={`flex-1 ${inputClass}`}
              />

              <button
                onClick={addCompany}
                className="rounded-lg bg-violet-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-violet-700"
              >
                Add
              </button>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {form.target_companies.map((name) => (
                <span
                  key={name}
                  className="flex items-center gap-2 rounded-full bg-violet-50 px-3 py-1 text-sm font-medium text-violet-700"
                >
                  {name}
                  <button
                    onClick={() => removeCompany(name)}
                    aria-label={`Remove ${name}`}
                    className="text-violet-400 hover:text-violet-700"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={saveGoal}
            disabled={saving}
            className="rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-violet-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : editingId ? "Save Changes" : "Create Goal"}
          </button>

          {editingId && (
            <button
              onClick={resetForm}
              className="rounded-lg px-5 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-100"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Goal list */}
      <div className="mt-6 max-w-2xl space-y-4">
        {loading ? (
          <p className="text-sm text-gray-500">Loading goals...</p>
        ) : goals.length === 0 ? (
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <p className="text-sm text-gray-500">No goals yet.</p>
          </div>
        ) : (
          goals.map((goal) => (
            <div key={goal.id} className="rounded-2xl bg-white p-6 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">
                    {goal.target_role}
                  </h2>

                  <p className="mt-1 text-sm text-gray-500">
                    {goal.target_company_type} · by {goal.target_date}
                  </p>
                </div>

                <span className="shrink-0 rounded-full bg-violet-50 px-3 py-1 text-xs font-medium text-violet-700">
                  {statusLabel(goal.status)}
                </span>
              </div>

              {goal.target_companies?.length > 0 && (
                <p className="mt-3 text-sm text-gray-600">
                  {goal.target_companies.join(", ")}
                </p>
              )}

              <div className="mt-4">
                <div className="mb-2 flex justify-between text-xs">
                  <span className="text-gray-500">Progress</span>
                  <span className="font-medium text-gray-900">
                    {goal.progress_percentage}%
                  </span>
                </div>

                <div className="h-2 w-full rounded-full bg-gray-100">
                  <div
                    className="h-2 rounded-full bg-violet-500 transition-all"
                    style={{ width: `${goal.progress_percentage}%` }}
                  />
                </div>
              </div>

              <div className="mt-4 flex gap-3 text-sm">
                <button
                  onClick={() => editGoal(goal)}
                  className="font-medium text-violet-600 hover:underline"
                >
                  Edit
                </button>

                <button
                  onClick={() => deleteGoal(goal)}
                  className="font-medium text-red-600 hover:underline"
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </main>
  );
}
