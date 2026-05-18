# PoE Filter Toolkit - Shockwave Cyclone Slayer

Projeto para manter o filtro de loot da build **Shockwave Cyclone / General's Cry Slayer** e gerar relatorios de mercado para a liga **Mirage**.

Filtro principal:

```text
void_shockwave_cyclone_slayer_lvl89_t9_t10_breach_hives_market_v18_reviewed.filter
```

Contexto atual:

```text
Path of Exile 1 - 3.28 Mirage
Build: Ronarray Shockwave Cyclone / General's Cry Slayer
Conteudo: mapas T9/T10
Atlas: Breach Hives / Wombgifts + Delirium
Estado do personagem: equipamentos_e_status_atuais_poe_slayer.txt
```

## O Que Os Scripts Fazem

Os scripts em `poe_market_filter_toolkit/scripts` ajudam a responder quatro perguntas:

- **Quanto vale o mercado agora?** Baixam dados do poe.ninja e criam relatorios por categoria.
- **O filtro esta cobrindo os itens valiosos?** Comparam os nomes do mercado com os `BaseType` existentes no filtro.
- **O filtro tem risco de erro no parser?** Procuram nomes suspeitos, regras genericas demais e duplicacoes.
- **O que vale comprar para a build?** Consultam a API oficial de trade do Path of Exile e listam candidatos de upgrade dentro de um budget informado.

Os scripts **nao compram itens**, **nao editam o filtro automaticamente** e **nao substituem PoB**. Eles geram uma lista melhor para revisao humana.

## Requisitos

- Python 3.10+.
- Internet para acessar poe.ninja e a API oficial de trade do Path of Exile.
- Nenhuma dependencia externa: os scripts usam apenas a biblioteca padrao do Python.
- Liga configurada em `poe_market_filter_toolkit/config/market_config.json`.

Configuracao importante:

```json
{
  "league": "Mirage",
  "request_delay_seconds": 0.7,
  "timeout_seconds": 30
}
```

## Como Usar

Rodar tudo:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py
```

Rodar tudo sem baixar mercado novo, usando `market/latest_market.json`:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --skip-update
```

Buscar upgrades no trade com 251 chaos:

```powershell
python poe_market_filter_toolkit\scripts\find_upgrade_deals.py --budget 251c
```

Buscar upgrades com 1 divine:

```powershell
python poe_market_filter_toolkit\scripts\find_upgrade_deals.py --budget 1d
```

Buscar apenas alguns tipos de upgrade:

```powershell
python poe_market_filter_toolkit\scripts\find_upgrade_deals.py --budget 251c --profiles ring_vulnerability,jewel_damage,large_cluster
```

Planejar compras 1x1, 2x2 e 3x3 dentro do budget:

```powershell
python poe_market_filter_toolkit\scripts\plan_upgrade_path.py --budget 251c
```

Perfis disponiveis no buscador de upgrades:

```text
ring_vulnerability
jewel_damage
abyss_jewel
large_cluster
rumi_uncorrupted
```

## Scripts

### `update_market.py`

Baixa precos do poe.ninja para as categorias configuradas em `market_config.json`.

Gera:

```text
poe_market_filter_toolkit/market/latest_market.json
poe_market_filter_toolkit/market/snapshots/*.json
```

### `market_report.py`

Le o `latest_market.json` e cria uma visao legivel dos itens por preco.

Gera:

```text
poe_market_filter_toolkit/market/reports/market_report.md
poe_market_filter_toolkit/market/reports/market_report.csv
```

### `suggest_filter_tiers.py`

Compara o mercado com os `BaseType` encontrados nos filtros e aponta itens que podem merecer destaque.

Gera:

```text
poe_market_filter_toolkit/market/reports/filter_suggestions.md
```

Uso recomendado: revisar o relatorio e aplicar manualmente apenas nomes validos no filtro.

### `filter_audit.py`

Audita o filtro atual procurando riscos como:

- `BaseType` potencialmente invalido;
- nomes de itens unicos usados no lugar errado;
- regras muito genericas;
- duplicacoes ou secoes que podem capturar itens antes da regra correta.

Gera:

```text
poe_market_filter_toolkit/market/reports/filter_audit.md
```

### `run_all.py`

Executa, em ordem:

```text
update_market.py
market_report.py
suggest_filter_tiers.py
filter_audit.py
```

E o comando principal para atualizar os relatorios de mercado e auditar o filtro.

### `find_upgrade_deals.py`

Consulta a API oficial de trade do Path of Exile, busca itens listados por jogadores e ranqueia candidatos de upgrade para a build.

