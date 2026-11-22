-- ============================================================================
-- L&K Skill Hub - Idempotent Migration to @csm.tech Email Accounts
-- Renames seeded and demo accounts to @csm.tech and adds must_change_password
-- ============================================================================

USE `skillhub_db`;

-- 1. Ensure must_change_password column exists in users
SET @col_exists = (
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() 
      AND TABLE_NAME = 'users' 
      AND COLUMN_NAME = 'must_change_password'
);

SET @sql_alter = IF(@col_exists = 0, 
    'ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT FALSE', 
    'SELECT 1'
);
PREPARE stmt FROM @sql_alter;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Migrate Core Demo Accounts in users
UPDATE users SET email = 'admin.demo@csm.tech', must_change_password = TRUE WHERE email IN ('admin@skillhub.com', 'admin@csm.tech');
UPDATE users SET email = 'mentor.demo@csm.tech', must_change_password = TRUE WHERE email IN ('mentor@skillhub.com', 'mentor@csm.tech');
UPDATE users SET email = 'ase.demo@csm.tech', must_change_password = TRUE WHERE email IN ('ase@skillhub.com', 'ase@csm.tech');

-- 3. Migrate 6 Demo ASEs in users
UPDATE users SET email = 'demo.aarav.sharma@csm.tech', must_change_password = TRUE WHERE email IN ('aarav.sharma@skillhub.com', 'ase1@skillhub.com');
UPDATE users SET email = 'demo.diya.patel@csm.tech', must_change_password = TRUE WHERE email IN ('diya.patel@skillhub.com', 'ase2@skillhub.com');
UPDATE users SET email = 'demo.rohan.gupta@csm.tech', must_change_password = TRUE WHERE email IN ('rohan.gupta@skillhub.com', 'ase3@skillhub.com');
UPDATE users SET email = 'demo.ananya.verma@csm.tech', must_change_password = TRUE WHERE email IN ('ananya.verma@skillhub.com', 'ase4@skillhub.com');
UPDATE users SET email = 'demo.kabir.mehta@csm.tech', must_change_password = TRUE WHERE email IN ('kabir.mehta@skillhub.com', 'ase5@skillhub.com');
UPDATE users SET email = 'demo.ishita.roy@csm.tech', must_change_password = TRUE WHERE email IN ('ishita.roy@skillhub.com', 'ase6@skillhub.com');

-- Also migrate any remaining @skillhub.com emails
UPDATE users SET email = REPLACE(email, '@skillhub.com', '@csm.tech'), must_change_password = TRUE WHERE email LIKE '%@skillhub.com';

-- Set must_change_password = TRUE for all existing demo accounts
UPDATE users SET must_change_password = TRUE WHERE email IN (
    'admin.demo@csm.tech',
    'mentor.demo@csm.tech',
    'ase.demo@csm.tech',
    'demo.aarav.sharma@csm.tech',
    'demo.diya.patel@csm.tech',
    'demo.rohan.gupta@csm.tech',
    'demo.ananya.verma@csm.tech',
    'demo.kabir.mehta@csm.tech',
    'demo.ishita.roy@csm.tech'
);

-- 4. Update SSO Audit Logs
UPDATE sso_audit_logs SET upn = 'admin.demo@csm.tech' WHERE upn = 'admin@skillhub.com';
UPDATE sso_audit_logs SET upn = 'demo.aarav.sharma@csm.tech' WHERE upn IN ('ase1@skillhub.com', 'aarav.sharma@skillhub.com');
UPDATE sso_audit_logs SET upn = REPLACE(upn, '@skillhub.com', '@csm.tech') WHERE upn LIKE '%@skillhub.com';

-- 5. Update User SSO Accounts
UPDATE user_sso_accounts SET upn = 'admin.demo@csm.tech' WHERE upn = 'admin@skillhub.com';
UPDATE user_sso_accounts SET upn = 'demo.aarav.sharma@csm.tech' WHERE upn IN ('ase1@skillhub.com', 'aarav.sharma@skillhub.com');
UPDATE user_sso_accounts SET upn = REPLACE(upn, '@skillhub.com', '@csm.tech') WHERE upn LIKE '%@skillhub.com';

-- 6. Update Admin Audit Logs
UPDATE admin_audit_logs SET actor_email = 'admin.demo@csm.tech' WHERE actor_email IN ('admin@skillhub.com', 'admin@csm.tech');
UPDATE admin_audit_logs SET actor_email = REPLACE(actor_email, '@skillhub.com', '@csm.tech') WHERE actor_email LIKE '%@skillhub.com';

-- 7. Update Login Attempts
UPDATE login_attempts SET email = 'admin.demo@csm.tech' WHERE email IN ('admin@skillhub.com', 'admin@csm.tech', 'admin@csmtech.com');
UPDATE login_attempts SET email = 'ase.demo@csm.tech' WHERE email IN ('ase@skillhub.com', 'ase@csm.tech');
UPDATE login_attempts SET email = REPLACE(email, '@skillhub.com', '@csm.tech') WHERE email LIKE '%@skillhub.com';
