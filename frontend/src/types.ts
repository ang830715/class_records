export type ClassStatus = "taught" | "canceled" | "rescheduled" | "extra" | "pending";

export interface StudentGroup {
  id: number;
  name: string;
  notes?: string | null;
}

export interface Course {
  id: number;
  name: string;
  default_duration_minutes: number;
  default_rate: string;
}

export interface ScheduleRule {
  id: number;
  user_id: number;
  student_group_id: number;
  course_id: number;
  weekday: number;
  start_time: string;
  duration_minutes: number;
  active_from: string;
  active_until?: string | null;
  is_active: boolean;
  notes?: string | null;
  student_group: StudentGroup;
  course: Course;
}

export interface ClassRecord {
  id: number;
  user_id: number;
  schedule_rule_id?: number | null;
  student_group_id: number;
  course_id: number;
  date: string;
  start_time: string;
  duration_minutes: number;
  status: ClassStatus;
  fee_amount: string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  student_group: StudentGroup;
  course: Course;
}

export interface TodayItem {
  kind: "expected" | "matched" | "actual";
  schedule_rule?: ScheduleRule | null;
  record?: ClassRecord | null;
  expected_date: string;
}

export interface StatsByStudent {
  student_group_id: number;
  student_group_name: string;
  taught_count: number;
  total_minutes: number;
  salary: string;
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
  by_student: StatsByStudent[];
}

export interface Semester {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
}