Ele usa regras conservadoras para evitar downgrades obvios, por exemplo:

- nao sugerir aneis sem vida ou sem resistencias uteis;
- nao sugerir jewels sem dano relevante;
- nao sugerir cluster fora do perfil desejado;
- respeitar o budget informado pelo usuario.

Gera:

```text
poe_market_filter_toolkit/market/reports/upgrade_deals.md
```

Esse relatorio e ignorado pelo Git porque os resultados mudam rapidamente.

### `plan_upgrade_path.py`

Le arquivos estruturados em `poe_market_filter_toolkit/builds/`, busca candidatos no trade e testa combinacoes de compra:

```text
1 item por 1 item
2 itens por 2 itens
3 itens por 3 itens
```

Ele considera:

- budget informado pelo usuario;
- slots travados, como peitoral e luvas atuais;
- pisos minimos da build, como resistencias, vida e chance de acerto;
- metas da build alvo, como Impale, Chaos Resistance, Spell Block e Vulnerability on Hit;
- possibilidade real de existir menos que top 10 ofertas seguras.

Gera:

```text
poe_market_filter_toolkit/market/reports/upgrade_plan.md
```

Arquivos de entrada:

```text
poe_market_filter_toolkit/builds/player_items.json
poe_market_filter_toolkit/builds/player_stats.json
poe_market_filter_toolkit/builds/target_build_items.json
poe_market_filter_toolkit/builds/target_build_stats.json
poe_market_filter_toolkit/builds/upgrade_rules.json
```

## Fluxo Recomendado

1. Atualize os precos:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py
```

2. Leia os relatorios:

```text
poe_market_filter_toolkit/market/reports/market_report.md
poe_market_filter_toolkit/market/reports/filter_suggestions.md
poe_market_filter_toolkit/market/reports/filter_audit.md
```

3. Ajuste o filtro manualmente quando fizer sentido.

4. Busque upgrades com o budget real:

```powershell
python poe_market_filter_toolkit\scripts\find_upgrade_deals.py --budget 251c
```

5. Planeje combos quando quiser saber se duas ou tres compras juntas resolvem melhor o personagem:

```powershell
python poe_market_filter_toolkit\scripts\plan_upgrade_path.py --budget 251c
```

6. Antes de comprar, confira no trade, no PoE Overlay e, se for item de equipamento, no PoB.

## Cuidados Importantes

- Preco de mercado muda rapido. Relatorios sao fotografia do momento.
- Nem todo item caro usa `BaseType` valido no filtro.
- Alguns recursos do filtro sao sensiveis a nomes exatos, principalmente `BaseType`, `HasExplicitMod` e `EnchantmentPassiveNode`.
- Itens unicos especificos, mapas unicos e nomes de divination cards podem exigir regra por `Class` ou outra condicao, nao apenas `BaseType`.
- O buscador de upgrades avalia custo-beneficio por regras simples. Ele ajuda a cortar lixo, mas ainda pode deixar passar item ruim ou ignorar item bom.

## Estado Atual Da Build

Resumo do arquivo `equipamentos_e_status_atuais_poe_slayer.txt`:

- Accuracy resolvida para o momento: 2543 de Accuracy Rating e 96% de chance de acerto.
- Gargalos principais: Impale, Vulnerability on Hit, jewels/cluster, Spell Block, ailment avoidance e Chaos Resistance.
- As luvas atuais tem papel importante na build e nao devem ser trocadas apenas por preco.
- Prioridades provaveis de compra: anel com Vulnerability, jewels de dano, cluster bom, Rumi's Concoction nao corrompido com rolagem melhor e pecas que melhorem defesa sem derrubar resistencias.

## Arquivos Gerados

Normalmente versionados:

```text
poe_market_filter_toolkit/market/reports/market_report.md
poe_market_filter_toolkit/market/reports/market_report.csv
poe_market_filter_toolkit/market/reports/filter_suggestions.md
poe_market_filter_toolkit/market/reports/filter_audit.md
```

Normalmente ignorados pelo Git:

```text
poe_market_filter_toolkit/market/latest_market.json
poe_market_filter_toolkit/market/snapshots/*.json
poe_market_filter_toolkit/market/trade_stats_cache.json
poe_market_filter_toolkit/market/reports/upgrade_deals.md
poe_market_filter_toolkit/market/reports/upgrade_plan.md
poe_market_filter_toolkit/filters/current/*.filter
```

## Referencia Da Build

```text
https://mobalytics.gg/poe/builds/ronarray-shockwave-cyclone-generals-cry-slayer
```
