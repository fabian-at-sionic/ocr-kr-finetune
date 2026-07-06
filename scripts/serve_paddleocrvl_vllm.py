#!/usr/bin/env python3
"""Serve the local PaddleOCR-VL 1.6 model through PaddleX's vLLM backend."""

import os

os.environ.setdefault("TRITON_PTXAS_PATH", "/usr/local/cuda/bin/ptxas")
os.environ.setdefault("TRITON_MOCK_PTX_VERSION", "86")

from triton.knobs import NvidiaTool
import triton.backends.nvidia.compiler as triton_nvidia_compiler


def _get_system_ptxas_as_cuda_12_8() -> NvidiaTool:
    return NvidiaTool("/usr/local/cuda/bin/ptxas", "12.9")


triton_nvidia_compiler.get_ptxas = _get_system_ptxas_as_cuda_12_8
triton_nvidia_compiler.get_ptxas.cache_clear() if hasattr(triton_nvidia_compiler.get_ptxas, "cache_clear") else None
triton_nvidia_compiler.get_ptxas_version.cache_clear()

from paddlex.inference.genai.backends.vllm import register_models, run_vllm_server


def main() -> None:
    model_dir = "/workspace/ocr-bench/model/PaddlePaddle/PaddleOCR-VL-1.6"
    register_models()
    run_vllm_server(
        host="127.0.0.1",
        port=8001,
        model_name="PaddleOCR-VL-1.6-0.9B",
        model_dir=model_dir,
        config={
            "trust-remote-code": True,
            "gpu-memory-utilization": 0.25,
            "max-model-len": 8192,
        },
        chat_template_path=f"{model_dir}/chat_template.jinja",
    )


if __name__ == "__main__":
    main()
