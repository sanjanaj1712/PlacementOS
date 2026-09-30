"use client";

import { useEffect, useState } from "react";

const API_URL = "http://127.0.0.1:5000";

const pathRoutes = {
  "Data Structures & Algorithms": "/learning/dsa",
  "Operating Systems": "/learning/os",
  "Computer Networks": "/learning/cn",
  DBMS: "/learning/dbms",
};

export default function Learning() {
  const [learningPaths, setLearningPaths] = useState([]);
  const [pathTopics, setPathTopics] = useState({});
  const [progressRecords, setProgressRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  

  useEffect(() => {
    loadLearningData();
  }, []);

  const loadLearningData = async () => {
    try {
      const token = localStorage.getItem("access_token");

      if (!token) {
        setError("Authentication required.");
        return;
      }

      const headers = {
        Authorization: `Bearer ${token}`,
      };

      // ------------------------------------------------
      // Get learning paths
      // ------------------------------------------------

      const pathsResponse = await fetch(
        `${API_URL}/learning-paths`,
        {
          headers,
        }
      );

      const pathsData = await pathsResponse.json();

      if (!pathsResponse.ok) {
        throw new Error(
          pathsData.error || "Failed to load learning paths"
        );
      }

      // Only show the four subject learning paths.
      const paths = pathsData.filter(
        (path) => pathRoutes[path.title]
      );

      setLearningPaths(paths);

      // ------------------------------------------------
      // Get topics for every learning path
      // ------------------------------------------------

      const topicsByPath = {};

      for (const path of paths) {
        const topicsResponse = await fetch(
          `${API_URL}/learning-paths/${path.id}/topics`,
          {
            headers,
          }
        );

        const topicsData = await topicsResponse.json();

        if (!topicsResponse.ok) {
          throw new Error(
            topicsData.error ||
              `Failed to load topics for ${path.title}`
          );
        }

        topicsByPath[path.id] = topicsData;
      }

      setPathTopics(topicsByPath);

      // ------------------------------------------------
      // Get user's progress
      // ------------------------------------------------

      const progressResponse = await fetch(
        `${API_URL}/progress`,
        {
          headers,
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
      console.error(
        "Failed to load learning data:",
        error
      );

      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  // ------------------------------------------------
  // Calculate progress for one learning path
  // ------------------------------------------------

  const getPathProgress = (pathId) => {
    const topics = pathTopics[pathId] || [];

    if (topics.length === 0) {
      return 0;
    }

    const completedCount = topics.filter((topic) => {
      const record = progressRecords.find(
        (progress) =>
          progress.path_topic_id === topic.id
      );

      return (
        !!record &&
        Number(record.progress_percentage) >= 100
      );
    }).length;

    return Math.round(
      (completedCount / topics.length) * 100
    );
  };

  return (
    <main className="flex-1 p-8">
      <h1 className="text-3xl font-bold text-gray-900">
        Learning Paths
      </h1>

      <p className="mt-2 text-gray-600">
        Build the skills you need for your placement.
      </p>

      {loading && (
        <p className="mt-8 text-sm text-gray-500">
          Loading learning paths...
        </p>
      )}

      {error && (
        <div className="mt-8 max-w-2xl rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          {learningPaths.map((path) => {
            const progress = getPathProgress(path.id);

            return (
              <a
                key={path.id}
                href={pathRoutes[path.title]}
                className="rounded-2xl bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
              >
                <h2 className="text-lg font-semibold text-gray-900">
                  {path.title}
                </h2>

                <p className="mt-2 text-sm text-gray-500">
                  {path.description}
                </p>

                <div className="mt-4">
                  <div className="mb-2 flex justify-between text-sm">
                    <span className="text-gray-500">
                      Progress
                    </span>

                    <span className="font-medium text-gray-900">
                      {progress}%
                    </span>
                  </div>

                  <div className="h-2 w-full rounded-full bg-gray-100">
                    <div
                      className="h-2 rounded-full bg-violet-500 transition-all"
                      style={{
                        width: `${progress}%`,
                      }}
                    />
                  </div>
                </div>
              </a>
            );
          })}
        </div>
      )}
    </main>
  );
}