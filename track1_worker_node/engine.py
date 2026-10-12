"""Local streaming inference for quantized GGUF models and Ollama."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterator, Optional

import psutil

LOGGER = logging.getLogger(__name__)

# Try optional imports
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

try:
    import ollama
except ImportError:
    ollama = None


class LocalExecutionEngine:
    """Loads one GGUF model (via llama-cpp-python) or connects to local Ollama and streams generated tokens."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: str = "llama3.2:1b",
        backend: str = "auto",
    ) -> None:
        self.model_path = model_path
        self.model_name = model_name
        self.backend = backend
        self._llm = None
        self._init_engine()

    def _init_engine(self) -> None:
        # 1. Check local GGUF model via llama_cpp if file exists and package is installed
        if (
            self.backend in ("auto", "llama_cpp")
            and self.model_path
            and Path(self.model_path).is_file()
            and Llama is not None
        ):
            try:
                LOGGER.info("Initializing GGUF engine via llama_cpp with %s", self.model_path)
                physical_cores = psutil.cpu_count(logical=False) or 1
                self._llm = Llama(
                    model_path=self.model_path,
                    n_threads=physical_cores,
                    n_gpu_layers=-1,
                )
                self.backend = "llama_cpp"
                return
            except Exception as exc:
                LOGGER.warning("Failed to initialize GGUF via llama_cpp: %s. Checking Ollama fallback...", exc)

        # 2. Check Ollama service
        if (
            self.backend in ("auto", "ollama")
            and ollama is not None
        ):
            try:
                client = ollama.Client()
                models = [m.model for m in client.list().models]
                matched = any(self.model_name in m or m.startswith(self.model_name) for m in models)
                if matched or self.backend == "ollama":
                    self.backend = "ollama"
                    LOGGER.info("Initialized Ollama engine with model '%s'", self.model_name)
                    return
            except Exception as exc:
                LOGGER.warning("Ollama connection check failed for '%s': %s", self.model_name, exc)

        # 3. Direct GGUF loading if model file exists
        if self.model_path and Path(self.model_path).is_file():
            if Llama is None:
                LOGGER.warning("GGUF file found at %s but llama-cpp-python is still compiling or not installed. Falling back to Ollama.", self.model_path)
                if ollama is not None:
                    self.backend = "ollama"
                    return
                raise RuntimeError("GGUF model file found but llama-cpp-python is not installed.")
            physical_cores = psutil.cpu_count(logical=False) or 1
            self._llm = Llama(
                model_path=self.model_path,
                n_threads=physical_cores,
                n_gpu_layers=-1,
            )
            self.backend = "llama_cpp"
            return

        # 4. If Ollama package is present, default to Ollama
        if ollama is not None:
            self.backend = "ollama"
            LOGGER.info("Defaulting to Ollama backend with model '%s'", self.model_name)
            return

        raise FileNotFoundError(
            f"Neither GGUF model ({self.model_path}) nor Ollama model ({self.model_name}) could be initialized."
        )

    def execute_task(self, prompt: str) -> Iterator[str]:
        """Yield each generated text token immediately as inference produces it."""
        if self.backend == "ollama" and ollama is not None:
            client = ollama.Client()
            stream = client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            for chunk in stream:
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
        elif self.backend == "llama_cpp" and self._llm is not None:
            stream = self._llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            for chunk in stream:
                delta = chunk["choices"][0]["delta"]
                token = delta.get("content", "")
                if token:
                    yield token
        else:
            raise RuntimeError(f"Execution engine backend '{self.backend}' is not properly configured.")


if __name__ == "__main__":
    import sys
    engine = LocalExecutionEngine()
    print(f"Engine initialized with backend: {engine.backend}")
    print("Testing inference:")
    for token in engine.execute_task("Hello! Tell me in 10 words what is QThorium Mesh."):
        sys.stdout.write(token)
        sys.stdout.flush()
    print()
