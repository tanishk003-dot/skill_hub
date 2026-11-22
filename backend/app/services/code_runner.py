import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import httpx
from fastapi import HTTPException, status
from app.core.config import settings

logger = logging.getLogger(__name__)

class TestCaseResult(BaseModel):
    id: int
    is_sample: bool
    passed: bool
    input: Optional[str] = None         # Populated ONLY for sample test cases; strictly None for hidden
    expected_output: Optional[str] = None # Populated ONLY for sample test cases; strictly None for hidden
    actual_output: Optional[str] = None   # Populated ONLY for sample test cases; strictly None for hidden
    execution_time_ms: float = 0.0
    memory_used_kb: float = 0.0
    status_description: str = "Accepted"
    compile_error: Optional[str] = None

class CodeExecutionSummary(BaseModel):
    passed_sample: int = 0
    total_sample: int = 0
    passed_hidden: int = 0
    total_hidden: int = 0
    total_passed: int = 0
    total_cases: int = 0
    overall_status: str = "ACCEPTED" # ACCEPTED, WRONG_ANSWER, TIME_LIMIT_EXCEEDED, COMPILATION_ERROR, RUNTIME_ERROR
    max_time_ms: float = 0.0
    max_memory_kb: float = 0.0
    test_results: List[TestCaseResult] = []

def sanitize_error_output(raw_text: Optional[str], hidden_cases: List[Dict[str, Any]]) -> Optional[str]:
    """
    Sanitizes stack traces, compile errors, or runtime errors to ensure
    no hidden test case input or expected output string ever leaks into error messages.
    """
    if not raw_text:
        return raw_text
    sanitized = raw_text
    for hc in hidden_cases:
        h_in = str(hc.get("input", "")).strip()
        h_out = str(hc.get("expected_output", "")).strip()
        if len(h_in) >= 2 and h_in in sanitized:
            sanitized = sanitized.replace(h_in, "[HIDDEN_INPUT_REDACTED]")
        if len(h_out) >= 2 and h_out in sanitized:
            sanitized = sanitized.replace(h_out, "[HIDDEN_OUTPUT_REDACTED]")
    return sanitized

class CodeRunner(ABC):
    @abstractmethod
    def run_tests(
        self,
        language: str,
        source_code: str,
        sample_cases: List[Dict[str, Any]],
        hidden_cases: List[Dict[str, Any]],
        is_sample_only: bool = False
    ) -> CodeExecutionSummary:
        pass

