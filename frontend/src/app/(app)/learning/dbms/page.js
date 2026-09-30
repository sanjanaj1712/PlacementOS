"use client";

import { useState } from "react";
import TopicCard from "@/components/TopicCard";

const topics = [
  {
    title: "DBMS Fundamentals",
    description:
      "Learn database concepts, DBMS architecture, schemas, instances, and data models.",
  },
  {
    title: "ER Model & Relational Model",
    description:
      "Understand entities, relationships, keys, tables, and relational database concepts.",
  },
  {
    title: "SQL",
    description:
      "Practice SELECT, JOINs, subqueries, aggregation, grouping, and other SQL operations.",
  },
  {
    title: "Normalization",
    description:
      "Learn functional dependencies and normalization using 1NF, 2NF, 3NF, and BCNF.",
  },
  {
    title: "Transactions",
    description:
      "Understand transactions, ACID properties, schedules, and transaction states.",
  },
  {
    title: "Concurrency Control",
    description:
      "Learn locking, serializability, deadlocks, and techniques for managing concurrent transactions.",
  },
  {
    title: "Indexing",
    description:
      "Understand indexes, B+ trees, hashing, and how databases speed up queries.",
  },
  {
    title: "Query Processing & Optimization",
    description:
      "Learn how databases execute queries and optimize query execution plans.",
  },
];

export default function DBMS() {
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
        Database Management Systems
      </h1>

      <p className="mt-2 text-gray-600">
        Master the database concepts commonly asked in technical interviews.
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