import type {
  ClassRecord,
  ScheduleRule,
  Semester,
  Stats,
  TeachingClass,
  TodayItem,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

type StatsRange = "week" | "month" | "semester" | "custom";

interface StatsParams {
  range?: StatsRange;
  start_date?: string;
  end_date?: string;
  semester_id?: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
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