class MockRunner(CodeRunner):
    """
    Mock runner used strictly during automated testing (APP_ENV=test).
    Evaluates python/sql code deterministically without calling external sandbox.
    """
    def run_tests(
        self,
        language: str,
        source_code: str,
        sample_cases: List[Dict[str, Any]],
        hidden_cases: List[Dict[str, Any]],
        is_sample_only: bool = False
    ) -> CodeExecutionSummary:
        cases_to_run = sample_cases if is_sample_only else (sample_cases + hidden_cases)
        results: List[TestCaseResult] = []

        passed_sample = 0
        passed_hidden = 0
        overall_status = "ACCEPTED"

        # Check for obvious syntax failure simulations
        if "syntax_error" in source_code or "SyntaxError" in source_code:
            overall_status = "COMPILATION_ERROR"
            for c in sample_cases:
                results.append(TestCaseResult(
                    id=c.get("id", 1),
                    is_sample=True,
                    passed=False,
                    input=str(c.get("input", "")),
                    expected_output=str(c.get("expected_output", "")),
                    actual_output="",
                    compile_error="SyntaxError: invalid syntax on line 1",
                    status_description="Compilation Error"
                ))
            return CodeExecutionSummary(
                passed_sample=0,
                total_sample=len(sample_cases),
                passed_hidden=0,
                total_hidden=len(hidden_cases),
                total_passed=0,
                total_cases=len(cases_to_run),
                overall_status=overall_status,
                test_results=results
            )

        for idx, c in enumerate(cases_to_run):
            is_sample = c in sample_cases
            # Mock evaluation logic: fails if source code contains "fail_test"
            should_pass = "fail_test" not in source_code

            if should_pass:
                if is_sample:
                    passed_sample += 1
                else:
                    passed_hidden += 1

            # Requirement 5: Hidden test cases MUST NEVER return input, expected_output, or actual_output
            if is_sample:
                results.append(TestCaseResult(
                    id=c.get("id", idx + 1),
                    is_sample=True,
                    passed=should_pass,
                    input=str(c.get("input", "")),
                    expected_output=str(c.get("expected_output", "")),
                    actual_output=str(c.get("expected_output", "")) if should_pass else "Wrong Output",
                    execution_time_ms=12.5,
                    memory_used_kb=2048.0,
                    status_description="Accepted" if should_pass else "Wrong Answer"
                ))
            else:
                # STRICT ZERO LEAKAGE FOR HIDDEN TESTS
                results.append(TestCaseResult(
                    id=c.get("id", idx + 1),
                    is_sample=False,
                    passed=should_pass,
                    input=None,           # Redacted
                    expected_output=None, # Redacted
                    actual_output=None,   # Redacted
                    execution_time_ms=15.0,
                    memory_used_kb=2100.0,
                    status_description="Accepted" if should_pass else "Wrong Answer"
                ))

        if not is_sample_only and (passed_sample + passed_hidden) < len(cases_to_run):
            overall_status = "WRONG_ANSWER"

        return CodeExecutionSummary(
            passed_sample=passed_sample,
            total_sample=len(sample_cases),
            passed_hidden=passed_hidden,
            total_hidden=len(hidden_cases),
            total_passed=passed_sample + passed_hidden,
            total_cases=len(cases_to_run),
            overall_status=overall_status,
            max_time_ms=18.0,
            max_memory_kb=2150.0,
            test_results=results
        )

