-- L&K Skill Hub - Complete Database Schema (MySQL 8.0+)
-- Database: skillhub_db

CREATE DATABASE IF NOT EXISTS `skillhub_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `skillhub_db`;

-- Drop existing tables in reverse dependency order
DROP TABLE IF EXISTS `ai_insights_cache`;
DROP TABLE IF EXISTS `llm_usage_logs`;
DROP TABLE IF EXISTS `chat_messages`;
DROP TABLE IF EXISTS `chat_sessions`;
DROP TABLE IF EXISTS `reminders_sent`;
DROP TABLE IF EXISTS `notifications`;
DROP TABLE IF EXISTS `live_class_attendees`;
DROP TABLE IF EXISTS `live_classes`;
DROP TABLE IF EXISTS `training_assignments`;
DROP TABLE IF EXISTS `trainings`;
DROP TABLE IF EXISTS `exam_violations`;
DROP TABLE IF EXISTS `assessment_responses`;
DROP TABLE IF EXISTS `assessment_attempts`;
DROP TABLE IF EXISTS `assessment_assignments`;
DROP TABLE IF EXISTS `cohort_members`;
DROP TABLE IF EXISTS `cohorts`;
DROP TABLE IF EXISTS `assessment_section_questions`;
DROP TABLE IF EXISTS `assessment_sections`;
DROP TABLE IF EXISTS `assessments`;
DROP TABLE IF EXISTS `question_bank`;
DROP TABLE IF EXISTS `mentor_ase_assignments`;
DROP TABLE IF EXISTS `users`;

-- ============================================================================
-- 1. Users Table (Phase 1, updated Phase 4 with is_demo)
-- ============================================================================
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `email` VARCHAR(150) NOT NULL UNIQUE,
    `hashed_password` VARCHAR(255) NOT NULL,
    `role` ENUM('ADMIN', 'MENTOR', 'ASE') NOT NULL DEFAULT 'ASE',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `last_splash_date` VARCHAR(20) NULL,
    `fresh_login` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_buddy_volunteer` BOOLEAN NOT NULL DEFAULT FALSE,
    `failed_login_attempts` INT NOT NULL DEFAULT 0,
    `lockout_until` DATETIME(6) NULL,
    `is_locked` BOOLEAN NOT NULL DEFAULT FALSE,
    `must_change_password` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_users_role` (`role`),
    INDEX `idx_users_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 2. Mentor-ASE Assignments (Phase 1)
-- ============================================================================
CREATE TABLE `mentor_ase_assignments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `mentor_id` INT NOT NULL,
    `ase_id` INT NOT NULL UNIQUE,
    `assigned_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_assignment_mentor` FOREIGN KEY (`mentor_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_assignment_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_assignment_mentor` (`mentor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 3. Question Bank (Phase 2)
-- ============================================================================
CREATE TABLE `question_bank` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `type` ENUM('Psychometric', 'Behavioural', 'Logical Thinking', 'Reasoning', 'Pattern Recognition', 'Aptitude') NOT NULL,
    `difficulty` ENUM('Easy', 'Medium', 'Hard') NOT NULL DEFAULT 'Medium',
    `skill_category` VARCHAR(100) NOT NULL,
    `question_text` TEXT NOT NULL,
    `question_type` ENUM('SINGLE_CHOICE', 'MULTI_CHOICE', 'CODING') NOT NULL DEFAULT 'SINGLE_CHOICE',
    `options` JSON NOT NULL,
    `correct_answers` JSON NOT NULL,
    `marks` INT NOT NULL DEFAULT 1,
    `problem_statement` TEXT NULL,
    `allowed_languages` JSON NULL,
    `starter_code` JSON NULL,
    `sample_test_cases` JSON NULL,
    `hidden_test_cases` JSON NULL,
    `time_limit_sec` FLOAT NULL DEFAULT 2.0,
    `memory_limit_mb` INT NULL DEFAULT 256,
    `version` INT NOT NULL DEFAULT 1,
    `author_id` INT NULL,
    `is_ai_generated` BOOLEAN NOT NULL DEFAULT FALSE,
    `ai_review_status` VARCHAR(30) NOT NULL DEFAULT 'APPROVED',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_question_type` (`type`),
    INDEX `idx_question_difficulty` (`difficulty`),
    INDEX `idx_question_skill` (`skill_category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 4. Assessments (Phase 2)
