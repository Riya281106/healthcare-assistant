import { useState } from "react";

const AUTH_BASE_URL = "http://127.0.0.1:8000/api/auth";


function Auth({ onLoginSuccess }) {

  const [mode, setMode] = useState("login");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);


  const handleSubmit = async () => {

    setError("");

    if (!email.trim() || !password.trim()) {
      setError("Please enter both email and password.");
      return;
    }

    if (mode === "register" && !name.trim()) {
      setError("Please enter your name.");
      return;
    }


    setLoading(true);

    try {

      const endpoint =
        mode === "register"
          ? `${AUTH_BASE_URL}/register`
          : `${AUTH_BASE_URL}/login`;

      const body =
        mode === "register"
          ? { name: name.trim(), email: email.trim(), password }
          : { email: email.trim(), password };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Something went wrong.");
      }

      onLoginSuccess(data.access_token, data.user);

    } catch (err) {

      setError(err.message);

    } finally {

      setLoading(false);
    }
  };


  return (
    <div className="auth-page">
      <div className="auth-card">
        <h2>{mode === "login" ? "Log in" : "Create account"}</h2>

        {mode === "register" && (
          <input
            type="text"
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        )}

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && <p className="auth-error">{error}</p>}

        <button onClick={handleSubmit} disabled={loading}>
          {loading ? "Please wait..." : mode === "login" ? "Log in" : "Sign up"}
        </button>

        <p className="auth-switch">
          {mode === "login" ? (
            <>
              No account?{" "}
              <span onClick={() => setMode("register")}>Sign up</span>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <span onClick={() => setMode("login")}>Log in</span>
            </>
          )}
        </p>
      </div>
    </div>
  );
}

export default Auth;