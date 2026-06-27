"""
agents/analytics_agent.py — Student, Faculty, and HoD analytics.

Reads raw data from Google Sheets, computes metrics, and
optionally uses Groq to generate a natural-language insight summary.
"""
from collections import defaultdict
from backend.services.sheets import SheetsService
from backend.services.llm import chat


# ── Student Analytics ─────────────────────────────────────────────────────────

def student_report(prn: str) -> dict:
    """
    Returns:
      attendance_pct, avg_quiz_score, topic_scores,
      weak_topics, gate_readiness_score, ai_insight
    """
    sheets = SheetsService()

    # Attendance
    att_records = sheets.get_student_attendance(prn)
    total  = len(att_records)
    present = sum(1 for r in att_records if r.get("Attendance") == "Present")
    att_pct = round((present / total) * 100, 2) if total else 0

    # Quiz performance per topic
    quiz_records = sheets.get_student_quiz_scores(prn)
    topic_scores: dict[str, list[float]] = defaultdict(list)
    for r in quiz_records:
        topic = str(r.get("Topic Number", "Unknown"))
        pct   = float(r.get("Percentage", 0))
        topic_scores[topic].append(pct)

    topic_avg  = {t: round(sum(v)/len(v), 2) for t, v in topic_scores.items()}
    weak_topics = [t for t, avg in topic_avg.items() if avg < 50]
    avg_quiz   = round(sum(topic_avg.values()) / len(topic_avg), 2) if topic_avg else 0

    # GATE readiness = 30% attendance + 70% quiz average
    gate_score = round(0.3 * att_pct + 0.7 * avg_quiz, 2)

    # AI insight via Groq (optional — returns placeholder if unavailable)
    try:
        insight = chat(
            system="You are an academic counsellor. Give a 2-sentence performance insight.",
            user=f"Student PRN {prn}: attendance {att_pct}%, avg quiz {avg_quiz}%, weak topics: {weak_topics}",
            temperature=0.4,
            max_tokens=200,
        )
    except Exception:
        insight = f"Attendance: {att_pct}%. Average quiz score: {avg_quiz}%. Set GROQ_API_KEY for AI insights."

    return {
        "student_prn":        prn,
        "attendance_pct":     att_pct,
        "avg_quiz_score":     avg_quiz,
        "topic_scores":       topic_avg,
        "weak_topics":        weak_topics,
        "gate_readiness":     gate_score,
        "total_lectures":     total,
        "ai_insight":         insight,
    }


# ── Faculty Analytics ─────────────────────────────────────────────────────────

def faculty_report(faculty_id: str) -> dict:
    """
    Returns:
      syllabus_coverage, teaching_progress, co_attainment, ai_insight
    """
    sheets = SheetsService()

    plan      = sheets.read_all("teaching_plan")
    completed = [r for r in plan if r.get("Status") == "Completed"]

    total_topics  = len(plan)
    done_topics   = len(completed)
    coverage_pct  = round((done_topics / total_topics) * 100, 2) if total_topics else 0

    total_planned_hrs = sum(float(r.get("Planned Hours", 0)) for r in plan)
    total_done_hrs    = sum(float(r.get("Completed Hours", 0)) for r in plan)
    progress_pct      = round((total_done_hrs / total_planned_hrs)*100, 2) if total_planned_hrs else 0

    # CO attainment: average quiz score per CO
    quiz = sheets.read_all("quiz")
    co_scores: dict[str, list[float]] = defaultdict(list)
    topic_to_co = {str(r.get("Topic Number", "")): str(r.get("Course Outcome", "CO1"))
                   for r in plan}
    for q in quiz:
        co = topic_to_co.get(str(q.get("Topic Number", "")), "CO1")
        co_scores[co].append(float(q.get("Percentage", 0)))
    co_attainment = {co: round(sum(v)/len(v), 2) for co, v in co_scores.items() if v}

    try:
        insight = chat(
            system="You are an academic quality analyst. Give a 2-sentence faculty performance insight.",
            user=f"Faculty {faculty_id}: syllabus coverage {coverage_pct}%, progress {progress_pct}%, CO attainment: {co_attainment}",
            temperature=0.4,
            max_tokens=200,
        )
    except Exception:
        insight = f"Syllabus coverage: {coverage_pct}%. Progress: {progress_pct}%. Set GROQ_API_KEY for AI insights."

    return {
        "faculty_id":       faculty_id,
        "syllabus_coverage": coverage_pct,
        "teaching_progress": progress_pct,
        "topics_completed":  done_topics,
        "topics_total":      total_topics,
        "co_attainment":     co_attainment,
        "ai_insight":        insight,
    }


# ── HoD Dashboard ─────────────────────────────────────────────────────────────

def hod_dashboard() -> dict:
    """
    Department-level snapshot for the HoD dashboard.
    Returns key metrics across all students, subjects, and faculty.
    Returns zeros gracefully when sheets are empty.
    """
    try:
        sheets = SheetsService()
        att   = sheets.read_all("attendance")  or []
        quiz  = sheets.read_all("quiz")        or []
        plan  = sheets.read_all("teaching_plan") or []
    except Exception:
        att, quiz, plan = [], [], []

    # Department attendance
    total   = len(att)
    present = sum(1 for r in att if r.get("Attendance") == "Present")
    dept_att_pct = round((present / total) * 100, 2) if total else 0

    # Subject-wise attendance
    subj_att: dict[str, list[bool]] = defaultdict(list)
    for r in att:
        subj_att[str(r.get("Subject", ""))].append(r.get("Attendance") == "Present")
    subject_attendance = {s: round(sum(v)/len(v)*100, 2) for s, v in subj_att.items()}

    # GATE readiness index (mean quiz %)
    quiz_pcts = [float(r.get("Percentage", 0)) for r in quiz]
    gate_idx  = round(sum(quiz_pcts) / len(quiz_pcts), 2) if quiz_pcts else 0

    # Syllabus coverage
    done   = sum(1 for r in plan if r.get("Status") == "Completed")
    total_t = len(plan)

    return {
        "dept_attendance_pct":  dept_att_pct,
        "subject_attendance":   subject_attendance,
        "gate_readiness_index": gate_idx,
        "topics_completed":     done,
        "topics_total":         total_t,
        "syllabus_coverage_pct":round((done/total_t)*100, 2) if total_t else 0,
        "total_quiz_attempts":  len(quiz),
    }
