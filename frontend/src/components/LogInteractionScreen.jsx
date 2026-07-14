import InteractionForm from "./InteractionForm";
import ChatInterface from "./ChatInterface";
import "./LogInteractionScreen.css";

export default function LogInteractionScreen() {
  return (
    <div className="screen">
      <header className="screen__header">
        <div>
          <h1 className="screen__title">AI Interaction Logger</h1>
          <p className="screen__subtitle">Use the assistant to populate and edit the HCP interaction record.</p>
        </div>
        <span className="screen__badge">LangGraph tool-driven UI</span>
      </header>

      <div className="screen__body">
        <div className="screen__panel screen__panel--form">
          <InteractionForm />
        </div>
        <div className="screen__panel screen__panel--chat">
          <ChatInterface />
        </div>
      </div>
    </div>
  );
}
