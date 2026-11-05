#!/usr/bin/env python3
"""
AV1 Encoder Pro - ERA Bounded Parameter Search
Based on Flat UCT / PUCT tree search from Google Research ERA (futs.py).

Explores SVT-AV1 parameter space (preset, CRF, tune, film grain) optimizing
a multi-objective balance of visual quality (SSIM/VMAF), file size, and encode speed.
"""
import os
import sys
import time
import math
import re
import random
import argparse
import tempfile
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

import av1core


@dataclass
class Candidate:
    preset: int
    crf: int
    tune: int = 0
    grain: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "preset": self.preset,
            "crf": self.crf,
            "tune": self.tune,
            "grain": self.grain,
        }

    def key(self) -> str:
        return f"p{self.preset}_crf{self.crf}_t{self.tune}_g{self.grain}"


@dataclass
class SearchNode:
    candidate: Candidate
    prior: float = 1.0
    visit_count: int = 0
    raw_score: Optional[float] = None
    rank_score: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)


class FlatPUCTSearch:
    """Flat tree search with PUCT selection and rank normalization."""

    def __init__(self, candidates: List[Candidate], c_puct: float = 1.414):
        self.c_puct = c_puct
        self.nodes: List[SearchNode] = [
            SearchNode(candidate=c, prior=1.0 / len(candidates))
            for c in candidates
        ]

    def select(self) -> SearchNode:
        """Select next node via PUCT."""
        # Prioritize unvisited nodes first
        unvisited = [n for n in self.nodes if n.visit_count == 0]
        if unvisited:
            return random.choice(unvisited)

        total_visits = sum(n.visit_count for n in self.nodes)
        sqrt_total = math.sqrt(total_visits)

        best_score = -float("inf")
        best_node = self.nodes[0]

        for node in self.nodes:
            # PUCT formula with normalized rank score
            exploration = self.c_puct * node.prior * (sqrt_total / (1 + node.visit_count))
            u_score = node.rank_score + exploration
            if u_score > best_score:
                best_score = u_score
                best_node = node

        return best_node

    def update(self, node: SearchNode, raw_score: float, metrics: Dict[str, Any]):
        """Backpropagate evaluation result and update relative ranks."""
        node.visit_count += 1
        node.raw_score = raw_score
        node.metrics = metrics
        self._update_ranks()

    def _update_ranks(self):
        """Normalize raw scores into [0, 1] percentiles (rank/(n-1))."""
        evaluated = [n for n in self.nodes if n.raw_score is not None]
        if not evaluated:
            return
        if len(evaluated) == 1:
            evaluated[0].rank_score = 1.0
            return

        evaluated.sort(key=lambda n: n.raw_score)
        n = len(evaluated)
        for rank, node in enumerate(evaluated):
            node.rank_score = rank / (n - 1)

    def best_node(self) -> Optional[SearchNode]:
        """Return candidate with highest raw score."""
        evaluated = [n for n in self.nodes if n.raw_score is not None]
        if not evaluated:
            return None
        return max(evaluated, key=lambda n: n.raw_score)


def generate_search_space() -> List[Candidate]:
    """Generate bounded parameter grid for SVT-AV1."""
    presets = [4, 6, 8, 10]
    crfs = [24, 28, 32, 36, 40]
    tunes = [0, 1]  # 0=VQ, 1=PSNR
    grains = [0, 8, 16]

    candidates = []
    for p in presets:
        for c in crfs:
            for t in tunes:
                for g in grains:
                    candidates.append(Candidate(preset=p, crf=c, tune=t, grain=g))
    return candidates


