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

## Manter por enquanto, mas revisar depois

```text
poe_market_filter_toolkit/builds/player_items.json
poe_market_filter_toolkit/builds/player_stats.json
poe_market_filter_toolkit/builds/target_build_items.json
poe_market_filter_toolkit/builds/target_build_stats.json
poe_market_filter_toolkit/builds/upgrade_rules.json
```

Esses arquivos sao o estado global legado. O fluxo atual por personagem usa
`builds/characters/<personagem>/` e `builds/profiles/<build>/`, mas alguns
scripts antigos ainda usam esses defaults. Nao remover ate todos os scripts
legados aceitarem explicitamente `--character`/`--build`.

```text
poe_market_filter_toolkit/scripts/run_build_matrix.py
poe_market_filter_toolkit/scripts/run_all.py
```

Ambos ainda existem para compatibilidade, mas o fluxo recomendado e
`run_character.py` ou `run_character_matrix.py`.

```text
poe_market_filter_toolkit/scripts/find_upgrade_deals.py
```

Parece legado como CLI, mas ainda fornece funcoes usadas por
`plan_upgrade_path.py`. Nao remover sem extrair essas funcoes para `core/trade`.

## Candidatos a consolidacao

```text
README.md
poe_market_filter_toolkit/README.md
poe_market_filter_toolkit/INSTRUCOES.md
plano_automacao_poe_build_agent.md
```

O README da raiz esta mais atual. O README e INSTRUCOES dentro do toolkit ainda
descrevem fluxos antigos (`run_all.py`, estado global e OAuth). Recomendo
consolidar tudo em `README.md` + `docs/`, depois remover os documentos antigos.

`plano_automacao_poe_build_agent.md` e um plano historico grande. Pode virar
arquivo de arquivo morto em `docs/archive/` ou ser removido depois que as partes
uteis estiverem documentadas em `docs/arquitetura.md`.

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
