/* ─────────────────────────────────────────────────────────────────────────
   app.js  —  Smart Classroom dashboard
   Role-based navigation, uploads, attendance, quiz, analytics, reports.
   ───────────────────────────────────────────────────────────────────────── */

const API = window.location.origin;

/* ── Session helpers ─────────────────────────────────────────────────────── */

function getUser()  { return JSON.parse(localStorage.getItem("sc_user") || "null"); }
function getToken() { return localStorage.getItem("sc_token") || ""; }
function authHeader() { return { "Authorization": "Bearer " + getToken() }; }

function logout() {
  localStorage.removeItem("sc_token");
  localStorage.removeItem("sc_user");
  window.location.href = "/";
}

/* ── Navigation config per role ──────────────────────────────────────────── */

const NAV = {
  student: [
    { tab: "profile",    label: "👤 My Profile" },
    { tab: "subjects",   label: "📚 My Subjects" },
    { tab: "lesson",     label: "📋 Lesson Plan" },
    { tab: "attendance", label: "📋 Attendance" },
    { tab: "quiz",       label: "📝 Take Quiz" },
    { tab: "analytics",  label: "📈 My Analytics" },
  ],
  faculty: [
    { tab: "dashboard",  label: "📊 Dashboard" },
    { tab: "students",   label: "👥 My Students" },
    { tab: "subjects",   label: "📚 My Subjects" },
    { tab: "lesson",     label: "📋 Lesson Plan" },
    { tab: "upload",     label: "⬆ Upload Data" },
    { tab: "attendance", label: "📋 Attendance / QR" },
    { tab: "questions",  label: "🧠 Question Bank" },
    { tab: "analytics",  label: "📈 Analytics" },
    { tab: "reports",    label: "📄 Reports" },
    { tab: "notify",     label: "🔔 Notify Parents" },
  ],
  hod: [
    { tab: "dashboard",  label: "📊 HoD Dashboard" },
    { tab: "students",   label: "👥 Students" },
    { tab: "faculty",    label: "👨‍🏫 Faculty" },
    { tab: "subjects",   label: "📚 Subjects" },
    { tab: "lesson",     label: "📋 Lesson Plans" },
    { tab: "upload",     label: "⬆ Upload Data" },
    { tab: "analytics",  label: "📈 Analytics" },
    { tab: "reports",    label: "📄 Reports" },
    { tab: "notify",     label: "🔔 Notifications" },
  ],
  admin: [
    { tab: "dashboard",  label: "📊 Dashboard" },
    { tab: "students",   label: "👥 Students" },
    { tab: "faculty",    label: "👨‍🏫 Faculty" },
    { tab: "subjects",   label: "📚 Subjects" },
    { tab: "lesson",     label: "📋 Lesson Plans" },
    { tab: "upload",     label: "⬆ Upload Data" },
    { tab: "attendance", label: "📋 Attendance" },
    { tab: "questions",  label: "🧠 Question Bank" },
    { tab: "analytics",  label: "📈 Analytics" },
    { tab: "reports",    label: "📄 Reports" },
    { tab: "notify",     label: "🔔 Notifications" },
  ],
};

/* ── Boot: check login, build nav, load default tab ─────────────────────── */

document.addEventListener("DOMContentLoaded", () => {
  const user = getUser();
  if (!user || !getToken()) {
    window.location.href = "/";
    return;
  }

  // Fill user badge
  document.getElementById("nav-name").textContent = user.name;
  document.getElementById("nav-role").textContent =
    user.role.charAt(0).toUpperCase() + user.role.slice(1) +
    (user.department ? ` · ${user.department}` : "");
  document.getElementById("nav-avatar").textContent =
    user.name ? user.name.charAt(0).toUpperCase() : "?";

  // Build sidebar nav
  const nav   = document.getElementById("sidebar-nav");
  const items = NAV[user.role] || NAV.student;
  items.forEach((item, i) => {
    const btn = document.createElement("button");
    btn.className = "nav-btn" + (i === 0 ? " active" : "");
    btn.dataset.tab = item.tab;
    btn.textContent = item.label;
    btn.addEventListener("click", () => switchTab(item.tab, btn));
    nav.appendChild(btn);
  });

  // Show admin-only uploads card
  if (user.role === "admin") {
    const el = document.getElementById("upload-users-card");
    if (el) el.style.display = "";
  }

  // Pre-fill student fields with logged-in user data
  if (user.role === "student") {
    setIfExists("att-prn", user.id);
    setIfExists("att-name", user.name);
    setIfExists("an-prn", user.id);
    setIfExists("qz-prn", user.id);
    setIfExists("qz-name", user.name);
  }
  if (user.role === "faculty") {
    setIfExists("an-fid", user.id);
  }

  // Set today's date
  const today = new Date().toISOString().split("T")[0];
  setIfExists("att-date", today);

  // Load first tab automatically
  const firstTab = items[0].tab;
  showTab(firstTab);
  if (firstTab === "dashboard") loadHodDashboard();
  if (firstTab === "profile")   loadStudentProfile();
  if (firstTab === "students")  loadStudents();
  if (firstTab === "faculty")   loadFaculty();
});

