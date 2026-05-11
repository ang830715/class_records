export type ClassStatus = "taught" | "canceled" | "rescheduled" | "extra" | "pending";

export interface User {
  id: number;
  name: string;
  email?: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface AuthToken {
  access_token: string;
  token_type: "bearer";
  user: User;
}

export interface TeachingClass {
  id: number;
  name: string;
  classroom?: string | null;
  notes?: string | null;
}

export interface ScheduleRule {
  id: number;
  user_id: number;
  teaching_class_id: number;
  weekday: number;
  start_time: string;
  duration_minutes: number;
  active_from: string;
  active_until?: string | null;
  is_active: boolean;
  notes?: string | null;
  teaching_class: TeachingClass;
}

export interface ScheduleImportCandidate {
  weekday: number;
  period?: string | null;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  class_name: string;
  notes?: string | null;
  confidence: number;
}

export interface ScheduleImportResult {
  lessons: ScheduleImportCandidate[];
}

export interface ClassRecord {
  id: number;
  user_id: number;
  schedule_rule_id?: number | null;
  teaching_class_id: number;
  classroom?: string | null;
  date: string;
  start_time: string;
  duration_minutes: number;
  status: ClassStatus;
  fee_amount: string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  teaching_class: TeachingClass;
}

export interface TodayItem {
  kind: "expected" | "matched" | "actual";
  schedule_rule?: ScheduleRule | null;
  record?: ClassRecord | null;
  expected_date: string;
}

export interface StatsByClass {
  teaching_class_id: number;
  class_name: string;
  taught_count: number;
  total_minutes: number;
}

export interface Stats {
  start_date: string;
  end_date: string;
  taught_count: number;
  canceled_count: number;
  rescheduled_count: number;
  extra_count: number;
  pending_count: number;
  total_minutes: number;
  salary: string;
  by_class: StatsByClass[];
}

export interface Semester {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
}
