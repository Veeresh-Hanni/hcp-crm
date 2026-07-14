import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchHistory } from "../store/interactionsSlice";
import SentimentBadge from "./SentimentBadge";
import "./InteractionHistoryList.css";

export default function InteractionHistoryList() {
  const dispatch = useDispatch();
  const { selectedHcp } = useSelector((s) => s.hcps);
  const { history, lastCreated, submitStatus } = useSelector((s) => s.interactions);
  const { messages } = useSelector((s) => s.chat);

  useEffect(() => {
    if (selectedHcp) dispatch(fetchHistory(selectedHcp.id));
  }, [selectedHcp, dispatch, submitStatus, messages.length]);

  if (!selectedHcp) {
    return (
      <div className="history history--empty">
        <p>Select an HCP to see their interaction history.</p>
      </div>
    );
  }

  return (
    <div className="history">
      <h3 className="history__title">History — {selectedHcp.name}</h3>
      {history.length === 0 && <p className="history__empty-note">No interactions logged yet.</p>}
      <ul className="history__list">
        {history.map((h) => (
          <li key={h.id} className="history__item">
            <div className="history__item-top">
              <span className="history__date">{new Date(h.interaction_date).toLocaleDateString()}</span>
              <span className="history__type">{h.type}</span>
              <SentimentBadge sentiment={h.sentiment} />
              {h.compliance_status === "flagged" && <span className="history__flag">flagged</span>}
            </div>
            <p className="history__summary">{h.summary || h.discussion_notes || "—"}</p>
            {h.next_steps && <p className="history__next">Next: {h.next_steps}</p>}
            <span className="history__source">via {h.source}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
