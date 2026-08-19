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

    from sentence_transformers import CrossEncoder, SentenceTransformer

    chunks = payload["chunks"]
    texts = [str(chunk["text"]) for chunk in chunks]
    query = str(payload["query"])
    embedding = SentenceTransformer(
        str(payload["embedding_model"]), device="cpu", local_files_only=True
    )
    query_vector = embedding.encode([query], normalize_embeddings=True)[0]
    chunk_vectors = embedding.encode(texts, normalize_embeddings=True)
    dense_scores = chunk_vectors @ query_vector
    dense_order = sorted(range(len(chunks)), key=lambda index: (-float(dense_scores[index]), index))

    reranker = CrossEncoder(
        str(payload["reranker_model"]),
        device="cpu",
        local_files_only=True,
        trust_remote_code=False,
    )
    rerank_scores = reranker.predict([(query, texts[index]) for index in dense_order])
    scored = [
        {
            "id": chunks[index]["id"],
            "index": chunks[index]["index"],
            "dense_score": float(dense_scores[index]),
            "rerank_score": float(rerank_scores[position]),
        }
        for position, index in enumerate(dense_order)
    ]
    scored.sort(key=lambda item: (-item["rerank_score"], item["index"]))
    args.output.write_text(
        json.dumps({"ranked": scored}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