def measure_ssim(encoded_path: str, reference_path: str, ffmpeg_path: str = "ffmpeg") -> float:
    """Calculate SSIM score between encoded video and source reference."""
    cmd = [
        ffmpeg_path, "-v", "info",
        "-i", encoded_path,
        "-i", reference_path,
        "-filter_complex", "ssim",
        "-f", "null", "-"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    # Output pattern: All:0.994803 (22.842791)
    match = re.search(r"All:([0-9.]+)", res.stderr + res.stdout)
    if match:
        return float(match.group(1))
    return 0.0


def evaluate_candidate(reference_video: str, candidate: Candidate,
                       metric: str = "ssim", weight_quality: float = 1.0,
                       weight_bitrate: float = 0.5, weight_speed: float = 0.2,
                       ffmpeg_path: str = None) -> Tuple[float, Dict[str, Any]]:
    """
    Encode candidate against reference and score quality, compression, and speed.
    """
    if ffmpeg_path is None:
        ffmpeg_path = av1core.get_ffmpeg_path()

    ref_size = os.path.getsize(reference_video)
    ref_dur = av1core.probe_video_duration(reference_video) or 1.0

    with tempfile.TemporaryDirectory() as tmpdir:
        cand_out = os.path.join(tmpdir, f"cand_{candidate.key()}.webm")
        cmd, _ = av1core.build_ffmpeg_command(
            input_path=reference_video,
            output_path=cand_out,
            quality=int(round((63 - candidate.crf) / 0.63)),
            preset=candidate.preset,
            encoder="libsvtav1",
            audio_codec="none",
            tune=candidate.tune,
            grain=candidate.grain,
            ffmpeg_path=ffmpeg_path
        )

        start_time = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        encode_time = max(0.001, time.perf_counter() - start_time)

        if proc.returncode != 0 or not os.path.exists(cand_out):
            return -100.0, {"error": f"Encode failed with exit code {proc.returncode}"}

        cand_size = os.path.getsize(cand_out)
        compression_ratio = cand_size / max(1, ref_size)
        fps = ref_dur / encode_time

        # Calculate quality metric
        if metric == "ssim":
            q_score = measure_ssim(cand_out, reference_video, ffmpeg_path=ffmpeg_path)
        else:
            q_score = 0.8  # Fallback dummy

        # Multi-objective composite score
        # High quality +, Lower relative size +, Higher speed +
        raw_score = (
            weight_quality * (q_score * 100.0)
            - weight_bitrate * (compression_ratio * 100.0)
            + weight_speed * min(50.0, fps * 10.0)
        )

        metrics = {
            "quality": q_score,
            "size_bytes": cand_size,
            "compression_ratio": compression_ratio,
            "encode_time_sec": encode_time,
            "fps": fps,
            "raw_score": raw_score,
        }
        return raw_score, metrics


def run_search(reference_video: str, budget_iterations: int = 10,
               metric: str = "ssim", c_puct: float = 1.414) -> Optional[SearchNode]:
    """Execute bounded ERA parameter search."""
    space = generate_search_space()
    searcher = FlatPUCTSearch(space, c_puct=c_puct)

    print(f"[ERA SEARCH] Initialized search space of {len(space)} candidate parameter sets.")
    print(f"[ERA SEARCH] Reference clip: {reference_video} (Budget: {budget_iterations} iterations, Metric: {metric})")

    for i in range(budget_iterations):
        node = searcher.select()
        c = node.candidate
        print(f"\n[ITERATION {i+1}/{budget_iterations}] Testing candidate: preset={c.preset}, crf={c.crf}, tune={c.tune}, grain={c.grain}")
        score, metrics = evaluate_candidate(reference_video, c, metric=metric)
        searcher.update(node, score, metrics)

        if "error" in metrics:
            print(f"  [FAIL] Failed: {metrics['error']}")
        else:
            print(f"  [OK] Quality ({metric}): {metrics['quality']:.4f} | Size: {metrics['size_bytes']/1024:.1f} KB ({metrics['compression_ratio']*100:.1f}%) | Time: {metrics['encode_time_sec']:.2f}s | Score: {score:.2f}")

    best = searcher.best_node()
    if best:
        print("\n" + "=" * 60)
        print("[ERA SEARCH COMPLETE] Optimal SVT-AV1 Candidate:")
        print(f"  * Preset: {best.candidate.preset}")
        print(f"  * CRF: {best.candidate.crf}")
        print(f"  * Tune: {best.candidate.tune}")
        print(f"  * Film Grain: {best.candidate.grain}")
        print(f"  * Score: {best.raw_score:.2f}")
        if best.metrics:
            print(f"  * {metric.upper()}: {best.metrics.get('quality', 0):.4f}")
            print(f"  * Size: {best.metrics.get('size_bytes', 0)/1024:.1f} KB")
            print(f"  * Encode Time: {best.metrics.get('encode_time_sec', 0):.2f}s")
        print("=" * 60)
    return best


def main():
    parser = argparse.ArgumentParser(description="ERA Bounded Parameter Search for SVT-AV1")
    parser.add_argument("-i", "--input", required=True, help="Path to reference video sample")
    parser.add_argument("-b", "--budget", type=int, default=10, help="Iteration budget (default: 10)")
    parser.add_argument("-m", "--metric", choices=["ssim"], default="ssim", help="Quality metric (default: ssim)")
    parser.add_argument("--puct", type=float, default=1.414, help="PUCT exploration constant (default: 1.414)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[ERROR] Reference file not found: {args.input}")
        sys.exit(1)

    run_search(args.input, budget_iterations=args.budget, metric=args.metric, c_puct=args.puct)


if __name__ == "__main__":
    main()
