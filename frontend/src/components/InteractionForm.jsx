import { useSelector } from "react-redux";
import "./InteractionForm.css";

const MATERIALS = [
  { key: "brochures", label: "Brochures" },
  { key: "samples", label: "Samples" },
  { key: "presentation", label: "Presentation" },
  { key: "study", label: "Clinical study" },
];

const displayValue = (value) => value || "Waiting for assistant";

export default function InteractionForm() {
  const { interactionDraft, lastToolName } = useSelector((s) => s.interactions);
  const materials = interactionDraft.materials_shared || {};

  return (
    <section className="interaction-form" aria-label="AI-controlled interaction details">
      <div className="interaction-form__header">
        <div>
          <p className="interaction-form__eyebrow">Interaction Details</p>
          <h2 className="interaction-form__title">AI-controlled form</h2>
        </div>
        <span className="interaction-form__status">{lastToolName || "Awaiting tool"}</span>
      </div>

      <div className="field">
        <label className="field-label" htmlFor="hcp-name">
          HCP Name
        </label>
        <input
          id="hcp-name"
          className="field-input field-input--readonly"
          value={displayValue(interactionDraft.hcp_name)}
          readOnly
        />
      </div>

      <div className="field-row">
        <div className="field">
          <label className="field-label" htmlFor="date">
            Date
          </label>
          <input
            id="date"
            className="field-input field-input--readonly"
            value={displayValue(interactionDraft.interaction_date)}
            readOnly
          />
        </div>
        <div className="field">
          <label className="field-label" htmlFor="sentiment">
            Sentiment
          </label>
          <input
            id="sentiment"
            className="field-input field-input--readonly"
            value={displayValue(interactionDraft.sentiment)}
            readOnly
          />
        </div>
      </div>

      <div className="field">
        <label className="field-label" htmlFor="discussion-product">
          Discussion/Product
        </label>
        <textarea
          id="discussion-product"
          className="field-input field-input--readonly"
          rows={3}
          value={displayValue(interactionDraft.discussion_product || interactionDraft.discussion_notes)}
          readOnly
        />
      </div>

      <div className="materials">
        <p className="field-label">Materials Shared</p>
        <div className="materials__grid">
          {MATERIALS.map((item) => (
            <label key={item.key} className="materials__item">
              <input type="checkbox" checked={Boolean(materials[item.key])} readOnly />
              <span>{item.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="field">
        <label className="field-label" htmlFor="next-steps">
          Next Steps
        </label>
        <input
          id="next-steps"
          className="field-input field-input--readonly"
          value={displayValue(interactionDraft.next_steps)}
          readOnly
        />
      </div>
    </section>
  );
}
