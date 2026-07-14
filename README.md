# AI-First CRM — HCP Module: Log Interaction Screen

A field-rep-facing "Log Interaction" screen for a healthcare-professional (HCP) CRM. Reps can log an
interaction either through a **structured form** or a **conversational chat interface** backed by a
LangGraph agent running on Groq. Both paths write through the same backend service layer, so the data
model never diverges depending on how a record was created.

Built for the AI-First CRM technical assignment (Round 1).

## What's in here

```
hcp-crm/
├── backend/     FastAPI + SQLAlchemy + LangGraph agent
├── frontend/    React + Redux Toolkit UI
└── README.md    (this file)
```

A full architecture write-up (agent design, all 5 tools, DB schema, API surface) lives in
`docs/hcp-log-interaction-design.md` if included, or see the "Architecture" section below for the summary.

## Architecture summary

- **Frontend:** React + Redux Toolkit, Google Inter font. `LogInteractionScreen` toggles between
  `InteractionForm` (form mode) and `ChatInterface` (chat mode); an `InteractionHistoryList` sidebar
  shows everything logged for the selected HCP so far.
- **Backend:** FastAPI. `/api/interactions` and `/api/hcps` handle form-mode CRUD directly.
  `/api/chat/message` runs one turn of the LangGraph agent per request and persists session state
  (draft interaction, last interaction id, active HCP) on the `chat_sessions` row between turns.
- **Agent:** LangGraph `StateGraph` with a router node (intent classification) that dispatches to one
  of five tool nodes, then a response is returned to the chat UI. See `backend/app/agent/`.
- **LLMs (Groq):** `gemma2-9b-it` is used for the router and for structured-extraction calls inside
  `log_interaction`/`edit_interaction`, where latency matters most in a live chat UI.
  `llama-3.3-70b-versatile` is used for the two calls that benefit more from reasoning depth than
  speed: `suggest_next_best_action` and the compliance-language scan.
- **DB:** Postgres (or MySQL — SQLAlchemy models are portable; connection string controls which).

## The 5 LangGraph tools

1. **`log_interaction`** *(mandatory)* — extracts structured interaction data (HCP, date, type,
   products, samples, sentiment, discussion notes, next steps) from free text via the LLM, fuzzy-resolves
   the HCP name, generates a short LLM summary, validates required fields (asking a clarifying question
   rather than guessing if something's missing), then writes the record.
2. **`edit_interaction`** *(mandatory)* — resolves which interaction to edit (explicit id, or the most
   recent one in the session), has the LLM turn a natural-language correction into a structured field
   diff, applies it, and writes an `audit_log` row per changed field for traceability.
3. **`lookup_hcp`** — fuzzy search on HCP name; returns specialty, last interaction date, interaction
   count, and compliance flags. Used both for direct rep questions and to disambiguate an ambiguous name
   before logging.
4. **`suggest_next_best_action`** — given an HCP's recent interaction history, recommends the next
   talking point and follow-up timing. Uses the 70B model.
5. **`compliance_check`** — checks a logged interaction against a sample-quantity rule and an LLM scan
   of discussion notes for off-label/unsupported-claim language. Flags rather than blocks.

## Running it locally

### Prerequisites
- Python 3.11+
- Node 18+
- A Postgres (or MySQL) instance
- A Groq API key ([console.groq.com](https://console.groq.com))

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DATABASE_URL to your Postgres/MySQL instance, and GROQ_API_KEY

uvicorn app.main:app --reload --port 8000
```

On startup the app creates tables automatically from the SQLAlchemy models (fine for this assignment;
`alembic/` is scaffolded if you want real migrations instead — see `backend/app/config.py` for the
migration-vs-autocreate note).

You'll need at least one HCP row to log interactions against. Quickest way in, via the API docs at
`http://localhost:8000/docs`, `POST /api/hcps/`:
```json
{ "name": "Dr. Anjali Sharma", "specialty": "Cardiology", "institution": "Fortis Bengaluru" }
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`. The dev server proxies `/api` to `http://localhost:8000` (see
`vite.config.js`), so both need to be running.

### 3. Try it

- **Form mode:** search for the HCP you created, fill the form, submit.
- **Chat mode:** try something like *"Met Dr. Sharma this morning, discussed CardioPlus efficacy data,
  left 2 samples, she was positive"* — watch the tool chip under the agent's reply confirm
  `log_interaction` fired. Then try *"actually change the sentiment to neutral"* to see `edit_interaction`,
  or *"what's the latest with Dr. Sharma?"* for `lookup_hcp`.

## Design notes

- Form and chat share one service layer (`backend/app/services/`) — both a `POST /api/interactions` call
  and the `log_interaction` tool call the same `create_interaction()` function, so validation can't drift
  between entry modes.
- The chat UI renders a small monospace "tool chip" under each agent reply showing which tool fired and
  its status (ok / needs_clarification / flagged / error) — this is deliberate: it keeps the agent's
  reasoning legible to the rep instead of a black box, and makes it easy to verify all 5 tools in a demo.
- Compliance checks flag rather than block, since silently blocking a rep's log entry would just train
  them to route around the tool — flagged interactions still get logged, but are marked for review.
