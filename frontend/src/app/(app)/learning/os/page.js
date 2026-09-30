"use client";

import { useState } from "react";
import TopicCard from "@/components/TopicCard";

const topics = [
  {
    title: "Processes & Threads",
    description:
      "Understand processes, threads, process states, and how they differ.",
  },
  {
    title: "CPU Scheduling",
    description:
      "Learn scheduling algorithms such as FCFS, SJF, Round Robin, and Priority Scheduling.",
  },
  {
    title: "Process Synchronization",
    description:
      "Learn critical sections, semaphores, mutexes, and synchronization problems.",
  },
  {
    title: "Deadlocks",
    description:
      "Understand deadlock conditions, prevention, avoidance, and detection.",
  },
  {
    title: "Memory Management",
    description:
      "Learn memory allocation, paging, segmentation, and address translation.",
  },
  {
    title: "Virtual Memory",
    description:
      "Understand virtual memory, page faults, demand paging, and page replacement.",
  },
  {
    title: "File Systems",
    description:
      "Learn file organization, directories, allocation methods, and file-system concepts.",
  },
  {
    title: "I/O Systems",
    description:
      "Understand I/O hardware, interrupts, buffering, and device management.",
  },
];

export default function OperatingSystems() {
  const [completedTopics, setCompletedTopics] = useState([]);

  const toggleTopic = (index) => {
    setCompletedTopics((current) => {
      if (current.includes(index)) {
        return current.filter((item) => item !== index);
      }

      return [...current, index];
    });
  };

  const completedCount = completedTopics.length;

  const progress = Math.round(
    (completedCount / topics.length) * 100
  );

  return (
    <main className="flex-1 p-8">
      <h1 className="text-3xl font-bold text-gray-900">
        Operating Systems
      </h1>

      <p className="mt-2 text-gray-600">
        Master the core operating system concepts required for technical interviews.
      </p>

      {/* Overall Progress */}
      <div className="mt-8 max-w-2xl rounded-2xl bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Your Progress
            </h2>

            <p className="mt-1 text-sm text-gray-500">
              {completedCount} of {topics.length} topics completed
            </p>
          </div>

          <span className="text-2xl font-bold text-violet-600">
            {progress}%
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
        {topics.map((topic, index) => (
          <TopicCard
            key={topic.title}
            title={topic.title}
            description={topic.description}
            completed={completedTopics.includes(index)}
            onToggle={() => toggleTopic(index)}
          />
        ))}
      </div>
    </main>
  );
}