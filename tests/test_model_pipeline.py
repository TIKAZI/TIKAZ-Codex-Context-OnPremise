import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from token_forge.model_pipeline import optimize_text_pack, rank_local_chunks


class ModelPipelineTests(unittest.TestCase):
    def test_local_ranker_returns_validated_hybrid_order(self):
        chunks = [
            {"id": "a", "index": 0, "text": "decorative launch copy"},
            {"id": "b", "index": 1, "text": "database rollback evidence"},
        ]
        with patch("token_forge.model_pipeline._run_helper", return_value={"ranked": [
            {"id": "b", "index": 1, "rerank_score": 4.0},
            {"id": "a", "index": 0, "rerank_score": 1.0},
        ]}):
            ranked = rank_local_chunks(chunks, "database rollback", self.adapters)
        self.assertEqual(ranked[0]["id"], "b")
        self.assertEqual(ranked[0]["strategy"], "hybrid-rrf-mmr")
    def test_high_risk_python_uses_deterministic_ast_route_without_model_helpers(self):
        filler = "\n\n".join(
            f"def unrelated_{index}():\n    return 'noise'" for index in range(50)
        )
        source = f'''API_URL = "https://api.example.com/v1"

def deploy(client):
    return client.post(API_URL)

{filler}
'''
        result = optimize_text_pack(
            source,
            "review deployment",
            100,
            adapters={},
            safety_class="code",
        )
        self.assertEqual(result.mode, "code-sliced")
        self.assertEqual(result.evidence["selection_method"], "python-ast-dependency-closure")

    def setUp(self) -> None:
        self.adapters = {
            "retrieval_python": "G:/envs/retrieval/python.exe",
            "llmlingua_python": "G:/envs/llmlingua/python.exe",
            "embedding_model": "G:/models/bge-m3",
            "reranker_model": "G:/models/bge-reranker-v2-m3",
            "llmlingua_model": "G:/models/llmlingua-2",
        }

    def test_high_risk_source_never_invokes_model_helpers(self) -> None:
        source = "command,value\n`Remove-Item`,250000.00\n" * 20
        with patch("token_forge.model_pipeline._run_helper") as helper:
            result = optimize_text_pack(
                source, "summarize", 20, self.adapters, safety_class="table"
            )
        helper.assert_not_called()
        self.assertEqual(result.mode, "safety-pass-through")
        self.assertEqual(result.text, source)

    def test_dense_and_reranked_chunks_use_deterministic_ids(self) -> None:
        source = (
            "# Release\nVersion v2.4.1 ships on 2026-09-01.\n\n"
            "# Decoration\nThis paragraph is decorative filler only.\n\n"
            "# Migration\nRun `python migrate.py --target v2.4.1` after backup.\n\n"
            "# More\nAdditional prose for the release migration checklist."
        )

        def fake_helper(_python, script, payload, _timeout):
            if script.name == "retrieve_local.py":
                chunks = payload.get("chunks") or payload["requests"][0]["chunks"]
                return {
                    "ranked": [
                        {"id": chunks[2]["id"], "index": 2, "dense_score": 0.8, "rerank_score": 4.2},
                        {"id": chunks[3]["id"], "index": 3, "dense_score": 0.7, "rerank_score": 3.5},
                    ]
                }
            return {"compressed_prompt": payload["context"][0]}

        with tempfile.TemporaryDirectory() as temp:
            with patch("token_forge.model_pipeline._run_helper", side_effect=fake_helper):
                first = optimize_text_pack(
                    source, "release migration", 60, self.adapters, output_dir=Path(temp)
                )
                second = optimize_text_pack(source, "release migration", 60, self.adapters)

            self.assertEqual(first.chunk_ids, second.chunk_ids)
            self.assertTrue(all(len(chunk_id) == 16 for chunk_id in first.chunk_ids))
            self.assertIn("python migrate.py --target v2.4.1", first.text)
            self.assertEqual(first.protected_recall, 1.0)
            self.assertTrue((Path(temp) / "model-ledger.json").is_file())
            self.assertIn("query_coverage", first.evidence)
            self.assertEqual(first.evidence["retrieval_strategy"], "hybrid-rrf-mmr")

    def test_learned_compression_never_receives_protected_blocks(self) -> None:
        source = (
            "Release v3.2.1 is scheduled for 2026-09-01.\n\n"
            "Migration prose describes validation and rollback steps.\n\n"
            "More explanatory prose for operators and maintainers."
        )

        compression_payloads = []

        def fake_helper(_python, script, payload, _timeout):
            if script.name == "retrieve_local.py":
                chunks = payload.get("chunks") or payload["requests"][0]["chunks"]
                return {"ranked": chunks}
            compression_payloads.append(payload)
            return {"compressed_prompt": "Migration rollback steps for maintainers."}

        with patch("token_forge.model_pipeline._run_helper", side_effect=fake_helper):
            result = optimize_text_pack(source, "migration", 25, self.adapters)

        self.assertEqual(result.mode, "learned-compressed")
        self.assertIn("v3.2.1", result.text)
        self.assertIn("2026-09-01", result.text)
        self.assertEqual(result.protected_recall, 1.0)
        self.assertLessEqual(result.final_tokens, 25)
        self.assertEqual(len(compression_payloads), 1)
        compressed_source = compression_payloads[0]["context"][0]
        self.assertNotIn("v3.2.1", compressed_source)
        self.assertNotIn("2026-09-01", compressed_source)
        self.assertLess(compression_payloads[0]["target_token"], 25)

    def test_model_failure_falls_back_to_deterministic_selection(self) -> None:
        source = "# Fact\nUse v4.0.1.\n\n# Noise\nDecorative filler.\n\n# More\nRelease notes."
        with patch("token_forge.model_pipeline._run_helper", side_effect=RuntimeError("offline load failed")):
            result = optimize_text_pack(source, "release", 25, self.adapters)
        self.assertEqual(result.mode, "deterministic-fallback")
        self.assertEqual(result.protected_recall, 1.0)
        self.assertIn("offline load failed", result.fallback_reason)


if __name__ == "__main__":
    unittest.main()
