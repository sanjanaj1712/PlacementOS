"use client";

import { useEffect, useState } from "react";

import { API_URL, getAccessToken } from "@/lib/api";

const statusOptions = [
  "saved",
  "applied",
  "interview",
  "offer",
  "rejected",
];

export default function Applications() {
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("applied");

  const [applications, setApplications] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // ---------------------------------------------------------
  // Load applications
  // ---------------------------------------------------------

  useEffect(() => {
    loadApplications();
  }, []);

  const loadApplications = async () => {
    try {
      setLoading(true);
      setError("");

      const token = await getAccessToken();

      const response = await fetch(`${API_URL}/applications`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to load applications");
      }

      setApplications(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------------------------------------
  // Add application
  // ---------------------------------------------------------

  const addApplication = async () => {
    if (company.trim() === "" || role.trim() === "") {
      return;
    }

    try {
      setError("");

      const token = await getAccessToken();

      const response = await fetch(`${API_URL}/applications`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          company_name: company.trim(),
          role: role.trim(),
          status: status,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to add application");
      }

      setCompany("");
      setRole("");
      setStatus("applied");

      await loadApplications();
    } catch (err) {
      setError(err.message);
    }
  };

  // ---------------------------------------------------------
  // Update application status
  // ---------------------------------------------------------

  const updateStatus = async (id, newStatus) => {
    try {
      setError("");

      const token = await getAccessToken();

      const response = await fetch(
        `${API_URL}/applications/${id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            status: newStatus,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Failed to update application"
        );
      }

      await loadApplications();
    } catch (err) {
      setError(err.message);
    }
  };

  // ---------------------------------------------------------
  // Statistics
  // ---------------------------------------------------------

  const totalApplications = applications.length;

  const interviewCount = applications.filter(
    (application) => application.status === "interview"
  ).length;

  const offerCount = applications.filter(
    (application) => application.status === "offer"
  ).length;

  // ---------------------------------------------------------
  // UI
  // ---------------------------------------------------------

  return (
    <main className="flex-1 p-8">
      <h1 className="text-3xl font-bold text-gray-900">
        Applications
      </h1>

      <p className="mt-2 text-gray-600">
        Track your placement applications and interview progress.
      </p>

      {/* Error */}
      {error && (
        <div className="mt-6 rounded-xl bg-red-50 p-4 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Statistics */}
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <p className="text-sm text-gray-500">
            Total Applications
          </p>

          <p className="mt-2 text-3xl font-bold text-gray-900">
            {totalApplications}
          </p>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <p className="text-sm text-gray-500">
            Interviews
          </p>

          <p className="mt-2 text-3xl font-bold text-gray-900">
            {interviewCount}
          </p>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <p className="text-sm text-gray-500">
            Offers
          </p>

          <p className="mt-2 text-3xl font-bold text-gray-900">
            {offerCount}
          </p>
        </div>
      </div>

      {/* Add Application */}
      <div className="mt-6 max-w-3xl rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">
          Add Application
        </h2>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <input
            type="text"
            placeholder="Company name"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            className="rounded-lg border border-gray-200 px-4 py-3 text-gray-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
          />

          <input
            type="text"
            placeholder="Role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="rounded-lg border border-gray-200 px-4 py-3 text-gray-900 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
          />

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-lg border border-gray-200 px-4 py-3 text-gray-900 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
          >
            {statusOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>

          <button
            onClick={addApplication}
            className="rounded-lg bg-violet-600 px-5 py-3 font-medium text-white transition hover:bg-violet-700"
          >
            Add Application
          </button>
        </div>
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
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">
                    {application.company_name}
                  </h2>

                  <p className="mt-1 text-sm text-gray-500">
                    {application.role}
                  </p>
                </div>

                <select
                  value={application.status}
                  onChange={(e) =>
                    updateStatus(
                      application.id,
                      e.target.value
                    )
                  }
                  className="w-fit rounded-full border border-violet-100 bg-violet-50 px-3 py-2 text-sm font-medium text-violet-700 outline-none"
                >
                  {statusOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ))
        )}
      </div>
    </main>
  );
}