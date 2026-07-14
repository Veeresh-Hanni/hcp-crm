from functools import partial

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.agent.state import AgentState
from app.agent import nodes


def build_agent_graph(db: Session):
    """
    Builds the LangGraph StateGraph for one request. We build it per-request
    (cheap — it's just graph wiring) and bind `db` into each node via
    functools.partial, since the session is request-scoped in FastAPI.

    Graph shape:
        START -> router -> {log, edit, lookup, suggest, compliance, chitchat} -> END
    """
    graph = StateGraph(AgentState)

    graph.add_node("router", partial(nodes.router_node, db=db))
    graph.add_node("log", partial(nodes.log_node, db=db))
    graph.add_node("edit", partial(nodes.edit_node, db=db))
    graph.add_node("lookup", partial(nodes.lookup_node, db=db))
    graph.add_node("suggest", partial(nodes.suggest_node, db=db))
    graph.add_node("compliance", partial(nodes.compliance_node, db=db))
    graph.add_node("chitchat", partial(nodes.chitchat_node, db=db))

    graph.set_entry_point("router")

    def route_by_intent(state: AgentState) -> str:
        return state.get("intent", "chitchat")

    graph.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "log": "log",
            "edit": "edit",
            "lookup": "lookup",
            "suggest": "suggest",
            "compliance": "compliance",
            "chitchat": "chitchat",
        },
    )

    for node_name in ["log", "edit", "lookup", "suggest", "compliance", "chitchat"]:
        graph.add_edge(node_name, END)

    return graph.compile()
