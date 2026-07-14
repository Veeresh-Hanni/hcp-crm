import { useState, useRef, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { sendMessage } from "../store/chatSlice";
import ToolActionChip from "./ToolActionChip";
import "./ChatInterface.css";

const REP_ID = "demo-rep-001";

const SUGGESTIONS = [
  "Today I met with Dr. Smith and discussed product X efficiency. The sentiment was positive and I shared the brochures.",
  "Sorry, the name was actually Dr. John and the sentiment was negative.",
  "What's the latest with Dr. John?",
  "What should I bring up with Dr. John next visit?",
  "Run a compliance review on this interaction.",
];

const TOOLS = [
  "log_interaction",
  "edit_interaction",
  "lookup_hcp",
  "suggest_next_best_action",
  "compliance_check",
];

export default function ChatInterface() {
  const dispatch = useDispatch();
  const { sessionId, messages, status } = useSelector((s) => s.chat);
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = (text) => {
    const trimmed = text.trim();
    if (!trimmed || status === "loading") return;
    dispatch(sendMessage({ sessionId, repId: REP_ID, text: trimmed }));
    setInput("");
  };

  return (
    <div className="chat">
      <div className="chat__header">
        <div>
          <p className="chat__eyebrow">AI Assistant</p>
          <h2 className="chat__title">Chat to update the form</h2>
        </div>
        <div className="chat__tools" aria-label="Available tools">
          {TOOLS.map((tool) => (
            <span key={tool} className="chat__tool">
              {tool}
            </span>
          ))}
        </div>
      </div>

      <div className="chat__log" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat__empty">
            <p>Describe an interaction or correction. The assistant will run tools and update the form.</p>
            <div className="chat__suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="chat__suggestion" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`chat__bubble-row chat__bubble-row--${m.role}`}>
            <div className={`chat__bubble chat__bubble--${m.role}`}>
              {m.content}
              {m.toolActions?.map((action, j) => (
                <ToolActionChip key={j} action={action} />
              ))}
            </div>
          </div>
        ))}

        {status === "loading" && (
          <div className="chat__bubble-row chat__bubble-row--agent">
            <div className="chat__bubble chat__bubble--agent chat__bubble--typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
      </div>

      <form
        className="chat__composer"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          className="chat__input"
          placeholder="Describe the interaction, or ask a question…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button className="btn btn--primary" type="submit" disabled={status === "loading"}>
          Send
        </button>
      </form>
    </div>
  );
}
