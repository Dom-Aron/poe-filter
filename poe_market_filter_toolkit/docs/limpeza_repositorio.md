# Revisao de arquivos defasados

Esta revisao separa arquivos que sao fonte de verdade dos que sao legado,
artefato local ou relatorio gerado.

## Pode remover localmente com seguranca

Estes arquivos nao sao fonte de verdade e podem ser recriados:

```text
poe_market_filter_toolkit/**/__pycache__/
poe_market_filter_toolkit/data/generated/*.log
poe_market_filter_toolkit/filters/current/active_loot_filter.filter
```

Motivo:

- `__pycache__` e `.pyc` sao cache do Python.
- Logs em `data/generated` sao depuracao antiga.
- `filters/current/active_loot_filter.filter` e uma copia ignorada pelo Git e
  estava diferente do filtro ativo rastreado na raiz (`active_loot_filter.filter`).
  Essa copia ainda continha regras antigas com risco de erro de parser.

## Removidos nesta limpeza

```text
poe_market_filter_toolkit/builds/player_items.json
poe_market_filter_toolkit/builds/player_stats.json
poe_market_filter_toolkit/builds/target_build_items.json
poe_market_filter_toolkit/builds/target_build_stats.json
poe_market_filter_toolkit/builds/upgrade_rules.json
poe_market_filter_toolkit/builds/active_build.json
poe_market_filter_toolkit/builds/active_character.json
poe_market_filter_toolkit/scripts/run_build_matrix.py
poe_market_filter_toolkit/README.md
poe_market_filter_toolkit/INSTRUCOES.md
```

Esses arquivos pertenciam ao estado global antigo. O fluxo atual por personagem
usa `builds/characters/<personagem>/`, `builds/profiles/<build>/` e
`data/generated/characters/<personagem>/`.

```text
poe_market_filter_toolkit/scripts/find_upgrade_deals.py
```

Ainda fornece funcoes usadas por `plan_upgrade_path.py`. A CLI agora exige
`--rules` explicito para evitar voltar ao estado global antigo.

## Candidatos a consolidacao

```text
README.md
plano_automacao_poe_build_agent.md
```

O README da raiz esta mais atual. O README interno e `INSTRUCOES.md` do toolkit
foram removidos nesta limpeza por duplicarem instrucoes antigas.

`plano_automacao_poe_build_agent.md` era um plano historico grande e tambem foi
removido depois que as partes uteis foram consolidadas em `README.md` e `docs/`.

## Gerados que devem continuar fora do Git

```text
poe_market_filter_toolkit/data/generated/
poe_market_filter_toolkit/data/raw/
poe_market_filter_toolkit/market/snapshots/
poe_market_filter_toolkit/market/trade_stats_cache.json
poe_market_filter_toolkit/market/reports/upgrade_plan.*
poe_market_filter_toolkit/market/reports/filter_strategy.*
```

Esses arquivos sao saida de execucao. Devem ficar locais e serem recriados pelos
scripts, nao tratados como fonte de verdade.

## Filtro ativo

Fonte canonica atual:

```text
active_loot_filter.filter
```

Se quisermos mover definitivamente o filtro para `poe_market_filter_toolkit/filters/current/`,
devemos fazer isso em um commit proprio e remover a regra de ignore
`filters/current/*.filter`. Ate la, manter apenas a versao da raiz evita que os
relatorios comparem duas copias divergentes.
