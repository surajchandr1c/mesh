"""Local streaming inference for quantized GGUF models."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import psutil
from llama_cpp import Llama


class LocalExecutionEngine:
    """Loads one GGUF model and streams generated chat-completion tokens."""

    def __init__(self, model_path: str) -> None:
        if not Path(model_path).is_file():
            raise FileNotFoundError(f"GGUF model file was not found: {model_path}")

        # Fall back to one thread only when the operating system cannot report
        # physical-core information.
        physical_cores = psutil.cpu_count(logical=False) or 1
        self._model_path = model_path
        self._llm = Llama(
            model_path=model_path,
            n_threads=physical_cores,
            n_gpu_layers=-1,
        )

    def execute_task(self, prompt: str) -> Iterator[str]:
        """Yield each generated text token immediately as inference produces it."""
        stream = self._llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        for chunk in stream:
            delta = chunk["choices"][0]["delta"]
            token = delta.get("content", "")
            if token:
                yield token


if __name__ == "__main__":
    dummy_model_path = "./models/dummy-model.gguf"
    print(
        "LocalExecutionEngine compiles successfully. "
        f"Configure a valid model before loading: {dummy_model_path}"
    )
