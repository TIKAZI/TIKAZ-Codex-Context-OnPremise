# Output contract

A context pack must contain:

- task and declared budget;
- source hashes and stable anchors;
- selected text and protected literals;
- omitted evidence with reasons;
- unresolved visual, table, OCR, or media work;
- adapter names, versions, timings, and errors;
- cache key and whether the result was a verified persistent-cache hit;
- raw, canonical, selected, compressed, and final token counts kept separate;
- fidelity checks and explicit pass-through or failure state.
- conversion verification level (`source-literal` or `output-only`) and nullable protected-literal recall when the source cannot be independently extracted.
- an explicit `needs-ocr` source-preservation state when a PDF has no extractable text and no eligible local OCR adapter.
- a `visual-evidence.json` ledger for video keyframes, with full frame hashes, scene/sample anchors, selection status, semantic status, duplicate provenance, and observations.

Keep visual accounting separate: source frames, unique frames, selected frames, exact duplicates, deferred frames, pending frames, and resolved frames are not image-token counts. A resolved observation must reference a selected frame's full SHA-256 digest. Decorative or perceptual-duplicate status remains unknown unless a declared detector and labeled fixture measured it.