function setIfExists(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val;
}

/* ── Tab switching ───────────────────────────────────────────────────────── */

function switchTab(tabId, btn) {
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  showTab(tabId);
  // Lazy-load data on first visit
  if (tabId === "students")  loadStudents();
  if (tabId === "faculty")   loadFaculty();
  if (tabId === "subjects")  loadSubjects();
  if (tabId === "lesson")    loadLessonPlan(true);
  if (tabId === "dashboard") loadHodDashboard();
}

function showTab(id) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  const el = document.getElementById("tab-" + id);
  if (el) el.classList.add("active");
}

/* ── Generic helpers ─────────────────────────────────────────────────────── */

function showResult(id, data, isError = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("hidden", "error");
  if (isError) el.classList.add("error");
  el.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function setLoading(btn, on) {
  if (on) { btn._orig = btn.innerHTML; btn.innerHTML = '<span class="spinner"></span>Working…'; btn.disabled = true; }
  else    { btn.innerHTML = btn._orig; btn.disabled = false; }
}

async function apiGet(path) {
  const r = await fetch(API + path, { headers: authHeader() });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ` + (await r.text()));
  return r.json();
}

async function apiPost(path, body) {
  const r = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ` + (await r.text()));
  return r.json();
}

/* ── Table helpers ───────────────────────────────────────────────────────── */

