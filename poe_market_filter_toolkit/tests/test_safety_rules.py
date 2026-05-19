import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compare_current_to_target as compare
import recommend_next_steps as recommend


class SafetyRulesTest(unittest.TestCase):
    def test_locked_slots_are_reported(self):
        player_items = json.loads((ROOT / "builds" / "player_items.json").read_text(encoding="utf-8"))
        rules = json.loads((ROOT / "builds" / "upgrade_rules.json").read_text(encoding="utf-8"))

        protected = compare.protected_slots(player_items, rules)

        self.assertIn("body_armour", protected)
        self.assertIn("gloves", protected)
        self.assertIn("The Brass Dome", protected["body_armour"])
        self.assertIn("Death Knuckle", protected["gloves"])

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


if __name__ == "__main__":
    unittest.main()