class Judge0Runner(CodeRunner):
    """
    Communicates over HTTP with self-hosted Judge0 CE sandbox container.
    Guarantees:
    - Never falls back to host execution.
    - If Judge0 is unhealthy or unreachable, returns HTTP 503.
    - Enforces resource limits (CPU, memory, max processes, output size, network disabled).
    """
    # Judge0 Language IDs
    LANGUAGE_MAP = {
        "python": 71,       # Python (3.8.1)
        "javascript": 63,   # JavaScript (Node.js 12.14.0)
        "java": 62,         # Java (OpenJDK 13.0.1)
        "sql": 82           # SQL (SQLite 3.27.2)
    }

    def _check_health(self) -> None:
        try:
            url = f"{settings.JUDGE0_URL.rstrip('/')}/about"
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    raise Exception(f"Judge0 responded with status {resp.status_code}")
        except Exception as e:
            logger.error(f"Judge0 healthcheck failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Code runner unavailable: The sandboxed code execution service is not reachable. Please contact the administrator."
            )

    def run_tests(
        self,
        language: str,
        source_code: str,
        sample_cases: List[Dict[str, Any]],
        hidden_cases: List[Dict[str, Any]],
        is_sample_only: bool = False
    ) -> CodeExecutionSummary:
        # Check health first: fails fast with 503 if unreachable
        self._check_health()

        lang_id = self.LANGUAGE_MAP.get(language.lower(), 71)
        cases_to_run = sample_cases if is_sample_only else (sample_cases + hidden_cases)
        results: List[TestCaseResult] = []

        passed_sample = 0
        passed_hidden = 0
        overall_status = "ACCEPTED"
        max_time = 0.0
        max_mem = 0.0

        endpoint = f"{settings.JUDGE0_URL.rstrip('/')}/submissions?wait=true"

        for idx, tc in enumerate(cases_to_run):
            is_sample = tc in sample_cases
            stdin_val = str(tc.get("input", ""))
            expected_out = str(tc.get("expected_output", "")).strip()

            payload = {
                "language_id": lang_id,
                "source_code": source_code,
                "stdin": stdin_val,
                "expected_output": expected_out,
                "cpu_time_limit": settings.JUDGE0_CPU_TIME_LIMIT,
                "wall_time_limit": settings.JUDGE0_WALL_TIME_LIMIT,
                "memory_limit": settings.JUDGE0_MEMORY_LIMIT,
                "max_processes_and_or_threads": settings.JUDGE0_MAX_PROCESSES,
                "max_file_size": min(settings.JUDGE0_MAX_OUTPUT_SIZE, 4096),
                "enable_network": settings.JUDGE0_ENABLE_NETWORK
            }

            try:
                with httpx.Client(timeout=settings.JUDGE0_WALL_TIME_LIMIT + 3.0) as client:
                    resp = client.post(endpoint, json=payload)
                    if resp.status_code not in [200, 201]:
                        raise Exception(f"Judge0 submission returned status {resp.status_code}")
                    data = resp.json()
            except Exception as e:
                logger.error(f"Error executing test case on Judge0: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Code runner unavailable: Execution service failed to respond."
                )

            status_obj = data.get("status", {})
            status_id = status_obj.get("id", 0) # 3: Accepted, 4: Wrong Answer, 5: Time Limit Exceeded, 6: Compilation Error, 7-12: Runtime Error
            status_desc = status_obj.get("description", "Unknown")

            passed = (status_id == 3)
            if passed:
                if is_sample:
                    passed_sample += 1
                else:
                    passed_hidden += 1
            else:
                if status_id == 6:
                    overall_status = "COMPILATION_ERROR"
                elif status_id == 5:
                    overall_status = "TIME_LIMIT_EXCEEDED"
                elif overall_status == "ACCEPTED":
                    overall_status = "WRONG_ANSWER"

            time_ms = float(data.get("time") or 0.0) * 1000.0
            mem_kb = float(data.get("memory") or 0.0)
            max_time = max(max_time, time_ms)
            max_mem = max(max_mem, mem_kb)

            raw_error = data.get("compile_output") or data.get("stderr")
            sanitized_err = sanitize_error_output(raw_error, hidden_cases)

            actual_out = (data.get("stdout") or "").strip()

            if is_sample:
                results.append(TestCaseResult(
                    id=tc.get("id", idx + 1),
                    is_sample=True,
                    passed=passed,
                    input=stdin_val,
                    expected_output=expected_out,
                    actual_output=actual_out,
                    execution_time_ms=time_ms,
                    memory_used_kb=mem_kb,
                    status_description=status_desc,
                    compile_error=sanitized_err
                ))
            else:
                # STRICT CONFIDENTIALITY: Hidden test input/outputs are never echoed
                results.append(TestCaseResult(
                    id=tc.get("id", idx + 1),
                    is_sample=False,
                    passed=passed,
                    input=None,
                    expected_output=None,
                    actual_output=None,
                    execution_time_ms=time_ms,
                    memory_used_kb=mem_kb,
                    status_description=status_desc,
                    compile_error=sanitized_err
                ))

        return CodeExecutionSummary(
            passed_sample=passed_sample,
            total_sample=len(sample_cases),
            passed_hidden=passed_hidden,
            total_hidden=len(hidden_cases),
            total_passed=passed_sample + passed_hidden,
            total_cases=len(cases_to_run),
            overall_status=overall_status,
            max_time_ms=max_time,
            max_memory_kb=max_mem,
            test_results=results
        )

def get_code_runner() -> CodeRunner:
    """
    Returns the appropriate CodeRunner implementation.
    Requirement 1: MockRunner is allowed ONLY when APP_ENV=test.
    In development or production, Judge0Runner is returned.
    """
    env = (settings.APP_ENV or "development").strip().lower()
    if env == "test":
        return MockRunner()
    return Judge0Runner()
