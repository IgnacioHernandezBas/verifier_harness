"""Tests for verifier.multi_layer_harness."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from verifier.multi_layer_harness import (
    DEFAULT_CONFIG,
    HarnessReport,
    LayerResult,
    MultiLayerHarness,
    Verdict,
    _merge_config,
)


# ---------------------------------------------------------------------------
# Data-structure tests
# ---------------------------------------------------------------------------


class TestLayerResult:
    def test_to_dict_roundtrip(self):
        lr = LayerResult(
            layer="static",
            verdict=Verdict.ACCEPT.value,
            score=0.85,
            details={"sqi": 85},
            findings=[],
            duration_s=1.23,
        )
        d = lr.to_dict()
        assert d["layer"] == "static"
        assert d["verdict"] == "ACCEPT"
        assert d["score"] == 0.85
        assert d["duration_s"] == 1.23

    def test_error_field(self):
        lr = LayerResult(layer="unit_test", verdict="ERROR", error="timeout")
        assert lr.error == "timeout"
        assert lr.to_dict()["error"] == "timeout"


class TestHarnessReport:
    def test_layer_by_name(self):
        r = HarnessReport(instance_id="test-1")
        r.layers.append(LayerResult(layer="static", verdict="ACCEPT"))
        r.layers.append(LayerResult(layer="unit_test", verdict="REJECT"))

        assert r.layer_by_name("static").verdict == "ACCEPT"
        assert r.layer_by_name("unit_test").verdict == "REJECT"
        assert r.layer_by_name("nonexistent") is None

    def test_to_json(self):
        r = HarnessReport(instance_id="test-2", verdict="ACCEPT", reason="ok")
        parsed = json.loads(r.to_json())
        assert parsed["instance_id"] == "test-2"
        assert parsed["verdict"] == "ACCEPT"


# ---------------------------------------------------------------------------
# Config merge
# ---------------------------------------------------------------------------


class TestMergeConfig:
    def test_shallow_merge(self):
        base = {"a": 1, "b": {"x": 10, "y": 20}}
        over = {"b": {"x": 99}}
        merged = _merge_config(base, over)
        assert merged["a"] == 1
        assert merged["b"]["x"] == 99
        assert merged["b"]["y"] == 20

    def test_none_overrides(self):
        base = {"a": 1}
        assert _merge_config(base, None) == {"a": 1}


# ---------------------------------------------------------------------------
# Aggregation policy tests
# ---------------------------------------------------------------------------


class TestAggregation:
    def _harness(self, policy="all_pass"):
        return MultiLayerHarness(config={
            "layers": [],
            "aggregation": {"policy": policy},
        })

    def test_all_pass_accept(self):
        h = self._harness("all_pass")
        layers = [
            LayerResult(layer="static", verdict="ACCEPT"),
            LayerResult(layer="unit_test", verdict="ACCEPT"),
        ]
        verdict, reason = h._aggregate(layers)
        assert verdict == "ACCEPT"

    def test_all_pass_reject(self):
        h = self._harness("all_pass")
        layers = [
            LayerResult(layer="static", verdict="ACCEPT"),
            LayerResult(layer="unit_test", verdict="REJECT"),
        ]
        verdict, _ = h._aggregate(layers)
        assert verdict == "REJECT"

    def test_all_pass_warning(self):
        h = self._harness("all_pass")
        layers = [
            LayerResult(layer="static", verdict="ACCEPT"),
            LayerResult(layer="claim_test", verdict="WARNING"),
        ]
        verdict, _ = h._aggregate(layers)
        assert verdict == "WARNING"

    def test_all_pass_skips_ignored(self):
        h = self._harness("all_pass")
        layers = [
            LayerResult(layer="static", verdict="ACCEPT"),
            LayerResult(layer="claim_test", verdict="SKIP"),
        ]
        verdict, _ = h._aggregate(layers)
        assert verdict == "ACCEPT"

    def test_majority_pass(self):
        h = self._harness("majority")
        layers = [
            LayerResult(layer="static", verdict="ACCEPT"),
            LayerResult(layer="unit_test", verdict="ACCEPT"),
            LayerResult(layer="claim_test", verdict="REJECT"),
        ]
        verdict, _ = h._aggregate(layers)
        assert verdict == "ACCEPT"

    def test_majority_reject(self):
        h = self._harness("majority")
        layers = [
            LayerResult(layer="static", verdict="REJECT"),
            LayerResult(layer="unit_test", verdict="REJECT"),
            LayerResult(layer="claim_test", verdict="ACCEPT"),
        ]
        verdict, _ = h._aggregate(layers)
        assert verdict == "REJECT"

    def test_any_pass_accept(self):
        h = self._harness("any_pass")
        layers = [
            LayerResult(layer="static", verdict="REJECT"),
            LayerResult(layer="unit_test", verdict="ACCEPT"),
        ]
        verdict, _ = h._aggregate(layers)
        assert verdict == "ACCEPT"

    def test_any_pass_reject(self):
        h = self._harness("any_pass")
        layers = [
            LayerResult(layer="static", verdict="REJECT"),
            LayerResult(layer="unit_test", verdict="REJECT"),
        ]
        verdict, _ = h._aggregate(layers)
        assert verdict == "REJECT"

    def test_empty_layers(self):
        h = self._harness("all_pass")
        verdict, _ = h._aggregate([])
        assert verdict == "ERROR"

    def test_all_skipped(self):
        h = self._harness("all_pass")
        layers = [LayerResult(layer="static", verdict="SKIP")]
        verdict, _ = h._aggregate(layers)
        assert verdict == "SKIP"


# ---------------------------------------------------------------------------
# Layer handler tests (with mocked dependencies)
# ---------------------------------------------------------------------------


class TestStaticLayer:
    def test_skip_when_no_repo(self):
        h = MultiLayerHarness(config={"layers": ["static"]})
        lr = h._run_static_layer({"diff": "some diff"})
        assert lr.verdict == "SKIP"
        assert "repo_path" in lr.error

    @patch("verifier.multi_layer_harness.MultiLayerHarness._run_static_layer")
    def test_static_accept_via_run(self, mock_static):
        mock_static.return_value = LayerResult(
            layer="static", verdict="ACCEPT", score=0.9
        )
        h = MultiLayerHarness(config={"layers": ["static"]})
        report = h.run({"instance_id": "test-1", "diff": "diff"})
        assert report.layers[0].verdict == "ACCEPT"


class TestUnitTestLayer:
    def test_skip_when_no_repo(self):
        h = MultiLayerHarness(config={"layers": ["unit_test"]})
        lr = h._run_unit_test_layer({"diff": "some diff"})
        assert lr.verdict == "SKIP"


class TestClaimTestLayer:
    def test_skip_when_no_sample(self):
        h = MultiLayerHarness(config={"layers": ["claim_test"]})
        lr = h._run_claim_test_layer({"diff": "diff"})
        assert lr.verdict == "SKIP"

    def test_skip_when_no_claim_tests_root(self):
        h = MultiLayerHarness(config={"layers": ["claim_test"]})
        lr = h._run_claim_test_layer({"diff": "diff", "sample": {"repo": "x"}})
        assert lr.verdict == "SKIP"


# ---------------------------------------------------------------------------
# Full harness integration (mocked layers)
# ---------------------------------------------------------------------------


class TestHarnessRun:
    def test_all_layers_accept(self):
        h = MultiLayerHarness(config={
            "layers": ["static", "unit_test", "claim_test"],
            "aggregation": {"policy": "all_pass"},
        })
        # Mock all handlers to return ACCEPT
        h._run_static_layer = MagicMock(return_value=LayerResult(layer="static", verdict="ACCEPT", score=0.9))
        h._run_unit_test_layer = MagicMock(return_value=LayerResult(layer="unit_test", verdict="ACCEPT", score=1.0))
        h._run_claim_test_layer = MagicMock(return_value=LayerResult(layer="claim_test", verdict="ACCEPT", score=0.8))

        report = h.run({"instance_id": "test-all", "diff": "..."})

        assert report.verdict == "ACCEPT"
        assert len(report.layers) == 3
        assert report.total_duration_s >= 0

    def test_one_reject_causes_overall_reject(self):
        h = MultiLayerHarness(config={
            "layers": ["static", "unit_test"],
            "aggregation": {"policy": "all_pass"},
        })
        h._run_static_layer = MagicMock(return_value=LayerResult(layer="static", verdict="ACCEPT"))
        h._run_unit_test_layer = MagicMock(return_value=LayerResult(layer="unit_test", verdict="REJECT"))

        report = h.run({"instance_id": "test-rej", "diff": "..."})
        assert report.verdict == "REJECT"

    def test_layer_exception_produces_error(self):
        h = MultiLayerHarness(config={"layers": ["static"]})
        h._run_static_layer = MagicMock(side_effect=RuntimeError("boom"))

        report = h.run({"instance_id": "test-err", "diff": "..."})
        assert report.layers[0].verdict == "ERROR"
        assert "boom" in report.layers[0].error

    def test_unknown_layer_skipped(self):
        h = MultiLayerHarness(config={"layers": ["nonexistent"]})
        report = h.run({"instance_id": "test-unk", "diff": "..."})
        assert len(report.layers) == 0

    def test_selective_layers(self):
        h = MultiLayerHarness(config={"layers": ["static"]})
        h._run_static_layer = MagicMock(return_value=LayerResult(layer="static", verdict="ACCEPT"))

        report = h.run({"instance_id": "test-sel", "diff": "..."})
        assert len(report.layers) == 1
        assert report.layers[0].layer == "static"

    def test_report_json_output(self):
        h = MultiLayerHarness(config={"layers": ["static"]})
        h._run_static_layer = MagicMock(return_value=LayerResult(layer="static", verdict="ACCEPT", score=0.75))

        report = h.run({"instance_id": "test-json", "diff": "..."})
        parsed = json.loads(report.to_json())
        assert parsed["instance_id"] == "test-json"
        assert parsed["verdict"] == "ACCEPT"
        assert len(parsed["layers"]) == 1
        assert parsed["layers"][0]["score"] == 0.75
