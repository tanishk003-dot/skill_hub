import os
import sys
import subprocess
import re
import json

test_files = [
    "tests/test_scoring.py",
    "tests/test_proctoring.py",
    "tests/test_cohorts_analytics.py",
    "tests/test_phase5_training_classes.py",
    "tests/test_phase6_ai_chat.py",
    "tests/test_phase7_coding_splash.py",
    "tests/test_phase8_ai_class_summary.py",
    "tests/test_phase9_wow_pack.py",
    "tests/test_phase10_webcam_accommodations.py",
    "tests/test_phase11_analytics_1on1_export_matching.py",
    "tests/test_phase12_buddy_forum.py",
    "tests/test_phase13_microsoft_integration.py",
    "tests/test_phase14_final_polish.py",
]

env = os.environ.copy()
env["DATABASE_URL"] = "mysql+pymysql://root:root@127.0.0.1:3306/skillhub_db?charset=utf8mb4"

python_bin = sys.executable

all_failures = []

print("=== STARTING MYSQL TEST RUN ONE FILE AT A TIME ===", flush=True)

for tf in test_files:
    sys.stdout.write(f"\n--- {tf} ---\n")
    sys.stdout.flush()
    try:
        proc = subprocess.run(
            [python_bin, "-m", "pytest", tf, "-v", "--tb=line", "-q"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=180,
            env=env
        )
        stdout = proc.stdout
        stderr = proc.stderr
        output_lines = stdout.splitlines()

        summary_line = ""
        for line in reversed(output_lines):
            if any(k in line for k in ["passed", "failed", "error", "skipped"]):
                summary_line = line
                break
        
        print(f"Summary: {summary_line}", flush=True)

        # Extract failing tests and error line
        failures = []
        for line in output_lines:
            if line.startswith("FAILED ") or line.startswith("ERROR "):
                failures.append(line)
                print(f"  {line}", flush=True)
                
                parts = line.split(" - ", 1)
                test_id = parts[0].replace("FAILED ", "").replace("ERROR ", "").strip()
                err_msg = parts[1].strip() if len(parts) > 1 else "Unknown error"
                all_failures.append({
                    "file": tf,
                    "test": test_id,
                    "error": err_msg
                })

    except subprocess.TimeoutExpired:
        print(f"Summary: TIMED OUT after 180 seconds!", flush=True)
        all_failures.append({
            "file": tf,
            "test": tf,
            "error": "TIMEOUT: Exceeded 180 seconds"
        })

with open("mysql_diagnostics_report.json", "w", encoding="utf-8") as f:
    json.dump(all_failures, f, indent=2)

print(f"\n=== FINISHED ALL FILES. Total failing/erroring items: {len(all_failures)} ===", flush=True)
