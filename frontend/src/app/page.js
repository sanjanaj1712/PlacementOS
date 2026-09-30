"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function Home() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignup, setIsSignup] = useState(false);

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  // Already signed in: go straight to the dashboard.
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.replace("/dashboard");
      }
    });
  }, [router]);

  const handleAuth = async () => {
    if (!email || !password) {
      setMessage("Please enter your email and password.");
      return;
    }

    try {
      setLoading(true);
      setMessage("");

      if (isSignup) {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
        });

        if (error) {
          throw error;
        }

        // Projects without email confirmation sign the user in right away.
        if (data.session) {
          router.replace("/dashboard");
          return;
        }

        setMessage(
          "Account created. Check your email to confirm it, then log in."
        );
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (error) {
          throw error;
        }

        // supabase-js keeps and refreshes the session itself.
        router.replace("/dashboard");
      }
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm">
        <h1 className="text-3xl font-bold text-gray-900">
          PlacementOS
        </h1>

        <p className="mt-2 text-gray-600">
          {isSignup
            ? "Create your placement account."
            : "Welcome back. Let's get you placement-ready."}
        </p>

        <div className="mt-8 space-y-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-gray-200 px-4 py-3 text-gray-900 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-gray-200 px-4 py-3 text-gray-900 outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
          />

          <button
            onClick={handleAuth}
            disabled={loading}
            className="w-full rounded-lg bg-violet-600 px-5 py-3 font-medium text-white transition hover:bg-violet-700 disabled:opacity-50"
          >
            {loading
              ? "Please wait..."
              : isSignup
              ? "Create Account"
              : "Login"}
          </button>

          {message && (
            <p className="text-sm text-gray-600">
              {message}
            </p>
          )}

          <button
            onClick={() => {
              setIsSignup(!isSignup);
              setMessage("");
            }}
            className="w-full text-sm text-violet-600 hover:underline"
          >
            {isSignup
              ? "Already have an account? Login"
              : "Don\u2019t have an account? Sign up"}
          </button>
        </div>
      </div>
    </main>
  );
}