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
import type { ClassRecord, ClassStatus, ScheduleRule, Stats, TeachingClass, TodayItem } from "./types";
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

function timeOnly(value: string): string {
  return value.slice(0, 5);
}

function classRoomLabel(classroom?: string | null): string {
  return classroom?.trim() || "No classroom";
}

function useAppData() {
  const [classes, setClasses] = useState<TeachingClass[]>([]);
  const [schedule, setSchedule] = useState<ScheduleRule[]>([]);
  const [records, setRecords] = useState<ClassRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refresh(showLoading = true) {
    if (showLoading) {
      setLoading(true);
    }
    setError(null);
    try {
      const [nextClasses, nextSchedule, nextRecords] = await Promise.all([
        api.classes(),
        api.schedule(),
        api.records(),
      ]);
      setClasses(nextClasses);
      setSchedule(nextSchedule);
      setRecords(nextRecords);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load data");
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return { classes, schedule, records, loading, error, refresh };
}

function App() {
  const [view, setView] = useState<View>("today");
  const appData = useAppData();

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Physics teaching log</p>
          <h1>Teaching Records</h1>
        </div>
        <nav aria-label="Main">
          <NavButton active={view === "today"} icon={<ClipboardList />} label="Today" onClick={() => setView("today")} />
          <NavButton active={view === "records"} icon={<CalendarDays />} label="Records" onClick={() => setView("records")} />
          <NavButton active={view === "stats"} icon={<BarChart3 />} label="Stats" onClick={() => setView("stats")} />
          <NavButton active={view === "schedule"} icon={<Settings />} label="Schedule" onClick={() => setView("schedule")} />
        </nav>
        <button className="icon-button wide" onClick={() => appData.refresh()} title="Refresh">
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

  async function loadToday(showBusy = true) {
    if (showBusy) {
      setBusy(true);
    }
    try {
      setItems(await api.today(date));
    } finally {
      if (showBusy) {
        setBusy(false);
      }
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
        teaching_class_id: rule.teaching_class_id,
        classroom: rule.teaching_class.classroom,
        date: item.expected_date,
        start_time: rule.start_time,
        duration_minutes: rule.duration_minutes,
        status,
        fee_amount: "0",
        notes: rule.notes,
      });
    }
    await Promise.all([loadToday(false), refresh(false)]);
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
          const teachingClass = item.record?.teaching_class ?? item.schedule_rule?.teaching_class;
          const classroom = item.record?.classroom ?? teachingClass?.classroom;
          const notes = item.record?.notes ?? item.schedule_rule?.notes ?? teachingClass?.notes;
          const status = item.record?.status ?? "pending";
          return (
            <article className="class-row" key={`${item.kind}-${item.record?.id ?? item.schedule_rule?.id}`}>
              <div className="time-pill">{timeOnly(source.start_time)}</div>
              <div className="class-main">
                <h3>{teachingClass?.name}</h3>
                <p>{classRoomLabel(classroom)} · {source.duration_minutes} min</p>
                {notes && <p className="note-line">{notes}</p>}
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

function RecordsView({ classes, records, refresh }: ReturnType<typeof useAppData>) {
  const [form, setForm] = useState({
    date: todayIso(),
    start_time: "16:00",
    duration_minutes: 60,
    teaching_class_id: "",
    classroom: "",
    status: "taught" as ClassStatus,
    notes: "",
  });

  function chooseClass(classId: string) {
    const selected = classes.find((item) => String(item.id) === classId);
    setForm({ ...form, teaching_class_id: classId, classroom: selected?.classroom ?? form.classroom });
  }

  async function addRecord(event: React.FormEvent) {
    event.preventDefault();
    if (!form.teaching_class_id) return;
    await api.createRecord({
      ...form,
      teaching_class_id: Number(form.teaching_class_id),
      fee_amount: "0",
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
        <select className="control" value={form.teaching_class_id} onChange={(event) => chooseClass(event.target.value)}>
          <option value="">Class</option>
          {classes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <input className="control" placeholder="Classroom" value={form.classroom} onChange={(event) => setForm({ ...form, classroom: event.target.value })} />
        <input className="control compact" type="number" min="1" value={form.duration_minutes} onChange={(event) => setForm({ ...form, duration_minutes: Number(event.target.value) })} />
        <input className="control wide-field" placeholder="Notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
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
              <th>Class</th>
              <th>Classroom</th>
              <th>Status</th>
              <th>Notes</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.id}>
                <td>{record.date}</td>
                <td>{timeOnly(record.start_time)}</td>
                <td>{record.teaching_class.name}</td>
                <td>
                  <input className="inline-text" defaultValue={record.classroom ?? ""} onBlur={(event) => patchRecord(record.id, { classroom: event.target.value })} />
                </td>
                <td>
                  <select className="inline-select" value={record.status} onChange={(event) => patchRecord(record.id, { status: event.target.value as ClassStatus })}>
                    {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                </td>
                <td>
                  <input className="inline-text note-cell" defaultValue={record.notes ?? ""} onBlur={(event) => patchRecord(record.id, { notes: event.target.value })} />
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
          <p className="eyebrow">Teaching totals</p>
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
            <Metric label="Canceled" value={stats.canceled_count} />
            <Metric label="Extra" value={stats.extra_count} />
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Class</th>
                  <th>Taught</th>
                  <th>Hours</th>
                </tr>
              </thead>
              <tbody>
                {stats.by_class.map((row) => (
                  <tr key={row.teaching_class_id}>
                    <td>{row.class_name}</td>
                    <td>{row.taught_count}</td>
                    <td>{(row.total_minutes / 60).toFixed(1)}</td>
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

function ScheduleView({ classes, schedule, refresh }: ReturnType<typeof useAppData>) {
  const scheduleDefaults = useMemo(() => ({
    teaching_class_id: "",
    weekday: "0",
    start_time: "16:00",
    duration_minutes: 60,
    active_from: todayIso(),
    notes: "",
  }), []);
  const [form, setForm] = useState(scheduleDefaults);
  const [newClass, setNewClass] = useState({ name: "", classroom: "", notes: "" });

  async function addRule(event: React.FormEvent) {
    event.preventDefault();
    if (!form.teaching_class_id) return;
    await api.createSchedule({
      ...form,
      teaching_class_id: Number(form.teaching_class_id),
      weekday: Number(form.weekday),
    });
    setForm(scheduleDefaults);
    await refresh();
  }

  async function addClass(event: React.FormEvent) {
    event.preventDefault();
    if (!newClass.name.trim()) return;
    await api.createClass({
      name: newClass.name.trim(),
      classroom: newClass.classroom.trim() || null,
      notes: newClass.notes.trim() || null,
    });
    setNewClass({ name: "", classroom: "", notes: "" });
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
      <form className="toolbar-form" onSubmit={addClass}>
        <input className="control" placeholder="Class name, e.g. PA4" value={newClass.name} onChange={(event) => setNewClass({ ...newClass, name: event.target.value })} />
        <input className="control" placeholder="Classroom" value={newClass.classroom} onChange={(event) => setNewClass({ ...newClass, classroom: event.target.value })} />
        <input className="control wide-field" placeholder="Notes" value={newClass.notes} onChange={(event) => setNewClass({ ...newClass, notes: event.target.value })} />
        <button className="icon-button primary" title="Save class"><Save size={18} /> Save</button>
      </form>
      <form className="toolbar-form" onSubmit={addRule}>
        <select className="control" value={form.teaching_class_id} onChange={(event) => setForm({ ...form, teaching_class_id: event.target.value })}>
          <option value="">Class</option>
          {classes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <select className="control" value={form.weekday} onChange={(event) => setForm({ ...form, weekday: event.target.value })}>
          {weekdays.map((day, index) => <option key={day} value={index}>{day}</option>)}
        </select>
        <input className="control" type="time" value={form.start_time} onChange={(event) => setForm({ ...form, start_time: event.target.value })} />
        <input className="control compact" type="number" min="1" value={form.duration_minutes} onChange={(event) => setForm({ ...form, duration_minutes: Number(event.target.value) })} />
        <input className="control wide-field" placeholder="Schedule notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
        <button className="icon-button primary" type="submit" title="Add schedule rule"><Plus size={18} /> Add</button>
      </form>
      <div className="schedule-grid">
        {schedule.map((rule) => (
          <article className="schedule-item" key={rule.id}>
            <div>
              <strong>{weekdays[rule.weekday]} {timeOnly(rule.start_time)} · {rule.teaching_class.name}</strong>
              <p>{classRoomLabel(rule.teaching_class.classroom)} · {rule.duration_minutes} min</p>
              {(rule.notes || rule.teaching_class.notes) && <p className="note-line">{rule.notes || rule.teaching_class.notes}</p>}
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



