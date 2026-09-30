"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import TopicCard from "@/components/TopicCard";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/useApi";

export default function LearningPath() {
  const { pathId } = useParams();

  const paths = useApi("/learning-paths");
  const topicsRequest = useApi(`/learning-paths/${pathId}/topics`);

  const [savingId, setSavingId] = useState(null);
  const [error, setError] = useState("");

  const path = (paths.data || []).find(
    (item) => String(item.id) === String(pathId)
  );
  const topics = topicsRequest.data || [];
  const loading = paths.loading || topicsRequest.loading;
  const loadError = topicsRequest.error || paths.error;

  const topLevel = topics.filter((topic) => !topic.parent_topic_id);
  const subtopicsOf = (topicId) =>
    topics.filter((topic) => topic.parent_topic_id === topicId);

  const completedCount = topics.filter(
    (topic) => topic.status === "completed"
  ).length;

  const progress =
    topics.length === 0
      ? 0
      : Math.round((completedCount / topics.length) * 100);

  const toggleTopic = async (topic) => {
    const completed = topic.status === "completed";

    try {
      setSavingId(topic.id);
      setError("");

      // The API upserts, so this creates or updates the user's record.
      await apiFetch("/progress", {
        method: "POST",
        body: {
          path_topic_id: topic.id,
          status: completed ? "not_started" : "completed",
          progress_percentage: completed ? 0 : 100,
        },
      });

      topicsRequest.reload();
      paths.reload();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingId(null);
    }
  };

  return (
    <main className="flex-1 p-8">
      <Link
        href="/learning"
        className="text-sm font-medium text-violet-600 hover:underline"
      >
        ← All learning paths
      </Link>

      <h1 className="mt-4 text-3xl font-bold text-gray-900">
        {path?.title || (loading ? "Loading..." : "Learning path")}
      </h1>

      {path?.description && (
        <p className="mt-2 text-gray-600">{path.description}</p>
      )}

      {(error || loadError) && (
        <div className="mt-6 max-w-2xl rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
          {error || loadError}
        </div>
      )}

      {!loadError && (
        <>
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
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Topics */}
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {loading ? (
              <p className="text-sm text-gray-500">Loading topics...</p>
            ) : (
              topLevel.map((topic) => (
                <TopicCard
                  key={topic.id}
                  title={topic.title}
                  description={topic.description}
                  resourceUrl={topic.resource_url}
                  completed={topic.status === "completed"}
                  progress={topic.progress_percentage}
                  disabled={savingId === topic.id}
                  onToggle={() => toggleTopic(topic)}
                  subtopics={subtopicsOf(topic.id).map((subtopic) => ({
                    id: subtopic.id,
                    title: subtopic.title,
                    completed: subtopic.status === "completed",
                    disabled: savingId === subtopic.id,
                    onToggle: () => toggleTopic(subtopic),
                  }))}
                />
              ))
            )}
          </div>
        </>
      )}
    </main>
  );
}
