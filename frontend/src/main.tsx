import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BarChart3,
  CalendarDays,
  Check,
  ClipboardList,
  LogOut,
  Plus,
  RefreshCcw,
  Save,
  Settings,
  Trash2,
  Upload,
  UserCircle,
  X,
} from "lucide-react";

import { api } from "./api";
import type { ClassRecord, ClassStatus, ScheduleImportCandidate, ScheduleRule, Stats, TeachingClass, TodayItem, User } from "./types";
import "./styles.css";

type View = "today" | "records" | "stats" | "schedule" | "account";
type StatsMode = "week" | "month" | "salary" | "custom";
type ScheduleImportDraft = ScheduleImportCandidate & { enabled: boolean };

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const statusLabels: Record<ClassStatus, string> = {
  taught: "Taught",
  canceled: "Canceled",
  rescheduled: "Rescheduled",
  extra: "Extra",
  pending: "Pending",
};

function todayIso(): string {
  return isoFromDate(new Date());
}

function isoFromDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function dateFromIso(value: string): Date {
  return new Date(`${value}T00:00:00`);
}

function longDateLabel(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(dateFromIso(value));
}

function salaryPeriodFor(value: string): { start: string; end: string } {
  const selected = dateFromIso(value);
  const year = selected.getFullYear();
  const month = selected.getMonth();
  const isAfterPeriodStart = selected.getDate() >= 15;
  const start = new Date(year, isAfterPeriodStart ? month : month - 1, 15);
  const end = new Date(year, isAfterPeriodStart ? month + 1 : month, 15);
  return { start: isoFromDate(start), end: isoFromDate(end) };
}

function timeOnly(value: string): string {
  return value.slice(0, 5);
}

function normalizeClassName(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

function classKey(value: string): string {
  return normalizeClassName(value).toLowerCase();
}

function clipboardImageFile(clipboardData: DataTransfer): File | null {
  for (const item of Array.from(clipboardData.items)) {
    if (item.kind !== "file" || !item.type.startsWith("image/")) {
      continue;
    }
    const file = item.getAsFile();
    if (!file) {
      continue;
    }
    if (file.name) {
      return file;
    }
    const extension = file.type.split("/")[1] || "png";
    return new File([file], `pasted-schedule-${Date.now()}.${extension}`, { type: file.type });
  }

  for (const file of Array.from(clipboardData.files)) {
    if (file.type.startsWith("image/")) {
      return file;
    }
  }

  return null;
}

function classRoomLabel(classroom?: string | null): string {
  return classroom?.trim() || "No classroom";
}

function periodLabel(value?: string | null): string | null {
  const text = value?.trim();
  return text && /^P\d+$/i.test(text) ? text.toUpperCase() : null;
}

function displayNotes(recordNotes?: string | null, scheduleNotes?: string | null, classNotes?: string | null): string | null {
  const actual = recordNotes?.trim();
  if (actual && !periodLabel(actual)) {
    return actual;
  }
  const expected = scheduleNotes?.trim();
  if (expected && !periodLabel(expected)) {
    return expected;
  }
  return classNotes?.trim() || null;
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
  const [user, setUser] = useState<User | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    api.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setCheckingSession(false));
  }, []);

  if (checkingSession) {
    return (
      <main className="auth-shell">
        <div className="loading">Checking your session...</div>
      </main>
    );
  }

  if (!user) {
    return <LoginView onLogin={setUser} />;
  }

  return <AuthenticatedApp user={user} onUserChange={setUser} onLogout={() => { api.setToken(null); setUser(null); }} />;
}

function LoginView({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await api.login(email, password);
      api.setToken(result.access_token);
      onLogin(result.user);
    } catch (err) {
      setError(err instanceof Error ? "Invalid email or password" : "Could not sign in");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <form className="login-panel" onSubmit={submit}>
        <div>
          <p className="eyebrow">Physics teaching log</p>
          <h1>Teaching Records</h1>
        </div>
        <label className="field">
          <span>Email</span>
          <input className="control" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label className="field">
          <span>Password</span>
          <input className="control" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error && <div className="banner">{error}</div>}
        <button className="icon-button primary" type="submit" disabled={busy || !email || !password}>
          {busy ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </main>
  );
}

