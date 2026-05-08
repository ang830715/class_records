import type {
  AuthToken,
  ClassRecord,
  ScheduleRule,
  Semester,
  Stats,
  TeachingClass,
  TodayItem,
  User,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const AUTH_TOKEN_KEY = "teaching-records-token";

type StatsRange = "week" | "month" | "semester" | "custom";

interface StatsParams {
  range?: StatsRange;
  start_date?: string;
  end_date?: string;
  semester_id?: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (response.status === 401) {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  setToken: (token: string | null) => {
    if (token) {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  },
  login: (email: string, password: string) =>
    request<AuthToken>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<User>("/auth/me"),
  updateMe: (body: { name: string; email: string }) =>
    request<User>("/auth/me", { method: "PUT", body: JSON.stringify(body) }),
  updatePassword: (body: { current_password: string; new_password: string }) =>
    request<void>("/auth/password", { method: "PUT", body: JSON.stringify(body) }),

  classes: () => request<TeachingClass[]>("/classes"),
  createClass: (body: Partial<TeachingClass>) =>
    request<TeachingClass>("/classes", { method: "POST", body: JSON.stringify(body) }),
  updateClass: (id: number, body: Partial<TeachingClass>) =>
    request<TeachingClass>(`/classes/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteClass: (id: number) => request<void>(`/classes/${id}`, { method: "DELETE" }),

  schedule: () => request<ScheduleRule[]>("/schedule"),
  createSchedule: (body: Partial<ScheduleRule>) =>
    request<ScheduleRule>("/schedule", { method: "POST", body: JSON.stringify(body) }),
  updateSchedule: (id: number, body: Partial<ScheduleRule>) =>
    request<ScheduleRule>(`/schedule/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteSchedule: (id: number) => request<void>(`/schedule/${id}`, { method: "DELETE" }),

  records: () => request<ClassRecord[]>("/records"),
  createRecord: (body: Partial<ClassRecord>) =>
    request<ClassRecord>("/records", { method: "POST", body: JSON.stringify(body) }),
  updateRecord: (id: number, body: Partial<ClassRecord>) =>
    request<ClassRecord>(`/records/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteRecord: (id: number) => request<void>(`/records/${id}`, { method: "DELETE" }),

  today: (date?: string) => request<TodayItem[]>(`/today${date ? `?target_date=${date}` : ""}`),
  stats: (params: StatsParams = {}) => {
    const query = new URLSearchParams();
    query.set("range", params.range ?? "month");
    if (params.start_date) query.set("start_date", params.start_date);
    if (params.end_date) query.set("end_date", params.end_date);
    if (params.semester_id) query.set("semester_id", String(params.semester_id));
    return request<Stats>(`/stats?${query.toString()}`);
  },
  semesters: () => request<Semester[]>("/semesters"),
  createSemester: (body: Partial<Semester>) =>
    request<Semester>("/semesters", { method: "POST", body: JSON.stringify(body) }),
};
