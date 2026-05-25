# PoE Filter Toolkit

Toolkit local para Path of Exile 1 / liga Mirage. O projeto faz duas coisas separadas:

1. ajuda a manter o filtro de loot com base em nomes, base types e precos de mercado;
2. planeja upgrades por personagem, comparando o estado atual com uma build alvo e buscando ofertas no trade.

O fluxo oficial **nao depende de OAuth**. OAuth fica mantido apenas como recurso opcional, caso algum dia o acesso seja aprovado.

## Fluxo Recomendado

Rodar tudo para um personagem salvo:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --open
```

Rodar de forma conservadora, bloqueando mercado velho ou coleta com erro:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --fail-on-stale-market --max-market-age-minutes 180 --fail-on-market-errors --open
```

Atalhos locais equivalentes:

```powershell
.\tasks.ps1 character aron_shockwave_cyclone_slayer 1000c
.\tasks.ps1 test
.\tasks.ps1 filter aron_shockwave_cyclone_slayer
```

Atalhos para desenvolvimento do codigo:

```powershell
.\dev.ps1 check
.\dev.ps1 status
.\dev.ps1 artifacts
```

O guia curto de desenvolvimento fica em [DEV.md](DEV.md).

Saidas por personagem:

```text
poe_market_filter_toolkit/data/generated/characters/<personagem>/
```

Arquivos principais gerados:

```text
build_dashboard.html
upgrade_plan.html
upgrade_recommendations.html
next_searches.html
market_report.html
validation_report.json
run_summary.json
```

## Atualizar Dados Do Personagem

Importar dados calculados do Path of Building salvo localmente:

```powershell
python poe_market_filter_toolkit\scripts\sync_pob.py --list-local
python poe_market_filter_toolkit\scripts\sync_pob.py --character aron_shockwave_cyclone_slayer --source "C:\Users\<voce>\Documents\Path of Building\Builds\MinhaBuild.xml"
```

Essa importacao atualiza itens, status calculados e grupos de gems/skills do personagem.

Importar usando o código exportado pelo PoB:

```powershell
python poe_market_filter_toolkit\scripts\sync_pob.py --character aron_shockwave_cyclone_slayer --from-clipboard --save-code poe_market_filter_toolkit\data\raw\pob_export_aron.txt
```

Importar a build alvo a partir de um PoB:

```powershell
python poe_market_filter_toolkit\scripts\sync_pob.py --build ronarray_shockwave_cyclone_slayer --source "C:\pob\BuildAlvo.xml" --as target
```

Nesse modo o toolkit gera `target_requirements.json`, que resume metas, pisos de seguranca, requisitos por slot, skills ativas, tags dominantes e pesos sugeridos sem depender do nome da build.

Para builds ja cadastradas, tambem da para regenerar essa leitura generica sem reimportar o PoB:

```powershell
python poe_market_filter_toolkit\scripts\analyze_target_build.py --build ronarray_shockwave_cyclone_slayer
```

Ou sincronizar e rodar o fluxo completo em seguida:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --sync-pob-from-clipboard --budget 1000c --open
```

Editar itens/status sem mexer no JSON cru:

```powershell
python poe_market_filter_toolkit\scripts\edit_character.py --character aron_shockwave_cyclone_slayer
```

Editar apenas alguns slots:

```powershell
python poe_market_filter_toolkit\scripts\edit_character.py --character aron_shockwave_cyclone_slayer --items --slots ring_1,ring_2,belt
```

Validar se o personagem e a build estao coerentes:

```powershell
python poe_market_filter_toolkit\scripts\validate_character.py --character aron_shockwave_cyclone_slayer
```

## Arquivos De Entrada

Personagem:

```text
poe_market_filter_toolkit/builds/characters/<personagem>/
  character_profile.json
  player_items.json
  player_stats.json
```

Build alvo:

```text
poe_market_filter_toolkit/builds/profiles/<build>/
  build_profile.json
  target_build_items.json
  target_build_stats.json
  target_requirements.json
  upgrade_rules.json
```

Cada personagem aponta para uma build em `character_profile.json`.

## Mercado E Filtro

Atualizar mercado e relatorios tecnicos do filtro:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --skip-update
```

Scripts dessa trilha:

```text
update_market.py
market_report.py
suggest_filter_tiers.py
filter_audit.py
review_filter_strategy.py
```

Esses scripts ajudam a manter o filtro, mas nao editam o filtro automaticamente.
`review_filter_strategy.py` cruza personagem, build alvo e mercado para separar
o que deve aparecer por valor de mercado do que deve aparecer por potencial para
a build. Ele tambem gera `market/reports/filter_strategy_snippets.filter` para
revisao manual.

## Testes

```powershell
python -m unittest discover -s poe_market_filter_toolkit\tests
```

## Documentacao

```text
poe_market_filter_toolkit/docs/fluxo_sem_oauth.md
poe_market_filter_toolkit/docs/json_schema.md
poe_market_filter_toolkit/docs/scripts.md
poe_market_filter_toolkit/docs/arquitetura.md
```

## Limites

- O planner nao substitui PoB.
- Itens sugeridos precisam de revisao humana antes da compra.
- Links do trade podem ficar obsoletos se o item vender ou mudar de preco.
- Rate limit da API publica pode deixar uma busca incompleta.
- O filtro de loot e a busca de upgrades usam o mercado de formas diferentes; uma coisa nao deve sobrescrever a outra automaticamente.
