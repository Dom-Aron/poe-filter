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
```

Esses scripts ajudam a manter o filtro, mas nao editam o filtro automaticamente.

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
