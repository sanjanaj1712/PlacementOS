"use client";

import Link from "next/link";
import TodaysFocus from "@/components/TodaysFocus";
import { useApi } from "@/lib/useApi";

const applicationStatusLabels = {
  interested: "Interested",
  applied: "Applied",
  oa: "OA",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
};

const activityLabels = {
  goal: "Goal",
  application: "Application",
  topic: "Topic",
};

function ProgressBar({ value }) {
  return (
    <div className="h-2 w-full rounded-full bg-gray-100">
      <div
        className="h-2 rounded-full bg-violet-500 transition-all"
        style={{ width: `${value}%` }}
      />
    </div>
  );
}

function formatStatus(status) {
  return (applicationStatusLabels[status] || status).replaceAll("_", " ");
}

export default function Dashboard() {
  const { data, loading, error } = useApi("/dashboard");

  const goal = data?.goals.current;
  const topics = data?.topics;
  const applications = data?.applications;

  return (
    <main className="flex-1 p-8">
      <h1 className="text-3xl font-bold text-gray-900">
        Dashboard
      </h1>

      <p className="mt-2 text-gray-600">
        Here&apos;s your placement progress.
      </p>

      {error && (
        <div className="mt-6 max-w-2xl rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="mt-8 grid gap-4 md:grid-cols-3">

        {/* Placement Goal */}
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Placement Goal
          </h2>

          <p className="mt-2 text-gray-600">
            {loading
              ? "Loading..."
              : goal
              ? `${goal.target_role} · by ${goal.target_date}`
              : "No goal set"}
          </p>

          {goal ? (
            <div className="mt-4">
              <div className="mb-2 flex justify-between text-sm">
                <span className="text-gray-500">
                  Progress
                </span>

                <span className="font-medium text-gray-900">
                  {goal.progress_percentage}%
                </span>
              </div>

              <ProgressBar value={goal.progress_percentage} />
            </div>
          ) : (
            !loading && (
              <Link
                href="/goals"
                className="mt-4 inline-block text-sm font-medium text-violet-600 hover:underline"
              >
                Set a goal
              </Link>
            )
          )}

          {data && data.goals.total > 1 && (
            <p className="mt-3 text-xs text-gray-500">
              {data.goals.total} goals · {data.goals.by_status.achieved} achieved
            </p>
          )}
        </div>

        {/* Topics Completed */}
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Topics Completed
          </h2>

          <p className="mt-2 text-3xl font-bold text-gray-900">
            {loading || !topics
              ? "..."
              : `${topics.completed} / ${topics.total}`}
          </p>

          <p className="mt-1 text-sm text-gray-500">
            {topics ? `${topics.progress_percentage}% overall` : ""}
          </p>
        </div>

        {/* Applications */}
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Applications
          </h2>

          <p className="mt-2 text-3xl font-bold text-gray-900">
            {loading || !applications ? "..." : applications.total}
          </p>

          <p className="mt-1 text-sm text-gray-500">
            {applications
              ? `${applications.active} active · ${applications.by_status.offer} offers`
              : ""}
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">

        {/* Subject progress */}
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Preparation by Subject
          </h2>

          <div className="mt-4 space-y-4">
            {(topics?.paths || []).map((path) => (
              <Link
                key={path.id}
                href={`/learning/${path.id}`}
                className="block"
              >
                <div className="mb-2 flex justify-between text-sm">
                  <span className="text-gray-700">{path.title}</span>

                  <span className="font-medium text-gray-900">
                    {path.completed_count}/{path.topic_count}
                  </span>
                </div>

                <ProgressBar value={path.progress_percentage} />
              </Link>
            ))}
          </div>
        </div>

        {/* Application pipeline */}
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Application Pipeline
          </h2>

          <div className="mt-4 grid grid-cols-3 gap-3">
            {Object.entries(applications?.by_status || {}).map(
              ([status, count]) => (
                <div key={status} className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-500">
                    {formatStatus(status)}
                  </p>

                  <p className="mt-1 text-xl font-bold text-gray-900">
                    {count}
                  </p>
                </div>
              )
            )}
          </div>
        </div>
      </div>

      {/* Recent activity */}
      <div className="mt-4 rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">
          Recent Activity
        </h2>

        {data && data.recent_activity.length === 0 && (
          <p className="mt-4 text-sm text-gray-500">
            Nothing yet. Set a goal, study a topic or add an application.
          </p>
        )}

        <ul className="mt-4 divide-y divide-gray-100">
          {(data?.recent_activity || []).map((item) => (
            <li
              key={`${item.type}-${item.id}`}
              className="flex items-center justify-between gap-4 py-3 text-sm"
            >
              <span className="text-gray-700">
                <span className="mr-2 rounded bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-700">
                  {activityLabels[item.type]}
                </span>
                {item.title}
              </span>

              <span className="shrink-0 text-gray-500">
                {formatStatus(item.status)} ·{" "}
                {new Date(item.updated_at).toLocaleDateString()}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <TodaysFocus />
    </main>
  );
}
