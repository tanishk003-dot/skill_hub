import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7
    ) -> Tuple[str, int, int]:
        """
        Takes conversation messages [{"role": "system"|"user"|"assistant", "content": "..."}]
        Returns: (response_text, prompt_tokens, completion_tokens)
        """
        pass

class MockProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return settings.LLM_MODEL or "mock-gpt-4"

    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7
    ) -> Tuple[str, int, int]:
        user_message = ""
        system_prompt = ""
        for m in messages:
            if m.get("role") == "user":
                user_message = m.get("content", "")
            elif m.get("role") == "system":
                system_prompt = m.get("content", "")

        q_lower = user_message.lower()

        # Prompt injection protection check in mock provider
        if any(bad in q_lower for bad in ["ignore previous", "system prompt", "reveal", "dump", "passwords", "other users", "all users"]):
            reply = (
                "I am a secure, read-only AI assistant for L&K Skill Hub. "
                "I cannot override security guidelines, disclose internal prompts, or access other users' data."
            )
            return reply, 120, 45

        # Check role from system prompt
        if "Role: ASE" in system_prompt or "role: ase" in system_prompt.lower():
            if "weak" in q_lower or "improve" in q_lower or "focus" in q_lower or "score" in q_lower:
                reply = (
                    "Based on your recent assessment results, your primary focus area is **Logical Thinking & Data Structures** "
                    "(currently below 70%).\n\n"
                    "**Recommended Next Steps:**\n"
                    "1. Review the *Advanced Async Python & Microservices* training module on your My Learning page.\n"
                    "2. Practice section questions with 25-minute focused interval drills.\n"
                    "3. Attend the upcoming Mentor Live Q&A session."
                )
            elif "deadline" in q_lower or "training" in q_lower or "schedule" in q_lower or "due" in q_lower:
                reply = (
                    "Here is a summary of your upcoming priorities:\n"
                    "- Check your **My Learning** tab for assigned modules and upcoming due dates.\n"
                    "- Visit your **Schedule** calendar to join scheduled virtual classes and review upcoming evaluations."
                )
            elif "study plan" in q_lower or "plan" in q_lower:
                reply = (
                    "**Suggested 2-Week Mastery Plan:**\n\n"
                    "- **Week 1 (Targeted Remediation):** Dedicate 45 mins/day to weaker topics. Complete assigned self-paced modules.\n"
                    "- **Week 2 (Practical Application):** Build a small hands-on prototype and take timed practice quizzes.\n"
                    "- Schedule a 1-on-1 review with your mentor before your next assessment."
                )
            else:
                reply = (
                    f"Hello! I am your L&K Skill Hub Learning Assistant. "
                    f"I can analyze your assessment performance, guide your study schedule, and suggest relevant modules. "
                    f"What would you like to explore today?"
                )

        elif "Role: MENTOR" in system_prompt or "role: mentor" in system_prompt.lower():
            if "attention" in q_lower or "risk" in q_lower or "weak" in q_lower or "fail" in q_lower:
                reply = (
                    "**Mentee Focus Summary:**\n"
                    "- **Rohan Gupta** requires immediate follow-up: scoring below passing threshold (45%) and has an overdue Python training module.\n"
                    "- **Kabir Mehta** was auto-submitted due to proctoring flags and should be scheduled for a 1-on-1 counseling session.\n"
                    "- Recommend assigning targeted remedial modules in Logical Thinking to the Beta cohort."
                )
            elif "cohort" in q_lower or "average" in q_lower or "ranking" in q_lower:
                reply = (
                    "**Cohort Performance Overview:**\n"
                    "- **Alpha Engineering Cohort:** Strong overall mastery (avg 82.5%), high completion velocity in Python tracks.\n"
                    "- **Beta Batch:** Passing rate currently at 70%. Focus is recommended on reasoning and section timer pacing."
                )
            else:
                reply = (
                    "Hello Mentor! I can assist you with mentee performance diagnostics, cohort weak-area summaries, "
                    "and recommended intervention strategies for at-risk engineers."
                )

        elif "Role: ADMIN" in system_prompt or "role: admin" in system_prompt.lower():
            if "skill gap" in q_lower or "org" in q_lower or "benchmark" in q_lower:
                reply = (
                    "**Organizational Skill Gap Analysis:**\n"
                    "- Across all engineering units, **Pattern Recognition** and **System Design** exhibit the widest competency gaps.\n"
                    "- Overall assessment workflow throughput is operating at healthy capacity.\n"
                    "- Recommendation: Increase live interactive workshops for emerging full-stack batches."
                )
            elif "user" in q_lower or "stat" in q_lower or "summary" in q_lower:
                reply = (
                    "**Organization Overview:**\n"
                    "- User directory and active cohorts are balanced.\n"
                    "- Training program completion rate across units is tracking positively.\n"
                    "- Live class attendance is averaging above organizational targets."
                )
            else:
                reply = (
                    "Hello Administrator! I am ready to summarize organizational KPIs, cohort benchmark comparisons, "
                    "and engineering competency trends."
                )
        else:
            reply = (
                "Hello! I am your L&K Skill Hub AI Assistant. How can I assist you with skills, trainings, or analytics today?"
            )

        # Approximate token counts
        prompt_tokens = sum(len(m.get("content", "").split()) for m in messages) * 2 + 10
        completion_tokens = len(reply.split()) * 2
        return reply, max(15, prompt_tokens), max(10, completion_tokens)

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        self._api_key = api_key
        self._model = model
        self._base_url = (base_url.rstrip("/") if base_url else "https://api.openai.com/v1")

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7
    ) -> Tuple[str, int, int]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
            "temperature": temperature
        }
        url = f"{self._base_url}/chat/completions"

        with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            return content, prompt_tokens, completion_tokens

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7
    ) -> Tuple[str, int, int]:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        # Extract system prompt if present
        system_text = ""
        formatted_messages = []
        for m in messages:
            if m.get("role") == "system":
                system_text += m.get("content", "") + "\n"
            else:
                formatted_messages.append({
                    "role": m.get("role"),
                    "content": m.get("content")
                })

        payload = {
            "model": self._model,
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
            "messages": formatted_messages,
            "temperature": temperature
        }
        if system_text:
            payload["system"] = system_text.strip()

        with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            resp = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            text_blocks = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
            content = "\n".join(text_blocks)
            usage = data.get("usage", {})
            prompt_tokens = usage.get("input_tokens", 0)
            completion_tokens = usage.get("output_tokens", 0)
            return content, prompt_tokens, completion_tokens

def get_llm_provider() -> LLMProvider:
    provider = (settings.LLM_PROVIDER or "mock").lower().strip()
    api_key = (settings.LLM_API_KEY or "").strip()

    # Rule: If no API key is set, default to MockProvider regardless of chosen provider name
    if not api_key or provider == "mock":
        return MockProvider()

    if provider == "openai":
        return OpenAIProvider(
            api_key=api_key,
            model=settings.LLM_MODEL or "gpt-4o-mini",
            base_url=settings.LLM_BASE_URL
        )
    elif provider == "anthropic":
        return AnthropicProvider(
            api_key=api_key,
            model=settings.LLM_MODEL or "claude-3-5-sonnet-20241022"
        )
    else:
        logger.warning(f"Unknown LLM provider '{provider}', falling back to MockProvider")
        return MockProvider()

def is_demo_mode() -> bool:
    provider = (settings.LLM_PROVIDER or "mock").lower().strip()
    api_key = (settings.LLM_API_KEY or "").strip()
    return provider == "mock" or not api_key
