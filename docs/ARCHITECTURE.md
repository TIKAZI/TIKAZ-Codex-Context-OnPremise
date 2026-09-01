# Architecture decision

## Chosen design: routed local compiler

Token Forge uses a small dependency-free controller and isolated external adapters. It does not import every heavy package into one Python environment and does not run every adapter for every source.

This is preferred over a monolithic RAG platform because it keeps failure boundaries visible, reuses the verified local Whisper environment, and permits converter-by-converter benchmarks. It is preferred over universal learned compression because answer plausibility can remain high while citation grounding collapses.

## Quality-gated routing

```text
profile -> cheapest eligible adapter -> quality gate
                                  pass -> canonical artifact
                                  fail -> stronger adapter or source fallback
canonical artifact -> retrieve -> rerank -> protect -> optional prose compression
```

## GPU policy

The verified host has an NVIDIA GeForce RTX 5060 Ti with 16 GB VRAM. Whisper, OCR, embeddings, reranking, learned compression, and Qwen3-VL are scheduled sequentially by default. Qwen3-VL 8B runs through loopback-only Ollama; the checked runtime reported its full 5,793,780,858-byte allocation in VRAM. PP-OCRv5 text and VLM observations remain separate, and only low-confidence, empty, ambiguous, or failed local visual results escalate to Codex. Existing faster-whisper CUDA float16 remains the ASR baseline because public RTX 50-series reports show INT8 compatibility failures on some CTranslate2/CUDA combinations.
