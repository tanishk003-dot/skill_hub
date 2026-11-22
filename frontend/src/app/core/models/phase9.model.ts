export interface ReadinessConfig {
  id?: number;
  assessment_weight: number;
  coding_weight: number;
  training_weight: number;
  attendance_weight: number;
  consistency_weight: number;
  updated_at?: string;
  updated_by?: number;
}

export interface ReadinessBreakdown {
  assessment_pct: number;
  coding_pct: number;
  training_pct: number;
  attendance_pct: number;
  consistency_pct: number;
  weighted_total: number;
}

export interface SkillDnaVector {
  technical_accuracy: number;
  problem_solving: number;
  code_quality: number;
  learning_velocity: number;
  attendance_consistency: number;
}

export interface ReadinessHistoryPoint {
  date: string;
  score: number;
}

export interface ReadinessResponse {
  ase_id: number;
  ase_name: string;
  overall_score: number;
  breakdown: ReadinessBreakdown;
  skill_dna: SkillDnaVector;
  legal_disclaimer: string;
  formula_display: string;
  trend: ReadinessHistoryPoint[];
}

export interface Milestone {
  id: number;
  day_category: number; // 30, 60, 90
  milestone_type: string;
  title: string;
  description: string;
  xp_reward: number;
  is_completed: boolean;
  completed_at?: string;
}

export interface GamificationProfile {
  total_xp: number;
  current_level: number;
  streak_days: number;
  badges: string[];
  is_leaderboard_opt_in: boolean;
}

export interface LeaderboardEntry {
  rank: number;
  ase_name: string;
  total_xp: number;
  current_level: number;
  badges_count: number;
}

export interface JourneyMapResponse {
  profile: GamificationProfile;
  milestones: Milestone[];
}

export interface RoadmapTask {
  id: string;
  title: string;
  duration_est: string;
  category: string;
  is_done: boolean;
  training_id?: number;
}

export interface RoadmapPlan {
  id: number;
  week_number: number;
  weak_skills: string[];
  tasks: RoadmapTask[];
  summary: string;
  generated_at: string;
}

export interface RiskSignal {
  ase_id: number;
  ase_name: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  flagged_reasons: string[];
  ai_explanation: string;
  last_nudged_at?: string;
  can_nudge: boolean;
}

export interface CEOCohortComparison {
  cohort_id: number;
  cohort_name: string;
  member_count: number;
  avg_readiness: number;
  avg_completion: number;
  is_masked: boolean;
}

export interface CEOOverview {
  org_readiness_avg: number;
  time_to_productivity_days: number | null;
  time_to_productivity_display?: string;
  time_to_productivity_status?: string;
  time_to_productivity_sample_size?: number;
  training_roi_uplift_pct: number | null;
  training_roi_display?: string;
  training_roi_status?: string;
  training_roi_sample_size?: number;
  total_ases: number;
  high_risk_count: number;
  skill_gap_heatmap: { [skill: string]: number };
  cohorts: CEOCohortComparison[];
  formulas: { [key: string]: string };
  correlation_disclaimer: string;
}

export interface CertificateItem {
  id: number;
  cert_uuid: string;
  course_title: string;
  cert_type: string;
  issue_date: string;
  status: string;
  pdf_url?: string;
  verify_url?: string;
}

export interface PublicVerifyResult {
  valid: boolean;
  cert_uuid: string;
  recipient_display_name?: string;
  course_title?: string;
  cert_type?: string;
  issue_date?: string;
  status?: string;
  message?: string;
}

export interface MockInterviewMessage {
  role: 'assistant' | 'user';
  content: string;
  timestamp?: string;
}

export interface MockInterviewSession {
  session_id: string;
  interview_type: string;
  difficulty: string;
  topic: string;
  status: string;
  current_question: string;
  messages: MockInterviewMessage[];
  previous_feedback?: {
    strengths?: string[];
    improvements?: string[];
    rating?: string;
  };
  is_demo_mode: boolean;
}
