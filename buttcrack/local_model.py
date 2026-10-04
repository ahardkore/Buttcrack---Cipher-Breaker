"""Optional local-model adapter with a safe no-model fallback.

No model is downloaded or executed automatically. Providers are detected only
when explicitly requested, and model output is always advisory text.
"""
from __future__ import annotations

from dataclasses import dataclass
import shutil

@dataclass(frozen=True)
class ModelCapability:
    provider: str
    available: bool
    reason: str

class LocalModelAdapter:
    def capabilities(self) -> list[ModelCapability]:
        return [
            ModelCapability("explainable-planner", True, "built in; no network or model files"),
            ModelCapability("ollama", shutil.which("ollama") is not None, "optional executable"),
            ModelCapability("llama.cpp", any(shutil.which(x) for x in ("llama-cli", "llama-cpp")), "optional executable"),
        ]

    def prompt(self, text: str, provider: str = "explainable-planner") -> str:
        if provider != "explainable-planner":
            raise NotImplementedError("optional providers require explicit local configuration")
        from .assistant import explain
        return explain(text)
