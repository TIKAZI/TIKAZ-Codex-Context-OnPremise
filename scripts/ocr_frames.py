from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _record_payload(result: object) -> dict[str, Any]:
    raw = getattr(result, "json", None)
    if callable(raw):
        raw = raw()
    if raw is None and isinstance(result, dict):
        raw = result
    if not isinstance(raw, dict):
        return {}
    nested = raw.get("res")
    return nested if isinstance(nested, dict) else raw


def _extract_text(result: object) -> tuple[str, float, int]:
    payload = _record_payload(result)
    raw_texts = payload.get("rec_texts", [])
    raw_scores = payload.get("rec_scores", [])
    texts = [str(text).strip() for text in raw_texts if str(text).strip()]
    scores = [float(score) for score in raw_scores if isinstance(score, (int, float))]
    confidence = sum(scores) / len(scores) if scores else 0.0
    return "\n".join(texts), max(0.0, min(1.0, confidence)), len(texts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", default="ch")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    from paddleocr import PaddleOCR

    ocr = PaddleOCR(
        lang=args.language,
        ocr_version="PP-OCRv5",
        device=args.device,
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_recognition_model_name="PP-OCRv5_mobile_rec",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False,
    )
    frames: list[dict[str, object]] = []
    for path in args.frame:
        resolved = path.resolve()
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
        try:
            predictions = list(ocr.predict(str(resolved)))
            text, confidence, line_count = _extract_text(predictions[0]) if predictions else ("", 0.0, 0)
            frames.append({
                "frame_sha256": digest,
                "text": text,
                "confidence": confidence,
                "line_count": line_count,
            })
        except Exception as error:
            frames.append({
                "frame_sha256": digest,
                "text": "",
                "confidence": 0.0,
                "line_count": 0,
                "error": f"{type(error).__name__}: {error}"[:1000],
            })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"schema_version": 1, "engine": "PP-OCRv5-mobile", "frames": frames},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
