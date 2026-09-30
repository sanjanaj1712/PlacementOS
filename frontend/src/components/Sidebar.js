"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const logout = async () => {
    await supabase.auth.signOut();
    router.replace("/");
  };

  const isActive = (path) => {
    if (path === "/dashboard") {
      return pathname === "/dashboard";
    }

    if (path === "/learning") {
      return pathname.startsWith("/learning");
    }

    return pathname === path;
  };

  const linkClass = (path) =>
    `rounded-lg px-4 py-3 text-sm font-medium transition ${
      isActive(path)
        ? "bg-violet-50 text-violet-700"
        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
    }`;

  return (
    <aside className="flex min-h-screen w-64 shrink-0 flex-col border-r border-gray-200 bg-white p-6">
      {/* Logo */}
      <h1 className="text-xl font-bold tracking-tight text-gray-900">
        PlacementOS
      </h1>

      {/* Navigation */}
      <nav className="mt-8 flex flex-col gap-2">
        <Link href="/dashboard" className={linkClass("/dashboard")}>
          Dashboard
        </Link>

        <Link href="/goals" className={linkClass("/goals")}>
          Goals
        </Link>

        <Link href="/learning" className={linkClass("/learning")}>
          Learning Paths
        </Link>

        <Link href="/applications" className={linkClass("/applications")}>
          Applications
        </Link>
      </nav>

      {/* Account */}
      <div className="mt-8">
        <p className="px-4 text-xs font-semibold uppercase tracking-wider text-gray-400">
          Account
        </p>

        <Link
          href="/profile"
          className={`mt-3 block ${linkClass("/profile")}`}
        >
          Profile
        </Link>

        <button
          onClick={logout}
          className="mt-2 w-full rounded-lg px-4 py-3 text-left text-sm font-medium text-gray-600 transition hover:bg-gray-50 hover:text-gray-900"
        >
          Log out
        </button>
      </div>

      {/* Footer */}
      <div className="mt-auto border-t border-gray-100 pt-4">
        <p className="text-xs text-gray-400">PlacementOS</p>

        <p className="mt-1 text-xs text-gray-500">
          Placement companion
        </p>
      </div>
    </aside>
  );
}