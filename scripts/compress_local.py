from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))

    from llmlingua import PromptCompressor

    compressor = PromptCompressor(
        model_name=str(payload["model"]),
        device_map="cpu",
        model_config={"local_files_only": True, "trust_remote_code": False},
        use_llmlingua2=True,
    )
    result = compressor.compress_prompt(
        [str(value) for value in payload["context"]],
        question=str(payload.get("question", "")),
        target_token=int(payload["target_token"]),
        force_reserve_digit=True,
        concate_question=False,
        strict_preserve_uncompressed=True,
    )
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
