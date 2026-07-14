import "./ToolActionChip.css";

const TOOL_LABELS = {
  log_interaction: "Log interaction",
  edit_interaction: "Edit interaction",
  lookup_hcp: "Lookup HCP",
  suggest_next_best_action: "Next best action",
  compliance_check: "Compliance check",
};

const STATUS_DOT = {
  ok: "var(--status-positive)",
  clear: "var(--status-positive)",
  needs_clarification: "var(--status-flagged)",
  flagged: "var(--status-negative)",
  error: "var(--status-negative)",
  not_found: "var(--status-flagged)",
  no_history: "var(--status-neutral)",
};

export default function ToolActionChip({ action }) {
  const label = TOOL_LABELS[action.tool] || action.tool;
  const dotColor = STATUS_DOT[action.status] || "var(--status-neutral)";

  return (
    <div className="tool-chip">
      <span className="tool-chip__dot" style={{ background: dotColor }} />
      <span className="tool-chip__name">{label}</span>
      <span className="tool-chip__status">{action.status}</span>
    </div>
  );
}