-- ============================================================================
CREATE TABLE `assessments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(200) NOT NULL,
    `type` ENUM('Psychometric', 'Behavioural', 'Logical Thinking', 'Reasoning', 'Pattern Recognition', 'Aptitude') NOT NULL,
    `total_duration_minutes` INT NOT NULL DEFAULT 30,
    `passing_percentage` FLOAT NOT NULL DEFAULT 60.0,
    `randomize_questions` BOOLEAN NOT NULL DEFAULT FALSE,
    `randomize_options` BOOLEAN NOT NULL DEFAULT FALSE,
    `webcam_mode` VARCHAR(20) NOT NULL DEFAULT 'OFF',
    `webcam_policy` VARCHAR(20) NOT NULL DEFAULT 'WARNING_ONLY',
    `camera_no_face_seconds` INT NOT NULL DEFAULT 10,
    `camera_multiple_faces_seconds` INT NOT NULL DEFAULT 5,
    `camera_head_turn_seconds` INT NOT NULL DEFAULT 12,
    `camera_grace_period_seconds` INT NOT NULL DEFAULT 30,
    `created_by` INT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_assessment_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_assessment_type` (`type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 5. Assessment Sections (Phase 2)
-- ============================================================================
CREATE TABLE `assessment_sections` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `assessment_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `order_index` INT NOT NULL DEFAULT 0,
    `timer_minutes` INT NOT NULL DEFAULT 15,
    CONSTRAINT `fk_section_assessment` FOREIGN KEY (`assessment_id`) REFERENCES `assessments` (`id`) ON DELETE CASCADE,
    INDEX `idx_section_assessment` (`assessment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 6. Assessment Section Questions Mapping (Phase 2)
-- ============================================================================
CREATE TABLE `assessment_section_questions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `section_id` INT NOT NULL,
    `question_id` INT NOT NULL,
    `order_index` INT NOT NULL DEFAULT 0,
    CONSTRAINT `fk_asq_section` FOREIGN KEY (`section_id`) REFERENCES `assessment_sections` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_asq_question` FOREIGN KEY (`question_id`) REFERENCES `question_bank` (`id`) ON DELETE CASCADE,
    INDEX `idx_asq_section` (`section_id`),
    INDEX `idx_asq_question` (`question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 7. Cohorts Table (Phase 4)
-- ============================================================================
CREATE TABLE `cohorts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(150) NOT NULL UNIQUE,
    `description` TEXT NULL,
    `start_date` DATE NOT NULL,
    `created_by` INT NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_cohort_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_cohort_name` (`name`),
    INDEX `idx_cohort_start_date` (`start_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 8. Cohort Members Table (Phase 4)
-- ============================================================================
CREATE TABLE `cohort_members` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `cohort_id` INT NOT NULL,
    `ase_id` INT NOT NULL UNIQUE,
    `added_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_cm_cohort` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cm_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_cm_cohort` (`cohort_id`),
    INDEX `idx_cm_ase` (`ase_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 9. Assessment Assignments (Phase 2, updated Phase 4 with cohort_id & is_demo)
-- ============================================================================
CREATE TABLE `assessment_assignments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `assessment_id` INT NOT NULL,
    `ase_id` INT NOT NULL,
    `cohort_id` INT NULL,
    `assigned_by` INT NULL,
    `start_date` DATETIME NOT NULL,
    `end_date` DATETIME NOT NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_aa_assessment` FOREIGN KEY (`assessment_id`) REFERENCES `assessments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_aa_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_aa_cohort` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_aa_assigned_by` FOREIGN KEY (`assigned_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `uk_assessment_ase` UNIQUE (`assessment_id`, `ase_id`),
    INDEX `idx_aa_assessment` (`assessment_id`),
    INDEX `idx_aa_ase` (`ase_id`),
    INDEX `idx_aa_cohort` (`cohort_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 10. Assessment Attempts (Phases 2-4)
-- ============================================================================
CREATE TABLE `assessment_attempts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `assessment_assignment_id` INT NOT NULL UNIQUE,
    `ase_id` INT NOT NULL,
    `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `submitted_at` DATETIME NULL,
    `status` ENUM('IN_PROGRESS', 'SUBMITTED', 'AUTO_SUBMITTED', 'AUTO_SUBMITTED_VIOLATION') NOT NULL DEFAULT 'IN_PROGRESS',
    `total_score` FLOAT NOT NULL DEFAULT 0,
    `max_score` FLOAT NOT NULL DEFAULT 0,
    `percentage` FLOAT NOT NULL DEFAULT 0,
    `passed` BOOLEAN NOT NULL DEFAULT FALSE,
    `violation_count` INT NOT NULL DEFAULT 0,
    `auto_submit_reason` VARCHAR(255) NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `camera_override_active` BOOLEAN NOT NULL DEFAULT FALSE,
    `camera_exempt` BOOLEAN NOT NULL DEFAULT FALSE,
    `accommodation_applied` BOOLEAN NOT NULL DEFAULT FALSE,
    `extended_total_duration_minutes` INT NULL,
    `last_camera_heartbeat_at` DATETIME(6) NULL,
    `camera_status` VARCHAR(30) NOT NULL DEFAULT 'INITIALIZING',
    `section_scores` JSON NULL,
    `skill_percentages` JSON NULL,
    `strong_areas` JSON NULL,
    `weak_areas` JSON NULL,
    CONSTRAINT `fk_attempt_assignment` FOREIGN KEY (`assessment_assignment_id`) REFERENCES `assessment_assignments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_attempt_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_attempt_status` (`status`),
    INDEX `idx_attempt_ase` (`ase_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 11. Exam Violations Table (Phase 3 Proctoring)
-- ============================================================================
CREATE TABLE `exam_violations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `attempt_id` INT NOT NULL,
    `type` VARCHAR(50) NOT NULL,
    `occurred_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `details` JSON NULL,
    CONSTRAINT `fk_violation_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `assessment_attempts` (`id`) ON DELETE CASCADE,
    INDEX `idx_violation_attempt` (`attempt_id`),
    INDEX `idx_violation_time` (`occurred_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 12. Assessment Responses (Phase 2)
-- ============================================================================
CREATE TABLE `assessment_responses` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `attempt_id` INT NOT NULL,
    `question_id` INT NOT NULL,
    `selected_options` JSON NOT NULL,
    `is_correct` BOOLEAN NOT NULL DEFAULT FALSE,
    `marks_obtained` FLOAT NOT NULL DEFAULT 0,
    `time_spent_seconds` FLOAT NOT NULL DEFAULT 0.0,
    `question_version` INT NOT NULL DEFAULT 1,
    CONSTRAINT `fk_response_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `assessment_attempts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_response_question` FOREIGN KEY (`question_id`) REFERENCES `question_bank` (`id`) ON DELETE CASCADE,
    INDEX `idx_response_attempt` (`attempt_id`),
    INDEX `idx_response_question` (`question_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 13. Trainings Table (Phase 5)
-- ============================================================================
CREATE TABLE `trainings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(200) NOT NULL,
    `description` TEXT NULL,
    `skill_category` VARCHAR(100) NOT NULL,
    `type` VARCHAR(50) NOT NULL DEFAULT 'Self-paced',
    `resources` JSON NOT NULL,
    `duration_hours` FLOAT NOT NULL DEFAULT 1.0,
    `created_by` INT NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_training_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_training_skill` (`skill_category`),
    INDEX `idx_training_type` (`type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 14. Training Assignments (Phase 5)
-- ============================================================================
CREATE TABLE `training_assignments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `training_id` INT NOT NULL,
    `ase_id` INT NOT NULL,
    `cohort_id` INT NULL,
    `assigned_by` INT NULL,
    `due_date` DATETIME NOT NULL,
    `status` ENUM('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED') NOT NULL DEFAULT 'NOT_STARTED',
    `progress_percent` FLOAT NOT NULL DEFAULT 0.0,
    `completed_at` DATETIME NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_ta_training` FOREIGN KEY (`training_id`) REFERENCES `trainings` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ta_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ta_cohort` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_ta_assigned_by` FOREIGN KEY (`assigned_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `uk_training_ase` UNIQUE (`training_id`, `ase_id`),
    INDEX `idx_ta_training` (`training_id`),
    INDEX `idx_ta_ase` (`ase_id`),
    INDEX `idx_ta_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 15. Live Classes Table (Phase 5)
-- ============================================================================
CREATE TABLE `live_classes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(200) NOT NULL,
    `description` TEXT NULL,
    `start_time` DATETIME NOT NULL,
    `duration_minutes` INT NOT NULL DEFAULT 60,
    `audience_type` VARCHAR(50) NOT NULL DEFAULT 'COHORT',
    `cohort_id` INT NULL,
    `meeting_link` VARCHAR(500) NOT NULL,
    `provider` VARCHAR(50) NOT NULL DEFAULT 'MANUAL',
    `created_by` INT NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_lc_cohort` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_lc_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_lc_start_time` (`start_time`),
    INDEX `idx_lc_cohort` (`cohort_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 16. Live Class Attendees Table (Phase 5)
-- ============================================================================
CREATE TABLE `live_class_attendees` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `live_class_id` INT NOT NULL,
    `ase_id` INT NOT NULL,
    `status` ENUM('INVITED', 'ATTENDED', 'ABSENT') NOT NULL DEFAULT 'INVITED',
    `marked_at` DATETIME NULL,
    `marked_by` INT NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_lca_class` FOREIGN KEY (`live_class_id`) REFERENCES `live_classes` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_lca_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_lca_marker` FOREIGN KEY (`marked_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `uk_class_ase` UNIQUE (`live_class_id`, `ase_id`),
    INDEX `idx_lca_class` (`live_class_id`),
    INDEX `idx_lca_ase` (`ase_id`),
    INDEX `idx_lca_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 17. Notifications Table (Phase 5)
-- ============================================================================
CREATE TABLE `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `message` TEXT NOT NULL,
    `type` VARCHAR(50) NOT NULL DEFAULT 'GENERAL',
    `link` VARCHAR(500) NULL,
    `is_read` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_notif_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_notif_user` (`user_id`),
    INDEX `idx_notif_read` (`is_read`),
    INDEX `idx_notif_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 18. Reminders Sent (Phase 5 - Idempotent Tracking)
-- ============================================================================
CREATE TABLE `reminders_sent` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `entity_type` VARCHAR(50) NOT NULL,
    `entity_id` INT NOT NULL,
    `reminder_type` VARCHAR(50) NOT NULL DEFAULT '24H_BEFORE',
    `sent_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_rs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `uk_reminder_idempotent` UNIQUE (`user_id`, `entity_type`, `entity_id`, `reminder_type`),
    INDEX `idx_rs_user` (`user_id`),
    INDEX `idx_rs_entity` (`entity_type`, `entity_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 19. Chat Sessions Table (Phase 6)
-- ============================================================================
CREATE TABLE `chat_sessions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL DEFAULT 'New Conversation',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_cs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_cs_user` (`user_id`),
    INDEX `idx_cs_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 20. Chat Messages Table (Phase 6)
-- ============================================================================
CREATE TABLE `chat_messages` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `session_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `sender_role` VARCHAR(20) NOT NULL,
    `content` TEXT NOT NULL,
    `feedback` VARCHAR(10) NULL,
    `feedback_comment` VARCHAR(255) NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_cm_session` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cm_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_cm_session` (`session_id`),
    INDEX `idx_cm_user` (`user_id`),
    INDEX `idx_cm_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 21. LLM Usage Logs Table (Phase 6)
-- ============================================================================
CREATE TABLE `llm_usage_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `role` VARCHAR(20) NOT NULL,
    `provider` VARCHAR(50) NOT NULL,
    `model` VARCHAR(50) NOT NULL,
    `prompt_tokens` INT NOT NULL DEFAULT 0,
    `completion_tokens` INT NOT NULL DEFAULT 0,
    `total_tokens` INT NOT NULL DEFAULT 0,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_lul_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_lul_user` (`user_id`),
    INDEX `idx_lul_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 22. AI Insights Cache Table (Phase 6)
-- ============================================================================
CREATE TABLE `ai_insights_cache` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ase_id` INT NOT NULL UNIQUE,
    `latest_attempt_id` INT NULL,
    `insights_json` TEXT NOT NULL,
    `provider` VARCHAR(50) NOT NULL DEFAULT 'mock',
    `is_stale` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_aic_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_aic_attempt` FOREIGN KEY (`latest_attempt_id`) REFERENCES `assessment_attempts` (`id`) ON DELETE SET NULL,
    INDEX `idx_aic_ase` (`ase_id`),
    INDEX `idx_aic_stale` (`is_stale`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- 23. Motivational Quotes Table (Phase 7)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `motivational_quotes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `role` VARCHAR(20) NOT NULL,
    `text` TEXT NOT NULL,
    `author` VARCHAR(100) NOT NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_mq_role` (`role`),
    INDEX `idx_mq_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 24. Coding Submissions Table (Phase 7)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `coding_submissions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `attempt_id` INT NOT NULL,
    `question_id` INT NOT NULL,
    `ase_id` INT NOT NULL,
    `language` VARCHAR(30) NOT NULL,
    `source_code` TEXT NOT NULL,
    `passed_sample_cases` INT NOT NULL DEFAULT 0,
    `total_sample_cases` INT NOT NULL DEFAULT 0,
    `passed_hidden_cases` INT NOT NULL DEFAULT 0,
    `total_hidden_cases` INT NOT NULL DEFAULT 0,
    `total_passed` INT NOT NULL DEFAULT 0,
    `total_cases` INT NOT NULL DEFAULT 0,
    `execution_time_ms` FLOAT NOT NULL DEFAULT 0.0,
    `memory_used_kb` FLOAT NOT NULL DEFAULT 0.0,
    `score` FLOAT NOT NULL DEFAULT 0.0,
    `status` VARCHAR(40) NOT NULL DEFAULT 'ACCEPTED',
    `ai_review` TEXT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_cs_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `assessment_attempts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cs_question` FOREIGN KEY (`question_id`) REFERENCES `question_bank` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cs_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_cs_attempt` (`attempt_id`),
    INDEX `idx_cs_question` (`question_id`),
    INDEX `idx_cs_ase` (`ase_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 25. Coding Run Logs Table (Phase 7 - DB Rate Limiting)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `coding_run_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `attempt_id` INT NOT NULL,
    `question_id` INT NOT NULL,
    `ase_id` INT NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_crl_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `assessment_attempts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_crl_question` FOREIGN KEY (`question_id`) REFERENCES `question_bank` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_crl_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_crl_attempt_ase` (`attempt_id`, `ase_id`),
    INDEX `idx_crl_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 26. Coding Plagiarism Flags Table (Phase 7)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `coding_plagiarism_flags` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `question_id` INT NOT NULL,
    `ase1_id` INT NOT NULL,
    `ase2_id` INT NOT NULL,
    `attempt1_id` INT NOT NULL,
    `attempt2_id` INT NOT NULL,
    `similarity_score` FLOAT NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'FLAGGED_FOR_REVIEW',
    `flagged_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_cpf_question` FOREIGN KEY (`question_id`) REFERENCES `question_bank` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cpf_ase1` FOREIGN KEY (`ase1_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cpf_ase2` FOREIGN KEY (`ase2_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_cpf_question` (`question_id`),
    INDEX `idx_cpf_ases` (`ase1_id`, `ase2_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 27. Class Transcripts Table (Phase 8 - AI Class Summary)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `class_transcripts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `live_class_id` INT NULL,
    `training_id` INT NULL,
    `uploaded_by` INT NULL,
    `raw_text` LONGTEXT NULL,
    `topics_covered` TEXT NULL,
    `file_name` VARCHAR(255) NULL,
    `file_type` VARCHAR(50) NULL,
    `privacy_consent_acknowledged` BOOLEAN NOT NULL DEFAULT FALSE,
    `token_count` INT NOT NULL DEFAULT 0,
    `used_token_count` INT NOT NULL DEFAULT 0,
    `truncated_ratio` FLOAT NOT NULL DEFAULT 1.0,
    `expires_at` DATETIME NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_ct_class` FOREIGN KEY (`live_class_id`) REFERENCES `live_classes` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ct_training` FOREIGN KEY (`training_id`) REFERENCES `trainings` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ct_user` FOREIGN KEY (`uploaded_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_ct_class` (`live_class_id`),
    INDEX `idx_ct_training` (`training_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 28. Class Summaries Table (Phase 8)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `class_summaries` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `transcript_id` INT NULL,
    `live_class_id` INT NULL,
    `training_id` INT NULL,
    `created_by` INT NULL,
    `key_topics` JSON NOT NULL,
    `key_concepts` JSON NOT NULL,
    `practical_examples` JSON NOT NULL,
    `ase_recap` TEXT NOT NULL,
    `suggested_homework` JSON NOT NULL,
    `is_published` BOOLEAN NOT NULL DEFAULT FALSE,
    `published_at` DATETIME NULL,
    `version` INT NOT NULL DEFAULT 1,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_csum_transcript` FOREIGN KEY (`transcript_id`) REFERENCES `class_transcripts` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_csum_class` FOREIGN KEY (`live_class_id`) REFERENCES `live_classes` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_csum_training` FOREIGN KEY (`training_id`) REFERENCES `trainings` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_csum_user` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_csum_class` (`live_class_id`),
    INDEX `idx_csum_training` (`training_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 29. AI Generated Assessments Table (Phase 8)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `ai_generated_assessments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `live_class_id` INT NULL,
    `training_id` INT NULL,
    `created_by` INT NULL,
    `title` VARCHAR(255) NOT NULL,
    `generation_mode` VARCHAR(50) NOT NULL DEFAULT 'AUTO',
    `status` VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
    `recommended_total_questions` INT NOT NULL DEFAULT 20,
    `difficulty_split` JSON NOT NULL,
    `topic_split` JSON NOT NULL,
    `is_immutable` BOOLEAN NOT NULL DEFAULT FALSE,
    `version` INT NOT NULL DEFAULT 1,
    `parent_id` INT NULL,
    `assessment_id` INT NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_aga_class` FOREIGN KEY (`live_class_id`) REFERENCES `live_classes` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_aga_training` FOREIGN KEY (`training_id`) REFERENCES `trainings` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_aga_user` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_aga_assessment` FOREIGN KEY (`assessment_id`) REFERENCES `assessments` (`id`) ON DELETE SET NULL,
    INDEX `idx_aga_class` (`live_class_id`),
    INDEX `idx_aga_training` (`training_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 30. AI Generated Questions Table (Phase 8)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `ai_generated_questions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ai_assessment_id` INT NOT NULL,
    `question_bank_id` INT NULL,
    `question_type` VARCHAR(50) NOT NULL DEFAULT 'SINGLE_CHOICE',
    `skill_category` VARCHAR(100) NOT NULL DEFAULT 'General',
    `difficulty` VARCHAR(50) NOT NULL DEFAULT 'MEDIUM',
    `question_text` TEXT NOT NULL,
    `options` JSON NOT NULL,
    `correct_answers` JSON NOT NULL,
    `explanation` TEXT NOT NULL,
    `source` VARCHAR(50) NOT NULL DEFAULT 'AI generated',
    `review_status` VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    `mentor_verify_required` BOOLEAN NOT NULL DEFAULT FALSE,
    `quality_flags` JSON NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_agq_assessment` FOREIGN KEY (`ai_assessment_id`) REFERENCES `ai_generated_assessments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_agq_bank` FOREIGN KEY (`question_bank_id`) REFERENCES `question_bank` (`id`) ON DELETE SET NULL,
    INDEX `idx_agq_assessment` (`ai_assessment_id`),
    INDEX `idx_agq_status` (`review_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 31. Class Effectiveness Reports Table (Phase 8)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `class_effectiveness_reports` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `live_class_id` INT NULL,
    `assessment_id` INT NULL,
    `generated_by` INT NULL,
    `total_attempts` INT NOT NULL DEFAULT 0,
    `topic_scores` JSON NOT NULL,
    `missed_concepts` JSON NOT NULL,
    `suggested_revision_topics` JSON NOT NULL,
    `follow_up_proposal` JSON NOT NULL,
    `has_enough_data` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_cer_class` FOREIGN KEY (`live_class_id`) REFERENCES `live_classes` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cer_assessment` FOREIGN KEY (`assessment_id`) REFERENCES `assessments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cer_user` FOREIGN KEY (`generated_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_cer_class` (`live_class_id`),
    INDEX `idx_cer_assessment` (`assessment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 32. AI Generate Rate Logs Table (Phase 8)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `ai_generate_rate_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `action_type` VARCHAR(50) NOT NULL,
    `question_count` INT NOT NULL DEFAULT 0,
    `tokens_used` INT NOT NULL DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_agrl_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_agrl_user_created` (`user_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 33. Readiness Configs Table (Phase 9 - WOW Pack)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `readiness_configs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `assessment_weight` FLOAT NOT NULL DEFAULT 0.30,
    `coding_weight` FLOAT NOT NULL DEFAULT 0.25,
    `training_weight` FLOAT NOT NULL DEFAULT 0.20,
    `attendance_weight` FLOAT NOT NULL DEFAULT 0.15,
    `consistency_weight` FLOAT NOT NULL DEFAULT 0.10,
    `updated_by` INT NULL,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_rc_user` FOREIGN KEY (`updated_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 34. Readiness Audit Logs Table (Phase 9)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `readiness_audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `changed_by` INT NULL,
    `old_weights` JSON NOT NULL,
    `new_weights` JSON NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_ral_user` FOREIGN KEY (`changed_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 35. ASE Readiness History Table (Phase 9)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `ase_readiness_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ase_id` INT NOT NULL,
    `overall_score` FLOAT NOT NULL DEFAULT 0.0,
    `breakdown_json` JSON NOT NULL,
    `skill_dna_json` JSON NOT NULL,
    `formula_snapshot` VARCHAR(255) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_arh_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_arh_ase` (`ase_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 36. ASE Gamification Table (Phase 9)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `ase_gamification` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ase_id` INT NOT NULL UNIQUE,
    `xp` INT NOT NULL DEFAULT 0,
    `level` INT NOT NULL DEFAULT 1,
    `streak_days` INT NOT NULL DEFAULT 0,
    `last_active_date` VARCHAR(20) NULL,
    `badges_json` JSON NOT NULL,
    `leaderboard_opt_in` BOOLEAN NOT NULL DEFAULT FALSE,
    `show_full_name_publicly` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_ag_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_ag_ase` (`ase_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 37. Onboarding Milestones Table (Phase 9)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `onboarding_milestones` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ase_id` INT NOT NULL,
    `day_phase` INT NOT NULL,
    `milestone_type` VARCHAR(50) NOT NULL,
    `entity_id` INT NULL,
    `title` VARCHAR(200) NOT NULL,
    `is_completed` BOOLEAN NOT NULL DEFAULT FALSE,
    `completed_at` DATETIME NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_om_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_om_ase` (`ase_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 38. AI Learning Roadmaps Table (Phase 9)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `ai_learning_roadmaps` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ase_id` INT NOT NULL,
    `week_number` INT NOT NULL DEFAULT 1,
    `generated_from_weak_skills` JSON NOT NULL,
    `roadmap_items_json` JSON NOT NULL,
    `version` INT NOT NULL DEFAULT 1,
    `is_stale` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_alr_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_alr_ase` (`ase_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 39. ASE Risk Signals Table (Phase 9 - Early Warning)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `ase_risk_signals` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ase_id` INT NOT NULL UNIQUE,
    `mentor_id` INT NULL,
    `risk_score` FLOAT NOT NULL DEFAULT 0.0,
    `risk_level` VARCHAR(20) NOT NULL DEFAULT 'LOW',
    `factors_json` JSON NOT NULL,
    `ai_explanation` TEXT NOT NULL,
    `last_nudged_at` DATETIME NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_ars_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ars_mentor` FOREIGN KEY (`mentor_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_ars_ase` (`ase_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 40. Mentor Nudge Logs Table (Phase 9)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `mentor_nudge_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `mentor_id` INT NOT NULL,
    `ase_id` INT NOT NULL,
    `message` TEXT NOT NULL,
    `sent_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_mnl_mentor` FOREIGN KEY (`mentor_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_mnl_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_mnl_pair` (`mentor_id`, `ase_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 41. Reassessment Schedules Table (Phase 9)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `reassessment_schedules` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `cohort_id` INT NULL,
    `ase_id` INT NULL,
    `phase_label` VARCHAR(50) NOT NULL,
    `original_assessment_id` INT NOT NULL,
    `reassessment_id` INT NOT NULL,
    `scheduled_date` DATETIME NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'SCHEDULED',
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_rs_cohort` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_rs_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_rs_orig` FOREIGN KEY (`original_assessment_id`) REFERENCES `assessments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_rs_reass` FOREIGN KEY (`reassessment_id`) REFERENCES `assessments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 42. Issued Certificates Table (Phase 9)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `issued_certificates` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `cert_uuid` VARCHAR(64) NOT NULL UNIQUE,
    `ase_id` INT NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `entity_type` VARCHAR(50) NOT NULL,
    `entity_id` INT NOT NULL,
    `issue_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `pdf_file_path` VARCHAR(255) NOT NULL,
    `is_revoked` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_ic_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_ic_uuid` (`cert_uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 43. Mock Interview Sessions Table (Phase 9)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `mock_interview_sessions` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ase_id` INT NOT NULL,
    `target_role` VARCHAR(100) NOT NULL,
    `skill_focus` VARCHAR(100) NOT NULL,
    `question_history_json` JSON NOT NULL,
    `feedback_json` JSON NOT NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_mis_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_mis_ase` (`ase_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 44. Mock Interview Rate Logs Table (Phase 9)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `mock_interview_rate_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ase_id` INT NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_mirl_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_mirl_ase_created` (`ase_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 45. Public Verify Rate Logs Table (Phase 9)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `public_verify_rate_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ip_address` VARCHAR(64) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_pvrl_ip_created` (`ip_address`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 46. Webcam Consents Table (Phase 10)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `webcam_consents` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `assignment_id` INT NOT NULL,
    `ase_id` INT NOT NULL,
    `consented` BOOLEAN NOT NULL DEFAULT FALSE,
    `consented_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `ip_address` VARCHAR(64) NULL,
    `user_agent` VARCHAR(255) NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_wc_assignment` FOREIGN KEY (`assignment_id`) REFERENCES `assessment_assignments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_wc_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_wc_assignment_ase` (`assignment_id`, `ase_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 47. Camera Handshakes Table (Phase 10)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `camera_handshakes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `handshake_token` VARCHAR(64) NOT NULL UNIQUE,
    `assignment_id` INT NOT NULL,
    `ase_id` INT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `expires_at` DATETIME(6) NOT NULL,
    `is_used` BOOLEAN NOT NULL DEFAULT FALSE,
    `used_at` DATETIME(6) NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_ch_assignment` FOREIGN KEY (`assignment_id`) REFERENCES `assessment_assignments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ch_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_ch_token` (`handshake_token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 48. Camera Heartbeats Table (Phase 10)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `camera_heartbeats` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `attempt_id` INT NOT NULL,
    `ase_id` INT NOT NULL,
    `status` VARCHAR(30) NOT NULL,
    `details` VARCHAR(255) NULL,
    `timestamp` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_chb_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `assessment_attempts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_chb_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_chb_attempt_ts` (`attempt_id`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 49. Camera Override Logs Table (Phase 10)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `camera_override_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `attempt_id` INT NULL,
    `assignment_id` INT NOT NULL,
    `ase_id` INT NOT NULL,
    `granted_by` INT NOT NULL,
    `reason` TEXT NOT NULL,
    `granted_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_col_assignment` FOREIGN KEY (`assignment_id`) REFERENCES `assessment_assignments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_col_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_col_grantor` FOREIGN KEY (`granted_by`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 50. Webcam Proctoring Snapshots Table (Phase 10)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `webcam_proctoring_snapshots` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `attempt_id` INT NOT NULL,
    `event_type` VARCHAR(50) NOT NULL,
    `snapshot_path` VARCHAR(255) NOT NULL,
    `is_encrypted` BOOLEAN NOT NULL DEFAULT TRUE,
    `captured_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `auto_purge_at` DATETIME(6) NOT NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_wps_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `assessment_attempts` (`id`) ON DELETE CASCADE,
    INDEX `idx_wps_purge` (`auto_purge_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 51. Webcam Audit Logs Table (Phase 10)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `webcam_audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `viewer_id` INT NOT NULL,
    `attempt_id` INT NOT NULL,
    `action` VARCHAR(50) NOT NULL,
    `viewed_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_wal_viewer` FOREIGN KEY (`viewer_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_wal_attempt` FOREIGN KEY (`attempt_id`) REFERENCES `assessment_attempts` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 52. Accommodation Requests Table (Phase 10)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `accommodation_requests` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `ase_id` INT NOT NULL,
    `requested_by` INT NOT NULL,
    `accommodation_type` VARCHAR(50) NOT NULL,
    `extra_time_percent` FLOAT NOT NULL DEFAULT 0.0,
    `reason_category` VARCHAR(50) NOT NULL,
    `medical_notes` TEXT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    `admin_notes` TEXT NULL,
    `reviewed_by` INT NULL,
    `reviewed_at` DATETIME NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_ar_ase` FOREIGN KEY (`ase_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ar_requester` FOREIGN KEY (`requested_by`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ar_reviewer` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_ar_ase_status` (`ase_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 53. Accommodation Audit Logs Table (Phase 10)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `accommodation_audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `request_id` INT NOT NULL,
    `action` VARCHAR(50) NOT NULL,
    `actor_id` INT NOT NULL,
    `note` TEXT NULL,
    `timestamp` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_aal_req` FOREIGN KEY (`request_id`) REFERENCES `accommodation_requests` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_aal_actor` FOREIGN KEY (`actor_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 54. Question Item Analytics Table (Phase 11)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `question_item_analytics` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `question_id` INT NOT NULL,
    `question_version` INT NOT NULL DEFAULT 1,
    `attempts_count` INT NOT NULL DEFAULT 0,
    `correct_count` INT NOT NULL DEFAULT 0,
    `difficulty_index` FLOAT NOT NULL DEFAULT 0.0,
    `discrimination_index` FLOAT NOT NULL DEFAULT 0.0,
    `is_indicative_discrimination` BOOLEAN NOT NULL DEFAULT FALSE,
    `most_chosen_wrong_option` VARCHAR(100) NULL,
    `avg_time_seconds` FLOAT NOT NULL DEFAULT 0.0,
    `is_too_easy` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_too_hard` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_poor_discrimination` BOOLEAN NOT NULL DEFAULT FALSE,
    `needs_review` BOOLEAN NOT NULL DEFAULT FALSE,
    `review_reason` VARCHAR(255) NULL,
    `option_distribution` JSON NULL,
    `formula_metadata` JSON NULL,
    `calculated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT `fk_qia_question` FOREIGN KEY (`question_id`) REFERENCES `question_bank` (`id`) ON DELETE CASCADE,
    INDEX `idx_qia_q_ver` (`question_id`, `question_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 55. 1-on-1 Meetings Table (Phase 11 - Field-Level Encrypted Private Notes)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `one_on_one_meetings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `mentor_id` INT NOT NULL,
    `mentee_id` INT NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `meeting_date` DATETIME NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'SCHEDULED',
    `shared_notes` TEXT NULL,
    `encrypted_private_notes` TEXT NULL,
    `ai_summary_shared` TEXT NULL,
    `ai_summary_private` TEXT NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_1on1_mentor` FOREIGN KEY (`mentor_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_1on1_mentee` FOREIGN KEY (`mentee_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_1on1_mentor_mentee` (`mentor_id`, `mentee_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 56. 1-on-1 Goals Table (Phase 11)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `one_on_one_goals` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `meeting_id` INT NULL,
    `mentor_id` INT NOT NULL,
    `mentee_id` INT NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `description` TEXT NULL,
    `target_date` DATETIME NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'NOT_STARTED',
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_goal_meeting` FOREIGN KEY (`meeting_id`) REFERENCES `one_on_one_meetings` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_goal_mentor` FOREIGN KEY (`mentor_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_goal_mentee` FOREIGN KEY (`mentee_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_goal_mentee` (`mentee_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 57. 1-on-1 Action Items Table (Phase 11)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `one_on_one_action_items` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `meeting_id` INT NULL,
    `goal_id` INT NULL,
    `mentor_id` INT NOT NULL,
    `mentee_id` INT NOT NULL,
    `task` TEXT NOT NULL,
    `assigned_to` VARCHAR(30) NOT NULL DEFAULT 'ASE',
    `is_completed` BOOLEAN NOT NULL DEFAULT FALSE,
    `completed_at` DATETIME NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_act_meeting` FOREIGN KEY (`meeting_id`) REFERENCES `one_on_one_meetings` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_act_goal` FOREIGN KEY (`goal_id`) REFERENCES `one_on_one_goals` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_act_mentor` FOREIGN KEY (`mentor_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_act_mentee` FOREIGN KEY (`mentee_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_act_mentee` (`mentee_id`, `is_completed`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 58. 1-on-1 Comments Table (Phase 11)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `one_on_one_comments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `meeting_id` INT NULL,
    `goal_id` INT NULL,
    `action_item_id` INT NULL,
    `user_id` INT NOT NULL,
    `comment_text` TEXT NOT NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_comm_meeting` FOREIGN KEY (`meeting_id`) REFERENCES `one_on_one_meetings` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comm_goal` FOREIGN KEY (`goal_id`) REFERENCES `one_on_one_goals` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comm_action` FOREIGN KEY (`action_item_id`) REFERENCES `one_on_one_action_items` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comm_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 59. Reporting API Tokens Table (Phase 11 - Power BI Read-Only Integration)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `reporting_api_tokens` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL,
    `token_hash` VARCHAR(64) NOT NULL UNIQUE,
    `created_by_admin_id` INT NOT NULL,
    `scopes` JSON NOT NULL,
    `include_pii` BOOLEAN NOT NULL DEFAULT FALSE,
    `allowed_ips` JSON NULL,
    `expires_at` DATETIME NOT NULL,
    `is_revoked` BOOLEAN NOT NULL DEFAULT FALSE,
    `last_used_at` DATETIME NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_rat_admin` FOREIGN KEY (`created_by_admin_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_rat_hash` (`token_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 60. Reporting Token Audit Logs Table (Phase 11)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `reporting_token_audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `token_id` INT NOT NULL,
    `ip_address` VARCHAR(100) NULL,
    `endpoint` VARCHAR(255) NOT NULL,
    `accessed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_rtal_token` FOREIGN KEY (`token_id`) REFERENCES `reporting_api_tokens` (`id`) ON DELETE CASCADE,
    INDEX `idx_rtal_token_time` (`token_id`, `accessed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 61. Staffing Projects Table (Phase 11)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `staffing_projects` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(200) NOT NULL,
    `description` TEXT NULL,
    `headcount` INT NOT NULL DEFAULT 1,
    `start_date` DATETIME NOT NULL,
    `ready_now_threshold_pct` FLOAT NOT NULL DEFAULT 90.0,
    `status` VARCHAR(30) NOT NULL DEFAULT 'PLANNING',
    `created_by_user_id` INT NOT NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_sp_creator` FOREIGN KEY (`created_by_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 62. Staffing Project Skills Table (Phase 11)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `staffing_project_skills` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `project_id` INT NOT NULL,
    `skill_name` VARCHAR(100) NOT NULL,
    `min_level_pct` FLOAT NOT NULL DEFAULT 70.0,
    `weight` FLOAT NOT NULL DEFAULT 1.0,
    CONSTRAINT `fk_sps_project` FOREIGN KEY (`project_id`) REFERENCES `staffing_projects` (`id`) ON DELETE CASCADE,
    INDEX `idx_sps_proj_skill` (`project_id`, `skill_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 63. Buddy Pairings Table (Phase 12)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `buddy_pairings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `buddy_id` INT NOT NULL,
    `buddee_id` INT NOT NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    `paired_by` INT NULL,
    `paired_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `change_reason` VARCHAR(500) NULL,
    `change_requested_by` INT NULL,
    `change_requested_at` DATETIME NULL,
    `completed_at` DATETIME NULL,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `chk_buddy_no_self_pair` CHECK (`buddy_id` != `buddee_id`),
    CONSTRAINT `fk_bp_buddy` FOREIGN KEY (`buddy_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_bp_buddee` FOREIGN KEY (`buddee_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_bp_paired_by` FOREIGN KEY (`paired_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_bp_change_req` FOREIGN KEY (`change_requested_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_bp_buddy_status` (`buddy_id`, `status`),
    INDEX `idx_bp_buddee_status` (`buddee_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 64. Buddy Ratings Table (Phase 12)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `buddy_ratings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `pairing_id` INT NOT NULL,
    `rated_by_id` INT NOT NULL,
    `rating` INT NOT NULL,
    `feedback` VARCHAR(1000) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_br_pairing` FOREIGN KEY (`pairing_id`) REFERENCES `buddy_pairings` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_br_rater` FOREIGN KEY (`rated_by_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_br_pairing` (`pairing_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 65. Buddy Milestones Table (Phase 12 - Weekly XP Cap Support)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `buddy_milestones` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `pairing_id` INT NOT NULL,
    `buddy_id` INT NOT NULL,
    `buddee_id` INT NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `description` VARCHAR(1000) NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    `xp_amount` INT NOT NULL DEFAULT 25,
    `xp_awarded` BOOLEAN NOT NULL DEFAULT FALSE,
    `confirmed_at` DATETIME NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_bm_pairing` FOREIGN KEY (`pairing_id`) REFERENCES `buddy_pairings` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_bm_buddy` FOREIGN KEY (`buddy_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_bm_buddee` FOREIGN KEY (`buddee_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_bm_buddy_status` (`buddy_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 66. Forum Posts Table (Phase 12 - Doubt Forum & Active Assessment Guard)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `forum_posts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `cohort_id` INT NOT NULL,
    `author_id` INT NOT NULL,
    `title` VARCHAR(250) NOT NULL,
    `body` TEXT NOT NULL,
    `tags` VARCHAR(255) NULL,
    `tagged_assessment_id` INT NULL,
    `is_anonymous` BOOLEAN NOT NULL DEFAULT FALSE,
    `status` VARCHAR(30) NOT NULL DEFAULT 'PUBLISHED',
    `held_reason` VARCHAR(500) NULL,
    `reviewed_by` INT NULL,
    `reviewed_at` DATETIME NULL,
    `review_notes` VARCHAR(500) NULL,
    `is_resolved` BOOLEAN NOT NULL DEFAULT FALSE,
    `accepted_answer_id` INT NULL,
    `view_count` INT NOT NULL DEFAULT 0,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_fp_cohort` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_fp_author` FOREIGN KEY (`author_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_fp_reviewer` FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_fp_assessment` FOREIGN KEY (`tagged_assessment_id`) REFERENCES `assessments` (`id`) ON DELETE SET NULL,
    INDEX `idx_fp_cohort_status` (`cohort_id`, `status`),
    INDEX `idx_fp_author` (`author_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 67. Forum Answers Table (Phase 12 - Answers & Mentor Verification)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `forum_answers` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `post_id` INT NOT NULL,
    `author_id` INT NOT NULL,
    `body` TEXT NOT NULL,
    `is_anonymous` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_accepted` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_mentor_verified` BOOLEAN NOT NULL DEFAULT FALSE,
    `verified_by` INT NULL,
    `verified_at` DATETIME NULL,
    `is_ai_generated` BOOLEAN NOT NULL DEFAULT FALSE,
    `ai_model` VARCHAR(50) NULL,
    `is_hidden` BOOLEAN NOT NULL DEFAULT FALSE,
    `hidden_reason` VARCHAR(500) NULL,
    `upvote_count` INT NOT NULL DEFAULT 0,
    `is_demo` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_fa_post` FOREIGN KEY (`post_id`) REFERENCES `forum_posts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_fa_author` FOREIGN KEY (`author_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_fa_verifier` FOREIGN KEY (`verified_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_fa_post_created` (`post_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 68. Forum Votes Table (Phase 12 - Answer Upvoting)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `forum_votes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `answer_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `vote_type` INT NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `uk_fv_answer_user` UNIQUE (`answer_id`, `user_id`),
    CONSTRAINT `fk_fv_answer` FOREIGN KEY (`answer_id`) REFERENCES `forum_answers` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_fv_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 69. Forum Reports Table (Phase 12 - Abuse & Report Abuse Tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `forum_reports` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `reporter_id` INT NOT NULL,
    `post_id` INT NULL,
    `answer_id` INT NULL,
    `reason` VARCHAR(50) NOT NULL,
    `notes` VARCHAR(500) NULL,
    `status` VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    `action_taken` VARCHAR(200) NULL,
    `resolved_by` INT NULL,
    `resolved_at` DATETIME NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_fr_reporter` FOREIGN KEY (`reporter_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_fr_post` FOREIGN KEY (`post_id`) REFERENCES `forum_posts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_fr_answer` FOREIGN KEY (`answer_id`) REFERENCES `forum_answers` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_fr_resolver` FOREIGN KEY (`resolved_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_fr_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 70. Forum Identity Audit Logs Table (Phase 12 - Anonymity Access Audit Trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `forum_identity_audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `viewer_id` INT NOT NULL,
    `viewer_role` VARCHAR(50) NOT NULL,
    `target_type` VARCHAR(20) NOT NULL,
    `target_id` INT NOT NULL,
    `revealed_author_id` INT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT `fk_fial_viewer` FOREIGN KEY (`viewer_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_fial_author` FOREIGN KEY (`revealed_author_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_fial_target` (`target_type`, `target_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 71. Forum Filter Audit Logs Table (Phase 12 - PII/Profanity Hit Logging)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `forum_filter_audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `target_type` VARCHAR(20) NOT NULL,
    `detected_category` VARCHAR(50) NOT NULL,
    `action` VARCHAR(50) NOT NULL DEFAULT 'BLOCKED_PRE_SUBMISSION',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT `fk_ffal_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_ffal_user` (`user_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 72. Forum Rate Limits Table (Phase 12 - DB-Level Rate Limiter)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `forum_rate_limits` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `action_type` VARCHAR(30) NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT `fk_frl_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_frl_user_action_time` (`user_id`, `action_type`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 73. User SSO Accounts Table (Phase 13 - Microsoft Entra ID Identity Mapping)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `user_sso_accounts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `tid` VARCHAR(100) NOT NULL,
    `oid` VARCHAR(100) NOT NULL,
    `upn` VARCHAR(150) NOT NULL,
    `encrypted_refresh_token` TEXT NULL,
    `token_expires_at` DATETIME(6) NULL,
    `last_login_at` DATETIME(6) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_usa_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    UNIQUE KEY `uk_sso_tid_oid` (`tid`, `oid`),
    INDEX `idx_usa_upn` (`upn`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 74. SSO Audit Logs Table (Phase 13 - SSO Authentication Trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `sso_audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NULL,
    `event_type` VARCHAR(50) NOT NULL,
    `upn` VARCHAR(150) NULL,
    `tid` VARCHAR(100) NULL,
    `oid` VARCHAR(100) NULL,
    `ip_address` VARCHAR(50) NULL,
    `user_agent` VARCHAR(300) NULL,
    `failure_reason` VARCHAR(255) NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT `fk_sal_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_sal_event` (`event_type`),
    INDEX `idx_sal_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 75. SSO Configurations Table (Phase 13 - System SSO Toggles & Guard)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `sso_configurations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `allow_local_login` BOOLEAN NOT NULL DEFAULT TRUE,
    `auto_provision_ase` BOOLEAN NOT NULL DEFAULT FALSE,
    `updated_by` INT NULL,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_sc_admin` FOREIGN KEY (`updated_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 76. SSO OAuth States Table (Phase 13 - PKCE, Nonce & State Ephemeral Storage)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `sso_oauth_states` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `state` VARCHAR(128) NOT NULL UNIQUE,
    `nonce` VARCHAR(128) NOT NULL,
    `code_verifier` VARCHAR(128) NOT NULL,
    `redirect_uri` VARCHAR(500) NOT NULL,
    `is_used` BOOLEAN NOT NULL DEFAULT FALSE,
    `expires_at` DATETIME NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_sos_state_used` (`state`, `is_used`, `expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 77. User Notification Preferences Table (Phase 13 - Multi-Channel & Quiet Hours)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `user_notification_preferences` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `preferred_channels` VARCHAR(100) NOT NULL DEFAULT 'IN_APP,EMAIL',
    `quiet_hours_enabled` BOOLEAN NOT NULL DEFAULT FALSE,
    `quiet_hours_start` VARCHAR(10) NOT NULL DEFAULT '22:00',
    `quiet_hours_end` VARCHAR(10) NOT NULL DEFAULT '07:00',
    `timezone` VARCHAR(50) NOT NULL DEFAULT 'UTC',
    `teams_recipient_id` VARCHAR(150) NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_unp_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 78. Class Attendance Imports Table (Phase 13 - Teams Attendance Staging & TTL)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `class_attendance_imports` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `live_class_id` INT NOT NULL,
    `imported_by` INT NULL,
    `raw_report_json` TEXT NULL,
    `staged_records_json` TEXT NOT NULL,
    `is_confirmed` BOOLEAN NOT NULL DEFAULT FALSE,
    `confirmed_at` DATETIME NULL,
    `confirmed_by` INT NULL,
    `expires_at` DATETIME NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_cai_class` FOREIGN KEY (`live_class_id`) REFERENCES `live_classes` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_cai_importer` FOREIGN KEY (`imported_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_cai_confirmer` FOREIGN KEY (`confirmed_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_cai_class` (`live_class_id`),
    INDEX `idx_cai_expires` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 79. Admin Audit Logs Table (Final Polish - Append-Only Governance)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `admin_audit_logs` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `actor_id` INT NULL,
    `actor_email` VARCHAR(255) NOT NULL,
    `action` VARCHAR(100) NOT NULL,
    `target_type` VARCHAR(100) NOT NULL,
    `target_id` VARCHAR(100) NULL,
    `details` TEXT NULL,
    `ip_address` VARCHAR(45) NULL,
    `user_agent` VARCHAR(300) NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT `fk_adm_audit_actor` FOREIGN KEY (`actor_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    INDEX `idx_aal_actor` (`actor_id`),
    INDEX `idx_aal_action` (`action`),
    INDEX `idx_aal_target` (`target_type`),
    INDEX `idx_aal_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 80. Login Attempts Table (Final Polish - Lockout & Exponential Backoff)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `login_attempts` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `email` VARCHAR(255) NOT NULL,
    `ip_address` VARCHAR(45) NOT NULL,
    `is_success` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_break_glass` BOOLEAN NOT NULL DEFAULT FALSE,
    `failure_reason` VARCHAR(100) NULL,
    `attempted_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX `idx_la_email` (`email`),
    INDEX `idx_la_ip` (`ip_address`),
    INDEX `idx_la_attempted` (`attempted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
