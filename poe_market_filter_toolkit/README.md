# PoE Market Filter Toolkit

Toolkit em Python para consultar precos do mercado de Path of Exile 1 no poe.ninja e gerar relatorios de apoio para revisar o filtro de loot.

Este pacote fica dentro de `poe_market_filter_toolkit/` e foi adaptado para o repositório atual. Ele analisa automaticamente:

- filtros `.filter` colocados em `poe_market_filter_toolkit/filters/current/`;
- filtros `.filter` que estejam na raiz do repositorio, incluindo o filtro ativo deste projeto.

O toolkit nao edita o filtro automaticamente. Ele coleta mercado, gera relatorios e aponta itens caros ausentes/presentes para revisao manual.

## Como rodar

Na raiz do repositorio:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py
```

Ou pelo PowerShell helper:

```powershell
.\poe_market_filter_toolkit\run_all.ps1
```

## Arquivos gerados

```text
poe_market_filter_toolkit/market/latest_market.json
poe_market_filter_toolkit/market/snapshots/market_YYYY-MM-DD_HHMMSS.json
poe_market_filter_toolkit/market/reports/market_report.md
poe_market_filter_toolkit/market/reports/market_report.csv
poe_market_filter_toolkit/market/reports/filter_suggestions.md
poe_market_filter_toolkit/market/reports/filter_audit.md
```

## API usada

O toolkit usa os endpoints atuais do poe.ninja para Path of Exile 1:

```text
https://poe.ninja/poe1/api/economy/exchange/current/overview
https://poe.ninja/poe1/api/economy/stash/current/item/overview
```

A liga padrao esta em:

```text
config/market_config.json
```

Atualmente:

```json
{
  "league": "Mirage"
}
```

## Categorias

Categorias de exchange:

```text
Currency
Fragment
Scarab
Fossil
Resonator
Essence
DivinationCard
Oil
DeliriumOrb
Omen
Tattoo
Runegraft
AllflameEmber
```

Categorias de stash:

```text
Map
UniqueMap
SkillGem
ClusterJewel
Invitation
Memory
Beast
```

## Relatorios

`market_report.md` mostra todos os itens coletados por tier de chaos.

`filter_suggestions.md` compara o mercado com os `BaseType` encontrados no filtro e destaca itens caros ausentes ou presentes.

`filter_audit.md` procura sinais estruturais de risco, como BaseTypes duplicados, nomes marcados como arriscados/removidos e regras genericas que podem vir antes de regras especificas.

## Uso seguro de BaseType

Nem todo nome vindo do poe.ninja/PoE Overlay e um `BaseType` valido para o parser do filtro.

Regra pratica:

```text
Categorias de exchange simples -> podem virar BaseType apos revisao.
Categorias de stash -> revisar manualmente e preferir regra estrutural.
```

Casos que nao devem ser convertidos automaticamente para `BaseType`:

```text
UniqueMap   -> usar Class "Maps" + Rarity Unique; excecao para bases reais conhecidas.
SkillGem    -> usar Class, GemLevel, Quality e Corrupted.
ClusterJewel-> usar base do cluster + EnchantmentPassiveNum; evitar EnchantmentPassiveNode automatico.
Beast       -> tratar como informacao de mercado, nao como drop normal garantido.
```

Exemplo: `Doryani's Machinarium` e `Charged Dash of Projection` aparecem como nomes de mercado, mas causam erro quando usados diretamente em `BaseType`. Em clusters, descricoes de enchant vindas do mercado tambem podem falhar em `EnchantmentPassiveNode`; prefira `EnchantmentPassiveNum` ate validar o texto exato.

## Observacoes

- `listing_count` representa listagens nas categorias de stash e volume/liquidez nas categorias de exchange.
- Itens com preco alto e pouca liquidez devem ser revisados manualmente.
- O relatorio de auditoria pode apontar duplicatas intencionais, porque o filtro usa regras globais de jackpot antes de regras genericas.
