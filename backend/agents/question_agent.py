"""
agents/question_agent.py — GATE-level question generation using RAG + Groq.

For each completed topic, generates 45 questions across 6 types:
  - 10 Easy MCQs
  - 10 Medium MCQs
  - 10 GATE-Level MCQs
  - 5  Numerical
  - 5  Assertion-Reason
  - 5  Conceptual

Uses ChromaDB to pull syllabus context and GATE PYQ patterns before
calling the LLM, so questions are grounded in the actual syllabus.
"""
import uuid
from backend.services.llm import chat_json
from backend.services.rag import get_syllabus_context, get_gate_examples
from backend.services.sheets import SheetsService

# Question batches per topic: (difficulty, type, count)
QUESTION_PLAN = [
    ("Easy",       "MCQ",            10),
    ("Medium",     "MCQ",            10),
    ("GATE Level", "MCQ",            10),
    ("Hard",       "Numerical",       5),
    ("Hard",       "Assertion-Reason",5),
    ("Medium",     "Conceptual",      5),
]

SYSTEM_PROMPT = """You are an expert GATE CS question paper setter for Indian universities.
Generate exactly {count} {difficulty} level {q_type} questions on the topic: '{topic}'.

Subject: {subject} | Unit: {unit} | CO: {co} | Bloom's: {blooms}

Syllabus Context:
{syllabus}

GATE PYQ Reference:
{gate_ref}

Return a JSON array with exactly {count} items. Each item must have these keys:
  question, a, b, c, d, answer (one of: A B C D), explanation, difficulty, type

Strict rules:
- All 4 options must be distinct and plausible
- Explanation must justify why the correct answer is right
- For Numerical: a/b/c/d are numeric values, answer is the correct one
- For Assertion-Reason: use standard GATE format (A: assertion, R: reason)"""


def _generate_batch(subject, unit, topic, co, blooms,
                    difficulty, q_type, count) -> list[dict]:
    """Generate one batch of questions using RAG context."""
    syllabus = get_syllabus_context(topic)
    gate_ref = get_gate_examples(f"{topic} {subject}")

    system = SYSTEM_PROMPT.format(
        count=count, difficulty=difficulty, q_type=q_type,
        topic=topic, subject=subject, unit=unit,
        co=co, blooms=blooms,
        syllabus=syllabus or "No specific syllabus context found.",
        gate_ref=gate_ref or "No GATE PYQ reference found.",
    )

    questions = chat_json(system=system, user=f"Generate {count} {difficulty} {q_type} questions.")
    return questions if isinstance(questions, list) else []


def run(payload: dict) -> dict:
    """
    payload keys:
      subject_code, unit, topic, topic_number, co_mapping, blooms_level
    Returns:
      { topic, total_generated, questions: [...] }
    """
    sheets = SheetsService()

    subject   = payload["subject_code"]
    unit      = payload["unit"]
    topic     = payload["topic"]
    topic_no  = payload["topic_number"]
    co        = payload.get("co_mapping", "CO1")
    blooms    = payload.get("blooms_level", "Apply")

    all_questions = []

    for difficulty, q_type, count in QUESTION_PLAN:
        batch = _generate_batch(subject, unit, topic, co, blooms, difficulty, q_type, count)

        for i, q in enumerate(batch, 1):
            q["id"]      = f"{subject}-U{unit}-{topic_no}-{difficulty[:1]}{i:02d}"
            q["subject"] = subject
            q["unit"]    = unit
            q["topic"]   = topic
            q["co"]      = co
            q["blooms"]  = blooms
            q["source"]  = "AI-GATE-Generator"
            # Save each question to Sheets immediately
            sheets.save_question(q)
            all_questions.append(q)

    return {
        "topic":           topic,
        "total_generated": len(all_questions),
        "breakdown": {
            "easy_mcq": 10, "medium_mcq": 10, "gate_mcq": 10,
            "numerical": 5, "assertion_reason": 5, "conceptual": 5,
        },
        "questions": all_questions,
    }
