import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BarChart3,
  CalendarDays,
  Check,
  ClipboardList,
  Plus,
  RefreshCcw,
  Save,
  Settings,
  Trash2,
  X,
} from "lucide-react";

import { api } from "./api";
import type { ClassRecord, ClassStatus, Course, ScheduleRule, Stats, StudentGroup, TodayItem } from "./types";
import "./styles.css";

type View = "today" | "records" | "stats" | "schedule";

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const statusLabels: Record<ClassStatus, string> = {
  taught: "Taught",
  canceled: "Canceled",
  rescheduled: "Rescheduled",
  extra: "Extra",
  pending: "Pending",
};

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function money(value: string | number): string {
  return Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function timeOnly(value: string): string {
  return value.slice(0, 5);
}

function useAppData() {
  const [groups, setGroups] = useState<StudentGroup[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [schedule, setSchedule] = useState<ScheduleRule[]>([]);
  const [records, setRecords] = useState<ClassRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [nextGroups, nextCourses, nextSchedule, nextRecords] = await Promise.all([
        api.studentGroups(),
        api.courses(),
        api.schedule(),
        api.records(),
      ]);
      setGroups(nextGroups);
      setCourses(nextCourses);
      setSchedule(nextSchedule);
      setRecords(nextRecords);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return { groups, courses, schedule, records, loading, error, refresh };
}

function App() {
  const [view, setView] = useState<View>("today");
  const appData = useAppData();

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Personal salary log</p>
          <h1>Teaching Records</h1>
        </div>
        <nav aria-label="Main">
          <NavButton active={view === "today"} icon={<ClipboardList />} label="Today" onClick={() => setView("today")} />
          <NavButton active={view === "records"} icon={<CalendarDays />} label="Records" onClick={() => setView("records")} />
          <NavButton active={view === "stats"} icon={<BarChart3 />} label="Stats" onClick={() => setView("stats")} />
          <NavButton active={view === "schedule"} icon={<Settings />} label="Schedule" onClick={() => setView("schedule")} />
        </nav>
        <button className="icon-button wide" onClick={appData.refresh} title="Refresh">
          <RefreshCcw size={18} />
          Refresh
        </button>
      </aside>

      <section className="workspace">
        {appData.error && <div className="banner">{appData.error}</div>}
        {appData.loading ? (
          <div className="loading">Loading your classes...</div>
        ) : (
          <>
            {view === "today" && <TodayView {...appData} />}
            {view === "records" && <RecordsView {...appData} />}
            {view === "stats" && <StatsView />}
            {view === "schedule" && <ScheduleView {...appData} />}
          </>
        )}
      </section>
    </main>
  );
}

function NavButton({ active, icon, label, onClick }: { active: boolean; icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button className={`nav-button ${active ? "active" : ""}`} onClick={onClick}>
      {icon}
      {label}
    </button>
  );
}

function TodayView({ refresh }: ReturnType<typeof useAppData>) {
  const [date, setDate] = useState(todayIso());
  const [items, setItems] = useState<TodayItem[]>([]);
  const [busy, setBusy] = useState(false);

  async function loadToday() {
    setBusy(true);
    try {
      setItems(await api.today(date));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void loadToday();
  }, [date]);

  async function mark(item: TodayItem, status: ClassStatus) {
    const rule = item.schedule_rule;
    const existing = item.record;
    if (existing) {
      await api.updateRecord(existing.id, { status });
    } else if (rule) {
      await api.createRecord({
        user_id: rule.user_id,
        schedule_rule_id: rule.id,
        student_group_id: rule.student_group_id,
        course_id: rule.course_id,
        date: item.expected_date,
        start_time: rule.start_time,
        duration_minutes: rule.duration_minutes,
        status,
        fee_amount: status === "taught" ? rule.course.default_rate : "0",
      });
    }
    await Promise.all([loadToday(), refresh()]);
  }

  const doneCount = items.filter((item) => item.record && item.record.status !== "pending").length;

  return (
    <div className="view">
      <header className="view-header">
        <div>
          <p className="eyebrow">Daily check</p>
          <h2>Today</h2>
        </div>
        <input className="control" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
      </header>
      <div className="summary-strip">
        <strong>{doneCount}</strong>
        <span>confirmed out of {items.length} expected or actual classes</span>
      </div>
      <div className="today-list">
        {busy && <div className="loading small">Refreshing...</div>}
        {!busy && items.length === 0 && <EmptyState text="No scheduled or recorded classes for this date." />}
        {items.map((item) => {
          const source = item.record ?? item.schedule_rule;
          if (!source) return null;
          const group = item.record?.student_group.name ?? item.schedule_rule?.student_group.name;
          const course = item.record?.course.name ?? item.schedule_rule?.course.name;
          const status = item.record?.status ?? "pending";
          return (
            <article className="class-row" key={`${item.kind}-${item.record?.id ?? item.schedule_rule?.id}`}>
              <div className="time-pill">{timeOnly(source.start_time)}</div>
              <div className="class-main">
                <h3>{group}</h3>
                <p>{course} · {source.duration_minutes} min</p>
              </div>
              <span className={`status ${status}`}>{statusLabels[status]}</span>
              <div className="actions">
                <button className="icon-button success" onClick={() => mark(item, "taught")} title="Mark taught">
                  <Check size={18} />
                </button>
                <button className="icon-button danger" onClick={() => mark(item, "canceled")} title="Mark canceled">
                  <X size={18} />
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function RecordsView({ groups, courses, records, refresh }: ReturnType<typeof useAppData>) {
  const [form, setForm] = useState({
    date: todayIso(),
    start_time: "16:00",
    duration_minutes: 60,
    student_group_id: "",
    course_id: "",
    status: "taught" as ClassStatus,
    fee_amount: "0",
    notes: "",
  });

  async function addRecord(event: React.FormEvent) {
    event.preventDefault();
    if (!form.student_group_id || !form.course_id) return;
    await api.createRecord({
      ...form,
      student_group_id: Number(form.student_group_id),
      course_id: Number(form.course_id),
    });
    setForm({ ...form, notes: "" });
    await refresh();
  }

  async function patchRecord(id: number, body: Partial<ClassRecord>) {
    await api.updateRecord(id, body);
    await refresh();
  }

  return (
    <div className="view">
      <header className="view-header">
        <div>
          <p className="eyebrow">Manual correction</p>
          <h2>Records</h2>
        </div>
      </header>
      <form className="toolbar-form" onSubmit={addRecord}>
        <input className="control" type="date" value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} />
        <input className="control" type="time" value={form.start_time} onChange={(event) => setForm({ ...form, start_time: event.target.value })} />
        <select className="control" value={form.student_group_id} onChange={(event) => setForm({ ...form, student_group_id: event.target.value })}>
          <option value="">Student</option>
          {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
        </select>
        <select className="control" value={form.course_id} onChange={(event) => setForm({ ...form, course_id: event.target.value })}>
          <option value="">Course</option>
          {courses.map((course) => <option key={course.id} value={course.id}>{course.name}</option>)}
        </select>
        <input className="control compact" type="number" min="1" value={form.duration_minutes} onChange={(event) => setForm({ ...form, duration_minutes: Number(event.target.value) })} />
        <input className="control compact" type="number" min="0" step="0.01" value={form.fee_amount} onChange={(event) => setForm({ ...form, fee_amount: event.target.value })} />
        <button className="icon-button primary" type="submit" title="Add record">
          <Plus size={18} />
          Add
        </button>
      </form>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Time</th>
              <th>Student</th>
              <th>Course</th>
              <th>Status</th>
              <th>Fee</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.id}>
                <td>{record.date}</td>
                <td>{timeOnly(record.start_time)}</td>
                <td>{record.student_group.name}</td>
                <td>{record.course.name}</td>
                <td>
                  <select className="inline-select" value={record.status} onChange={(event) => patchRecord(record.id, { status: event.target.value as ClassStatus })}>
                    {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </td>
                <td>
                  <input className="inline-number" type="number" min="0" step="0.01" defaultValue={record.fee_amount} onBlur={(event) => patchRecord(record.id, { fee_amount: event.target.value })} />
                </td>
                <td>
                  <button className="icon-button subtle" onClick={async () => { await api.deleteRecord(record.id); await refresh(); }} title="Delete record">
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatsView() {
  const [range, setRange] = useState<"week" | "month">("month");
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    api.stats(range).then(setStats).catch((err) => setError(err instanceof Error ? err.message : "Could not load stats"));
  }, [range]);

  return (
    <div className="view">
      <header className="view-header">
        <div>
          <p className="eyebrow">Salary source</p>
          <h2>Stats</h2>
        </div>
        <div className="segmented">
          <button className={range === "week" ? "selected" : ""} onClick={() => setRange("week")}>Week</button>
          <button className={range === "month" ? "selected" : ""} onClick={() => setRange("month")}>Month</button>
        </div>
      </header>
      {error && <div className="banner">{error}</div>}
      {stats && (
        <>
          <div className="metrics">
            <Metric label="Taught" value={stats.taught_count} />
            <Metric label="Hours" value={(stats.total_minutes / 60).toFixed(1)} />
            <Metric label="Salary" value={money(stats.salary)} />
            <Metric label="Canceled" value={stats.canceled_count} />
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Taught</th>
                  <th>Hours</th>
                  <th>Salary</th>
                </tr>
              </thead>
              <tbody>
                {stats.by_student.map((row) => (
                  <tr key={row.student_group_id}>
                    <td>{row.student_group_name}</td>
                    <td>{row.taught_count}</td>
                    <td>{(row.total_minutes / 60).toFixed(1)}</td>
                    <td>{money(row.salary)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function ScheduleView({ groups, courses, schedule, refresh }: ReturnType<typeof useAppData>) {
  const defaults = useMemo(() => ({
    student_group_id: "",
    course_id: "",
    weekday: "0",
    start_time: "16:00",
    duration_minutes: 60,
    active_from: todayIso(),
    notes: "",
  }), []);
  const [form, setForm] = useState(defaults);
  const [newGroup, setNewGroup] = useState("");
  const [newCourse, setNewCourse] = useState({ name: "", default_rate: "0", default_duration_minutes: 60 });

  async function addRule(event: React.FormEvent) {
    event.preventDefault();
    if (!form.student_group_id || !form.course_id) return;
    await api.createSchedule({
      ...form,
      student_group_id: Number(form.student_group_id),
      course_id: Number(form.course_id),
      weekday: Number(form.weekday),
    });
    setForm(defaults);
    await refresh();
  }

  async function addGroup(event: React.FormEvent) {
    event.preventDefault();
    if (!newGroup.trim()) return;
    await api.createStudentGroup({ name: newGroup.trim() });
    setNewGroup("");
    await refresh();
  }

  async function addCourse(event: React.FormEvent) {
    event.preventDefault();
    if (!newCourse.name.trim()) return;
    await api.createCourse(newCourse);
    setNewCourse({ name: "", default_rate: "0", default_duration_minutes: 60 });
    await refresh();
  }

  return (
    <div className="view">
      <header className="view-header">
        <div>
          <p className="eyebrow">Expected classes</p>
          <h2>Schedule</h2>
        </div>
      </header>
      <div className="setup-grid">
        <form className="mini-form" onSubmit={addGroup}>
          <input className="control" placeholder="New student or group" value={newGroup} onChange={(event) => setNewGroup(event.target.value)} />
          <button className="icon-button primary" title="Save student group"><Save size={18} /></button>
        </form>
        <form className="mini-form" onSubmit={addCourse}>
          <input className="control" placeholder="Course name" value={newCourse.name} onChange={(event) => setNewCourse({ ...newCourse, name: event.target.value })} />
          <input className="control compact" type="number" min="0" step="0.01" value={newCourse.default_rate} onChange={(event) => setNewCourse({ ...newCourse, default_rate: event.target.value })} />
          <button className="icon-button primary" title="Save course"><Save size={18} /></button>
        </form>
      </div>
      <form className="toolbar-form" onSubmit={addRule}>
        <select className="control" value={form.student_group_id} onChange={(event) => setForm({ ...form, student_group_id: event.target.value })}>
          <option value="">Student</option>
          {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
        </select>
        <select className="control" value={form.course_id} onChange={(event) => setForm({ ...form, course_id: event.target.value })}>
          <option value="">Course</option>
          {courses.map((course) => <option key={course.id} value={course.id}>{course.name}</option>)}
        </select>
        <select className="control" value={form.weekday} onChange={(event) => setForm({ ...form, weekday: event.target.value })}>
          {weekdays.map((day, index) => <option key={day} value={index}>{day}</option>)}
        </select>
        <input className="control" type="time" value={form.start_time} onChange={(event) => setForm({ ...form, start_time: event.target.value })} />
        <input className="control compact" type="number" min="1" value={form.duration_minutes} onChange={(event) => setForm({ ...form, duration_minutes: Number(event.target.value) })} />
        <button className="icon-button primary" type="submit" title="Add schedule rule"><Plus size={18} /> Add</button>
      </form>
      <div className="schedule-grid">
        {schedule.map((rule) => (
          <article className="schedule-item" key={rule.id}>
            <div>
              <strong>{weekdays[rule.weekday]} {timeOnly(rule.start_time)}</strong>
              <p>{rule.student_group.name} · {rule.course.name} · {rule.duration_minutes} min</p>
            </div>
            <button className="icon-button subtle" onClick={async () => { await api.deleteSchedule(rule.id); await refresh(); }} title="Delete schedule">
              <Trash2 size={16} />
            </button>
          </article>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
