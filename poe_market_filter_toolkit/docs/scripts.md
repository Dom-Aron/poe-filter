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
sync_pob.py
```

Importa XML/codigo exportado do Path of Building sem OAuth. Pode atualizar os
arquivos do personagem atual ou os arquivos da build alvo. Hoje extrai itens,
status calculados e grupos de gems/skills ativos. Ao importar uma build alvo,
tambem gera `target_requirements.json`, com metas, pisos de seguranca,
requisitos por slot, skills ativas, tags dominantes e pesos sugeridos derivados
genericamente do PoB. O planner usa os status para medir se uma troca aproxima
o personagem das metas da build.

```powershell
python poe_market_filter_toolkit\scripts\sync_pob.py --list-local
python poe_market_filter_toolkit\scripts\sync_pob.py --character aron_shockwave_cyclone_slayer --source "C:\Users\<voce>\Documents\Path of Building\Builds\MinhaBuild.xml"
python poe_market_filter_toolkit\scripts\sync_pob.py --character aron_shockwave_cyclone_slayer --from-clipboard --save-code poe_market_filter_toolkit\data\raw\pob_export_aron.txt
python poe_market_filter_toolkit\scripts\sync_pob.py --build ronarray_shockwave_cyclone_slayer --source "C:\pob\BuildAlvo.xml" --as target
```

```text
analyze_target_build.py
```

Regera `target_requirements.json` para uma build ja cadastrada usando
`target_build_stats.json`, `target_build_items.json` e, quando existir,
`target_build_skills.json`. Use `--update-stats` se quiser reescrever tambem
`target_build_stats.json` com pisos minimos inferidos.

```powershell
python poe_market_filter_toolkit\scripts\analyze_target_build.py --build ronarray_shockwave_cyclone_slayer
python poe_market_filter_toolkit\scripts\analyze_target_build.py --build ronarray_shockwave_cyclone_slayer --update-stats
```

```text
switch_build.py
```

Cadastra builds e personagens. O fluxo recomendado continua sendo
`run_character.py`, que grava contexto e relatorios por personagem.

## Mercado e filtro

```text
update_market.py
market_report.py
suggest_filter_tiers.py
filter_audit.py
review_filter_strategy.py
```

Atualizam snapshot de mercado, relatórios de preços e auditoria do filtro de loot.
`review_filter_strategy.py` faz a ponte conservadora entre mercado, personagem e
build alvo, gerando `filter_strategy.md` e `filter_strategy_snippets.filter`
sem editar o filtro automaticamente.

## Build agent

```text
compare_current_to_target.py
recommend_next_steps.py
plan_upgrade_path.py
generate_dashboard.py
```

Comparam personagem/build, geram recomendações, buscam planos no trade e criam HTMLs.
O `plan_upgrade_path.py` tambem calcula uma confianca (`Alta`, `Media` ou
`Baixa`) para cada plano. A confianca separa potencial de upgrade de risco
operacional: score alto com slot sensivel, metas ainda abaixo ou link incompleto
deve aparecer como algo a validar no PoB antes da compra.

## OAuth

```text
oauth_login.py
oauth_refresh.py
fetch_character.py
```

Mantidos como opcionais e experimentais. Eles nao rodam por acidente: use
`--allow-experimental-oauth` apenas se voce tiver credenciais aprovadas e quiser
testar esse caminho. O projeto nao depende deles para funcionar.
