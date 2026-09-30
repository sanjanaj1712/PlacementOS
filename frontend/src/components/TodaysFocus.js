"use client";

import { useState } from "react";

export default function TodaysFocus() {
  const [completed, setCompleted] = useState([false, false, false]);

  const tasks = [
    "Revise Dynamic Programming",
    "Solve 2 Graph problems",
    "Apply to 1 company",
  ];

  const toggleTask = (index) => {
    const updatedTasks = [...completed];
    updatedTasks[index] = !updatedTasks[index];
    setCompleted(updatedTasks);
  };

  return (
    <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900">
        Today&apos;s Focus
      </h2>

      <div className="mt-4 space-y-3">
        {tasks.map((task, index) => (
          <label
            key={task}
            className={`flex items-center gap-3 text-sm ${
              completed[index]
                ? "text-gray-400 line-through"
                : "text-gray-600"
            }`}
          >
            <input
              type="checkbox"
              checked={completed[index]}
              onChange={() => toggleTask(index)}
            />

            {task}
          </label>
        ))}
      </div>
    </div>
  );
}