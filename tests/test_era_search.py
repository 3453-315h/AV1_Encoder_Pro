import os
import unittest
import tempfile
import subprocess

from era_search import Candidate, SearchNode, FlatPUCTSearch, generate_search_space, run_search


class TestPUCTTreeSearch(unittest.TestCase):
    def test_puct_selection_and_rank_update(self):
        candidates = [
            Candidate(preset=6, crf=30),
            Candidate(preset=8, crf=35),
            Candidate(preset=10, crf=40),
        ]
        searcher = FlatPUCTSearch(candidates, c_puct=1.0)

        # Select and update each candidate
        node1 = searcher.select()
        searcher.update(node1, raw_score=50.0, metrics={"quality": 0.90})

        node2 = searcher.select()
        searcher.update(node2, raw_score=80.0, metrics={"quality": 0.95})

        node3 = searcher.select()
        searcher.update(node3, raw_score=20.0, metrics={"quality": 0.85})

        selected = [node1.candidate, node2.candidate, node3.candidate]
        self.assertEqual(len(set(c.key() for c in selected)), 3)

        # Node with highest raw score (80.0) must have rank 1.0, lowest (20.0) rank 0.0, middle rank 0.5
        eval_nodes = sorted(searcher.nodes, key=lambda n: n.raw_score)
        self.assertAlmostEqual(eval_nodes[0].rank_score, 0.0)
        self.assertAlmostEqual(eval_nodes[1].rank_score, 0.5)
        self.assertAlmostEqual(eval_nodes[2].rank_score, 1.0)

        # Best node should be the one with raw_score=80.0
        best = searcher.best_node()
        self.assertIsNotNone(best)
        self.assertEqual(best.raw_score, 80.0)

    def test_generate_search_space(self):
        space = generate_search_space()
        self.assertGreater(len(space), 10)
        # All candidates must have valid presets and CRFs
        for c in space:
            self.assertIn(c.preset, [4, 6, 8, 10])
            self.assertIn(c.crf, [24, 28, 32, 36, 40])


class TestERASearchIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.ref_path = os.path.join(cls.tmpdir.name, "ref_era.mp4")
        gen_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=160x120:rate=10",
            "-c:v", "libx264",
            cls.ref_path
        ]
        res = subprocess.run(gen_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode != 0:
            raise unittest.SkipTest("ffmpeg unable to generate reference test video")

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def test_run_search_smoke(self):
        """Smoke test run_search on small clip with budget=2."""
        best = run_search(self.ref_path, budget_iterations=2, metric="ssim")
        self.assertIsNotNone(best)
        self.assertIsNotNone(best.raw_score)
        self.assertIn("quality", best.metrics)
        self.assertGreater(best.metrics["quality"], 0.80)


if __name__ == "__main__":
    unittest.main()
