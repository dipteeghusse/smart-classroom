/* ── API base URL ─────────────────────────────────────────────────────────── */
const API = "http://localhost:8080";

/* ── Tab navigation ───────────────────────────────────────────────────────── */
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

/* ── Helpers ──────────────────────────────────────────────────────────────── */

function showResult(elId, data, isError = false) {
  const el = document.getElementById(elId);
  el.classList.remove("hidden", "error");
  if (isError) el.classList.add("error");
  el.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function setLoading(btnEl, loading) {
  if (loading) {
    btnEl._originalText = btnEl.innerHTML;
    btnEl.innerHTML = '<span class="spinner"></span>Working…';
    btnEl.disabled = true;
  } else {
    btnEl.innerHTML = btnEl._originalText;
    btnEl.disabled = false;
  }
}

async function apiPost(path, body) {
  const r = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
  return r.json();
}

async function apiGet(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
  return r.json();
}

/* ── Dashboard ─────────────────────────────────────────────────────────────── */

async function loadHodDashboard() {
  const btn = event.target;
  setLoading(btn, true);
  try {
    const data = await apiGet("/api/analytics/hod");
    document.getElementById("val-attendance").textContent = (data.dept_attendance_pct ?? "—") + "%";
    document.getElementById("val-gate").textContent       = (data.gate_readiness_index ?? "—") + "%";
    document.getElementById("val-coverage").textContent   = (data.syllabus_coverage_pct ?? "—") + "%";
    document.getElementById("val-quizzes").textContent    = data.total_quiz_attempts ?? "—";
    document.getElementById("val-topics").textContent     = `${data.topics_completed ?? "—"} / ${data.topics_total ?? "—"}`;
    showResult("dashboard-result", data);
  } catch (e) {
    showResult("dashboard-result", e.message, true);
  } finally {
    setLoading(btn, false);
  }
}

/* ── QR Code ───────────────────────────────────────────────────────────────── */

async function generateQR() {
  const lectureId = document.getElementById("qr-lecture-id").value.trim();
  if (!lectureId) return alert("Enter a Lecture ID.");

  const btn = event.target;
  setLoading(btn, true);
  try {
    const data = await apiGet(`/api/qr/${encodeURIComponent(lectureId)}`);
    const container = document.getElementById("qr-result");
    container.classList.remove("hidden");
    document.getElementById("qr-image").src = `data:image/png;base64,${data.image_b64}`;
    document.getElementById("qr-token-display").textContent = `Token: ${data.token}`;
    document.getElementById("qr-expiry-display").textContent =
      `Expires: ${new Date(data.expires_at * 1000).toLocaleTimeString()} (60s window)`;
  } catch (e) {
    alert("Error: " + e.message);
  } finally {
    setLoading(btn, false);
  }
}

/* ── Mark Attendance ────────────────────────────────────────────────────────── */

async function markAttendance() {
  const [slat, slon] = document.getElementById("att-student-gps").value.split(",").map(Number);
  const [clat, clon] = document.getElementById("att-classroom-gps").value.split(",").map(Number);

  const body = {
    lecture_id:     document.getElementById("att-lecture-id").value.trim(),
    lecture_number: parseInt(document.getElementById("att-lecture-no").value),
    subject_code:   document.getElementById("att-subject").value.trim(),
    date:           document.getElementById("att-date").value,
    student_prn:    document.getElementById("att-prn").value.trim(),
    student_name:   document.getElementById("att-name").value.trim(),
    qr_token:       document.getElementById("att-token").value.trim(),
    student_lat:    slat, student_lon: slon,
    classroom_lat:  clat, classroom_lon: clon,
  };

  const btn = event.target;
  setLoading(btn, true);
  try {
    const data = await apiPost("/api/attend", body);
    showResult("att-result", data, data.status === "Absent");
  } catch (e) {
    showResult("att-result", e.message, true);
  } finally {
    setLoading(btn, false);
  }
}

/* ── Generate Questions ─────────────────────────────────────────────────────── */

async function generateQuestions() {
  const body = {
    subject_code:  document.getElementById("q-subject").value.trim(),
    unit:          parseInt(document.getElementById("q-unit").value),
    topic:         document.getElementById("q-topic").value.trim(),
    topic_number:  document.getElementById("q-topic-no").value.trim(),
    co_mapping:    document.getElementById("q-co").value.trim() || "CO1",
    blooms_level:  document.getElementById("q-blooms").value,
  };

  if (!body.subject_code || !body.topic) return alert("Fill Subject Code and Topic.");

  const btn = event.target;
  setLoading(btn, true);
  showResult("q-result", "⏳ Generating 45 GATE-level questions via RAG + Groq…\nThis may take 30–60 seconds.");
  document.getElementById("q-result").classList.remove("hidden");

  try {
    const data = await apiPost("/api/questions", body);
    showResult("q-result", data);
  } catch (e) {
    showResult("q-result", e.message, true);
  } finally {
    setLoading(btn, false);
  }
}

/* ── Evaluate Quiz ──────────────────────────────────────────────────────────── */

async function evaluateQuiz() {
  let answers, answerKey;
  try {
    answers   = JSON.parse(document.getElementById("qz-answers").value);
    answerKey = JSON.parse(document.getElementById("qz-key").value);
  } catch {
    return alert("Invalid JSON in answers or answer key.");
  }

  const body = {
    student_prn:    document.getElementById("qz-prn").value.trim(),
    student_name:   document.getElementById("qz-name").value.trim(),
    subject_code:   document.getElementById("qz-subject").value.trim(),
    topic_number:   document.getElementById("qz-topic").value.trim(),
    lecture_number: parseInt(document.getElementById("qz-lecture").value),
    answers,
    answer_key: answerKey,
  };

  const btn = event.target;
  setLoading(btn, true);
  try {
    const data = await apiPost("/api/quiz/evaluate", body);
    const isError = !data.passed;
    showResult("qz-result", data, isError);
  } catch (e) {
    showResult("qz-result", e.message, true);
  } finally {
    setLoading(btn, false);
  }
}

/* ── Student Analytics ──────────────────────────────────────────────────────── */

async function getStudentAnalytics() {
  const prn = document.getElementById("an-prn").value.trim();
  if (!prn) return alert("Enter a Student PRN.");

  const btn = event.target;
  setLoading(btn, true);
  try {
    const data = await apiGet(`/api/analytics/student/${encodeURIComponent(prn)}`);
    showResult("an-student-result", data);
  } catch (e) {
    showResult("an-student-result", e.message, true);
  } finally {
    setLoading(btn, false);
  }
}

/* ── Faculty Analytics ──────────────────────────────────────────────────────── */

async function getFacultyAnalytics() {
  const fid = document.getElementById("an-fid").value.trim();
  if (!fid) return alert("Enter a Faculty ID.");

  const btn = event.target;
  setLoading(btn, true);
  try {
    const data = await apiGet(`/api/analytics/faculty/${encodeURIComponent(fid)}`);
    showResult("an-faculty-result", data);
  } catch (e) {
    showResult("an-faculty-result", e.message, true);
  } finally {
    setLoading(btn, false);
  }
}

/* ── Generate Report ────────────────────────────────────────────────────────── */

async function generateReport() {
  const formats = [];
  if (document.getElementById("rpt-pdf").checked)  formats.push("pdf");
  if (document.getElementById("rpt-xlsx").checked) formats.push("xlsx");
  if (document.getElementById("rpt-docx").checked) formats.push("docx");
  if (!formats.length) return alert("Select at least one format.");

  const body = {
    report_type: document.getElementById("rpt-type").value,
    formats,
  };

  const btn = event.target;
  setLoading(btn, true);
  try {
    const data = await apiPost("/api/reports", body);
    showResult("rpt-result", data);
  } catch (e) {
    showResult("rpt-result", e.message, true);
  } finally {
    setLoading(btn, false);
  }
}

/* ── Send Notifications ─────────────────────────────────────────────────────── */

async function sendNotifications() {
  const body = {
    subject_code:  document.getElementById("nt-subject").value.trim(),
    faculty_email: document.getElementById("nt-email").value.trim() || "faculty@mitaoe.ac.in",
  };

  const btn = event.target;
  setLoading(btn, true);
  try {
    const data = await apiPost("/api/notify", body);
    showResult("nt-result", data);
  } catch (e) {
    showResult("nt-result", e.message, true);
  } finally {
    setLoading(btn, false);
  }
}

/* ── Auto-load dashboard on page open ──────────────────────────────────────── */
window.addEventListener("DOMContentLoaded", () => {
  // Set today's date as default for attendance
  const today = new Date().toISOString().split("T")[0];
  const dateInput = document.getElementById("att-date");
  if (dateInput) dateInput.value = today;
});
