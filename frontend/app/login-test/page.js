"use client";

import { useState } from "react";
import { signIn, signOut, useSession } from "next-auth/react";

export default function LoginTestPage() {
  const { data: session, status } = useSession();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  async function handleLogin(event) {
    event.preventDefault();

    setMessage("Signing in...");

    const result = await signIn("credentials", {
      email,
      password,
      redirect: false,
    });

    if (result?.error) {
      setMessage("Login failed.");
      return;
    }

    setMessage("Login successful.");
  }

  async function handleLogout() {
    await signOut({ redirect: false });
    setMessage("Logged out.");
  }

  if (status === "loading") {
    return <p>Checking session...</p>;
  }

  return (
    <main style={{ padding: "40px", maxWidth: "500px" }}>
      <h1>Auth Test</h1>

      {session ? (
        <div>
          <h2>Authenticated ✅</h2>

          <p>
            <strong>Name:</strong> {session.user?.name}
          </p>

          <p>
            <strong>Email:</strong> {session.user?.email}
          </p>

          <p>
            <strong>User ID:</strong> {session.user?.id}
          </p>

          <p>
            <strong>Role:</strong> {session.user?.role}
          </p>

          <button onClick={handleLogout}>
            Logout
          </button>

          {message && <p>{message}</p>}
        </div>
      ) : (
        <form onSubmit={handleLogin}>
          <div>
            <label>Email</label>
            <br />
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <br />

          <div>
            <label>Password</label>
            <br />
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          <br />

          <button type="submit">
            Login
          </button>

          {message && <p>{message}</p>}
        </form>
      )}
    </main>
  );
}