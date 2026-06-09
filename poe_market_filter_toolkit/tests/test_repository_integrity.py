import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
FIXTURES = ROOT / "tests" / "fixtures"
MAX_CYCLOMATIC_COMPLEXITY = 30

sys.path.insert(0, str(ROOT))

from core import validation as core_validation


def git_ls_files(*patterns: str) -> list[str]:
    command = ["git", "ls-files", *patterns]
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=True)
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def cyclomatic_complexity(node: ast.AST) -> int:
    score = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With, ast.AsyncWith, ast.Assert, ast.IfExp, ast.Match)):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += max(0, len(child.values) - 1)
        elif isinstance(child, ast.comprehension):
            score += 1 + len(child.ifs)
    return score


def python_functions(path: Path) -> list[tuple[str, int, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rows: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            rows.append((node.name, node.lineno, cyclomatic_complexity(node)))
    return rows


class RepositoryIntegrityTest(unittest.TestCase):
    def test_tracked_json_files_are_valid(self):
        broken: list[str] = []
        for raw_path in git_ls_files("*.json"):
            path = REPO_ROOT / raw_path
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                broken.append(f"{raw_path}: {exc}")

        self.assertEqual(broken, [])

    def test_generated_and_sensitive_files_are_not_tracked(self):
        tracked = git_ls_files()
        forbidden_prefixes = (
            "poe_market_filter_toolkit/secrets/",
            "poe_market_filter_toolkit/builds/characters/",
            "poe_market_filter_toolkit/data/raw/",
            "poe_market_filter_toolkit/data/generated/",
            "poe_market_filter_toolkit/market/reports/",
        )
        forbidden_exact = {
            "poe_market_filter_toolkit/market/latest_market.json",
            "equipamentos_e_status_atuais_poe_slayer.txt",
        }
        offenders = [
            path
            for path in tracked
            if path.endswith((".bat", ".ps1")) or path in forbidden_exact or any(path.startswith(prefix) for prefix in forbidden_prefixes)
        ]

        self.assertEqual(offenders, [])

    def test_build_profiles_have_required_files(self):
        required = {"build_profile.json", "target_build_items.json", "target_build_stats.json", "upgrade_rules.json"}
        offenders: list[str] = []
        for profile_dir in (ROOT / "builds" / "profiles").iterdir():
            if profile_dir.is_dir():
                missing = sorted(required - {path.name for path in profile_dir.iterdir()})
                if missing:
                    offenders.append(f"{profile_dir.relative_to(REPO_ROOT)} missing {', '.join(missing)}")

        self.assertEqual(offenders, [])

    def test_repository_fixtures_validate_character_flow(self):
        old_characters = core_validation.paths.CHARACTERS
        old_profiles = core_validation.paths.PROFILES
        core_validation.paths.CHARACTERS = FIXTURES / "characters"
        core_validation.paths.PROFILES = FIXTURES / "profiles"
        try:
            report = core_validation.validate_character("sample_character")
        finally:
            core_validation.paths.CHARACTERS = old_characters
            core_validation.paths.PROFILES = old_profiles

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["build_slug"], "sample_build")

    def test_python_cyclomatic_complexity_stays_bounded(self):
        offenders: list[str] = []
        for folder in ("core", "scripts"):
            for path in sorted((ROOT / folder).glob("*.py")):
                for name, line, score in python_functions(path):
                    if score > MAX_CYCLOMATIC_COMPLEXITY:
                        rel = path.relative_to(REPO_ROOT)
                        offenders.append(f"{rel}:{line} {name} complexity={score}")

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
