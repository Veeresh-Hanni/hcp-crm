import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatSession, ChatMessage, MessageRole
from app.schemas.chat import ChatMessageIn, ChatMessageOut, ToolActionOut, ChatSessionOut
from app.agent.graph import build_agent_graph

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message", response_model=ChatMessageOut)
def send_message(payload: ChatMessageIn, db: Session = Depends(get_db)):
    # Get or create session, restoring prior agent state (draft interaction, last_interaction_id, etc.)
    if payload.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(id=str(uuid.uuid4()), rep_id=payload.rep_id, state={})
        db.add(session)
        db.commit()
        db.refresh(session)

    db.add(ChatMessage(id=str(uuid.uuid4()), session_id=session.id, role=MessageRole.user, content=payload.text))
    db.commit()

    initial_state = {
        "session_id": session.id,
        "rep_id": payload.rep_id,
        "user_text": payload.text,
        "active_hcp_id": session.state.get("active_hcp_id"),
        "draft_interaction": session.state.get("draft_interaction", {}),
        "last_interaction_id": session.state.get("last_interaction_id"),
    }

    graph = build_agent_graph(db)
    result_state = graph.invoke(initial_state)

    # Persist agent scratch state back onto the session for the next turn
    session.state = {
        "active_hcp_id": result_state.get("active_hcp_id"),
        "draft_interaction": result_state.get("draft_interaction", {}),
        "last_interaction_id": result_state.get("last_interaction_id"),
    }
    db.add(session)

    tool_result = result_state.get("tool_result", {})
    tool_actions = []
    if tool_result:
        tool_actions.append(
            ToolActionOut(
                tool=tool_result.get("tool", "unknown"),
                status=tool_result.get("status", "ok"),
                data={k: v for k, v in tool_result.items() if k not in ("tool", "status")},
            )
        )

    db.add(
        ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session.id,
            role=MessageRole.agent,
            content=result_state["reply"],
            tool_calls={"actions": [a.model_dump() for a in tool_actions]},
        )
    )
    db.commit()

    return ChatMessageOut(session_id=session.id, reply=result_state["reply"], tool_actions=tool_actions)


@router.get("/session/{session_id}", response_model=ChatSessionOut)
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
