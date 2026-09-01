# Third-party notices

TIKAZ Context On-Premise is designed, integrated, independently implemented, and maintained by **TIKAZ**. It interoperates with optional third-party tools and models but does not claim authorship of them and does not redistribute their model weights.

| Component | Purpose | Upstream | Observed license |
|---|---|---|---|
| MarkItDown | Office/PDF/HTML conversion | https://github.com/microsoft/markitdown | MIT |
| Docling | document conversion | https://github.com/docling-project/docling | MIT |
| MinerU | PDF/OCR pipeline | https://github.com/opendatalab/MinerU | AGPL-3.0 |
| PaddleOCR / PP-OCRv5 | local OCR | https://github.com/PaddlePaddle/PaddleOCR | Apache-2.0 |
| Defuddle | webpage main-content extraction | https://github.com/kepano/defuddle | MIT |
| Playwright | local browser rendering | https://github.com/microsoft/playwright | Apache-2.0 |
| FFmpeg | media conversion | https://ffmpeg.org | LGPL/GPL depending on build |
| faster-whisper | local ASR | https://github.com/SYSTRAN/faster-whisper | MIT |
| PySceneDetect | scene detection | https://github.com/Breakthrough/PySceneDetect | BSD-3-Clause |
| yt-dlp | public metadata/subtitles | https://github.com/yt-dlp/yt-dlp | Unlicense |
| BGE-M3 | multilingual dense retrieval | https://huggingface.co/BAAI/bge-m3 | MIT |
| BGE Reranker v2 M3 | reranking | https://huggingface.co/BAAI/bge-reranker-v2-m3 | Apache-2.0 |
| LLMLingua-2 XLM-R | guarded prose compression | https://huggingface.co/microsoft/llmlingua-2-xlm-roberta-large-meetingbank | MIT |
| Qwen3-VL 8B | local visual semantics | https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct | Apache-2.0 |
| Ollama | loopback model runtime | https://github.com/ollama/ollama | MIT |

Licenses can change between versions. Before redistribution or production deployment, verify the license shipped with the exact binary, package, model revision, and FFmpeg build you use. The project records tested revisions in `docs/DEPENDENCIES.md` where available.
