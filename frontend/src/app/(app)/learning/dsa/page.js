"use client";

import { useEffect, useState } from "react";
import TopicCard from "@/components/TopicCard";

import { API_URL, getAccessToken } from "@/lib/api";

export default function DSA() {
  const [topics, setTopics] = useState([]);
  const [progressRecords, setProgressRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    loadDSA();
  }, []);

  const loadDSA = async () => {
    try {
      setLoading(true);
      setMessage("");

      const token = await getAccessToken();

      if (!token) {
        throw new Error("Authentication required.");
      }

      // 1. Get all learning paths
      const pathsResponse = await fetch(
        `${API_URL}/learning-paths`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const pathsData = await pathsResponse.json();

      if (!pathsResponse.ok) {
        throw new Error(
          pathsData.error || "Failed to load learning paths"
        );
      }

      // 2. Find the actual DSA learning path
      const dsaPath = pathsData.find(
        (path) =>
          path.title === "Data Structures & Algorithms"
      );

      if (!dsaPath) {
        throw new Error(
          "Data Structures & Algorithms learning path not found."
        );
      }

      // 3. Get topics belonging to DSA
      const topicsResponse = await fetch(
        `${API_URL}/learning-paths/${dsaPath.id}/topics`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const topicsData = await topicsResponse.json();

      if (!topicsResponse.ok) {
        throw new Error(
          topicsData.error || "Failed to load DSA topics"
        );
      }

      setTopics(topicsData);

      // 4. Get user's progress
      const progressResponse = await fetch(
        `${API_URL}/progress`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const progressData = await progressResponse.json();

      if (!progressResponse.ok) {
        throw new Error(
          progressData.error || "Failed to load progress"
        );
      }

      setProgressRecords(progressData);
    } catch (error) {
      console.error("Failed to load DSA:", error);
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleTopic = async (topic) => {
    try {
      setMessage("");

      const token = await getAccessToken();

      if (!token) {
        throw new Error("Authentication required.");
      }

      // Find existing progress record for this topic
      const existingProgress = progressRecords.find(
        (record) =>
          record.path_topic_id === topic.id
      );

      const isCompleted =
        existingProgress &&
        Number(existingProgress.progress_percentage) >= 100;

      // ------------------------------------------------
      // UNCHECK → set progress back to 0
      // ------------------------------------------------
      if (isCompleted) {
        if (existingProgress) {
          const response = await fetch(
            `${API_URL}/progress/${existingProgress.id}`,
            {
              method: "PATCH",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({
                progress_percentage: 0,
                status: "not_started",
              }),
            }
          );

          const data = await response.json();

          if (!response.ok) {
            throw new Error(
              data.error || "Failed to update progress"
            );
          }

          setProgressRecords((current) =>
            current.map((record) =>
              record.id === existingProgress.id
                ? {
                    ...record,
                    progress_percentage: 0,
                    status: "not_started",
                  }
                : record
            )
          );
        }

        return;
      }

      // ------------------------------------------------
      // CHECK → create/update progress to 100%
      // ------------------------------------------------
      if (existingProgress) {
        const response = await fetch(
          `${API_URL}/progress/${existingProgress.id}`,
          {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              progress_percentage: 100,
              status: "completed",
            }),
          }
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error || "Failed to update progress"
          );
        }

        setProgressRecords((current) =>
          current.map((record) =>
            record.id === existingProgress.id
              ? {
                  ...record,
                  progress_percentage: 100,
                  status: "completed",
                }
              : record
          )
        );
      } else {
        const response = await fetch(
          `${API_URL}/progress`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              path_topic_id: topic.id,
              progress_percentage: 100,
              status: "completed",
            }),
          }
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.error || "Failed to save progress"
          );
        }

        setProgressRecords((current) => [
          ...current,
          {
            id: data.id,
            path_topic_id: topic.id,
            progress_percentage: 100,
            status: "completed",
          },
        ]);
      }
    } catch (error) {
      console.error(
        "Failed to update topic progress:",
        error
      );

      setMessage(error.message);
    }
  };

  // ------------------------------------------------
  // Calculate overall DSA progress
  // ------------------------------------------------

  const completedCount = topics.filter((topic) => {
    const record = progressRecords.find(
      (progress) =>
        progress.path_topic_id === topic.id
    );

    return (
      record &&
      Number(record.progress_percentage) >= 100
    );
  }).length;

  const progress =
    topics.length === 0
      ? 0
      : Math.round(
          (completedCount / topics.length) * 100
        );

  return (
    <main className="flex-1 p-8">
      <h1 className="text-3xl font-bold text-gray-900">
        Data Structures & Algorithms
      </h1>

      <p className="mt-2 text-gray-600">
        Master the core topics required for technical interviews.
      </p>

      {message && (
        <div className="mt-6 max-w-2xl rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
          {message}
        </div>
      )}

      {/* Overall Progress */}
      <div className="mt-8 max-w-2xl rounded-2xl bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Your Progress
            </h2>

            <p className="mt-1 text-sm text-gray-500">
              {loading
                ? "Loading..."
                : `${completedCount} of ${topics.length} topics completed`}
            </p>
          </div>

          <span className="text-2xl font-bold text-violet-600">
            {loading ? "..." : `${progress}%`}
          </span>
        </div>

        <div className="mt-4 h-2 w-full rounded-full bg-gray-100">
          <div
            className="h-2 rounded-full bg-violet-500 transition-all"
            style={{
              width: `${progress}%`,
            }}
          />
        </div>
      </div>

      {/* Topics */}
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {loading ? (
          <p className="text-sm text-gray-500">
            Loading topics...
          </p>
        ) : (
          topics.map((topic) => {
            const record = progressRecords.find(
              (progress) =>
                progress.path_topic_id === topic.id
            );

            const completed =
              !!record &&
              Number(record.progress_percentage) >= 100;

            return (
              <TopicCard
                key={topic.id}
                title={topic.title}
                description={topic.description}
                completed={completed}
                onToggle={() => toggleTopic(topic)}
              />
            );
          })
        )}
      </div>
    </main>
  );
}
