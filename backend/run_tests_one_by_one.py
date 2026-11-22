import subprocess
import sys
import os
import re

TEST_FILES = [
    "tests/test_cohorts_analytics.py",
    "tests/test_phase10_webcam_accommodations.py",
    "tests/test_phase11_analytics_1on1_export_matching.py",
    "tests/test_phase12_buddy_forum.py",
    "tests/test_phase13_microsoft_integration.py",
    "tests/test_phase14_final_polish.py",
    "tests/test_phase5_training_classes.py",
    "tests/test_phase6_ai_chat.py",
    "tests/test_phase7_coding_splash.py",
    "tests/test_phase8_ai_class_summary.py",
    "tests/test_phase9_wow_pack.py",
    "tests/test_proctoring.py",
    "tests/test_scoring.py",
]

backend_dir = os.path.dirname(os.path.abspath(__file__))
python_exe = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
if not os.path.exists(python_exe):
    python_exe = sys.executable

results = []

print("=== Running MySQL Tests One Test File at a Time ===")

for tf in TEST_FILES:
    print(f"\n--- Running: {tf} ---")
    cmd = [python_exe, "-m", "pytest", tf, "-v", "--tb=short"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
            encoding="utf-8",
            errors="replace"
        )
        output = proc.stdout
        timed_out = False
    except subprocess.TimeoutExpired as e:
        output = e.stdout or ""
        timed_out = True

    if timed_out:
        print(f"TIMEOUT: {tf} exceeded 180s limit.")
        results.append({
            "file": tf,
            "status": "TIMEOUT",
            "summary": "TIMED OUT after 180s",
            "failures": ["TIMEOUT"]
        })
        continue

    # Extract summary line (e.g. "= 20 passed in 4.28s =" or "= 2 failed, 5 passed in ... =")
    summary_match = re.findall(r"=+\s*([\d\w\s,]+in\s+[\d\.]+s)\s*=+", output)
    summary_line = summary_match[-1] if summary_match else "No summary line found"

    # Extract failing/erroring test names
    failing_tests = []
    for line in output.splitlines():
        if " FAILED " in line or line.startswith("FAILED ") or " ERROR " in line or line.startswith("ERROR "):
            failing_tests.append(line.strip())

    print(f"Summary: {summary_line}")
    if failing_tests:
        print("Failing / Erroring tests:")
        for ft in failing_tests:
            print(f"  * {ft}")
    else:
        print("All passed!")

    results.append({
        "file": tf,
        "summary": summary_line,
        "failing": failing_tests,
        "full_output": output if failing_tests else ""
    })

print("\n\n=== RUN COMPLETE ===")
with open(os.path.join(backend_dir, "test_run_results.txt"), "w", encoding="utf-8") as f:
    for res in results:
        f.write(f"FILE: {res['file']}\n")
        f.write(f"SUMMARY: {res['summary']}\n")
        if res.get("failing"):
            f.write("FAILURES:\n")
            for ft in res["failing"]:
                f.write(f"  {ft}\n")
            f.write("\nOUTPUT:\n")
            f.write(res.get("full_output", ""))
            f.write("\n" + "="*60 + "\n\n")
        else:
            f.write("STATUS: ALL PASSED\n\n")
