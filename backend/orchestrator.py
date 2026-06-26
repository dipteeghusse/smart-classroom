"""
orchestrator.py — LangGraph agent router.

The Supervisor node uses Groq to read the task_type and route
to the correct agent. Each agent node is a simple Python function.

Graph shape:
  [supervisor] → one of 8 agent nodes → END
"""
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from backend.services.llm import chat
from backend.agents import (
    attendance_agent,
    question_agent,
    quiz_agent,
    analytics_agent,
    notification_agent,
    report_agent,
)

# ── State shared across all nodes ─────────────────────────────────────────────

class AgentState(TypedDict):
    task_type:  str           # what to do
    payload:    dict          # input data
    result:     dict          # output filled by the chosen agent
    next_node:  Optional[str] # set by supervisor
    error:      Optional[str]


# ── Supervisor — picks the right agent ───────────────────────────────────────

_AGENTS = [
    "attendance",       # QR scan + GPS check + mark sheet
    "question_gen",     # GATE MCQ generation via RAG + Groq
    "quiz_eval",        # Evaluate quiz submission
    "student_analytics",# Student performance report
    "faculty_analytics",# Faculty performance report
    "hod_dashboard",    # Department-level KPIs
    "notify_parents",   # WhatsApp + Email alerts
    "generate_report",  # Export PDF / XLSX / DOCX
]

_SUPERVISOR_PROMPT = """You are a task router for an AI Smart Classroom system.
Given the task_type below, reply with EXACTLY one agent name from this list:
{agents}

task_type: {{task_type}}
Reply with only the agent name, nothing else.""".format(agents=", ".join(_AGENTS))


def supervisor_node(state: AgentState) -> AgentState:
    reply = chat(
        system=_SUPERVISOR_PROMPT,
        user=f"task_type: {state['task_type']}",
        temperature=0,
        max_tokens=20,
    ).strip().lower()

    # Fallback if LLM returns something unexpected
    if reply not in _AGENTS:
        reply = "attendance"

    return {**state, "next_node": reply}


# ── Agent nodes — each calls one agent module ─────────────────────────────────

def attendance_node(state: AgentState) -> AgentState:
    return {**state, "result": attendance_agent.run(state["payload"])}

def question_gen_node(state: AgentState) -> AgentState:
    return {**state, "result": question_agent.run(state["payload"])}

def quiz_eval_node(state: AgentState) -> AgentState:
    return {**state, "result": quiz_agent.run(state["payload"])}

def student_analytics_node(state: AgentState) -> AgentState:
    prn = state["payload"].get("student_prn", "")
    return {**state, "result": analytics_agent.student_report(prn)}

def faculty_analytics_node(state: AgentState) -> AgentState:
    fid = state["payload"].get("faculty_id", "")
    return {**state, "result": analytics_agent.faculty_report(fid)}

def hod_dashboard_node(state: AgentState) -> AgentState:
    return {**state, "result": analytics_agent.hod_dashboard()}

def notify_parents_node(state: AgentState) -> AgentState:
    return {**state, "result": notification_agent.run(state["payload"])}

def generate_report_node(state: AgentState) -> AgentState:
    return {**state, "result": report_agent.run(state["payload"])}


# ── Router: supervisor decides which node runs ────────────────────────────────

def _route(state: AgentState) -> str:
    return state["next_node"]


# ── Build and compile the graph ───────────────────────────────────────────────

def _build():
    g = StateGraph(AgentState)

    # Add nodes
    g.add_node("supervisor",        supervisor_node)
    g.add_node("attendance",        attendance_node)
    g.add_node("question_gen",      question_gen_node)
    g.add_node("quiz_eval",         quiz_eval_node)
    g.add_node("student_analytics", student_analytics_node)
    g.add_node("faculty_analytics", faculty_analytics_node)
    g.add_node("hod_dashboard",     hod_dashboard_node)
    g.add_node("notify_parents",    notify_parents_node)
    g.add_node("generate_report",   generate_report_node)

    # Entry point
    g.set_entry_point("supervisor")

    # Supervisor routes to one agent, agent goes to END
    g.add_conditional_edges("supervisor", _route, {a: a for a in _AGENTS})
    for agent in _AGENTS:
        g.add_edge(agent, END)

    return g.compile()


# Singleton — compiled once at import time
graph = _build()


def invoke(task_type: str, payload: dict) -> dict:
    """Public entry point. Returns the agent result dict."""
    state: AgentState = {
        "task_type": task_type,
        "payload":   payload,
        "result":    {},
        "next_node": None,
        "error":     None,
    }
    final = graph.invoke(state)
    return final["result"]
