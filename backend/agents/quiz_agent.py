"""
agents/quiz_agent.py — Quiz evaluation agent.

Receives student answers, checks against answer key,
computes score and percentage, writes result to Google Sheets.
"""
from datetime import date
from backend.services.sheets import SheetsService


def run(payload: dict) -> dict:
    """
    payload keys:
      student_prn, student_name, subject_code, topic_number, lecture_number,
      answers: [ { question_id, selected } ],
      answer_key: { question_id: correct_option }
    Returns:
      { prn, score, total, percentage, correct, wrong }
    """
    sheets = SheetsService()

    answers    = payload["answers"]         # list of { question_id, selected }
    answer_key = payload["answer_key"]      # { question_id: "A"|"B"|"C"|"D" }

    correct = sum(
        1 for a in answers
        if answer_key.get(a["question_id"]) == a["selected"]
    )
    total      = len(answers)
    wrong      = total - correct
    percentage = round((correct / total) * 100, 2) if total else 0

    sheets.save_quiz_result(
        date       = payload.get("date", date.today().isoformat()),
        lecture_no = payload["lecture_number"],
        subject    = payload["subject_code"],
        topic_no   = payload["topic_number"],
        prn        = payload["student_prn"],
        name       = payload["student_name"],
        attempt    = payload.get("attempt", 1),
        score      = correct,
        total      = total,
        pct        = percentage,
        time_s     = payload.get("time_taken_seconds", 0),
        count      = payload.get("attempt_count", 1),
    )

    return {
        "student_prn": payload["student_prn"],
        "score":       correct,
        "total":       total,
        "correct":     correct,
        "wrong":       wrong,
        "percentage":  percentage,
        "passed":      percentage >= 40,
    }
