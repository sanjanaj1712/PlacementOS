"use client";

export default function TopicCard({
  title,
  description,
  resourceUrl,
  completed,
  progress = completed ? 100 : 0,
  disabled = false,
  onToggle,
  subtopics = [],
}) {
  // Only link to http(s) resources; anything else could run script.
  const safeResourceUrl = /^https?:\/\//i.test(resourceUrl || "")
    ? resourceUrl
    : null;

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900">
        {title}
      </h2>

      <p className="mt-2 text-sm text-gray-500">
        {description}
      </p>

      {safeResourceUrl && (
        <a
          href={safeResourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-block text-sm font-medium text-violet-600 hover:underline"
        >
          Study resource
        </a>
      )}

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
          disabled={disabled}
          onChange={onToggle}
          className="h-4 w-4 rounded"
        />

        {completed ? "Completed" : "Mark as completed"}
      </label>

      {subtopics.length > 0 && (
        <ul className="mt-4 space-y-2 border-l-2 border-violet-100 pl-4">
          {subtopics.map((subtopic) => (
            <li key={subtopic.id}>
              <label
                className={`flex cursor-pointer items-center gap-3 text-sm ${
                  subtopic.completed
                    ? "text-gray-400 line-through"
                    : "text-gray-600"
                }`}
              >
                <input
                  type="checkbox"
                  checked={subtopic.completed}
                  disabled={subtopic.disabled}
                  onChange={subtopic.onToggle}
                  className="h-4 w-4 rounded"
                />

                {subtopic.title}
              </label>
            </li>
          ))}
        </ul>
      )}

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
