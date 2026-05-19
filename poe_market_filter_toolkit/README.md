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

## Buscar upgrades no trade oficial

Para procurar compras com bom custo-beneficio para a build atual:

```powershell
python poe_market_filter_toolkit\scripts\find_upgrade_deals.py --budget 251c
```

Tambem aceita budget em divines:

```powershell
python poe_market_filter_toolkit\scripts\find_upgrade_deals.py --budget 1d
```

Perfis:

```text
ring_vulnerability
jewel_damage
abyss_jewel
large_cluster
rumi_uncorrupted
```

O relatorio fica em:

```text
poe_market_filter_toolkit/market/reports/upgrade_deals.md
```

O script consulta o trade oficial (`/api/trade/search` e `/api/trade/fetch`), aplica o budget em chaos/divines, ranqueia por score heuristico e imprime os melhores achados. Sempre confirme manualmente antes de comprar.

Para planejar compras combinadas dentro do budget:

```powershell
python poe_market_filter_toolkit\scripts\plan_upgrade_path.py --budget 251c
```

Sem budget, o planejador mostra os 3 upgrades seguros mais baratos encontrados:

```powershell
python poe_market_filter_toolkit\scripts\plan_upgrade_path.py
```

Esse planejador le os arquivos em `poe_market_filter_toolkit/builds/`, testa trocas 1x1, 2x2 e 3x3, e rejeita combinacoes que derrubem pisos minimos como vida, resistencias e chance de acerto.

Arquivos de entrada:

```text
builds/player_items.json
builds/player_stats.json
builds/target_build_items.json
builds/target_build_stats.json
builds/upgrade_rules.json
```

Relatorio:

```text
poe_market_filter_toolkit/market/reports/upgrade_plan.md
poe_market_filter_toolkit/market/reports/upgrade_plan.html
```

Se o relatorio mostrar menos que o top pedido, isso nao e erro: pode nao existir oferta suficiente, o budget pode estar baixo, ou a build atual pode ja estar boa nos slots pesquisados.

Para rodar mercado, auditoria e planejador de uma vez:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --upgrade-plan --budget 251c
```

Tambem funciona sem budget:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --upgrade-plan
```

## Capturar personagem pela API oficial

### 1. Pedir acesso OAuth para a GGG

A GGG informa na documentacao oficial que o registro de aplicacoes OAuth e feito por email para:

```text
oauth@grindinggear.com
```

Para este projeto, peca um **Public Client** com:

```text
Grant type: Authorization Code with PKCE
Scopes: account:characters
Redirect URI: http://127.0.0.1:8080/callback
```

Explique que o uso e pessoal/local, para ler o personagem da sua propria conta e gerar relatorios de build. Nao envie senha, token, client secret ou dados sensiveis por email.

### 2. Configurar conta e OAuth

Crie `config/account_config.json` a partir de `config/account_config.example.json`:

```json
{
  "account_name": "ACCOUNT#0000",
  "character_name": "NOME_DO_PERSONAGEM",
  "realm": "pc",
  "league": "Mirage"
}
```

Crie `config/oauth_config.json` a partir de `config/oauth_config.example.json`:

```json
{
  "client_id": "SEU_CLIENT_ID_APROVADO_PELA_GGG",
  "redirect_uri": "http://127.0.0.1:8080/callback",
  "scope": "account:characters",
  "authorization_url": "https://www.pathofexile.com/oauth/authorize",
  "token_url": "https://www.pathofexile.com/oauth/token"
}
```

### 3. Fazer login OAuth

Quando tiver o `client_id`, rode:

```powershell
python poe_market_filter_toolkit\scripts\oauth_login.py
```

O script abre o navegador, espera o callback local e salva:

```text
poe_market_filter_toolkit/secrets/tokens.json
```

Alternativa manual: forneca o token OAuth por variavel de ambiente:

```powershell
$env:POE_OAUTH_TOKEN="SEU_TOKEN"
```

Ou crie `secrets/tokens.json`:

```json
{
  "access_token": "SEU_TOKEN"
}
```

### 4. Rodar captura e analise

Rodar captura + parse + analise:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --fetch-character --compare-build
```

Gerar tambem proximas buscas e recomendacoes:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --fetch-character --compare-build --recommend-next
```

Gerar dashboard HTML unico:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --compare-build --recommend-next --upgrade-plan --dashboard
```

Rodar testes de seguranca:

```powershell
python -m unittest discover -s poe_market_filter_toolkit\tests
```

Para atualizar tambem os arquivos usados pelo planejador:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --fetch-character --compare-build --update-builds
```

Scripts envolvidos:

```text
fetch_character.py            -> salva data/raw/character_api_raw.json
parse_character.py            -> gera data/current/player_*.json
compare_current_to_target.py  -> gera data/generated/gap_analysis.*
recommend_next_steps.py       -> gera next_searches e upgrade_recommendations
generate_dashboard.py         -> gera data/generated/build_dashboard.html
```

Limitacoes importantes:

```text
O script nao substitui Path of Building.
O script nao compra automaticamente.
O script nao garante que o vendedor ainda esta online.
O script usa baselines conservadores do gear atual para evitar downgrades obvios.
O relatorio prioriza linguagem simples: acao, motivo e alertas.
```

## Arquivos gerados

```text
poe_market_filter_toolkit/market/latest_market.json
poe_market_filter_toolkit/market/snapshots/market_YYYY-MM-DD_HHMMSS.json
poe_market_filter_toolkit/market/reports/market_report.md
poe_market_filter_toolkit/market/reports/market_report.csv
poe_market_filter_toolkit/market/reports/filter_suggestions.md
poe_market_filter_toolkit/market/reports/filter_audit.md
poe_market_filter_toolkit/market/reports/upgrade_deals.md
poe_market_filter_toolkit/market/reports/upgrade_plan.md
poe_market_filter_toolkit/market/reports/upgrade_plan.html
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
