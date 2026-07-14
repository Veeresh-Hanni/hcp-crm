# AI-First CRM — HCP Module: Log Interaction Screen
### Architecture & Design Document

---

## 1. Problem Framing

Field reps need to log every HCP (Healthcare Professional) touchpoint — visit, call, email, virtual meeting — quickly and accurately, without friction. Two entry modes are required:

1. **Structured Form** — fast, explicit, good when the rep already knows exactly what to record.
2. **Conversational Chat** — the rep just types (or eventually speaks) what happened in natural language, e.g. *"Met Dr. Sharma this morning, discussed CardioPlus efficacy data, left 2 samples, she wants a follow-up call next week."* The LangGraph agent turns this into a structured record.

Both modes write to the **same underlying data model**, so downstream reporting doesn't care how the record was created.

---

## 2. High-Level Architecture

```
┌─────────────────────────────┐
│      React + Redux UI       │
│  ┌────────────┬──────────┐  │
│  │ Form Mode  │ Chat Mode │  │
│  └─────┬──────┴─────┬────┘  │
└────────┼────────────┼───────┘
         │ REST        │ REST (chat msg)
         ▼             ▼
┌─────────────────────────────┐
│         FastAPI Backend      │
│  /interactions   /chat       │
│  /hcps           /reports    │
└────────┬─────────────┬───────┘
         │              │
         │        ┌─────▼─────────────┐
         │        │  LangGraph Agent   │
         │        │  (StateGraph)      │
         │        │  Groq: gemma2-9b-it│
         │        │  (llama-3.3-70b for│
         │        │   heavy reasoning) │
         │        └─────┬──────────────┘
         │              │ tool calls
         │        ┌─────▼──────────────┐
         │        │ 5 Agent Tools       │
         │        └─────┬──────────────┘
         ▼              ▼
┌─────────────────────────────┐
│     Postgres / MySQL DB      │
│ hcps, interactions,          │
│ chat_sessions, audit_log     │
└─────────────────────────────┘
```

---

## 3. Role of the LangGraph Agent

The agent is the layer that turns unstructured rep speech into governed, structured CRM data. Specifically it:

- **Maintains conversational state** — which HCP is being discussed, which fields of the draft interaction are already filled, what's still missing.
- **Classifies intent per turn** — is the rep logging a new interaction, editing a previous one, asking about an HCP, or asking for a recommendation?
- **Routes to the correct tool(s)** — a single chat turn can trigger a lookup tool then a log tool, for example.
- **Uses the LLM for NLU tasks inside tools** — entity extraction (HCP name, product, date), summarization, sentiment inference, compliance-language scanning.
- **Asks clarifying questions** when required fields are missing, rather than guessing or writing incomplete records — this is a compliance-sensitive domain, so the agent under-assumes rather than over-assumes.
- **Confirms before writing** — drafts are shown back to the rep ("Logged: Dr. Sharma, CardioPlus discussion, 2 samples, sentiment positive — confirm?") before a DB write happens.
- **Supports correction turns** — "actually change the date to yesterday" should route to Edit Interaction against the just-created record held in session state.

### LangGraph graph shape

```
START
  → router (intent classification, LLM call)
    → log_interaction_node
    → edit_interaction_node
    → lookup_hcp_node
    → suggest_next_action_node
    → compliance_check_node
  → needs_clarification? ──yes──▶ ask_user (loop back to START on next turn)
                         ──no───▶ response_generator → END
```

State object carried through the graph (`AgentState`):
```python
class AgentState(TypedDict):
    session_id: str
    rep_id: str
    messages: list[BaseMessage]
    active_hcp_id: str | None
    draft_interaction: dict | None   # accumulates across turns
    last_interaction_id: str | None  # for "edit my last log" turns
    pending_clarification: str | None
```

---

## 4. The Five Tools

### 4.1 `log_interaction` (mandatory)

**Purpose:** convert free text (+ any structured hints already gathered) into a validated `interactions` row.

**Flow:**
1. Receives raw text and current `draft_interaction` from state.
2. Calls Groq (`gemma2-9b-it`) with a structured-extraction prompt requesting JSON output for: HCP name, date, interaction type (visit/call/email/virtual), products discussed, materials/samples shared, HCP sentiment (positive/neutral/negative), key discussion points, next steps.
3. Resolves the extracted HCP name against the `hcps` table using fuzzy matching (trigram similarity in Postgres, or `pg_trgm` / `rapidfuzz` in-app); if ambiguous, defers to `lookup_hcp` tool and returns a clarification request instead of guessing.
4. Runs a second, shorter LLM call to produce a 1–2 sentence `summary` field (this is what shows up in list views/reports — separate from raw discussion notes).
5. Validates required fields (HCP resolved, date, type). If anything's missing, returns `status: needs_clarification` with the specific missing field so the agent can ask a follow-up question instead of writing a partial record.
6. On success, writes the row via the service layer, returns `interaction_id` and the full structured record for confirmation display in the UI.

**Why LLM matters here specifically:** entity extraction + summarization + sentiment inference from unstructured text is the crux of the "conversational logging" feature — this is not a simple regex/form-fill.

### 4.2 `edit_interaction` (mandatory)

**Purpose:** modify a previously logged interaction via natural language.

**Flow:**
1. Input: either an explicit `interaction_id`, or a reference like "my last log" / "the Dr. Sharma visit yesterday" — resolved via `last_interaction_id` in session state or a lookup query against `interactions` filtered by HCP + date range.
2. LLM parses the requested change into a structured diff, e.g. `{"field": "sentiment", "old": "neutral", "new": "positive"}` — supports multiple fields in one instruction.
3. Fetches current record, applies the partial update.
4. Writes an `audit_log` row per changed field (`old_value`, `new_value`, `changed_by`, `changed_at`) — required for pharma compliance traceability, since interaction records are often auditable.
5. Returns the updated record for the agent to confirm back to the rep.

