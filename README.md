# PoE Filter Toolkit

Toolkit local para Path of Exile 1. Ele ajuda a manter um filtro de loot,
atualizar dados de mercado e planejar upgrades por personagem comparando o
estado atual com uma build alvo.

English version: [README.en.md](README.en.md).

## Estado De Seguranca

O fluxo principal nao depende de OAuth. Credenciais, tokens, arquivos de conta,
exports crus do Path of Building e dados reais de personagem devem ficar apenas
na maquina local.

Arquivos locais ignorados pelo Git:

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

Os arquivos `*.example.json` podem ser versionados porque nao contem segredos.

## Fluxo Recomendado

Rodar tudo para um personagem salvo localmente:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --open
```

Rodar de forma conservadora, bloqueando mercado velho ou coleta com erro:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --fail-on-stale-market --max-market-age-minutes 180 --fail-on-market-errors --open
```

Revisar filtro para um personagem local:

```powershell
python poe_market_filter_toolkit\scripts\review_filter_strategy.py --character aron_shockwave_cyclone_slayer
python poe_market_filter_toolkit\scripts\filter_audit.py
python poe_market_filter_toolkit\scripts\suggest_filter_tiers.py
```

## Dados Do Personagem

Crie ou atualize um personagem local a partir do Path of Building:

```powershell
python poe_market_filter_toolkit\scripts\sync_pob.py --list-local
python poe_market_filter_toolkit\scripts\sync_pob.py --character aron_shockwave_cyclone_slayer --source "C:\Users\<voce>\Documents\Path of Building\Builds\MinhaBuild.xml"
```

Tambem e possivel importar o codigo exportado pelo PoB:

```powershell
python poe_market_filter_toolkit\scripts\sync_pob.py --character aron_shockwave_cyclone_slayer --from-clipboard --save-code poe_market_filter_toolkit\data\raw\pob_export_aron.txt
```

Editar dados manualmente:

```powershell
python poe_market_filter_toolkit\scripts\edit_character.py --character aron_shockwave_cyclone_slayer
python poe_market_filter_toolkit\scripts\validate_character.py --character aron_shockwave_cyclone_slayer
```

Arquivos locais por personagem:

```text
poe_market_filter_toolkit/builds/characters/<personagem>/
  character_profile.json
  player_items.json
  player_stats.json
  player_skills.json
```

## Build Alvo

Builds alvo ficam versionadas quando forem presets publicos ou anonimizados:

```text
poe_market_filter_toolkit/builds/profiles/<build>/
  build_profile.json
  target_build_items.json
  target_build_stats.json
  target_requirements.json
  upgrade_rules.json
```

Importar uma build alvo a partir de um PoB:

```powershell
python poe_market_filter_toolkit\scripts\sync_pob.py --build ronarray_shockwave_cyclone_slayer --source "C:\pob\BuildAlvo.xml" --as target
python poe_market_filter_toolkit\scripts\analyze_target_build.py --build ronarray_shockwave_cyclone_slayer
```

## Mercado E Filtro

Atualizar mercado e relatorios tecnicos do filtro:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --skip-update
```

Scripts principais:

```text
update_market.py
market_report.py
suggest_filter_tiers.py
filter_audit.py
review_filter_strategy.py
```

Esses scripts ajudam a revisar o filtro, mas nao editam automaticamente
`active_loot_filter.filter`.

## Saidas

Os resultados sao gerados localmente em:

```text
poe_market_filter_toolkit/data/generated/characters/<personagem>/
```

Arquivos comuns:

```text
build_dashboard.html
upgrade_plan.html
upgrade_recommendations.html
next_searches.html
market_report.html
validation_report.json
run_summary.json
```

O plano de compra marca cada sugestao com `Confianca` (`Alta`, `Media` ou
`Baixa`). Esse campo mede a seguranca operacional da recomendacao; valide no PoB
antes de comprar.

## OAuth Opcional

OAuth esta mantido apenas como recurso experimental. Para usar, copie os
exemplos para arquivos locais ignorados:

```powershell
Copy-Item poe_market_filter_toolkit\config\account_config.example.json poe_market_filter_toolkit\config\account_config.json
Copy-Item poe_market_filter_toolkit\config\oauth_config.example.json poe_market_filter_toolkit\config\oauth_config.json
```

Depois gere `poe_market_filter_toolkit\secrets\tokens.json` com
`oauth_login.py` ou use a variavel `POE_OAUTH_TOKEN`. Nao commite esses arquivos.

## Testes

```powershell
python -m unittest discover -s poe_market_filter_toolkit\tests
python -m compileall poe_market_filter_toolkit\core poe_market_filter_toolkit\scripts
```

## Documentacao

```text
poe_market_filter_toolkit/docs/fluxo_sem_oauth.md
poe_market_filter_toolkit/docs/json_schema.md
poe_market_filter_toolkit/docs/scripts.md
poe_market_filter_toolkit/docs/arquitetura.md
poe_market_filter_toolkit/docs/limpeza_repositorio.md
```

## Limites

- O planner nao substitui o Path of Building.
- `Confianca` ajuda a priorizar, mas nao prova que o item e upgrade final.
- Itens sugeridos precisam de revisao humana antes da compra.
- Links do trade podem ficar obsoletos se o item vender ou mudar de preco.
- Rate limit da API publica pode deixar uma busca incompleta.
- O filtro de loot e a busca de upgrades usam o mercado de formas diferentes.
