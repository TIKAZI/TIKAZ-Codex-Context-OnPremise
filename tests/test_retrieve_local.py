import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "retrieve_local.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("retrieve_local", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class FakeEmbedding:
    def __init__(self) -> None:
        self.calls = 0

    def encode(self, texts, normalize_embeddings=True):
        self.calls += 1
        return [[float(len(text)), 1.0] for text in texts]


class FakeReranker:
    def __init__(self) -> None:
        self.calls = 0

    def predict(self, pairs):
        self.calls += 1
        return [float(len(text)) for _, text in pairs]


class RetrieveLocalBatchTests(unittest.TestCase):
    def test_batch_encodes_and_reranks_all_requests_once(self) -> None:
        helper = load_helper()
        embedding = FakeEmbedding()
        reranker = FakeReranker()
        requests = [
            {"query": "q1", "chunks": [{"id": "a", "index": 0, "text": "x"}, {"id": "b", "index": 1, "text": "long"}]},
            {"query": "q2", "chunks": [{"id": "c", "index": 0, "text": "mid"}, {"id": "d", "index": 1, "text": "longest"}]},
        ]

        results = helper._rank_many(requests, embedding, reranker)

        self.assertEqual(embedding.calls, 1)
        self.assertEqual(reranker.calls, 1)
        self.assertEqual([[item["id"] for item in result["ranked"]] for result in results], [["b", "a"], ["d", "c"]])


if __name__ == "__main__":
    unittest.main()
