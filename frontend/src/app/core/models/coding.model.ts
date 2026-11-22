export interface TestCaseResult {
  test_case_id: number;
  status: string;
  is_sample: boolean;
  input?: string | null;
  expected_output?: string | null;
  actual_output?: string | null;
  execution_time_ms: number;
  memory_kb: number;
  error_message?: string | null;
  marks_awarded: number;
}

export interface CodingRunRequest {
  attempt_id: number;
  question_id: number;
  language: string;
  source_code: string;
  custom_input?: string;
}

export interface CodingRunResponse {
  status: string;
  passed: boolean;
  results: TestCaseResult[];
  stdout?: string | null;
  error?: string | null;
  runs_remaining?: number | null;
}

export interface CodingSubmitRequest {
  attempt_id: number;
  question_id: number;
  language: string;
  source_code: string;
}

export interface CodingSubmitResponse {
  submission_id: number;
  status: string;
  passed_sample_cases: number;
  total_sample_cases: number;
  passed_hidden_cases: number;
  total_hidden_cases: number;
  total_passed: number;
  total_cases: number;
  score: number;
  results: TestCaseResult[];
  error?: string | null;
}

export interface CodingSubmissionOut {
  id: number;
  attempt_id: number;
  question_id: number;
  ase_id: number;
  language: string;
  status: string;
  score: number;
  total_passed: number;
  total_cases: number;
  execution_time_ms: number;
  memory_used_kb: number;
  ai_review?: string | null;
  created_at: string;
}

export interface PlagiarismFlag {
  id: number;
  question_id: number;
  attempt1_id: number;
  attempt2_id: number;
  ase1_id: number;
  ase1_name: string;
  ase2_id: number;
  ase2_name: string;
  similarity_score: number;
  status: string;
  flagged_at: string;
}

export interface CodeReviewResponse {
  submission_id: number;
  review: string;
}

export interface OnboardingProgress {
  ase_id: number;
  ase_name: string;
  overall_percentage: number;
  assessments: {
    completed: number;
    total: number;
    percentage: number;
    weight: number;
  };
  trainings: {
    completed: number;
    total: number;
    percentage: number;
    weight: number;
  };
  live_classes: {
    attended: number;
    total: number;
    percentage: number;
    weight: number;
  };
}
