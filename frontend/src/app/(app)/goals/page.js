"use client";

import { useEffect, useState } from "react";

const API_URL = "http://127.0.0.1:5000";

export default function Goals() {
  const [role, setRole] = useState("Software Engineer");
  const [company, setCompany] = useState("");
  const [companies, setCompanies] = useState([
    "Google",
    "Microsoft",
    "Amazon",
  ]);
  const [targetDate, setTargetDate] = useState("");

  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  // Load the existing goal when the page opens
  useEffect(() => {
    loadGoal();
  }, []);

  const loadGoal = async () => {
    try {
      const token = localStorage.getItem("access_token");

      if (!token) {
        setMessage("Authentication required.");
        return;
      }

      const response = await fetch(`${API_URL}/goals`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to load goal");
      }

      // Load the most recently created goal
      if (data.length > 0) {
        const goal = data[0];

        setRole(goal.target_role || "Software Engineer");
        setTargetDate(goal.target_date || "");
      }
    } catch (error) {
      console.error("Failed to load goal:", error);
      setMessage(error.message);
    }
  };

  const saveGoal = async () => {
    // Make sure all required fields have been filled
    if (!role.trim()) {
      setMessage("Please enter a target role.");
      return;
    }

    if (companies.length === 0) {
      setMessage("Please add at least one target company.");
      return;
    }

    if (!targetDate) {
      setMessage("Please select a target date.");
      return;
    }

    try {
      setSaving(true);
      setMessage("");

      const token = localStorage.getItem("access_token");

      if (!token) {
        setMessage("Authentication required.");
        return;
      }

      const response = await fetch(`${API_URL}/goals`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          target_role: role.trim(),
          target_company_type: "Product-based",
          target_date: targetDate,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to save goal");
      }

      setMessage("Goal saved successfully!");
    } catch (error) {
      console.error("Failed to save goal:", error);
      setMessage(error.message);
    } finally {
      setSaving(false);
    }
  };

  const addCompany = () => {
    if (company.trim() === "") return;

    setCompanies([...companies, company.trim()]);
    setCompany("");
  };

  return (
    <main className="flex-1 p-8">
      <h1 className="text-3xl font-bold text-gray-900">
        Your Goals
      </h1>

      <p className="mt-2 text-gray-600">
        Set your placement goals and track your progress.
      </p>

      {/* Target Role */}
      <div className="mt-8 max-w-2xl rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">
          Target Role
        </h2>

        <p className="mt-1 text-sm text-gray-500">
          What role are you preparing for?
        </p>

        <input
          type="text"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="mt-4 w-full rounded-lg border border-gray-200 px-4 py-3 text-gray-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
        />

        <button
          onClick={saveGoal}
          disabled={saving}
          className="mt-4 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-violet-700 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Goal"}
        </button>

        {message && (
          <p className="mt-3 text-sm text-gray-600">
            {message}
          </p>
        )}
      </div>

      {/* Target Companies */}
      <div className="mt-6 max-w-2xl rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">
          Target Companies
        </h2>

        <p className="mt-1 text-sm text-gray-500">
          Which companies are you preparing for?
        </p>

        <div className="mt-4 flex gap-3">
          <input
            type="text"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Company name"
            className="flex-1 rounded-lg border border-gray-200 px-4 py-3 text-gray-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
          />

          <button
            onClick={addCompany}
            className="rounded-lg bg-violet-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-violet-700"
          >
            Add
          </button>
        </div>

        <div className="mt-5 space-y-2">
          {companies.map((company) => (
            <div
              key={company}
              className="rounded-lg bg-gray-50 px-4 py-3 text-sm font-medium text-gray-700"
            >
              {company}
            </div>
          ))}
        </div>
      </div>

      {/* Target Date */}
      <div className="mt-6 max-w-2xl rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">
          Placement Target Date
        </h2>

        <p className="mt-1 text-sm text-gray-500">
          When do you want to be placement-ready?
        </p>

        <input
          type="date"
          value={targetDate}
          onChange={(e) => setTargetDate(e.target.value)}
          className="mt-4 rounded-lg border border-gray-200 px-4 py-3 text-gray-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
        />
      </div>
    </main>
  );
}