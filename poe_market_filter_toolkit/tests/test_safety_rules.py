import json
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compare_current_to_target as compare
import analyze_target_build
import generate_dashboard
import plan_upgrade_path
import recommend_next_steps as recommend
import review_filter_strategy
import run_character
import switch_build
import sync_pob
import update_market
import validate_character
from core import target_analysis
from core import validation as core_validation


CHARACTER_DIR = ROOT / "builds" / "characters" / "aron_shockwave_cyclone_slayer"
BUILD_DIR = ROOT / "builds" / "profiles" / "ronarray_shockwave_cyclone_slayer"


def make_candidate(**overrides):
    data = {
        "profile": "test_profile",
        "profile_label": "Test Profile",
        "slot": "ring",
        "name": "Test Item",
        "type_line": "Ruby Ring",
        "price_chaos": 50.0,
        "price_text": "50 chaos",
        "score": 100.0,
        "value_score": 2.0,
        "effects": {"life": 30.0},
        "gains": ["life +30"],
        "warnings": [],
        "seller": "seller",
        "trade_url": "https://www.pathofexile.com/trade/search/Mirage/test",
        "trade_item_url": "https://www.pathofexile.com/trade/search/Mirage/test#item",
        "trade_search_url": "https://www.pathofexile.com/trade/search/Mirage/test",
        "trade_fetch_url": "https://www.pathofexile.com/api/trade/fetch/test",
        "result_id": "result",
        "query_id": "query",
        "whisper": "@seller Hi",
        "item_mods": [],
    }
    data.update(overrides)
    return plan_upgrade_path.Candidate(**data)


def make_plan(**overrides):
    candidate = make_candidate()
    data = {
        "candidates": (candidate,),
        "price_chaos": 50.0,
        "score": 160.0,
        "value_score": 3.2,
        "final_stats": {"life": 3900.0},
        "gains": ["life +30"],
        "warnings": [],
    }
    data.update(overrides)
    return plan_upgrade_path.Plan(**data)


def search_rules(*stats: str) -> dict:
    library = {}
    for stat in stats:
        library[stat] = {
            "title": f"{stat} search",
            "priority": "alta",
            "reason": f"Improve {stat}",
            "trade_terms": [stat],
            "price_hint": "test",
            "profiles": ["jewel_damage"],
        }
    return {"search_library": library}


@contextmanager
def temporary_character_tree(build_slug: str = "test_build"):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        characters = root / "characters"
        profiles = root / "profiles"
        character = characters / "test_character"
        build = profiles / build_slug
        character.mkdir(parents=True)
        build.mkdir(parents=True)

        (character / "character_profile.json").write_text(
            json.dumps({"schema_version": 1, "slug": "test_character", "build_slug": build_slug}),
            encoding="utf-8",
        )
        (character / "player_items.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "items": {
                        "weapon": {"name": "Sample Staff", "stats": {"accuracy": 120}},
                        "ring_1": {"name": "Sample Ring", "stats": {"life": 80}},
                        "body_armour": {"name": "Sample Armour", "stats": {"life": 100}},
                    },
                }
            ),
            encoding="utf-8",
        )
        (character / "player_stats.json").write_text(
            json.dumps({"schema_version": 1, "stats": {"life": 3600, "fire_resistance": 75, "chance_to_hit": 92, "accuracy": 2000, "crit_multiplier": 250}}),
            encoding="utf-8",
        )
        (build / "build_profile.json").write_text(
            json.dumps({"schema_version": 1, "slug": build_slug, "name": "Test Build"}),
            encoding="utf-8",
        )
        (build / "target_build_items.json").write_text(
            json.dumps({"schema_version": 1, "items": {"weapon": {"name": "Target Staff"}, "ring_1": {"name": "Target Ring"}, "body_armour": {"name": "Target Armour"}}}),
            encoding="utf-8",
        )
        (build / "target_build_stats.json").write_text(
            json.dumps({"schema_version": 1, "minimums": {"life": 3400, "fire_resistance": 75}, "goals": {"life": 4000, "chance_to_hit": 95, "crit_multiplier": 300}}),
            encoding="utf-8",
        )
        (build / "upgrade_rules.json").write_text(
            json.dumps({"schema_version": 1, "weights": {"life": 1.0, "accuracy": 0.2}, "use_builtin_trade_profiles": True}),
            encoding="utf-8",
        )

        old_characters = core_validation.paths.CHARACTERS
        old_profiles = core_validation.paths.PROFILES
        core_validation.paths.CHARACTERS = characters
        core_validation.paths.PROFILES = profiles
        try:
            yield character
        finally:
            core_validation.paths.CHARACTERS = old_characters
            core_validation.paths.PROFILES = old_profiles


