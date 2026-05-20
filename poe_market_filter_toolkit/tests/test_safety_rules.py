import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compare_current_to_target as compare
import generate_dashboard
import plan_upgrade_path
import recommend_next_steps as recommend
import run_build_matrix
import switch_build


class SafetyRulesTest(unittest.TestCase):
    def test_guarded_slots_are_reported(self):
        player_items = json.loads((ROOT / "builds" / "player_items.json").read_text(encoding="utf-8"))
        rules = json.loads((ROOT / "builds" / "upgrade_rules.json").read_text(encoding="utf-8"))

        guarded = compare.guarded_slots(player_items, rules)

        self.assertIn("body_armour", guarded)
        self.assertIn("gloves", guarded)
        self.assertIn("The Brass Dome", guarded["body_armour"])
        self.assertIn("Death Knuckle", guarded["gloves"])

    def test_strength_is_not_scored_as_life_with_brass_dome(self):
        rules = json.loads((ROOT / "builds" / "upgrade_rules.json").read_text(encoding="utf-8"))
        weights = rules.get("weights", {})

        self.assertNotIn("strength", weights)
        self.assertNotIn("strength_as_life", weights)

    def test_high_priority_searches_sort_before_medium(self):
        gap = {
            "risks": {
                "spell_block": {"current": 17, "goal": 30, "status": "needs_improvement", "missing_to_goal": 13},
                "life": {"current": 3410, "goal": 3800, "status": "needs_improvement", "missing_to_goal": 390},
            },
            "current_priorities": {
                "spell_block": "high",
                "life": "high",
            },
        }

        entries = recommend.search_entries(gap)

        self.assertEqual(entries[0]["stat"], "life")

    def test_accuracy_is_downgraded_when_already_near_cap(self):
        gap = {
            "risks": {
                "chance_to_hit": {"current": 96, "goal": 100, "status": "needs_improvement", "missing_to_goal": 4},
            },
            "current_priorities": {
                "chance_to_hit": "high",
            },
        }

        entries = recommend.search_entries(gap)

        self.assertEqual(entries[0]["priority"], "low")

    def test_dashboard_links_are_relative_to_generated_html(self):
        output = ROOT / "data" / "generated" / "build_dashboard.html"
        target = ROOT / "market" / "reports" / "upgrade_plan.html"

        self.assertEqual(
            generate_dashboard.relative_link(target, output),
            "../../market/reports/upgrade_plan.html",
        )

    def test_budget_is_sampled_across_price_windows(self):
        self.assertEqual(
            plan_upgrade_path.budget_price_windows(1000),
            [(None, 200.0), (200.0, 600.0), (600.0, 1000.0)],
        )

    def test_dashboard_builds_exact_trade_link_from_result_id(self):
        html = generate_dashboard.trade_actions(
            {
                "trade_search_url": "https://www.pathofexile.com/trade/search/Mirage/abc123",
                "result_id": "deadbeef",
                "trade_fetch_url": "https://www.pathofexile.com/api/trade/fetch/deadbeef?query=abc123",
            }
        )

        self.assertIn("https://www.pathofexile.com/trade/search/Mirage/abc123/deadbeef", html)
        self.assertIn("Item exato", html)
        self.assertIn("Busca original", html)

    def test_build_switcher_detects_pobb_links(self):
        detected = switch_build.detect_pob_reference("https://pobb.in/abc-123_X")

        self.assertEqual(detected["kind"], "pobb.in")
        self.assertEqual(detected["id"], "abc-123_X")

    def test_build_switcher_slugifies_names(self):
        self.assertEqual(
            switch_build.slugify("Shockwave Cyclone / General's Cry Slayer"),
            "shockwave_cyclone_general_s_cry_slayer",
        )

    def test_build_matrix_localizes_global_html_links(self):
        content = (
            '<a href="../../data/generated/build_dashboard.html">Dashboard</a>'
            '<a href="../../market/reports/upgrade_plan.html">Plano</a>'
        )

        localized = run_build_matrix.localize_global_links(content)

        self.assertIn('href="build_dashboard.html"', localized)
        self.assertIn('href="upgrade_plan.html"', localized)
        self.assertNotIn("../../data/generated", localized)
        self.assertNotIn("../../market/reports", localized)

    def test_build_matrix_switcher_preserves_current_page(self):
        rows = [
            {"slug": "build_a", "name": "Build A"},
            {"slug": "build_b", "name": "Build B"},
        ]

        switcher = run_build_matrix.build_switcher("build_a", "next_searches.html", rows)

        self.assertIn('data-page="next_searches.html"', switcher)
        self.assertIn('<option value="build_a" selected>', switcher)
        self.assertIn('<option value="build_b">', switcher)


if __name__ == "__main__":
    unittest.main()
