import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "web" / "map-viewer" / "index.html"
ANALYSIS = ROOT / "web" / "map-viewer" / "assets" / "analysis-results.json"
AUDIT = ROOT / "web" / "map-viewer" / "assets" / "audit-manifest.json"


class ViewerContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = HTML.read_text(encoding="utf-8")
        cls.analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
        cls.audit = json.loads(AUDIT.read_text(encoding="utf-8"))

    def test_full_map_and_floating_panel_contract(self):
        self.assertRegex(self.html, r"#workspace\s*\{[^}]*inset:64px 0 96px")
        self.assertRegex(self.html, r"#map-viewport\s*\{[^}]*inset:0")
        self.assertIn('id="collapse-tree"', self.html)
        self.assertIn("#toolbar.collapsed", self.html)
        self.assertIn("#details.collapsed", self.html)

    def test_map_style_and_scenario_controls_are_explicit(self):
        for control in ("map-satellite", "map-standard", "layer-terrain", "collapse-tree"):
            self.assertIn(f'id="{control}"', self.html)
        self.assertIn('value="normal"', self.html)
        self.assertIn('value="source-outage"', self.html)
        self.assertIn('value="storage-depleted"', self.html)
        self.assertIn("setMapStyle('standard')", self.html)
        self.assertIn("scenarioId", self.html)
        self.assertIn("tile.openstreetmap.org", self.html)
        self.assertIn("OpenStreetMap contributors", self.html)

    def test_map_click_focuses_and_exposes_selection_state(self):
        self.assertIn("if (hit) focusObject(byId.get(hit.object.userData.viewerId));", self.html)
        self.assertIn("viewport.dataset.selectedId = item.id", self.html)
        self.assertIn("viewport.dataset.focusedId = item.id", self.html)

    def test_map_actions_clear_right_panel_hit_area(self):
        self.assertRegex(self.html, r"#map-actions\s*\{[^}]*margin-right:340px")
        self.assertIn("document.getElementById('reset').addEventListener('click', resetView)", self.html)

    def test_reset_clears_selection_and_focus_contract(self):
        reset_start = self.html.index("function resetView")
        reset_end = self.html.index("function makeLocationList", reset_start)
        reset_body = self.html[reset_start:reset_end]
        for expression in (
            "selected = null",
            "restoreSelectionHighlight()",
            "selectionChip.textContent = 'overview'",
            "delete viewport.dataset.selectedId",
            "delete viewport.dataset.focusedId",
            "detailTitle.textContent = '对象详情'",
        ):
            self.assertIn(expression, reset_body)

    def test_analysis_asset_has_two_solver_scenarios_and_derived_boundary(self):
        self.assertEqual(self.analysis["basis"], "synthetic teaching, no local operational validation")
        self.assertEqual(set(self.analysis["summary"]), {"MVP_NORMAL", "MVP_SOURCE_OUTAGE"})
        self.assertEqual(len(self.analysis["rows"]), 48)
        outage = [row for row in self.analysis["rows"] if row["scenario_id"] == "MVP_SOURCE_OUTAGE"]
        first_depleted = next(row["hour_index"] for row in outage if row["storage_end_mwh"] <= 0)
        self.assertEqual(first_depleted, 5)
        self.assertIn("不是新的热力求解", self.html)

    def test_tree_selection_shows_details_before_focus(self):
        focus_start = self.html.index("function focusObject")
        focus_end = self.html.index("function resetView", focus_start)
        focus_body = self.html[focus_start:focus_end]
        self.assertLess(focus_body.index("showDetails(item)"), focus_body.index("const obj = objectById.get(item.id)"))

    def test_audit_surface_has_traceable_sources_and_limits(self):
        self.assertIn('id="audit-toggle"', self.html)
        self.assertIn('id="audit-panel"', self.html)
        self.assertIn("audit-manifest.json", self.html)
        self.assertEqual(self.audit["web_model"]["pickable_objects"], 59)
        self.assertEqual(self.audit["blender"]["version"], "5.2.1 LTS")
        self.assertEqual(len(self.audit["limitations"]), 3)
        self.assertIn("未接入 Google Maps API key", self.audit["limitations"][-1])


if __name__ == "__main__":
    unittest.main()
