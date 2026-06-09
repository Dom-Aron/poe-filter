# PoE Filter Toolkit

Local toolkit for Path of Exile 1. It helps maintain a loot filter, refresh
market data, and plan character upgrades by comparing the current character
state against a target build.

Portuguese version: [README.md](README.md).

## Security Status

The main workflow does not require OAuth. Credentials, tokens, account files,
raw Path of Building exports, and real character data should stay only on the
local machine.

Local files ignored by Git:

```text
poe_market_filter_toolkit/secrets/tokens.json
poe_market_filter_toolkit/config/account_config.json
poe_market_filter_toolkit/config/oauth_config.json
poe_market_filter_toolkit/builds/characters/
poe_market_filter_toolkit/data/raw/
poe_market_filter_toolkit/data/generated/
equipamentos_e_status_atuais_poe_slayer.txt
.env
```

The `*.example.json` files are safe to commit because they do not contain
secrets.

## Recommended Flow

Run the full workflow for a locally saved character:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --open
```

Run conservatively, failing on stale market data or market collection errors:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --fail-on-stale-market --max-market-age-minutes 180 --fail-on-market-errors --open
```

Local shortcuts:

```powershell
.\tasks.ps1 character aron_shockwave_cyclone_slayer 1000c
.\tasks.ps1 test
.\tasks.ps1 filter aron_shockwave_cyclone_slayer
```

Development shortcuts:

```powershell
.\dev.ps1 check
.\dev.ps1 status
.\dev.ps1 artifacts
```

## Character Data

Create or update a local character from Path of Building:

```powershell
python poe_market_filter_toolkit\scripts\sync_pob.py --list-local
python poe_market_filter_toolkit\scripts\sync_pob.py --character aron_shockwave_cyclone_slayer --source "C:\Users\<you>\Documents\Path of Building\Builds\MyBuild.xml"
```

You can also import an exported PoB code:

```powershell
python poe_market_filter_toolkit\scripts\sync_pob.py --character aron_shockwave_cyclone_slayer --from-clipboard --save-code poe_market_filter_toolkit\data\raw\pob_export_aron.txt
```

Edit and validate data manually:

```powershell
python poe_market_filter_toolkit\scripts\edit_character.py --character aron_shockwave_cyclone_slayer
python poe_market_filter_toolkit\scripts\validate_character.py --character aron_shockwave_cyclone_slayer
```

Local character files:

```text
poe_market_filter_toolkit/builds/characters/<character>/
  character_profile.json
  player_items.json
  player_stats.json
  player_skills.json
```

## Target Build

Target builds can be versioned when they are public or anonymized presets:

```text
poe_market_filter_toolkit/builds/profiles/<build>/
  build_profile.json
  target_build_items.json
  target_build_stats.json
  target_requirements.json
  upgrade_rules.json
```

Import a target build from a PoB file:

```powershell
python poe_market_filter_toolkit\scripts\sync_pob.py --build ronarray_shockwave_cyclone_slayer --source "C:\pob\TargetBuild.xml" --as target
python poe_market_filter_toolkit\scripts\analyze_target_build.py --build ronarray_shockwave_cyclone_slayer
```

## Market And Filter

Refresh market data and technical filter reports:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --skip-update
```

Main scripts:

```text
update_market.py
market_report.py
suggest_filter_tiers.py
filter_audit.py
review_filter_strategy.py
```

These scripts help review the filter, but they do not automatically edit
`active_loot_filter.filter`.

## Outputs

Results are generated locally under:

```text
poe_market_filter_toolkit/data/generated/characters/<character>/
```

Common files:

```text
build_dashboard.html
upgrade_plan.html
upgrade_recommendations.html
next_searches.html
market_report.html
validation_report.json
run_summary.json
```

The purchase plan labels each suggestion with `Confianca` (`Alta`, `Media`, or
`Baixa`). This measures operational confidence, not real PoB DPS. Validate in
PoB before buying.

## Optional OAuth

OAuth is kept only as an experimental helper. To use it, copy the examples to
ignored local files:

```powershell
Copy-Item poe_market_filter_toolkit\config\account_config.example.json poe_market_filter_toolkit\config\account_config.json
Copy-Item poe_market_filter_toolkit\config\oauth_config.example.json poe_market_filter_toolkit\config\oauth_config.json
```

Then generate `poe_market_filter_toolkit\secrets\tokens.json` with
`oauth_login.py` or set `POE_OAUTH_TOKEN`. Do not commit these files.

## Tests

```powershell
python -m unittest discover -s poe_market_filter_toolkit\tests
```

## Documentation

```text
poe_market_filter_toolkit/docs/fluxo_sem_oauth.md
poe_market_filter_toolkit/docs/json_schema.md
poe_market_filter_toolkit/docs/scripts.md
poe_market_filter_toolkit/docs/arquitetura.md
poe_market_filter_toolkit/docs/limpeza_repositorio.md
```

## Limits

- The planner does not replace Path of Building.
- `Confianca` helps prioritize, but it does not prove an item is a final upgrade.
- Suggested items need human review before purchase.
- Trade links can become stale if an item sells or its price changes.
- Public API rate limits can leave a search incomplete.
- The loot filter and upgrade search use market data in different ways.