function renderTable(tbodyId, rows, columns) {
  const tbody = document.getElementById(tbodyId);
  tbody.innerHTML = "";
  rows.forEach(row => {
    const tr = document.createElement("tr");
    columns.forEach(col => {
      const td = document.createElement("td");
      td.textContent = row[col] ?? "";
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
}

function filterTable(tableId, query) {
  const q = query.toLowerCase();
  document.querySelectorAll(`#${tableId} tbody tr`).forEach(tr => {
    tr.style.display = tr.textContent.toLowerCase().includes(q) ? "" : "none";
  });
}

/* ── HoD Dashboard ───────────────────────────────────────────────────────── */

async function loadHodDashboard() {
  setVal("val-att",    "…"); setVal("val-gate", "…");
  setVal("val-cov",    "…"); setVal("val-quiz", "…"); setVal("val-topics", "…");
  try {
    const data = await apiGet("/api/analytics/hod");
    const att  = data.dept_attendance_pct   ?? 0;
    const gate = data.gate_readiness_index  ?? 0;
    const cov  = data.syllabus_coverage_pct ?? 0;
    const quiz = data.total_quiz_attempts   ?? 0;
    const done = data.topics_completed      ?? 0;
    const tot  = data.topics_total          ?? 0;

    setVal("val-att",    att  + "%");
    setVal("val-gate",   gate + "%");
    setVal("val-cov",    cov  + "%");
    setVal("val-quiz",   quiz);
    setVal("val-topics", `${done} / ${tot}`);

    // Colour-code attendance
    const attEl = document.getElementById("val-att");
    if (attEl) attEl.style.color = att < 75 ? "#ef4444" : att < 85 ? "#f59e0b" : "#16a34a";

    const noData = att === 0 && quiz === 0 && tot === 0;
    const msg = noData
      ? "No data yet — upload students, lesson plan and mark attendance to see live metrics."
      : JSON.stringify(data, null, 2);
    showResult("hod-result", msg, noData);
  } catch (e) {
    showResult("hod-result", "Could not load analytics: " + e.message, true);
  }
}
function setVal(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }

/* ── Student Profile ─────────────────────────────────────────────────────── */

async function loadStudentProfile() {
  const user = getUser();
  if (!user) return;
  try {
    // Profile card
    const s = await apiGet(`/api/students/${user.id}`);
    const card = document.getElementById("profile-card");
    if (card) card.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:13px">
        <div><b>PRN:</b> ${s["PRN/Roll Number"]||""}</div>
        <div><b>Name:</b> ${s["Student Name"]||""}</div>
        <div><b>Department:</b> ${s["Department"]||""}</div>
        <div><b>Program:</b> ${s["Program"]||""}</div>
        <div><b>Class:</b> ${s["Class"]||""}</div>
        <div><b>Division:</b> ${s["Division"]||""}</div>
        <div><b>Semester:</b> ${s["Semester"]||""}</div>
        <div><b>Mobile:</b> ${s["Mobile Number"]||""}</div>
      </div>`;
    // Analytics
    const a = await apiGet(`/api/analytics/student/${user.id}`);
    setVal("st-att",  (a.attendance_pct ?? "—") + "%");
    setVal("st-quiz", (a.avg_quiz_score ?? "—") + "%");
    setVal("st-gate", (a.gate_readiness ?? "—") + "%");
    if (a.weak_topics?.length) {
      const el = document.getElementById("st-weak");
      el.textContent = "⚠ Weak topics: " + a.weak_topics.join(", ");
      el.classList.remove("hidden");
    }
    if (a.ai_insight) {
      const el = document.getElementById("st-insight");
      el.textContent = "💡 " + a.ai_insight;
      el.classList.remove("hidden");
    }
  } catch (e) {
    const card = document.getElementById("profile-card");
    if (card) card.innerHTML = `<p style="color:#dc2626">${e.message}</p>`;
  }
}

/* ── Load Students ────────────────────────────────────────────────────────── */

async function loadStudents() {
  try {
    const data = await apiGet("/api/students");
    renderTable("student-tbody", data, [
      "PRN/Roll Number","Student Name","Class","Division",
      "Department","Mobile Number","Parent Email",
    ]);
  } catch (e) { console.warn("students:", e.message); }
}

/* ── Load Faculty ─────────────────────────────────────────────────────────── */

async function loadFaculty() {
  try {
    const data = await apiGet("/api/faculty");
    renderTable("faculty-tbody", data, [
      "Faculty ID","Faculty Name","Department","Subject",
      "Course","Semester","Email",
    ]);
  } catch (e) { console.warn("faculty:", e.message); }
}

/* ── Load Subjects ────────────────────────────────────────────────────────── */

async function loadSubjects() {
  try {
    const data = await apiGet("/api/subjects");
    renderTable("subject-tbody", data, [
      "Subject Code","Subject Name","Department","Semester","Credits","Faculty Assigned",
    ]);
  } catch (e) { console.warn("subjects:", e.message); }
}

/* ── Load Lesson Plan ─────────────────────────────────────────────────────── */

async function loadLessonPlan(all = false) {
  const subCode = document.getElementById("lesson-subject")?.value.trim();
  const path = (!all && subCode) ? `/api/lesson_plan/${subCode}` : "/api/lesson_plan";
  try {
    const data = await apiGet(path);
    const tbody = document.getElementById("lesson-tbody");
    tbody.innerHTML = "";
    data.forEach(r => {
      const status = r["Status"] || "Pending";
      const color  = status === "Completed" ? "#dcfce7"
                   : status === "Partial"   ? "#fef9c3" : "#fff";
      const tr = document.createElement("tr");
      tr.style.background = color;
      [
        r["Subject Code"],"Unit "+r["Unit Number"],r["Topic Number"],
        r["Topic Name"],r["Planned Date"],r["Planned Hours"]+" hrs",
        r["Course Outcome"],r["Blooms Level"],
      ].forEach(val => {
        const td = document.createElement("td");
        td.textContent = val ?? "";
        tr.appendChild(td);
      });
      // Status badge
      const td = document.createElement("td");
      td.innerHTML = `<span style="padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;
        background:${status==="Completed"?"#bbf7d0":status==="Partial"?"#fef08a":"#e2e8f0"};
        color:${status==="Completed"?"#15803d":status==="Partial"?"#713f12":"#475569"}">${status}</span>`;
      tr.appendChild(td);
      tbody.appendChild(tr);
    });
  } catch (e) { console.warn("lesson_plan:", e.message); }
}

/* ── File Upload ─────────────────────────────────────────────────────────── */

async function uploadFile(type, inputEl) {
  const file = inputEl.files[0];
  if (!file) return;
  const label = document.getElementById(`drop-${type}-label`);
  if (label) label.textContent = `Uploading ${file.name}…`;

  const form = new FormData();
  form.append("file", file);

  try {
    const r = await fetch(`${API}/api/upload/${type}`, {
      method: "POST",
      headers: authHeader(),
      body: form,
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
    showResult(`result-${type}`, data, data.errors?.length > 0);
    if (label) label.textContent = `✅ ${data.inserted} rows inserted`;

    // Refresh the related table automatically
    if (type === "students")    loadStudents();
    if (type === "faculty")     loadFaculty();
    if (type === "subjects")    loadSubjects();
    if (type === "lesson_plan") loadLessonPlan(true);
  } catch (e) {
    showResult(`result-${type}`, e.message, true);
    if (label) label.textContent = "❌ Upload failed";
  }
  inputEl.value = "";
}

function handleDrop(event, type) {
  event.preventDefault();
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const fakeInput = { files: [file], value: "" };
  uploadFile(type, fakeInput);
}

/* Sample CSV download using in-memory data */
const SAMPLES = {
  students:    "PRN/Roll Number,Student Name,Department,Program,Semester,Class,Division,Batch,Mobile Number,Parent Mobile,Parent Email,WhatsApp Number\nMIT2024001,Aarav Sharma,CSE AI&ML,B.Tech,3,SE,A,2024-2025,9876543210,9876543200,parent@gmail.com,9876543210",
  faculty:     "Faculty ID,Faculty Name,Department,Subject,Course,Semester,Mobile Number,Email\nFAC001,Dr. Priya Sharma,CSE AI&ML,Deep Learning,B.Tech,5,9823001001,faculty@mitaoe.ac.in",
  subjects:    "Subject Code,Subject Name,Department,Course,Semester,Credits,Faculty Assigned\nCS501,Deep Learning,CSE AI&ML,B.Tech,5,4,FAC001",
  lesson_plan: "Subject Code,Unit Number,Topic Number,Topic Name,Planned Date,Planned Hours,Course Outcome,Blooms Level,Status\nCS501,1,1.1,Neural Networks,2026-07-01,2,CO1,Apply,Pending",
  users:       "ID,Name,Role,Department,Class,Division,Password_Hash\nMIT2024001,Student Name,student,CSE AI&ML,SE,A,yourpassword",
};

function downloadSample(type) {
  const csv  = SAMPLES[type] || "";
  const blob = new Blob([csv], { type: "text/csv" });
  const a    = document.createElement("a");
  a.href     = URL.createObjectURL(blob);
  a.download = `sample_${type}.csv`;
  a.click();
}

/* ── QR Code ─────────────────────────────────────────────────────────────── */

async function generateQR() {
  const lid = document.getElementById("qr-lecture-id")?.value.trim();
  if (!lid) return alert("Enter a Lecture ID.");
  const btn = event.target;
  setLoading(btn, true);
  try {
    const data = await apiGet(`/api/qr/${encodeURIComponent(lid)}`);
    document.getElementById("qr-result").classList.remove("hidden");
    document.getElementById("qr-image").src = `data:image/png;base64,${data.image_b64}`;
    document.getElementById("qr-token-display").textContent = `Token: ${data.token}`;
    document.getElementById("qr-expiry-display").textContent =
      `Expires: ${new Date(data.expires_at * 1000).toLocaleTimeString()} — rotate every 60s`;
  } catch (e) { alert("Error: " + e.message); }
  finally { setLoading(btn, false); }
}

/* ── Attendance ──────────────────────────────────────────────────────────── */

async function markAttendance() {
  const [slat, slon] = (document.getElementById("att-sgps")?.value || "").split(",").map(Number);
  const [clat, clon] = (document.getElementById("att-cgps")?.value || "").split(",").map(Number);
  const body = {
    lecture_id:     document.getElementById("att-lid")?.value.trim(),
    lecture_number: +document.getElementById("att-lno")?.value,
    subject_code:   document.getElementById("att-sub")?.value.trim(),
    date:           document.getElementById("att-date")?.value,
    student_prn:    document.getElementById("att-prn")?.value.trim(),
    student_name:   document.getElementById("att-name")?.value.trim(),
    qr_token:       document.getElementById("att-tok")?.value.trim(),
    student_lat: slat, student_lon: slon, classroom_lat: clat, classroom_lon: clon,
  };
  const btn = event.target;
  setLoading(btn, true);
  try {
    const data = await apiPost("/api/attend", body);
    showResult("att-result", data, data.status === "Absent");
  } catch (e) { showResult("att-result", e.message, true); }
  finally { setLoading(btn, false); }
}

/* ── Questions ───────────────────────────────────────────────────────────── */

async function generateQuestions() {
  const body = {
    subject_code: document.getElementById("q-sub")?.value.trim(),
    unit:         +document.getElementById("q-unit")?.value,
    topic:        document.getElementById("q-topic")?.value.trim(),
    topic_number: document.getElementById("q-tno")?.value.trim(),
    co_mapping:   document.getElementById("q-co")?.value.trim() || "CO1",
    blooms_level: document.getElementById("q-blooms")?.value,
  };
  if (!body.subject_code || !body.topic) return alert("Fill Subject Code and Topic.");
  const btn = event.target;
  setLoading(btn, true);
  showResult("q-result", "⏳ Generating 45 GATE-level questions via RAG + Groq…\nThis may take 30–60 s.");
  document.getElementById("q-result").classList.remove("hidden");
  try {
    const data = await apiPost("/api/questions", body);
    showResult("q-result", data);
  } catch (e) { showResult("q-result", e.message, true); }
  finally { setLoading(btn, false); }
}

/* ── Quiz Evaluate ───────────────────────────────────────────────────────── */

async function evaluateQuiz() {
  let answers, key;
  try { answers = JSON.parse(document.getElementById("qz-answers")?.value); } catch { return alert("Invalid JSON in Answers."); }
  try { key     = JSON.parse(document.getElementById("qz-key")?.value);     } catch { return alert("Invalid JSON in Answer Key."); }
  const body = {
    student_prn:    document.getElementById("qz-prn")?.value.trim(),
    student_name:   document.getElementById("qz-name")?.value.trim(),
    subject_code:   document.getElementById("qz-sub")?.value.trim(),
    topic_number:   document.getElementById("qz-topic")?.value.trim(),
    lecture_number: +document.getElementById("qz-lno")?.value,
    answers, answer_key: key,
  };
  const btn = event.target;
  setLoading(btn, true);
  try {
    const data = await apiPost("/api/quiz/evaluate", body);
    showResult("qz-result", data, !data.passed);
  } catch (e) { showResult("qz-result", e.message, true); }
  finally { setLoading(btn, false); }
}

/* ── Analytics ───────────────────────────────────────────────────────────── */

async function getStudentAnalytics() {
  const prn = document.getElementById("an-prn")?.value.trim();
  if (!prn) return alert("Enter a Student PRN.");
  const btn = event.target; setLoading(btn, true);
  try   { showResult("an-student", await apiGet(`/api/analytics/student/${prn}`)); }
  catch (e) { showResult("an-student", e.message, true); }
  finally { setLoading(btn, false); }
}

async function getFacultyAnalytics() {
  const fid = document.getElementById("an-fid")?.value.trim();
  if (!fid) return alert("Enter a Faculty ID.");
  const btn = event.target; setLoading(btn, true);
  try   { showResult("an-faculty", await apiGet(`/api/analytics/faculty/${fid}`)); }
  catch (e) { showResult("an-faculty", e.message, true); }
  finally { setLoading(btn, false); }
}

/* ── Reports ─────────────────────────────────────────────────────────────── */

async function generateReport() {
  const formats = [];
  if (document.getElementById("rpt-pdf")?.checked)  formats.push("pdf");
  if (document.getElementById("rpt-xlsx")?.checked) formats.push("xlsx");
  if (document.getElementById("rpt-docx")?.checked) formats.push("docx");
  if (!formats.length) return alert("Select at least one format.");
  const body = { report_type: document.getElementById("rpt-type")?.value, formats };
  const btn = event.target; setLoading(btn, true);
  try   { showResult("rpt-result", await apiPost("/api/reports", body)); }
  catch (e) { showResult("rpt-result", e.message, true); }
  finally { setLoading(btn, false); }
}

/* ── Notifications ───────────────────────────────────────────────────────── */

async function sendNotifications() {
  const body = {
    subject_code:  document.getElementById("nt-sub")?.value.trim(),
    faculty_email: document.getElementById("nt-email")?.value.trim() || "faculty@mitaoe.ac.in",
  };
  const btn = event.target; setLoading(btn, true);
  try   { showResult("nt-result", await apiPost("/api/notify", body)); }
  catch (e) { showResult("nt-result", e.message, true); }
  finally { setLoading(btn, false); }
}
