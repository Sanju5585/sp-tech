export type Role = "super_admin" | "school_admin" | "teacher" | "student" | "parent";

export type Session = {
  access_token: string;
  refresh_token: string;
  role: Role;
  school_id: number | null;
  user_id: number;
  full_name: string;
  teacher_id?: number | null;
};

export type Dashboard = {
  total_classes: number;
  total_sections: number;
  total_teachers: number;
  total_subjects: number;
  total_rooms: number;
  timetable_status: string;
  last_generated: string | null;
  hard_conflicts: number;
  soft_preference_score: number;
  teacher_workload: { teacher_id: number; name: string; periods: number; max_week: number }[];
  selected_version_id: number | null;
};

export type School = {
  id: number;
  name: string;
  code: string;
  address: string;
  phone: string;
  timezone: string;
  setup_completed: boolean;
};

export type StaffUser = {
  id: number;
  username: string;
  email: string;
  full_name: string;
  phone: string;
  is_active: boolean;
  school_id: number | null;
  role: Role;
};

export type Period = {
  id: number;
  name: string;
  period_index: number;
  start_time: string;
  end_time: string;
  is_break: boolean;
  is_free_slot: boolean;
};

export type Day = { id: number; name: string; weekday: number; is_working: boolean };

export type Section = {
  id: number;
  class_id: number;
  name: string;
  display_name: string;
  label: string;
  room_id: number | null;
};

export type SchoolClass = {
  id: number;
  name: string;
  grade_level: number;
  sections: Section[];
};

export type Subject = {
  id: number;
  name: string;
  short_name: string;
  code: string;
  subject_type: string;
  weekly_required_periods: number;
  preferred_periods: number[];
  can_be_consecutive: boolean;
  requires_room: boolean;
  required_room_type: string | null;
  priority: number;
  is_difficult: boolean;
};

export type Teacher = {
  id: number;
  name: string;
  employee_id: string;
  email: string;
  phone: string;
  max_periods_day: number;
  max_periods_week: number;
  min_periods_day: number;
  subject_ids: number[];
};

export type Room = {
  id: number;
  name: string;
  capacity: number;
  room_type: string;
  allowed_subject_ids: number[];
};

export type Assignment = {
  id: number;
  teacher_id: number;
  section_id: number;
  subject_id: number;
  weekly_periods: number | null;
  teacher_name: string;
  section_label: string;
  subject_name: string;
};

export type Rule = {
  id: number;
  name: string;
  kind: string;
  constraint_type: string;
  payload: Record<string, unknown>;
  weight: number;
  is_active: boolean;
  natural_language: string;
  source: string;
};

export type Entry = {
  id: number;
  version_id: number;
  section_id: number;
  day_id: number;
  period_id: number;
  subject_id: number | null;
  teacher_id: number | null;
  room_id: number | null;
  is_free: boolean;
  is_locked: boolean;
  subject_name: string;
  subject_short: string;
  teacher_name: string;
  room_name: string;
  section_label: string;
  day_name: string;
  period_name: string;
  period_index: number;
};

export type Version = {
  id: number;
  name: string;
  status: string;
  score: number;
  score_breakdown: Record<string, number>;
  constraint_stats: Record<string, unknown>;
  warnings: string[];
  unsatisfied_preferences: string[];
  generation_time_ms: number;
  is_selected: boolean;
};
