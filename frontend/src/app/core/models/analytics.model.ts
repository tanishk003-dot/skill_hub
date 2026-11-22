export interface CandidateImprovement {
  skill: string;
  score: number;
  priority: 'HIGH' | 'MEDIUM';
  priority_badge: string;
  suggested_action: string;
  target_goal: string;
}

export interface ProgressHistoryItem {
  attempt_id: number;
  assessment_title: string;
  date: string;
  percentage: number;
  total_score: number;
  max_score: number;
  passed: boolean;
}

export interface ASEDashboardData {
  summary: {
    total_attempts: number;
    passed_attempts: number;
    average_score: number;
    latest_score: number;
    latest_passed?: boolean;
    has_attempts: boolean;
  };
  radar_skills: {
    labels: string[];
    values: number[];
  };
  section_scores: {
    labels: string[];
    scores: number[];
    max_scores: number[];
  };
  progress_history: ProgressHistoryItem[];
  strong_areas: string[];
  weak_areas: string[];
  what_to_improve: CandidateImprovement[];
  latest_attempt_id?: number;
}

export interface HeatmapRow {
  ase_id: number;
  ase_name: string;
  scores: { [skill: string]: number | null };
  has_attempt: boolean;
}

export interface MentorRankingRow {
  rank: number | string;
  ase_id: number;
  ase_name: string;
  ase_email: string;
  average_score: number;
  attempts_count: number;
  passed_count: number;
  flagged: boolean;
  suggested_focus: string;
  latest_attempt_id?: number;
  has_attempt: boolean;
}

export interface NeedsAttentionItem {
  ase_id: number;
  ase_name: string;
  ase_email: string;
  reason: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  score?: number;
  status?: string;
}

export interface TrainingMetrics {
  total_assigned: number;
  completed: number;
  in_progress: number;
  not_started: number;
  completion_rate: number;
}

export interface AttendanceMetrics {
  total_classes: number;
  total_invited: number;
  total_attended: number;
  total_absent: number;
  attendance_rate: number;
}

export interface OverdueTrainingItem {
  assignment_id: number;
  training_title: string;
  ase_id: number;
  ase_name: string;
  due_date: string;
  progress_percent: number;
}

export interface MentorDashboardData {
  cohort_options: { id: number; name: string }[];
  selected_cohort_id?: number;
  cohort_radar: {
    labels: string[];
    values: number[];
  };
  heatmap: {
    skills: string[];
    rows: HeatmapRow[];
  };
  ranking_table: MentorRankingRow[];
  needs_attention: NeedsAttentionItem[];
  training_metrics?: TrainingMetrics;
  attendance_metrics?: AttendanceMetrics;
  overdue_trainings?: OverdueTrainingItem[];
}

export interface CohortComparisonItem {
  cohort_id: number;
  cohort_name: string;
  member_count: number;
  average_score: number;
  passing_rate: number;
}

export interface OrgSkillGapItem {
  skill: string;
  average_score: number;
  benchmark: number;
  gap: number;
  is_gap: boolean;
}

export interface AdminDashboardData {
  cohort_comparison: CohortComparisonItem[];
  completion_rate: {
    total_assigned: number;
    completed: number;
    in_progress: number;
    expired_or_unattempted: number;
    percentage: number;
  };
  org_skill_gaps: OrgSkillGapItem[];
  users_summary: {
    total_users: number;
    active_users: number;
    inactive_users: number;
    pending_attempts: number;
  };
  training_metrics?: TrainingMetrics;
  attendance_metrics?: AttendanceMetrics;
  overdue_trainings?: OverdueTrainingItem[];
}
