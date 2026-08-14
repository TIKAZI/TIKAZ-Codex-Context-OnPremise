# Dependency routing matrix

| Source or stage | Primary | Fallback | Default gate |
|---|---|---|---|
| Simple Office/PDF | MarkItDown | Docling | headings, text and declared facts survive |
| Structured/table PDF | Docling | MinerU | reading order and table cells survive |
| Chinese/math/complex PDF | MinerU | source preservation | formulas, CJK and anchors survive |
| Scan/image text | PaddleOCR or MinerU | source preservation | OCR confidence and literal checks pass |
| Static webpage | Defuddle | Readability | main-content density and links pass |
| Dynamic webpage | Playwright + Defuddle | source HTML | rendered content is non-empty |
| Video/audio | existing faster-whisper float16 | platform subtitles | timestamped transcript exists |
| Keyframes | PySceneDetect + FFmpeg | bounded interval frames | scene and OCR coverage pass |
| Retrieval | BM25 + BGE-M3 | BM25 | fixed-query recall passes |
| Reranking | domain-tested BGE reranker | fused retrieval order | no domain regression |
| Prose compression | LLMLingua-2 | extractive selection/pass-through | facts, anchors and grounding pass |

Dependencies are installed into isolated G-drive environments after their profile passes the fixed benchmark. The repository stores adapters and version manifests, not environments or model weights.

