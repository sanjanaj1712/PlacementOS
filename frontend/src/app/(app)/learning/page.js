"use client";

import Link from "next/link";
import { useApi } from "@/lib/useApi";

export default function Learning() {
  const { data, loading, error } = useApi("/learning-paths");
  const learningPaths = data || [];

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
          {learningPaths.map((path) => (
            <Link
              key={path.id}
              href={`/learning/${path.id}`}
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
                    {path.completed_count} of {path.topic_count} topics
                  </span>

                  <span className="font-medium text-gray-900">
                    {path.progress_percentage}%
                  </span>
                </div>

                <div className="h-2 w-full rounded-full bg-gray-100">
                  <div
                    className="h-2 rounded-full bg-violet-500 transition-all"
                    style={{ width: `${path.progress_percentage}%` }}
                  />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
