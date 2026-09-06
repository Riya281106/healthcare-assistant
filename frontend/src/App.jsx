import { useState } from "react";
import "./App.css";
import Auth from "./Auth.jsx";
const API_URL = "http://127.0.0.1:8000/api/chat";

function App() {
  const [authToken, setAuthToken] = useState(
    localStorage.getItem("authToken")
  );

  const [currentUser, setCurrentUser] = useState(
    JSON.parse(localStorage.getItem("currentUser") || "null")
  );

      const handleLoginSuccess = (token, user) => {

    localStorage.setItem("authToken", token);
    localStorage.setItem("currentUser", JSON.stringify(user));

    setAuthToken(token);
    setCurrentUser(user);
  };


  const handleLogout = () => {

    localStorage.removeItem("authToken");
    localStorage.removeItem("currentUser");

    setAuthToken(null);
    setCurrentUser(null);
  };
  
  const [message, setMessage] = useState("");

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I am your Agentic Healthcare Assistant. How can I help you today?",
      tier: "general",
    },
  ]);

  const [loading, setLoading] = useState(false);


  const sendMessage = async () => {
    const trimmedMessage = message.trim();

    if (!trimmedMessage || loading) {
      return;
    }


    const userMessage = {
      role: "user",
      content: trimmedMessage,
      tier: null,
    };


    setMessages((previousMessages) => [
      ...previousMessages,
      userMessage,
    ]);


    setMessage("");
    setLoading(true);


    try {

      const response = await fetch(
        API_URL,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

                    body: JSON.stringify({
            user_id: String(currentUser.id),
            message: trimmedMessage,
          }),
        }
      );


      const data = await response.json();


      if (!response.ok) {

        throw new Error(
          data.detail ||
          "Backend request failed"
        );
      }


      setMessages((previousMessages) => [

        ...previousMessages,

        {
          role: "assistant",

          content:
            data.response ||
            "I am sorry, I could not generate a response.",

          tier: data.urgency_tier || "general",
        },
      ]);

    } catch (error) {

      console.error(
        "CHAT ERROR:",
        error
      );


      setMessages((previousMessages) => [

        ...previousMessages,

        {
          role: "assistant",

          content:
            "Sorry, I could not connect to the healthcare assistant backend. Please make sure the backend server is running on port 8000.",

          tier: "general",
        },
      ]);

    } finally {

      setLoading(false);
    }
  };


  const handleKeyDown = (event) => {

    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {

      sendMessage();
    }
  };


  if (!authToken || !currentUser) {

    return <Auth onLoginSuccess={handleLoginSuccess} />;
  }


  return (

    <div className="app-container">

      {/* ================= SIDEBAR ================= */}

      <aside className="sidebar">

        <h2>Healthcare AI</h2>


        <div className="sidebar-section">

          <p>
            Agentic Healthcare Assistant
          </p>

        </div>


               <div className="sidebar-info">

          <p>✓ LLM Powered</p>

          <p>✓ RAG Enabled</p>

          <p>✓ Memory Enabled</p>

          <p>✓ Agentic Workflow</p>

        </div>


        <button
          onClick={handleLogout}
          style={{
            marginTop: "20px",
            padding: "10px",
            background: "#dc2626",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
          }}
        >
          Log Out
        </button>
      </aside>


      {/* ================= CHAT ================= */}

      <main className="chat-container">


        <header className="chat-header">

          <div>

            <h1>
              Agentic Healthcare Assistant
            </h1>

            <p>
              AI-powered healthcare assistance with intelligent agents
            </p>

          </div>


          <div className="status">

            <span className="status-dot"></span>

            System Active

          </div>

        </header>


        {/* ================= MESSAGES ================= */}

        <section className="messages-container">

          {messages.map((item, index) => (

            <div
              key={index}
              className={`message-row ${item.role}`}
            >

              <div
                className={`message ${item.role} ${
                  item.role === "assistant"
                    ? `tier-${item.tier || "general"}`
                    : ""
                }`}
              >

                <strong>

                  {item.role === "user"
                    ? "You"
                    : "Healthcare AI"}

                </strong>


                <p>
                  {item.content}
                </p>

              </div>

            </div>

          ))}


          {loading && (

            <div className="message-row assistant">

              <div className="message assistant">

                <strong>
                  Healthcare AI
                </strong>

                <p>
                  Thinking...
                </p>

              </div>

            </div>

          )}

        </section>


        {/* ================= INPUT ================= */}

        <div className="input-container">

          <input

            type="text"

            placeholder="Describe your symptoms or ask a healthcare question..."

            value={message}

            onChange={(event) =>
              setMessage(event.target.value)
            }

            onKeyDown={handleKeyDown}

            disabled={loading}

          />


          <button

            onClick={sendMessage}

            disabled={loading}

          >

            {loading
              ? "..."
              : "Send"}

          </button>

        </div>

      </main>

    </div>
  );
}


export default App;