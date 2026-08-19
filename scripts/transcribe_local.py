import argparse
import json
import os
import sys
from pathlib import Path


def _configure_windows_dlls() -> list[object]:
    if os.name != "nt":
        return []
    site_packages = Path(sys.prefix) / "Lib" / "site-packages"
    candidates = (
        site_packages / "nvidia" / "cublas" / "bin",
        site_packages / "nvidia" / "cudnn" / "bin",
        site_packages / "ctranslate2",
    )
    existing = [path for path in candidates if path.is_dir()]
    if existing:
        os.environ["PATH"] = os.pathsep.join(map(str, existing)) + os.pathsep + os.environ.get("PATH", "")
    return [os.add_dll_directory(str(path)) for path in existing]


_DLL_HANDLES = _configure_windows_dlls()

from faster_whisper import WhisperModel


def transcribe(model_path, audio, language, device, compute_type):
    model = WhisperModel(model_path, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(audio, language=language)
    return [
        f"[{segment.start:.2f}-{segment.end:.2f}] {segment.text.strip()}"
        for segment in segments
        if segment.text.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata")
    args = parser.parse_args()
    try:
        lines = transcribe(args.model, args.audio, args.language, "cuda", "float16")
        runtime = {"device": "cuda", "compute_type": "float16", "fallback": False}
    except Exception as cuda_error:
        print(f"CUDA unavailable; falling back to CPU int8: {cuda_error}")
        lines = transcribe(args.model, args.audio, args.language, "cpu", "int8")
        runtime = {
            "device": "cpu",
            "compute_type": "int8",
            "fallback": True,
            "cuda_error": str(cuda_error),
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    if args.metadata:
        metadata = Path(args.metadata)
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_text(json.dumps(runtime, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