class SafetyRulesTest(unittest.TestCase):
    def test_plan_confidence_high_when_links_and_score_are_clean(self):
        plan = make_plan()

        confidence, reasons, needs_pob = plan_upgrade_path.plan_confidence(plan, {})

        self.assertEqual(confidence, "alta")
        self.assertFalse(needs_pob)
        self.assertTrue(any("score alto" in reason for reason in reasons))

    def test_plan_confidence_requires_pob_for_sensitive_or_unresolved_plan(self):
        plan = make_plan(
            score=165.0,
            warnings=[
                "slot sensivel: gloves",
                "ainda abaixo da meta: life 3700/4000",
            ],
        )

        confidence, reasons, needs_pob = plan_upgrade_path.plan_confidence(plan, {})

        self.assertEqual(confidence, "media")
        self.assertTrue(needs_pob)
        self.assertTrue(any("slot sensivel" in reason for reason in reasons))
        self.assertTrue(any("meta(s) ainda abaixo" in reason for reason in reasons))

    def test_guarded_slots_are_reported(self):
        player_items = {
            "items": {
                "body_armour": {"name": "The Brass Dome"},
                "gloves": {"name": "Death Knuckle"},
            }
        }
        rules = {
            "guarded_slots": {
                "body_armour": ["The Brass Dome"],
                "gloves": ["Death Knuckle"],
            }
        }

        guarded = compare.guarded_slots(player_items, rules)

        self.assertIn("body_armour", guarded)
        self.assertIn("gloves", guarded)
        self.assertIn("The Brass Dome", guarded["body_armour"])
        self.assertIn("Death Knuckle", guarded["gloves"])

    def test_strength_is_not_scored_as_life_with_brass_dome(self):
        rules = json.loads((BUILD_DIR / "upgrade_rules.json").read_text(encoding="utf-8"))
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

        entries = recommend.search_entries(gap, search_rules("life", "spell_block"))

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

        entries = recommend.search_entries(gap, search_rules("chance_to_hit"))

        self.assertEqual(entries[0]["priority"], "low")

    def test_accuracy_recommendation_accepts_unknown_current_value(self):
        gap = {
            "risks": {
                "chance_to_hit_evasive": {"current": None, "goal": 95, "status": "unknown", "missing_to_goal": None},
            },
            "current_priorities": {"chance_to_hit_evasive": "needs_data"},
        }

        entries = recommend.search_entries(gap, search_rules("chance_to_hit_evasive"))

        self.assertEqual(entries[0]["stat"], "chance_to_hit_evasive")

    def test_search_entries_require_configured_library(self):
        gap = {
            "risks": {
                "life": {"current": 3400, "goal": 3800, "status": "needs_improvement", "missing_to_goal": 400},
            },
            "current_priorities": {"life": "high"},
        }

        entries = recommend.search_entries(gap)

        self.assertEqual(entries, [])

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

    def test_goal_stats_score_only_progress_towards_target(self):
        contribution = plan_upgrade_path.weighted_stat_contribution(
            key="life",
            value=500,
            base_stats={"life": 3900},
            final_stats={"life": 4400},
            target_stats={"goals": {"life": 3800}},
            weights={"life": 1.0},
        )

        self.assertEqual(contribution, 0)

    def test_goal_stats_penalize_moving_away_from_target(self):
        contribution = plan_upgrade_path.weighted_stat_contribution(
            key="chaos_resistance",
            value=-20,
            base_stats={"chaos_resistance": 23},
            final_stats={"chaos_resistance": 3},
            target_stats={"goals": {"chaos_resistance": 40}},
            weights={"chaos_resistance": 1.7},
        )

        self.assertLess(contribution, 0)

    def test_target_requirements_infer_safe_minimums_from_pob_goals(self):
        requirements = target_analysis.build_target_requirements(
            {"stats": {"life": 4000, "fire_resistance": 82, "chaos_resistance": 35, "chance_to_hit": 97}},
            {"items": {}},
            {"skill_groups": []},
        )

        self.assertEqual(requirements["minimums"]["life"], 3400)
        self.assertEqual(requirements["minimums"]["fire_resistance"], 75)
        self.assertEqual(requirements["minimums"]["chaos_resistance"], 0)
        self.assertEqual(requirements["minimums"]["chance_to_hit"], 90)
        self.assertEqual(requirements["goals"]["fire_resistance"], 82)

    def test_target_requirements_extract_slot_and_skill_tags(self):
        requirements = target_analysis.build_target_requirements(
            {"stats": {"life": 3500, "combined_dps": 500000}},
            {
                "items": {
                    "weapon": {
                        "name": "Hate Mast",
                        "base": "Ezomyte Staff",
                        "rarity": "Rare",
                        "mods_raw": ["+120 to Accuracy Rating", "+30% to Global Critical Strike Multiplier"],
                        "stats": {"accuracy": 120, "crit_multiplier": 30},
                    }
                }
            },
            {
                "skill_groups": [
                    {
                        "index": 1,
                        "slot": "body_armour",
                        "main_gem": "Cyclone",
                        "include_in_full_dps": True,
                        "gems": [
                            {"name": "Cyclone", "level": 21, "quality": 20, "enabled": True},
                            {"name": "Brutality Support", "level": 20, "quality": 20, "enabled": True},
                        ],
                    }
                ]
            },
        )

        weapon = requirements["slot_requirements"]["weapon"]
        self.assertIn("accuracy", weapon["desired_stats"])
        self.assertIn("crit", weapon["tags"])
        self.assertIn("staff", weapon["tags"])
        self.assertIn("gem_level", requirements["weights"])
        self.assertEqual(requirements["skill_requirements"][0]["main_skill"], "Cyclone")

    def test_analyze_target_build_uses_goals_as_pob_stats_source(self):
        stats_doc = analyze_target_build.stats_doc_from_target_stats(
            {"source": "manual", "goals": {"life": 3800, "chance_to_hit": 100}, "minimums": {"life": 3300}}
        )

        self.assertEqual(stats_doc["stats"]["life"], 3800)
        self.assertNotIn("minimums", stats_doc)

    def test_analyze_target_build_keeps_explicit_minimums(self):
        minimums = analyze_target_build.explicit_minimums(
            {"minimums": {"fire_resistance": 75, "notes": "cap", "life": 3300}}
        )

        self.assertEqual(minimums, {"fire_resistance": 75, "life": 3300})

    def test_filter_strategy_separates_safe_market_basetypes(self):
        rows = review_filter_strategy.market_rows(
            {
                "items": [
                    {"name": "Divine Orb", "requested_category": "Currency", "category": "Currency", "chaos_value": 400},
                    {"name": "Doryani's Machinarium", "requested_category": "UniqueMap", "category": "UniqueMap", "chaos_value": 500},
                ]
            },
            {"tier_thresholds_chaos": {"T1": 100}},
            20,
        )

        safe = {row["name"]: row["safe_basetype"] for row in rows}
        self.assertTrue(safe["Divine Orb"])
        self.assertFalse(safe["Doryani's Machinarium"])

    def test_filter_strategy_collects_build_bases_from_current_and_target(self):
        bases = review_filter_strategy.useful_build_bases(
            {
                "items": {
                    "weapon": {"base": "Ezomyte Staff", "name": "Hate Mast", "stats": {"accuracy": 130}},
                    "flask_1": {"base": "Granite Flask", "name": "Granite Flask", "stats": {}},
                }
            },
            {"items": {"gloves": {"base": "Precursor Gauntlets", "name": "Death Knuckle", "stats": {"life": 113}}}},
            {"slot_requirements": {"ring_1": {"base": "Amethyst Ring", "desired_stats": ["chaos_resistance"], "stats": {}}}},
        )

        names = {row["base"] for row in bases}
        self.assertIn("Ezomyte Staff", names)
        self.assertIn("Precursor Gauntlets", names)
        self.assertIn("Amethyst Ring", names)
        self.assertNotIn("Granite Flask", names)

    def test_elemental_attack_damage_is_not_double_counted_as_generic_elemental(self):
        effects = plan_upgrade_path.candidate_effects(
            "quiver_damage",
            {"explicitMods": ["32% increased Elemental Damage with Attack Skills"]},
        )

        self.assertEqual(effects.get("elemental_damage_with_attacks"), 32)
        self.assertNotIn("elemental_damage", effects)

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

    def test_recommendations_can_use_build_specific_library(self):
        gap = {
            "risks": {
                "crit_multiplier": {"current": 400, "goal": 550, "status": "needs_improvement", "missing_to_goal": 150},
            },
            "current_priorities": {"crit_multiplier": "high"},
        }
        rules = {
            "search_library": {
                "crit_multiplier": {
                    "title": "Crit multi da build ativa",
                    "priority": "alta",
                    "reason": "Crit multi e central para esta build.",
                    "trade_terms": ["Global Critical Strike Multiplier"],
                    "price_hint": "Validar no PoB.",
                    "profiles": ["deadeye_jewel"],
                }
            }
        }

        entries = recommend.search_entries(gap, rules)

        self.assertEqual(entries[0]["title"], "Crit multi da build ativa")
        self.assertEqual(entries[0]["profiles"], ["deadeye_jewel"])

    def test_trade_profiles_can_come_from_rules(self):
        rules_path = ROOT / "builds" / "profiles" / "maxroll_hxobac03" / "upgrade_rules.json"

        profiles = plan_upgrade_path.trade.make_profiles(rules_path)

        self.assertIn("bow_elemental_dps", profiles)
        self.assertNotIn("ring_vulnerability", profiles)

    def test_market_dedupe_preserves_named_variants(self):
        items = [
            {"source_endpoint": "stash", "requested_category": "SkillGem", "category": "SkillGem", "name": "Example Gem", "variant": "20/20", "details_id": "a", "chaos_value": 10},
            {"source_endpoint": "stash", "requested_category": "SkillGem", "category": "SkillGem", "name": "Example Gem", "variant": "21/20", "details_id": "b", "chaos_value": 100},
        ]

        deduped = update_market.dedupe_items(items)

        self.assertEqual(len(deduped), 2)

    def test_character_validator_accepts_saved_character_profile(self):
        with temporary_character_tree():
            report = validate_character.validate_character("test_character")

        self.assertIn(report["status"], {"ok", "warning"})
        self.assertEqual(report["build_slug"], "test_build")
        self.assertEqual(report["errors"], [])
        self.assertNotIn("preencha mais slots em target_build_items.json", " ".join(report["suggestions"]))

    def test_character_validator_rejects_missing_character(self):
        report = validate_character.validate_character("personagem_que_nao_existe")

        self.assertEqual(report["status"], "failed")
        self.assertTrue(report["errors"])

    def test_run_character_requires_explicit_oauth_opt_in(self):
        with self.assertRaises(SystemExit) as raised:
            run_character.main(["--character", "aron_shockwave_cyclone_slayer", "--fetch-character", "--skip-market-update"])

        self.assertIn("experimental", str(raised.exception))

    def test_sync_pob_extracts_stats_and_active_items(self):
        xml = """<PathOfBuilding>
          <Build level="90" className="Duelist" ascendClassName="Slayer">
            <PlayerStat stat="Life" value="3977"/>
            <PlayerStat stat="HitChance" value="89"/>
            <PlayerStat stat="FireResist" value="81"/>
            <PlayerStat stat="CritMultiplier" value="2.69"/>
            <PlayerStat stat="CombinedDPS" value="668772.5"/>
          </Build>
          <Items activeItemSet="1">
            <Item id="1">Rarity: Rare
Hate Mast
Ezomyte Staff
--------
+130 to Accuracy Rating
20% increased Attack Speed
+16% to Global Critical Strike Multiplier</Item>
            <ItemSet id="1">
              <Slot name="Weapon 1" itemId="1"/>
            </ItemSet>
          </Items>
        </PathOfBuilding>"""
        root = sync_pob.ET.fromstring(xml)

        stats = sync_pob.extract_stats(root)
        items = sync_pob.extract_items(root)
        skills = sync_pob.extract_skills(root)

        self.assertEqual(stats["character"]["class"], "Duelist")
        self.assertEqual(stats["character"]["ascendancy"], "Slayer")
        self.assertEqual(stats["stats"]["life"], 3977)
        self.assertEqual(stats["stats"]["chance_to_hit"], 89)
        self.assertEqual(stats["stats"]["crit_multiplier"], 269)
        self.assertEqual(stats["stats"]["combined_dps"], 668772.5)
        self.assertIn("weapon", items["items"])
        self.assertEqual(items["items"]["weapon"]["name"], "Hate Mast")
        self.assertEqual(items["items"]["weapon"]["base"], "Ezomyte Staff")
        self.assertEqual(items["items"]["weapon"]["stats"]["accuracy"], 130)
        self.assertEqual(skills["skill_groups"], [])

    def test_sync_pob_save_code_normalizes_whitespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "export.txt"
            sync_pob.save_pob_code(path, " abc \n def ")

            self.assertEqual(path.read_text(encoding="utf-8"), "abcdef\n")

    def test_run_summary_observability_contract(self):
        args = SimpleNamespace(
            fetch_character=False,
            parse_character=False,
            sync_pob_source=None,
            sync_pob_from_clipboard=False,
            skip_market_update=True,
            skip_market_report=False,
            skip_filter_reports=False,
            skip_upgrade_plan=True,
            skip_validation=False,
            strict_validation=False,
            budget="1000c",
            profiles="all",
            top=10,
            max_fetch=30,
            max_combo_size=None,
            request_delay=None,
            best_any_budget_mode="reuse",
            fail_on_stale_market=True,
            max_market_age_minutes=180.0,
            fail_on_market_errors=True,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "validation_report.json").write_text(
                json.dumps({"status": "ok", "warnings": [], "errors": []}),
                encoding="utf-8",
            )
            (root / "latest_market.json").write_text(
                json.dumps({"generated_at": "2026-05-25T00:00:00Z", "items": [{}, {}], "errors": []}),
                encoding="utf-8",
            )

            execution = run_character.build_execution_context(args)
            observability = run_character.build_observability(root, args)

        self.assertTrue(execution["fail_on_stale_market"])
        self.assertEqual(execution["max_market_age_minutes"], 180.0)
        self.assertTrue(execution["fail_on_market_errors"])
        self.assertEqual(observability["validation_status"], "ok")
        self.assertEqual(observability["market_items"], 2)
        self.assertEqual(observability["market_errors"], 0)
        self.assertEqual(observability["market_data_source"], "reused_cached")
        self.assertIsInstance(observability["market_age_minutes"], float)

    def test_utc_timestamps_are_marked_with_z(self):
        self.assertTrue(core_validation.utc_now_iso().endswith("Z"))
        self.assertTrue(update_market.utc_now_iso().endswith("Z"))
        self.assertTrue(run_character.utc_now_iso().endswith("Z"))
        self.assertTrue(compare.utc_now_iso().endswith("Z"))
        self.assertTrue(recommend.utc_now_iso().endswith("Z"))
        self.assertTrue(plan_upgrade_path.utc_now_iso().endswith("Z"))

    def test_market_observability_reads_errors_and_age(self):
        args = SimpleNamespace(skip_market_update=False)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "latest_market.json"
            path.write_text(
                json.dumps({"generated_at": "2026-05-25T00:00:00Z", "items": [{}], "errors": [{"category": "Currency"}]}),
                encoding="utf-8",
            )

            health = run_character.market_observability_from_file(path, args)

        self.assertEqual(health["market_items"], 1)
        self.assertEqual(health["market_errors"], 1)
        self.assertEqual(health["market_data_source"], "updated_now")
        self.assertIsInstance(health["market_age_minutes"], float)


if __name__ == "__main__":
    unittest.main()
