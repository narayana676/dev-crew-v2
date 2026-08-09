"""Provider-agnostic LLM interface supporting structured output and usage metrics."""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Type, TypeVar
from pydantic import BaseModel
from app.config import settings
from app.core.state import (
    ArchitectureOutput,
    CodeFile,
    PlanOutput,
    PlanTask,
    ReviewOutput,
    UsageMetrics,
)

T = TypeVar("T", bound=BaseModel)


class CoderOutput(BaseModel):
    """Structured output for Coder agent node."""
    code_files: List[CodeFile]


class DebugOutput(BaseModel):
    """Structured output for Debugger agent node."""
    code_files: List[CodeFile]
    root_cause: str = ""


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers delivering structured Pydantic outputs."""

    @abstractmethod
    def generate_structured(
        self, prompt: str, system_prompt: str, response_model: Type[T]
    ) -> Tuple[T, UsageMetrics]:
        """Generate structured output conforming strictly to response_model."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for offline testing and deterministic fallback."""

    def generate_structured(
        self, prompt: str, system_prompt: str, response_model: Type[T]
    ) -> Tuple[T, UsageMetrics]:
        usage = UsageMetrics()
        usage.add_usage(prompt=250, completion=150)

        if response_model == PlanOutput:
            obj = PlanOutput(
                summary="Build requested module",
                architecture_overview="Modular architecture with API and test coverage",
                tasks=[
                    PlanTask(id="task-1", title="Implement module", description="Core functionality", target_files=["main.py"]),
                    PlanTask(id="task-2", title="Implement tests", description="Pytest test suite", target_files=["test_main.py"]),
                ],
            )
            return obj, usage  # type: ignore

        if response_model == ArchitectureOutput:
            obj = ArchitectureOutput(
                components=["Core Logic", "Test Runner"],
                interfaces=["Python Module API"],
                file_structure=["main.py", "test_main.py"],
                design_notes="Mock architectural spec",
            )
            return obj, usage  # type: ignore

        if response_model == CoderOutput:
            obj = CoderOutput(
                code_files=[
                    CodeFile(
                        path="main.py",
                        content="def add(a: int, b: int) -> int:\n    return a + b\n",
                        language="python",
                    ),
                    CodeFile(
                        path="test_main.py",
                        content="from main import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
                        language="python",
                    ),
                ]
            )
            return obj, usage  # type: ignore

        if response_model == ReviewOutput:
            obj = ReviewOutput(passed=True, score=0.98, comments=["Code satisfies architecture and spec"])
            return obj, usage  # type: ignore

        if response_model == DebugOutput:
            obj = DebugOutput(
                code_files=[
                    CodeFile(
                        path="main.py",
                        content="def add(a: int, b: int) -> int:\n    return a + b\n",
                        language="python",
                    ),
                    CodeFile(
                        path="test_main.py",
                        content="from main import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
                        language="python",
                    ),
                ],
                root_cause="Fixed assertions",
            )
            return obj, usage  # type: ignore

        raise ValueError(f"Unsupported response model for MockLLMProvider: {response_model}")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider using structured output capabilities."""

    def __init__(self, api_key: str = "", model_name: str = "gpt-4o"):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model_name = model_name or settings.OPENAI_MODEL

    def generate_structured(
        self, prompt: str, system_prompt: str, response_model: Type[T]
    ) -> Tuple[T, UsageMetrics]:
        if not self.api_key:
            raise RuntimeError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. "
                "Set OPENAI_API_KEY in .env or switch LLM_PROVIDER=mock."
            )

        import openai
        client = openai.OpenAI(api_key=self.api_key)
        try:
            completion = client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                response_format=response_model,
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}") from e

        parsed_obj = completion.choices[0].message.parsed
        usage = UsageMetrics()
        if completion.usage:
            usage.add_usage(
                prompt=completion.usage.prompt_tokens,
                completion=completion.usage.completion_tokens,
            )
        return parsed_obj, usage  # type: ignore


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider using structured output via with_structured_output."""

    def __init__(self, api_key: str = "", model_name: str = ""):
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL

    def generate_structured(
        self, prompt: str, system_prompt: str, response_model: Type[T]
    ) -> Tuple[T, UsageMetrics]:
        if not self.api_key:
            raise RuntimeError(
                "LLM_PROVIDER=gemini but GOOGLE_API_KEY is not set. "
                "Set GOOGLE_API_KEY in .env or switch LLM_PROVIDER=mock."
            )

        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(model=self.model_name, google_api_key=self.api_key)
        structured_llm = llm.with_structured_output(response_model, include_raw=True)

        try:
            result = structured_llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
            )
        except Exception as e:
            raise RuntimeError(f"Gemini API call failed: {e}") from e

        parsed_obj = result.get("parsed") if isinstance(result, dict) else result
        if parsed_obj is None:
            raise RuntimeError(
                f"Gemini returned no parseable {response_model.__name__} structured output. "
                f"Raw response: {result}"
            )

        usage = UsageMetrics()
        raw_msg = result.get("raw") if isinstance(result, dict) else None
        usage_meta = getattr(raw_msg, "usage_metadata", None) if raw_msg is not None else None
        if usage_meta:
            usage.add_usage(
                prompt=usage_meta.get("input_tokens", 0),
                completion=usage_meta.get("output_tokens", 0),
            )
        return parsed_obj, usage  # type: ignore


def get_llm_provider(provider_type: str = "") -> BaseLLMProvider:
    """Factory function to get swappable LLM provider."""
    provider = provider_type or settings.LLM_PROVIDER
    if provider == "openai":
        return OpenAIProvider()
    if provider == "gemini":
        return GeminiProvider()
    return MockLLMProvider()