function AuthenticatedApp({ user, onUserChange, onLogout }: { user: User; onUserChange: (user: User) => void; onLogout: () => void }) {
  const [view, setView] = useState<View>("today");
  const appData = useAppData();

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Physics teaching log</p>
          <h1>Teaching Records</h1>
          <p className="user-line">{user.name}</p>
        </div>
        <nav aria-label="Main">
          <NavButton active={view === "today"} icon={<ClipboardList />} label="Today" onClick={() => setView("today")} />
          <NavButton active={view === "records"} icon={<CalendarDays />} label="Records" onClick={() => setView("records")} />
          <NavButton active={view === "stats"} icon={<BarChart3 />} label="Stats" onClick={() => setView("stats")} />
          <NavButton active={view === "schedule"} icon={<Settings />} label="Schedule" onClick={() => setView("schedule")} />
          <NavButton active={view === "account"} icon={<UserCircle />} label="Account" onClick={() => setView("account")} />
        </nav>
        <button className="icon-button wide" onClick={() => appData.refresh()} title="Refresh">
          <RefreshCcw size={18} />
          Refresh
        </button>
        <button className="icon-button wide subtle" onClick={onLogout} title="Sign out">
          <LogOut size={18} />
          Sign out
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
            {view === "account" && <AccountView user={user} onUserChange={onUserChange} onLogout={onLogout} />}
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

function AccountView({ user, onUserChange, onLogout }: { user: User; onUserChange: (user: User) => void; onLogout: () => void }) {
  const [profile, setProfile] = useState({ name: user.name, email: user.email ?? "" });
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setProfile({ name: user.name, email: user.email ?? "" });
  }, [user]);

  async function saveProfile(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setProfileMessage(null);
    try {
      const updated = await api.updateMe({ name: profile.name.trim(), email: profile.email.trim() });
      onUserChange(updated);
      setProfileMessage("Account updated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update account");
    } finally {
      setBusy(false);
    }
  }

  async function savePassword(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setPasswordMessage(null);
    if (passwords.new_password !== passwords.confirm_password) {
      setError("New passwords do not match");
      setBusy(false);
      return;
    }
    try {
      await api.updatePassword({
        current_password: passwords.current_password,
        new_password: passwords.new_password,
      });
      setPasswords({ current_password: "", new_password: "", confirm_password: "" });
      setPasswordMessage("Password changed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change password");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="view">
      <header className="view-header">
        <div>
          <p className="eyebrow">Signed in</p>
          <h2>Account</h2>
          <p className="date-heading">{user.email}</p>
        </div>
        <button className="icon-button subtle" type="button" onClick={onLogout}>
          <LogOut size={18} />
          Sign out
        </button>
      </header>
      {error && <div className="banner">{error}</div>}
      <div className="account-grid">
        <form className="account-panel" onSubmit={saveProfile}>
          <h3 className="form-title">Profile</h3>
          <label className="field">
            <span>Name</span>
            <input className="control" value={profile.name} onChange={(event) => setProfile({ ...profile, name: event.target.value })} />
          </label>
          <label className="field">
            <span>Email</span>
            <input className="control" type="email" value={profile.email} onChange={(event) => setProfile({ ...profile, email: event.target.value })} />
          </label>
          {profileMessage && <div className="success-banner">{profileMessage}</div>}
          <button className="icon-button primary" type="submit" disabled={busy || !profile.name.trim() || !profile.email.trim()}>
            <Save size={18} />
            Save profile
          </button>
        </form>
        <form className="account-panel" onSubmit={savePassword}>
          <h3 className="form-title">Password</h3>
          <label className="field">
            <span>Current password</span>
            <input className="control" type="password" autoComplete="current-password" value={passwords.current_password} onChange={(event) => setPasswords({ ...passwords, current_password: event.target.value })} />
          </label>
          <label className="field">
            <span>New password</span>
            <input className="control" type="password" autoComplete="new-password" value={passwords.new_password} onChange={(event) => setPasswords({ ...passwords, new_password: event.target.value })} />
          </label>
          <label className="field">
            <span>Confirm password</span>
            <input className="control" type="password" autoComplete="new-password" value={passwords.confirm_password} onChange={(event) => setPasswords({ ...passwords, confirm_password: event.target.value })} />
          </label>
          {passwordMessage && <div className="success-banner">{passwordMessage}</div>}
          <button className="icon-button primary" type="submit" disabled={busy || !passwords.current_password || passwords.new_password.length < 8 || !passwords.confirm_password}>
            <Save size={18} />
            Change password
          </button>
        </form>
      </div>
    </div>
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

  function recordFromSchedule(item: TodayItem, status: ClassStatus): Partial<ClassRecord> | null {
    const rule = item.schedule_rule;
    if (!rule) return null;
    return {
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
    };
  }

  async function mark(item: TodayItem, status: ClassStatus) {
    const existing = item.record;
    if (existing) {
      await api.updateRecord(existing.id, { status });
    } else {
      const payload = recordFromSchedule(item, status);
      if (payload) {
        await api.createRecord(payload);
      }
    }
    await Promise.all([loadToday(false), refresh(false)]);
  }

  async function markScheduledDay(status: ClassStatus) {
    const scheduledItems = items.filter((item) => item.schedule_rule);
    if (scheduledItems.length === 0) return;
    setBusy(true);
    try {
      await Promise.all(
        scheduledItems.map((item) => {
          if (item.record) {
            return api.updateRecord(item.record.id, { status });
          }
          const payload = recordFromSchedule(item, status);
          return payload ? api.createRecord(payload) : Promise.resolve();
        }),
      );
      await Promise.all([loadToday(false), refresh(false)]);
    } finally {
      setBusy(false);
    }
  }

  const scheduledCount = items.filter((item) => item.schedule_rule).length;
  const doneCount = items.filter((item) => item.record && item.record.status !== "pending").length;
  const isToday = date === todayIso();

  return (
    <div className="view">
      <header className="view-header">
        <div>
          <p className="eyebrow">Daily check</p>
          <h2>Today</h2>
          <p className="date-heading">{longDateLabel(date)}</p>
        </div>
        <div className="date-controls">
          {!isToday && (
            <button className="icon-button subtle" type="button" onClick={() => setDate(todayIso())}>
              Today
            </button>
          )}
          <input className="control" type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </div>
      </header>
      <div className="summary-strip">
        <strong>{doneCount}</strong>
        <span>confirmed out of {items.length} expected or actual classes</span>
      </div>
      <div className="day-actions">
        <button className="icon-button success" type="button" disabled={busy || scheduledCount === 0} onClick={() => markScheduledDay("taught")}>
          <Check size={18} />
          Mark all taught
        </button>
        <button className="icon-button danger" type="button" disabled={busy || scheduledCount === 0} onClick={() => markScheduledDay("canceled")}>
          <X size={18} />
          Cancel day
        </button>
      </div>
      <div className="today-list">
        {busy && <div className="loading small">Refreshing...</div>}
        {!busy && items.length === 0 && <EmptyState text="No scheduled or recorded classes for this date." />}
        {items.map((item) => {
          const source = item.record ?? item.schedule_rule;
          if (!source) return null;
          const teachingClass = item.record?.teaching_class ?? item.schedule_rule?.teaching_class;
          const classroom = item.record?.classroom ?? teachingClass?.classroom;
          const period = periodLabel(item.schedule_rule?.notes);
          const notes = displayNotes(item.record?.notes, item.schedule_rule?.notes, teachingClass?.notes);
          const status = item.record?.status ?? "pending";
          return (
            <article className="class-row" key={`${item.kind}-${item.record?.id ?? item.schedule_rule?.id}`}>
              <div className="time-pill">
                {period && <span>{period}</span>}
                <strong>{timeOnly(source.start_time)}</strong>
              </div>
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
  const salaryPeriod = salaryPeriodFor(todayIso());
  const [filters, setFilters] = useState({
    start_date: salaryPeriod.start,
    end_date: salaryPeriod.end,
    teaching_class_id: "",
    status: "" as "" | ClassStatus,
  });
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

  const filteredRecords = records.filter((record) => {
    if (filters.start_date && record.date < filters.start_date) return false;
    if (filters.end_date && record.date > filters.end_date) return false;
    if (filters.teaching_class_id && String(record.teaching_class_id) !== filters.teaching_class_id) return false;
    if (filters.status && record.status !== filters.status) return false;
    return true;
  });

  return (
    <div className="view">
      <header className="view-header">
        <div>
          <p className="eyebrow">Manual correction</p>
          <h2>Records</h2>
          <p className="date-heading">{filteredRecords.length} shown out of {records.length} records</p>
        </div>
      </header>
      <div className="toolbar-form">
        <h3 className="form-title">Find records</h3>
        <label className="field compact">
          <span>From</span>
          <input className="control" type="date" value={filters.start_date} onChange={(event) => setFilters({ ...filters, start_date: event.target.value })} />
        </label>
        <label className="field compact">
          <span>To</span>
          <input className="control" type="date" value={filters.end_date} onChange={(event) => setFilters({ ...filters, end_date: event.target.value })} />
        </label>
        <label className="field">
          <span>Class</span>
          <select className="control" value={filters.teaching_class_id} onChange={(event) => setFilters({ ...filters, teaching_class_id: event.target.value })}>
            <option value="">All classes</option>
            {classes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Status</span>
          <select className="control" value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value as "" | ClassStatus })}>
            <option value="">All statuses</option>
            {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <button className="icon-button subtle" type="button" onClick={() => setFilters({ start_date: "", end_date: "", teaching_class_id: "", status: "" })}>
          Clear
        </button>
      </div>
      <form className="toolbar-form schedule-form" onSubmit={addRecord}>
        <h3 className="form-title">Add actual class</h3>
        <label className="field compact">
          <span>Date</span>
          <input className="control" type="date" value={form.date} onChange={(event) => setForm({ ...form, date: event.target.value })} />
        </label>
        <label className="field compact">
          <span>Start</span>
          <input className="control" type="time" value={form.start_time} onChange={(event) => setForm({ ...form, start_time: event.target.value })} />
        </label>
        <label className="field">
          <span>Class</span>
          <select className="control" value={form.teaching_class_id} onChange={(event) => chooseClass(event.target.value)}>
            <option value="">Choose class</option>
            {classes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Classroom</span>
          <input className="control" placeholder="Actual room" value={form.classroom} onChange={(event) => setForm({ ...form, classroom: event.target.value })} />
        </label>
        <label className="field compact">
          <span>Minutes</span>
          <input className="control" type="number" min="1" value={form.duration_minutes} onChange={(event) => setForm({ ...form, duration_minutes: Number(event.target.value) })} />
        </label>
        <label className="field wide-field">
          <span>Notes</span>
          <input className="control" placeholder="Optional" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
        </label>
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
            {filteredRecords.map((record) => (
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
  const initialSalaryPeriod = salaryPeriodFor(todayIso());
  const [mode, setMode] = useState<StatsMode>("salary");
  const [startDate, setStartDate] = useState(initialSalaryPeriod.start);
  const [endDate, setEndDate] = useState(initialSalaryPeriod.end);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    const request =
      mode === "custom" || mode === "salary"
        ? api.stats({ range: "custom", start_date: startDate, end_date: endDate })
        : api.stats({ range: mode });
    request.then(setStats).catch((err) => setError(err instanceof Error ? err.message : "Could not load stats"));
  }, [mode, startDate, endDate]);

  function chooseMode(nextMode: StatsMode) {
    setMode(nextMode);
    if (nextMode === "salary") {
      const period = salaryPeriodFor(todayIso());
      setStartDate(period.start);
      setEndDate(period.end);
    }
  }

  return (
    <div className="view">
      <header className="view-header">
        <div>
          <p className="eyebrow">Teaching totals</p>
          <h2>Stats</h2>
          {stats && <p className="date-heading">{stats.start_date} to {stats.end_date}</p>}
        </div>
        <div className="segmented">
          <button className={mode === "week" ? "selected" : ""} onClick={() => chooseMode("week")}>Week</button>
          <button className={mode === "month" ? "selected" : ""} onClick={() => chooseMode("month")}>Month</button>
          <button className={mode === "salary" ? "selected" : ""} onClick={() => chooseMode("salary")}>Salary</button>
          <button className={mode === "custom" ? "selected" : ""} onClick={() => chooseMode("custom")}>Custom</button>
        </div>
      </header>
      {(mode === "salary" || mode === "custom") && (
        <div className="toolbar-form">
          <input className="control" type="date" value={startDate} onChange={(event) => { setMode("custom"); setStartDate(event.target.value); }} />
          <span className="range-separator">to</span>
          <input className="control" type="date" value={endDate} onChange={(event) => { setMode("custom"); setEndDate(event.target.value); }} />
        </div>
      )}
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
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importActiveFrom, setImportActiveFrom] = useState(todayIso());
  const [importRows, setImportRows] = useState<ScheduleImportDraft[]>([]);
  const [importBusy, setImportBusy] = useState(false);
  const [clearBusy, setClearBusy] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importMessage, setImportMessage] = useState<string | null>(null);

  function selectImportFile(file: File | null, source: "picker" | "paste") {
    setImportFile(file);
    setImportError(null);
    if (file && source === "paste") {
      setImportMessage(`Pasted screenshot ready: ${file.name || "clipboard image"}.`);
    } else if (file) {
      setImportMessage(`Selected screenshot: ${file.name}.`);
    } else {
      setImportMessage(null);
    }
  }

  function handlePaste(data: DataTransfer): boolean {
    const file = clipboardImageFile(data);
    if (!file) {
      return false;
    }
    selectImportFile(file, "paste");
    return true;
  }

  useEffect(() => {
    function onWindowPaste(event: ClipboardEvent) {
      if (event.defaultPrevented || !event.clipboardData) {
        return;
      }
      if (handlePaste(event.clipboardData)) {
        event.preventDefault();
      }
    }

    window.addEventListener("paste", onWindowPaste);
    return () => window.removeEventListener("paste", onWindowPaste);
  }, []);

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

  async function importSchedule(event: React.FormEvent) {
    event.preventDefault();
    if (!importFile) return;
    setImportBusy(true);
    setImportError(null);
    setImportMessage(null);
    try {
      const result = await api.importScheduleImage(importFile);
      setImportRows(
        result.lessons
          .map((lesson) => ({ ...lesson, class_name: normalizeClassName(lesson.class_name), enabled: true }))
          .sort((left, right) => left.weekday - right.weekday || left.start_time.localeCompare(right.start_time)),
      );
      setImportMessage(`${result.lessons.length} lessons found. Review before saving.`);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Could not import schedule image");
    } finally {
      setImportBusy(false);
    }
  }

  function updateImportRow(index: number, patch: Partial<ScheduleImportDraft>) {
    setImportRows((rows) => rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  function removeImportRow(index: number) {
    setImportRows((rows) => rows.filter((_, rowIndex) => rowIndex !== index));
  }

  async function saveImportedSchedule() {
    const selectedRows = importRows.filter((row) => row.enabled && normalizeClassName(row.class_name));
    if (selectedRows.length === 0) return;
    setImportBusy(true);
    setImportError(null);
    setImportMessage(null);
    try {
      const classByName = new Map(classes.map((item) => [classKey(item.name), item]));
      for (const row of selectedRows) {
        const normalizedName = normalizeClassName(row.class_name);
        if (!classByName.has(classKey(normalizedName))) {
          const created = await api.createClass({ name: normalizedName, classroom: null, notes: null });
          classByName.set(classKey(created.name), created);
        }
      }

      let createdCount = 0;
      let skippedCount = 0;
      for (const row of selectedRows) {
        const teachingClass = classByName.get(classKey(row.class_name));
        if (!teachingClass) continue;
        const note = row.period?.trim() || row.notes?.trim() || null;
        const alreadyExists = schedule.some(
          (rule) =>
            classKey(rule.teaching_class.name) === classKey(teachingClass.name) &&
            rule.weekday === row.weekday &&
            timeOnly(rule.start_time) === row.start_time &&
            rule.duration_minutes === row.duration_minutes &&
            (rule.notes ?? null) === note &&
            rule.active_from === importActiveFrom,
        );
        if (alreadyExists) {
          skippedCount += 1;
          continue;
        }
        await api.createSchedule({
          teaching_class_id: teachingClass.id,
          weekday: row.weekday,
          start_time: row.start_time,
          duration_minutes: row.duration_minutes,
          active_from: importActiveFrom,
          notes: note,
        });
        createdCount += 1;
      }

      setImportRows([]);
      setImportFile(null);
      setImportMessage(`Saved ${createdCount} lessons${skippedCount ? `, skipped ${skippedCount} duplicates` : ""}.`);
      await refresh();
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Could not save imported schedule");
    } finally {
      setImportBusy(false);
    }
  }

  async function clearSchedule() {
    if (schedule.length === 0 || clearBusy) return;
    const confirmed = window.confirm(
      "Clear all weekly schedule rules? Existing class records will stay in Records.",
    );
    if (!confirmed) return;
    setClearBusy(true);
    setImportError(null);
    setImportMessage(null);
    try {
      await api.clearSchedule();
      setImportRows([]);
      setImportMessage("Weekly schedule cleared. Existing records were not deleted.");
      await refresh();
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Could not clear schedule");
    } finally {
      setClearBusy(false);
    }
  }

  return (
    <div className="view">
      <header className="view-header">
        <div>
          <p className="eyebrow">Expected classes</p>
          <h2>Schedule</h2>
        </div>
        <button className="icon-button danger" type="button" disabled={clearBusy || schedule.length === 0} onClick={clearSchedule} title="Clear weekly schedule">
          <Trash2 size={18} />
          {clearBusy ? "Clearing..." : "Clear schedule"}
        </button>
      </header>
      <form className="toolbar-form schedule-form" onSubmit={importSchedule}>
        <h3 className="form-title">Import timetable image</h3>
        <div
          className="paste-target"
          tabIndex={0}
          onPaste={(event) => {
            if (handlePaste(event.clipboardData)) {
              event.preventDefault();
            }
          }}
        >
          <Upload size={24} />
          <div>
            <strong>Paste a screenshot here</strong>
            <span>Copy a timetable screenshot, then press Ctrl+V or Command+V.</span>
            {importFile && <em>{importFile.name || "Clipboard image"} is ready to import.</em>}
          </div>
        </div>
        <label className="field wide-field">
          <span>Or choose image file</span>
          <input className="control file-control" type="file" accept="image/*" onChange={(event) => selectImportFile(event.target.files?.[0] ?? null, "picker")} />
        </label>
        <label className="field compact">
          <span>Active from</span>
          <input className="control" type="date" value={importActiveFrom} onChange={(event) => setImportActiveFrom(event.target.value)} />
        </label>
        <button className="icon-button primary" type="submit" disabled={importBusy || !importFile} title="Import timetable image">
          <Upload size={18} />
          {importBusy ? "Reading..." : "Import"}
        </button>
      </form>
      {importError && <div className="banner">{importError}</div>}
      {importMessage && <div className="success-banner">{importMessage}</div>}
      {importRows.length > 0 && (
        <div className="import-preview">
          <div className="import-preview-header">
            <h3 className="form-title">Review imported lessons</h3>
            <button className="icon-button primary" type="button" disabled={importBusy} onClick={saveImportedSchedule}>
              <Save size={18} />
              Save selected
            </button>
          </div>
          <div className="table-wrap">
            <table className="import-table">
              <thead>
                <tr>
                  <th>Use</th>
                  <th>Day</th>
                  <th>Period</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>Minutes</th>
                  <th>Class</th>
                  <th>Confidence</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {importRows.map((row, index) => (
                  <tr key={`${row.weekday}-${row.start_time}-${row.class_name}-${index}`}>
                    <td>
                      <input type="checkbox" checked={row.enabled} onChange={(event) => updateImportRow(index, { enabled: event.target.checked })} />
                    </td>
                    <td>
                      <select className="inline-select" value={row.weekday} onChange={(event) => updateImportRow(index, { weekday: Number(event.target.value) })}>
                        {weekdays.map((day, dayIndex) => <option key={day} value={dayIndex}>{day}</option>)}
                      </select>
                    </td>
                    <td>
                      <input className="inline-text compact-cell" value={row.period ?? ""} onChange={(event) => updateImportRow(index, { period: event.target.value || null })} />
                    </td>
                    <td>
                      <input className="inline-text time-cell" type="time" value={row.start_time} onChange={(event) => updateImportRow(index, { start_time: event.target.value })} />
                    </td>
                    <td>
                      <input className="inline-text time-cell" type="time" value={row.end_time} onChange={(event) => updateImportRow(index, { end_time: event.target.value })} />
                    </td>
                    <td>
                      <input className="inline-number" type="number" min="1" value={row.duration_minutes} onChange={(event) => updateImportRow(index, { duration_minutes: Number(event.target.value) })} />
                    </td>
                    <td>
                      <input className="inline-text" value={row.class_name} onChange={(event) => updateImportRow(index, { class_name: event.target.value })} />
                    </td>
                    <td>{Math.round(row.confidence * 100)}%</td>
                    <td>
                      <button className="icon-button subtle" type="button" onClick={() => removeImportRow(index)} title="Remove row">
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <form className="toolbar-form schedule-form" onSubmit={addClass}>
        <h3 className="form-title">Add class</h3>
        <label className="field">
          <span>Class name</span>
          <input className="control" placeholder="PA4" value={newClass.name} onChange={(event) => setNewClass({ ...newClass, name: event.target.value })} />
        </label>
        <label className="field">
          <span>Usual classroom</span>
          <input className="control" placeholder="2-201" value={newClass.classroom} onChange={(event) => setNewClass({ ...newClass, classroom: event.target.value })} />
        </label>
        <label className="field wide-field">
          <span>Class notes</span>
          <input className="control" placeholder="Optional" value={newClass.notes} onChange={(event) => setNewClass({ ...newClass, notes: event.target.value })} />
        </label>
        <button className="icon-button primary" title="Save class"><Save size={18} /> Save</button>
      </form>
      <form className="toolbar-form schedule-form" onSubmit={addRule}>
        <h3 className="form-title">Add weekly lesson</h3>
        <label className="field">
          <span>Class</span>
          <select className="control" value={form.teaching_class_id} onChange={(event) => setForm({ ...form, teaching_class_id: event.target.value })}>
            <option value="">Choose class</option>
            {classes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <label className="field">
          <span>Weekday</span>
          <select className="control" value={form.weekday} onChange={(event) => setForm({ ...form, weekday: event.target.value })}>
            {weekdays.map((day, index) => <option key={day} value={index}>{day}</option>)}
          </select>
        </label>
        <label className="field compact">
          <span>Start</span>
          <input className="control" type="time" value={form.start_time} onChange={(event) => setForm({ ...form, start_time: event.target.value })} />
        </label>
        <label className="field compact">
          <span>Minutes</span>
          <input className="control" type="number" min="1" value={form.duration_minutes} onChange={(event) => setForm({ ...form, duration_minutes: Number(event.target.value) })} />
        </label>
        <label className="field wide-field">
          <span>Period / notes</span>
          <input className="control" placeholder="P1, P2, or other note" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
        </label>
        <button className="icon-button primary" type="submit" title="Add weekly lesson"><Plus size={18} /> Add</button>
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