### 4.3 `lookup_hcp`

**Purpose:** resolve ambiguous HCP references and give the rep context before/while logging.

**Flow:** fuzzy search on `hcps.name` (+ optional specialty/territory filters) → returns candidate matches with specialty, institution, last interaction date, interaction frequency, and any compliance flags (e.g. "gift limit reached this quarter"). Used both proactively (agent disambiguates "Dr. Sharma" when there are 3 of them) and on explicit rep request ("what's Dr. Sharma's last visit about?").

### 4.4 `suggest_next_best_action`

**Purpose:** sales-enablement — recommend what the rep should do/say next with a given HCP.

**Flow:** pulls the HCP's recent interaction history (last N interactions, sentiment trend, products already discussed vs. not yet covered), feeds it to `llama-3.3-70b-versatile` (heavier reasoning than gemma2-9b-it is well suited for this) with a prompt asking for a next talking point and ideal follow-up timing. Returns a short recommendation, not a full plan — this is meant to be glanceable, e.g. during pre-call planning.

### 4.5 `compliance_check`

**Purpose:** flag regulatory/compliance risk before an interaction is committed — realistic and necessary for a life-sciences CRM.

**Flow:** validates the draft interaction against configurable rules:
- Sample quantity vs. per-HCP/per-quarter limits.
- Off-label or unapproved-claim language in discussion notes, detected via an LLM scan against a list of approved claims/products.
- Gift/spend thresholds if materials have associated value.

Returns `status: clear` or `status: flagged` with reasons; flagged interactions are still logged but marked for review rather than blocked outright (blocking silently would just cause reps to route around the tool).

### (Optional 6th, stretch) `history_summary`
Generates a natural-language rollup of an HCP's interaction history over a period — useful for QBR/territory-review prep, and a good "extra" to demo if time allows.

---

## 5. Data Model

```sql
hcps
  id, name, specialty, institution, territory, contact_info,
  compliance_flags (jsonb), created_at

interactions
  id, hcp_id (fk), rep_id, interaction_date, type
    (visit | call | email | virtual),
  summary, discussion_notes, sentiment (positive|neutral|negative),
  materials_shared (jsonb), samples_given (jsonb),
  next_steps, source (form | chat), compliance_status,
  created_at, updated_at

interaction_products
  id, interaction_id (fk), product_id, discussion_notes

products
  id, name, approved_claims (jsonb)

chat_sessions
  id, rep_id, hcp_id (nullable), started_at, ended_at

chat_messages
  id, session_id (fk), role (user|agent|tool), content,
  tool_calls (jsonb), created_at

audit_log
  id, interaction_id (fk), field, old_value, new_value,
  changed_by, changed_at
```

---

## 6. Backend (FastAPI)

```
POST   /api/interactions          # form-mode create
GET    /api/interactions/{id}
PATCH  /api/interactions/{id}     # direct edit (non-chat)
GET    /api/interactions?hcp_id=  # history

GET    /api/hcps?search=
GET    /api/hcps/{id}

POST   /api/chat/message          # {session_id, rep_id, text} -> agent turn
GET    /api/chat/session/{id}     # message history

GET    /api/reports/hcp/{id}/summary
```

Service layer sits between routers and DB (SQLAlchemy models + Pydantic schemas), and is called both by REST endpoints directly (form mode) and by the LangGraph tools (chat mode) — single source of truth for validation logic, so form and chat can never diverge in what they consider a "valid" interaction.

---

## 7. Frontend (React + Redux)

```
src/
  components/
    LogInteractionScreen.jsx   # tab toggle: Form | Chat
    InteractionForm.jsx        # controlled form
    ChatInterface.jsx          # message list + input, renders tool-action cards
    HcpSearchInput.jsx         # autocomplete, used by both modes
    InteractionHistoryList.jsx
  store/
    interactionsSlice.js       # CRUD thunks -> /api/interactions
    chatSlice.js                # session + messages -> /api/chat/message
    hcpsSlice.js                 # search/lookup
  api/
    client.js                   # fetch wrapper
  theme/
    fonts.css                   # Google Inter
```

Chat responses render as message bubbles, with tool actions shown as inline confirmation cards (e.g. "✅ Logged interaction — Dr. Sharma, CardioPlus, sentiment: positive [Edit]"), so the rep always sees exactly what got written before moving on.

---

## 8. Why Groq / gemma2-9b-it + llama-3.3-70b split

- **gemma2-9b-it** — fast, cheap, used for the router/intent classification and the bulk of structured-extraction calls inside `log_interaction` and `edit_interaction`, where latency matters most (this is a live chat UI).
- **llama-3.3-70b-versatile** — reserved for calls needing more reasoning depth: `suggest_next_best_action` (synthesizing a recommendation across history) and the compliance-language scan, where a wrong call has more downstream cost than a slow one.

---

## 9. Suggested Build Order (for the 36hr window)

1. DB schema + FastAPI CRUD for `hcps`/`interactions` (form mode fully working, no AI yet).
2. React form mode wired to that API — get one full path working end to end first.
3. LangGraph skeleton with `log_interaction` and `edit_interaction` only — prove the chat path.
4. Add `lookup_hcp`, `suggest_next_best_action`, `compliance_check`.
5. Chat UI + tool-action cards.
6. README + record demo video last, once all 5 tools are demonstrably working.
