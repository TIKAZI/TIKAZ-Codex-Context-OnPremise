import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--audio", required=True)
parser.add_argument("--model", required=True)
parser.add_argument("--language", default="zh")
parser.add_argument("--output", required=True)
args = parser.parse_args()

from faster_whisper import WhisperModel

def transcribe(device, compute_type):
    model = WhisperModel(args.model, device=device, compute_type=compute_type)
    segments, info = model.transcribe(args.audio, language=args.language)
    return [
        f"[{segment.start:.2f}-{segment.end:.2f}] {segment.text.strip()}"
        for segment in segments
        if segment.text.strip()
    ]

try:
    lines = transcribe("cuda", "float16")
except Exception as cuda_error:
    print(f"CUDA unavailable; falling back to CPU int8: {cuda_error}")
    lines = transcribe("cpu", "int8")
Path(args.output).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
