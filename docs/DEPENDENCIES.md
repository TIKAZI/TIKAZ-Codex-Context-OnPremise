# Dependency routing matrix

| Source or stage | Primary | Fallback | Default gate |
|---|---|---|---|
| Simple Office/PDF | MarkItDown | Docling | headings, text and declared facts survive |
| Structured/table PDF | Docling | MinerU | reading order and table cells survive |
| Chinese/math/complex PDF | MinerU | source preservation | formulas, CJK and anchors survive |
| Scan/image text | MinerU or a separately verified local OCR entry point | source preservation | OCR confidence and literal checks pass |
| Static webpage | Defuddle | Readability | main-content density and links pass |
| Dynamic webpage | Playwright + Defuddle | source HTML | rendered content is non-empty |
| Video/audio | existing faster-whisper float16 | platform subtitles | timestamped transcript exists |
| Keyframes | PySceneDetect + FFmpeg | bounded interval frames | scene and OCR coverage pass |
| Visual semantics | PP-OCRv5 mobile + Qwen3-VL 8B over loopback Ollama | bounded SHA-256 Codex handoff | selected-frame anchors and declared visual facts pass |
| Retrieval | BM25 + BGE-M3 | BM25 | fixed-query recall passes |
| Reranking | domain-tested BGE reranker | fused retrieval order | no domain regression |
| Prose compression | LLMLingua-2 | extractive selection/pass-through | facts, anchors and grounding pass |
| Legacy Office | LibreOffice headless conversion | source preservation | converted structure and declared facts survive |
| Platform media | official subtitles, platform-specific workflow, yt-dlp | source URL | authorization and transcript checks pass |
| Email/archive | EML/MSG parser, 7-Zip | inventory/source preservation | bounded extraction and path-safety checks pass |

See `FORMAT_MATRIX.md` for extensions and explicit non-universal cases, and `INSTALL_LAYOUT.md` for isolated runtime and cache paths.

Dependencies are installed into isolated G-drive environments after their profile passes the fixed benchmark. The repository stores adapters and version manifests, not environments or model weights.

## Local model provenance

| Purpose | Upstream model | License declared by model card | Pinned revision used for validation |
|---|---|---|---|
| Dense multilingual retrieval | [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) | MIT | `5617a9f61b028005a4858fdac845db406aefb181` |
| Cross-encoder reranking | [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | Apache-2.0 | `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` |
| Low-risk prose compression | [microsoft/llmlingua-2-xlm-roberta-large-meetingbank](https://huggingface.co/microsoft/llmlingua-2-xlm-roberta-large-meetingbank) | MIT | `ebaba9b0e874dadd3003ffcff828e4397e568089` |
| Visual OCR | [PaddleOCR PP-OCRv5](https://github.com/PaddlePaddle/PaddleOCR) | Apache-2.0 | cached `PP-OCRv5_mobile_det` + `PP-OCRv5_mobile_rec` |
| Visual semantics | [Qwen/Qwen3-VL-8B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) | Apache-2.0 | Ollama blob `sha256:ed12a4674d72...` |

These models remain separate third-party works. TIKAZ Context On-Premise owns its routing, evidence gates, adapters, benchmarks, and integration, not the upstream model weights. Recheck the linked model cards before redistributing weights.

Local smoke evidence covers MinerU image/PDF OCR, Playwright Chromium 1234 + Defuddle, FFmpeg + CUDA faster-whisper + PySceneDetect, BGE-M3 retrieval, BGE reranking, guarded LLMLingua-2 compression, and PP-OCRv5 mobile OCR. Qwen3-VL is exposed only through Ollama's loopback API. The runtime follows [Ollama's RTX 50-series support matrix](https://docs.ollama.com/gpu) and [structured chat API](https://docs.ollama.com/api/chat); remote vision remains disabled by default.
