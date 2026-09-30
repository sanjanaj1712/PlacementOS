"use client";

import { useState } from "react";
import TopicCard from "@/components/TopicCard";

const topics = [
  {
    title: "Network Fundamentals",
    description:
      "Learn the basics of computer networks, protocols, network architecture, and the Internet.",
  },
  {
    title: "Application Layer",
    description:
      "Understand HTTP, DNS, email protocols, and how applications communicate over networks.",
  },
  {
    title: "Transport Layer",
    description:
      "Learn TCP, UDP, reliable data transfer, flow control, and congestion control.",
  },
  {
    title: "Network Layer",
    description:
      "Understand IP addressing, routing, forwarding, routing algorithms, and IPv4/IPv6.",
  },
  {
    title: "Data Link Layer",
    description:
      "Learn framing, error detection, MAC protocols, Ethernet, and switching.",
  },
  {
    title: "Physical Layer",
    description:
      "Understand how bits are transmitted through physical communication media.",
  },
  {
    title: "Network Security",
    description:
      "Learn the fundamentals of encryption, authentication, firewalls, and common network attacks.",
  },
  {
    title: "Wireless & Mobile Networks",
    description:
      "Understand Wi-Fi, wireless communication, mobility, and cellular networks.",
  },
];

export default function ComputerNetworks() {
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
        Computer Networks
      </h1>

      <p className="mt-2 text-gray-600">
        Master the networking concepts commonly asked in technical interviews.
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