import { useState, useEffect, useRef } from "react";
import MessageList from "../components/MessageList";
import InputArea from "../components/InputArea";
import ThemeToggle from "../components/ThemeToggle";
import { sendMessage } from "../services/api";
import { sendToAgent } from "../services/api"
import "./Chat.css";
import { v4 as uuidv4 } from "uuid";

function Chat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [theme, setTheme] = useState("light");
  const bottomRef = useRef(null);
  const [sessionId, setSessionId] = useState("");


  const createNewSession = () => {
  const id = uuidv4();

  sessionStorage.setItem("session_id", id);
  setSessionId(id);

  setMessages([]); // clear chat
};

useEffect(() => {
  let id = sessionStorage.getItem("session_id");

  if (!id) {
    id = uuidv4(); // new session per tab/session
    sessionStorage.setItem("session_id", id);
  }

  setSessionId(id);
}, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const toggleTheme = () => setTheme((t) => (t === "light" ? "dark" : "light"));

  const handleSend = async (text) => {
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);
    try {
      const data = await sendToAgent(sessionId,text);
      //const data = await sendMessage(sessionId,text);
      setMessages((prev) => [...prev, { role: "assistant", text: data.answer  }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Error: could not reach server." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const started = messages.length > 0;

  return (
    <div className="chat-page">
      <div className="main">
        <div className="topbar">
          <button className="new-thread-pill" onClick={createNewSession}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
            <span>New conversation</span>
          </button>
          <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
        </div>

        {!started ? (
          <div className="landing">
            <h1>How can I help you today?</h1>
            <InputArea onSend={handleSend} disabled={loading} />
          </div>
        ) : (
          <>
            <MessageList messages={messages} loading={loading} />
            <div ref={bottomRef} />
            <InputArea onSend={handleSend} disabled={loading} />
          </>
        )}
      </div>
    </div>
  );
}

export default Chat;