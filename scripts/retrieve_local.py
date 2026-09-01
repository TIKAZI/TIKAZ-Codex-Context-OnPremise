from __future__ import annotations

import argparse
import json
from pathlib import Path


def _dot(left, right):
    return sum(float(a) * float(b) for a, b in zip(left, right))


def _rank_many(requests, embedding, reranker):
    sentences = []
    layouts = []
    for request in requests:
        chunks = request["chunks"]
        query = str(request["query"])
        texts = [str(chunk["text"]) for chunk in chunks]
        query_index = len(sentences)
        sentences.append(query)
        chunk_start = len(sentences)
        sentences.extend(texts)
        layouts.append((chunks, query, texts, query_index, chunk_start))

    vectors = embedding.encode(sentences, normalize_embeddings=True)
    dense_orders = []
    all_pairs = []
    for chunks, query, texts, query_index, chunk_start in layouts:
        query_vector = vectors[query_index]
        dense_scores = [
            _dot(vectors[chunk_start + index], query_vector)
            for index in range(len(chunks))
        ]
        dense_order = sorted(
            range(len(chunks)), key=lambda index: (-dense_scores[index], index)
        )
        dense_orders.append((dense_scores, dense_order))
        all_pairs.extend((query, texts[index]) for index in dense_order)

    all_rerank_scores = reranker.predict(all_pairs)
    results = []
    score_offset = 0
    for (chunks, _query, _texts, _query_index, _chunk_start), (dense_scores, dense_order) in zip(layouts, dense_orders):
        rerank_scores = all_rerank_scores[score_offset : score_offset + len(dense_order)]
        score_offset += len(dense_order)
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
        results.append({"ranked": scored})
    return results


def _rank(request, embedding, reranker):
    return _rank_many([request], embedding, reranker)[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))

    from sentence_transformers import CrossEncoder, SentenceTransformer

    embedding = SentenceTransformer(
        str(payload["embedding_model"]), device="cpu", local_files_only=True
    )
    reranker = CrossEncoder(
        str(payload["reranker_model"]),
        device="cpu",
        local_files_only=True,
        trust_remote_code=False,
    )
    requests = payload.get("requests")
    response = (
        {"results": _rank_many(requests, embedding, reranker)}
        if isinstance(requests, list)
        else _rank(payload, embedding, reranker)
    )
    args.output.write_text(
        json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
