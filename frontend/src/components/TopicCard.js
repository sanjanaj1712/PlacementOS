"use client";

export default function TopicCard({
  title,
  description,
  completed,
  onToggle,
}) {
  const progress = completed ? 100 : 0;

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900">
        {title}
      </h2>

      <p className="mt-2 text-sm text-gray-500">
        {description}
      </p>

      <label
        className={`mt-4 flex cursor-pointer items-center gap-3 text-sm ${
          completed
            ? "text-gray-400 line-through"
            : "text-gray-600"
        }`}
      >
        <input
          type="checkbox"
          checked={completed}
          onChange={onToggle}
          className="h-4 w-4 rounded"
        />

        {completed ? "Completed" : "Mark as completed"}
      </label>

      <div className="mt-4">
        <div className="mb-2 flex justify-between text-xs">
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
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  );
}