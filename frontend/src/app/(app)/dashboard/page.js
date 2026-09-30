"use client";

import { useEffect, useState } from "react";
import TodaysFocus from "@/components/TodaysFocus";

const API_URL = "http://127.0.0.1:5000";

export default function Dashboard() {
  const [applicationCount, setApplicationCount] = useState(0);
  const [goal, setGoal] = useState(null);
  const [progressRecords, setProgressRecords] = useState([]);

  const [loadingApplications, setLoadingApplications] = useState(true);
  const [loadingGoal, setLoadingGoal] = useState(true);

  useEffect(() => {
    loadApplicationCount();
    loadGoal();
    loadProgress();
  }, []);

  const loadApplicationCount = async () => {
    try {
      const token = localStorage.getItem("access_token");

      if (!token) {
        return;
      }

      const response = await fetch(`${API_URL}/applications`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Failed to load applications"
        );
      }

      setApplicationCount(data.length);
    } catch (error) {
      console.error(
        "Failed to load application count:",
        error
      );
    } finally {
      setLoadingApplications(false);
    }
  };

  const loadGoal = async () => {
    try {
      const token = localStorage.getItem("access_token");

      if (!token) {
        return;
      }

      const response = await fetch(`${API_URL}/goals`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Failed to load goal"
        );
      }

      if (data.length > 0) {
        setGoal(data[0]);
      }
    } catch (error) {
      console.error("Failed to load goal:", error);
    } finally {
      setLoadingGoal(false);
    }
  };

  const loadProgress = async () => {
  try {
    const token = localStorage.getItem("access_token");

    if (!token) {
      return;
    }

    const response = await fetch(`${API_URL}/progress`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.error || "Failed to load progress"
      );
    }

    setProgressRecords(data);
  } catch (error) {
    console.error(
      "Failed to load progress:",
      error
    );
  }
};

const completedTopics = progressRecords.filter(
  (record) =>
    Number(record.progress_percentage) >= 100
).length;

  return (
    <main className="flex-1 p-8">
      <h1 className="text-3xl font-bold text-gray-900">
        Good morning 👋
      </h1>

      <p className="mt-2 text-gray-600">
        Here's your placement progress for today.
      </p>

      <div className="mt-8 grid gap-4 md:grid-cols-2">

        {/* Placement Goal */}
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Placement Goal
          </h2>

          <p className="mt-2 text-gray-600">
            {loadingGoal
              ? "Loading..."
              : goal
              ? goal.target_role
              : "No goal set"}
          </p>

          <div className="mt-4">
            <div className="mb-2 flex justify-between text-sm">
              <span className="text-gray-500">
                Progress
              </span>

              <span className="font-medium text-gray-900">
                75%
              </span>
            </div>

            <div className="h-2 w-full rounded-full bg-gray-100">
              <div className="h-2 w-3/4 rounded-full bg-violet-500"></div>
            </div>
          </div>
        </div>

        {/* Topics Completed */}
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Topics Completed
          </h2>

          <p className="mt-2 text-3xl font-bold text-gray-900">
            18 / 30
          </p>

          <p className="mt-1 text-sm text-gray-500">
            topics completed
          </p>
        </div>

        {/* Applications */}
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Applications
          </h2>

          <p className="mt-2 text-3xl font-bold text-gray-900">
            {loadingApplications
              ? "..."
              : applicationCount}
          </p>

          <p className="mt-1 text-sm text-gray-500">
            applications submitted
          </p>
        </div>
      </div>

      <TodaysFocus />
    </main>
  );
}