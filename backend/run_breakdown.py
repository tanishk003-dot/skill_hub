import os, subprocess, json

os.environ["DATABASE_URL"] = "mysql+pymysql://root:root@127.0.0.1:3306/skillhub_db?charset=utf8mb4"

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

results = {}

for tf in test_files:
    print(f"Running {tf}...")
    res = subprocess.run(
        ["backend/venv/Scripts/python.exe", "-m", "pytest", tf, "-v", "--tb=line"],
        cwd="backend",
        capture_output=True,
        text=True,
        env=os.environ
    )
    lines = res.stdout.splitlines()
    summary = [l for l in lines if "passed" in l or "failed" in l or "error" in l]
    failures = [l for l in lines if l.startswith("FAILED ") or l.startswith("ERROR ")]
    results[tf] = {
        "returncode": res.returncode,
        "summary": summary[-1] if summary else "No summary",
        "failures": failures
    }
    print(f"  {results[tf]['summary']}")
    for f in failures:
        print(f"    {f}")

with open("test_mysql_breakdown.json", "w", encoding="utf-8") as out:
    json.dump(results, out, indent=2)

print("\nDone detailed breakdown.")
