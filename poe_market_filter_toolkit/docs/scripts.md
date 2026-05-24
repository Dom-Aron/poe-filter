# Scripts Principais

## Fluxo recomendado

```text
run_character.py
```

Orquestra um personagem salvo do inicio ao fim. Usa arquivos isolados do personagem e da build associada.

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --open
```

## Manutencao local

```text
validate_character.py
```

Confere se os arquivos de personagem/build existem e se as regras fazem sentido antes de rodar buscas caras.

```text
edit_character.py
```

Assistente interativo para preencher `player_items.json` e `player_stats.json`.

```text
switch_build.py
```

Cadastra builds e personagens. Ainda mantem compatibilidade com estado global legado, mas o fluxo recomendado nao depende disso.

## Mercado e filtro

```text
update_market.py
market_report.py
suggest_filter_tiers.py
filter_audit.py
```

Atualizam snapshot de mercado, relatórios de preços e auditoria do filtro de loot.

## Build agent

```text
compare_current_to_target.py
recommend_next_steps.py
plan_upgrade_path.py
generate_dashboard.py
```

Comparam personagem/build, geram recomendações, buscam planos no trade e criam HTMLs.

## Scripts legados

```text
run_build_matrix.py
parse_character.py --update-builds
```

Podem mexer em arquivos globais antigos. Use apenas com flags de legado quando realmente precisar.

## OAuth

```text
oauth_login.py
oauth_refresh.py
fetch_character.py
```

Mantidos como opcionais e experimentais. Eles nao rodam por acidente: use
`--allow-experimental-oauth` apenas se voce tiver credenciais aprovadas e quiser
testar esse caminho. O projeto nao depende deles para funcionar.
