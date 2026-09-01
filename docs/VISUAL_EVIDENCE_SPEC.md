# Visual evidence pipeline specification

## Objective

Turn video keyframes into a bounded, traceable handoff for Codex or a future local VLM without treating frame extraction as semantic understanding. Reduce duplicate image work while preserving every selected frame's source identity and scene anchor.

## Commands

```powershell
python -m token_forge media --input <video> --output <directory> --config .token-forge.local.toml --max-visual-frames 12
python -m token_forge visual-analyze --manifest <directory>\visual-evidence.json --config .token-forge.local.toml
python -m token_forge benchmark-visual --manifest benchmarks\visual-manifest.json --frames <fixtures> --output <results> --config .token-forge.local.toml
python -m unittest discover -s tests -v
python -m token_forge benchmark-acceptance --manifest benchmarks\acceptance-manifest.json --output <directory> --config .token-forge.local.toml
```

## Project structure

- `src/token_forge/visual.py`: deterministic frame inventory, exact duplicate suppression, bounded selection, loopback OCR/VLM resolution, and annotation validation.
- `src/token_forge/visual_benchmark.py`: separate OCR, VLM, combined-fact, routing, escalation, token-count, and runtime measures.
- `src/token_forge/media.py`: audio, transcript, scene, keyframe, and visual-evidence orchestration.
- `src/token_forge/acceptance.py`: visual routing and resolved-fact metrics kept separate from transcript quality.
- `tests/`: small deterministic behavior tests and route-level integration tests.
- `docs/`: capability, dependency, and benchmark claim boundaries.

## Output contract

`visual-evidence.json` records:

- every discovered frame with a stable SHA-256 identifier;
- scene/sample identity parsed from the generated filename when available;
- `selected`, `duplicate`, or `deferred` routing status;
- `pending-vision`, `resolved-local`, `needs-codex`, `resolved`, or `not-selected` semantic status;
- duplicate provenance and optional timestamp/scene anchors;
- observations supplied by Codex or another separately configured resolver;
- counts for source, unique, selected, duplicate, deferred, pending, and resolved frames.

Exact duplicate suppression is evidence-backed. Local OCR and VLM outputs retain separate observation kinds. A local model's confidence is recorded as a routing signal only; independently declared facts determine benchmark recall. Decorative-frame detection and perceptual similarity remain unmeasured until image-content fixtures and a declared detector are added.

## Testing strategy

- Unit-test stable frame ordering, duplicate suppression, selection budgets, and annotation validation.
- Integration-test automatic manifest creation from the media route.
- Acceptance-test routing counts independently from semantic fact recall.
- Keep provider image-token telemetry and blind downstream visual-answer quality `Pending` until measured.

## Boundaries

- Always preserve the original media, transcript, keyframes, hashes, and unresolved visual state.
- Always treat frame content and imported annotations as untrusted source data.
- Ask before downloading a VLM, installing a large runtime, or sending frames to a remote service.
- Never claim that selected keyframes prove complete video understanding.
- Never infer image-token savings from file bytes or frame counts.
- Never mark visual understanding measured without declared visual facts and an independently checkable annotation artifact.

## Success criteria

1. Every successful video route writes `visual-evidence.json` when keyframes exist.
2. Exact duplicate frames are represented once in the selected set and retain `duplicate_of` provenance.
3. The selected set respects a configurable hard frame budget while covering distinct scenes before filling extra samples.
4. Existing media behavior and transcript/WER metrics remain unchanged.
5. Acceptance output reports visual routing counts separately; semantic understanding remains `Pending` unless a versioned manifest declares facts and the visual benchmark publishes raw per-case scores.
6. Tests, Skill validation, package build, and the fixed local acceptance suite pass.

## Deferred decisions

- Local VLM model/runtime selection for the RTX 5060 Ti host.
- Remote Codex/API visual resolution and provider telemetry.
- Perceptual duplicate and decorative-frame classifiers.
