import unittest

from token_forge.retrieval import (
    build_query_plan,
    expanded_query_terms,
    fuse_and_diversify,
    lexical_rank,
    retrieval_metrics,
    select_evidence,
)


class RetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunks = [
            {"id": "noise-a", "index": 0, "text": "品牌活动使用蓝色主视觉。"},
            {"id": "rollback", "index": 1, "text": "数据库迁移失败时运行回滚脚本 rollback_db.py，并核验 MIGRATION_OK。"},
            {"id": "backup", "index": 2, "text": "执行数据库迁移前必须完成备份并记录 BACKUP_READY。"},
            {"id": "noise-b", "index": 3, "text": "品牌活动的蓝色视觉规范与首页相同。"},
        ]

    def test_lexical_rank_handles_chinese_compound_queries(self):
        ranked = lexical_rank(self.chunks, "数据库迁移回滚证据")
        self.assertEqual(ranked[0]["id"], "rollback")
        self.assertGreater(ranked[0]["lexical_score"], 0)

    def test_query_expansion_exposes_implicit_evidence_facets(self):
        accessibility = set(expanded_query_terms("usable without a mouse and readable on a phone"))
        scanned = set(expanded_query_terms("没有可复制文字的报告怎样保住表格和插图信息"))
        proof = set(expanded_query_terms("keep proof in the smallest useful material"))
        self.assertTrue({"keyboard", "focus", "responsive", "mobile"} <= accessibility)
        self.assertTrue({"ocr", "扫描", "回退", "来源锚点"} <= scanned)
        self.assertTrue({"evidence", "anchor", "omitted", "budget"} <= proof)

    def test_fusion_keeps_distinct_evidence_instead_of_duplicate_noise(self):
        model_ranked = [
            {"id": "rollback", "index": 1, "rerank_score": 8.0},
            {"id": "noise-a", "index": 0, "rerank_score": 7.5},
            {"id": "noise-b", "index": 3, "rerank_score": 7.4},
            {"id": "backup", "index": 2, "rerank_score": 6.0},
        ]
        ranked = fuse_and_diversify(
            self.chunks,
            "数据库迁移回滚和备份证据",
            model_ranked=model_ranked,
        )
        top_three = [item["id"] for item in ranked[:3]]
        self.assertIn("rollback", top_three)
        self.assertIn("backup", top_three)
        self.assertLess(top_three.index("backup"), top_three.index("noise-b") if "noise-b" in top_three else 3)

    def test_semantic_bridge_recovers_certificate_workflow_without_models(self):
        chunks = [
            {"id": "cause", "index": 0, "text": "The gateway certificate expired and TLS handshakes began failing."},
            {"id": "rotate", "index": 1, "text": "Rotate the certificate from the approved secret store."},
            {"id": "restart", "index": 2, "text": "Restart gateway workers so they load the renewed certificate."},
            {"id": "check", "index": 3, "text": "Validate checkout and login through the repaired HTTPS endpoint."},
            {"id": "alert", "index": 4, "text": "Add certificate-expiry monitoring to prevent recurrence."},
            {"id": "machine-noise", "index": 5, "text": "The office coffee machine is serviced monthly."},
            {"id": "identity-noise", "index": 6, "text": "The brand identity manual defines logo spacing."},
            {"id": "traffic-noise", "index": 7, "text": "Marketing traffic increased after the campaign."},
        ]

        ranked = fuse_and_diversify(
            chunks,
            "What should operators do when encrypted traffic stops because machine identity is no longer valid?",
        )

        self.assertEqual(
            set(item["id"] for item in ranked[:5]),
            {"cause", "rotate", "restart", "check", "alert"},
        )

    def test_evidence_facets_suppress_literal_polysemy_noise(self):
        chunks = [
            {"id": "keyboard", "index": 0, "text": "All interactive controls support keyboard navigation."},
            {"id": "focus", "index": 1, "text": "Visible focus indicators show the current control."},
            {"id": "label", "index": 2, "text": "Semantic labels give assistive technology meaningful names."},
            {"id": "mobile", "index": 3, "text": "Responsive breakpoints prevent horizontal overflow on narrow screens."},
            {"id": "type", "index": 4, "text": "Readable typography and contrast remain clear at mobile sizes."},
            {"id": "mouse-noise", "index": 5, "text": "The wireless mouse is available in three colors."},
            {"id": "phone-noise", "index": 6, "text": "The phone campaign launches next month."},
            {"id": "interface-noise", "index": 7, "text": "The audio interface has two input channels."},
        ]

        ranked = fuse_and_diversify(
            chunks, "make the interface usable without a mouse and readable on a phone"
        )

        self.assertEqual(
            set(item["id"] for item in ranked[:5]),
            {"keyboard", "focus", "label", "mobile", "type"},
        )

    def test_query_plan_exposes_separate_evidence_slots(self):
        plan = build_query_plan("prepare the smallest useful material while keeping proof")

        self.assertEqual(
            {facet.name for facet in plan.facets},
            {"task-selection", "source-anchor", "protected-facts", "budget", "omissions"},
        )

    def test_query_plan_rejects_unbounded_caller_variants(self):
        with self.assertRaises(ValueError):
            build_query_plan("release recovery", query_variants=("hint",) * 6)

    def test_dynamic_selection_stops_after_all_evidence_slots_are_covered(self):
        chunks = [
            {"id": "combined", "index": 0, "text": "Backup the database, run rollback_db.py after failure, and verify MIGRATION_OK."},
            {"id": "owner", "index": 1, "text": "The release owner records the verification result."},
            {"id": "duplicate", "index": 2, "text": "A second note repeats rollback_db.py and MIGRATION_OK."},
            {"id": "noise", "index": 3, "text": "The landing page uses a blue background."},
        ]
        query = "database backup rollback verification owner"
        query_variants = ("database backup rollback verification", "release owner")
        ranked = fuse_and_diversify(chunks, query, query_variants=query_variants)

        selection = select_evidence(
            ranked, query, query_variants=query_variants, min_items=1, max_items=5
        )

        self.assertEqual({item["id"] for item in selection.items}, {"combined", "owner"})
        self.assertEqual(selection.status, "matched")
        self.assertEqual(selection.facet_coverage, 1.0)

    def test_dynamic_selection_returns_insufficient_instead_of_filling_with_noise(self):
        chunks = [
            {"id": "visual", "index": 0, "text": "The campaign uses a blue illustration."},
            {"id": "office", "index": 1, "text": "The office closes at six."},
        ]
        query = "database rollback verification"
        ranked = fuse_and_diversify(chunks, query)

        selection = select_evidence(ranked, query, min_items=1, max_items=5)

        self.assertEqual(selection.items, ())
        self.assertEqual(selection.status, "insufficient-evidence")

    def test_metrics_report_recall_precision_mrr_and_ndcg_separately(self):
        metrics = retrieval_metrics(
            ["rollback", "noise-a", "backup"],
            {"rollback": 2, "backup": 1},
            k_values=(1, 3),
        )
        self.assertEqual(metrics["recall_at_1"], 0.5)
        self.assertEqual(metrics["recall_at_3"], 1.0)
        self.assertAlmostEqual(metrics["precision_at_3"], 2 / 3)
        self.assertEqual(metrics["mrr"], 1.0)
        self.assertGreater(metrics["ndcg_at_3"], 0.8)


if __name__ == "__main__":
    unittest.main()
