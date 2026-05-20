# PoE Filter Toolkit

Projeto para manter filtros de loot do Path of Exile, gerar relatorios de mercado e planejar upgrades para a build alvo ativa.

Filtro principal:

```text
active_loot_filter.filter
```

Contexto atual:

```text
Path of Exile 1 - 3.28 Mirage
Build ativa: definida em poe_market_filter_toolkit/builds/active_build.json
Conteudo: mapas T9/T10
Atlas: Breach Hives / Wombgifts + Delirium
Estado do personagem: poe_market_filter_toolkit/builds/player_items.json e player_stats.json
```

## Duas Funcionalidades

O repositorio tem duas trilhas que usam dados de mercado, mas com objetivos diferentes.

### 1. Filtro de loot dentro do jogo

O filtro existe para facilitar a vida do jogador durante mapas: destacar itens bons, currencies caras, drops da build e coisas que valem pegar no chao.

O mercado entra aqui como fonte de manutencao:

- confirmar nomes, classes, currencies e `BaseType`;
- perceber quais itens estao caros ou liquidos;
- corrigir nomes que quebram o parser;
- ajustar destaques do filtro sem transformar preco de mercado em regra automatica cega.

Scripts principais dessa trilha:

```text
update_market.py
market_report.py
suggest_filter_tiers.py
filter_audit.py
```

### 2. Busca de upgrades para a build

Essa trilha procura itens vendidos por jogadores e tenta responder: "com o budget atual, quais compras aproximam meu personagem da build alvo sem piorar pontos essenciais?"

Ela usa:

- equipamentos e status atuais do jogador;
- itens e status alvo da build;
- regras de seguranca da build;
- API oficial de trade;
- budget em chaos/divines quando informado.

Scripts principais dessa trilha:

```text
fetch_character.py
parse_character.py
compare_current_to_target.py
recommend_next_steps.py
find_upgrade_deals.py
plan_upgrade_path.py
generate_dashboard.py
```

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

Listar builds alvo salvas:

```powershell
python poe_market_filter_toolkit\scripts\switch_build.py --list
```

Criar/ativar uma build alvo a partir dos arquivos atuais em `builds/`:

```powershell
python poe_market_filter_toolkit\scripts\switch_build.py --name "Minha Build" --pob-url "https://pobb.in/..." --from-current --activate
```

Trocar para uma build alvo ja cadastrada:

```powershell
python poe_market_filter_toolkit\scripts\switch_build.py --switch-to minha_build
```

Tambem da para trocar a build antes de rodar o fluxo:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --switch-build minha_build --skip-update --compare-build --recommend-next --upgrade-plan --budget 500c --dashboard
```

Rodar relatorios para varias builds e abrir uma pagina com seletor:

```powershell
python poe_market_filter_toolkit\scripts\run_build_matrix.py --builds ronarray_shockwave_cyclone_slayer,teste_storm_burst_totem --budget 500c --max-fetch 9
start poe_market_filter_toolkit\data\generated\multi_build_dashboard.html
```

Ou via fluxo principal:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --builds all --budget 500c --max-fetch 9
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

Planejar compras 1x1, 2x2 e 3x3 usando o budget como teto por plano de upgrade:

```powershell
python poe_market_filter_toolkit\scripts\plan_upgrade_path.py --budget 251c
```

Sem budget, o planejador busca os 3 upgrades seguros mais baratos:

```powershell
python poe_market_filter_toolkit\scripts\plan_upgrade_path.py
```

Rodar mercado, auditoria e planejador de uma vez:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --upgrade-plan --budget 251c
```

Capturar personagem pela API oficial da GGG, parsear e gerar analise de gaps:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --fetch-character --compare-build
```

Gerar proximas buscas e recomendacoes a partir dos gaps:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --compare-build --recommend-next
```

Gerar um painel HTML unico:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --skip-update --compare-build --recommend-next --upgrade-plan --budget 251c --dashboard
start poe_market_filter_toolkit\data\generated\build_dashboard.html
```

O painel agora e a tela principal para usuario leigo na trilha de upgrades da build: ele junta resumo da build, gaps, slots sensiveis, proximas buscas, planos de compra, links do trade, link direto da listagem via API e o whisper do vendedor.

Rodar os testes de seguranca:

```powershell
python -m unittest discover -s poe_market_filter_toolkit\tests
```

Para permitir que o parser atualize os arquivos usados pelo planejador:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --fetch-character --compare-build --update-builds
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

- budget informado pelo usuario como teto para uma troca 1x1, 2x2 ou 3x3, nao como soma de todas as ideias do relatorio;
- amostragem por faixas de preco dentro do budget, para nao olhar apenas os itens mais baratos quando o budget e alto;
- slots sensiveis, como peitoral e luvas atuais;
- pisos minimos da build, como resistencias, vida e chance de acerto;
- metas da build alvo, como Impale, Chaos Resistance, Spell Block e Vulnerability on Hit;
- possibilidade real de existir menos que top 10 ofertas seguras.

Gera:

```text
poe_market_filter_toolkit/market/reports/upgrade_plan.md
poe_market_filter_toolkit/market/reports/upgrade_plan.html
poe_market_filter_toolkit/market/reports/upgrade_plan.json
```

Se `--budget` nao for informado, mostra por padrao o top 3 dos upgrades seguros mais baratos encontrados. Quando `--budget` e informado, ele ranqueia os melhores planos seguros ate aquele teto e ainda mostra uma secao separada de melhor compra barata sem usar o budget como limite. A versao HTML e melhor para usuario leigo porque abre no navegador e traz links clicaveis para o trade oficial, para a listagem especifica via API e para o whisper.

Arquivos de entrada:

```text
poe_market_filter_toolkit/builds/player_items.json
poe_market_filter_toolkit/builds/player_stats.json
poe_market_filter_toolkit/builds/target_build_items.json
poe_market_filter_toolkit/builds/target_build_stats.json
poe_market_filter_toolkit/builds/upgrade_rules.json
```

### `fetch_character.py`

Busca o personagem autenticado na API oficial do Path of Exile.

Precisa de:

```text
poe_market_filter_toolkit/config/account_config.json
POE_OAUTH_TOKEN ou poe_market_filter_toolkit/secrets/tokens.json
```

Saida:

```text
poe_market_filter_toolkit/data/raw/character_api_raw.json
```

### `oauth_login.py`

Ajuda a criar `secrets/tokens.json` usando OAuth com PKCE depois que voce tiver um `client_id` aprovado pela GGG.

Implementacao alinhada ao fluxo oficial de cliente publico: Authorization Code com PKCE, `redirect_uri` local e escopo `account:characters`.

Antes de usar:

```text
1. Copie poe_market_filter_toolkit/config/oauth_config.example.json para oauth_config.json.
2. Preencha client_id.
3. Confirme redirect_uri = http://127.0.0.1:8080/callback.
```

Rodar:

```powershell
python poe_market_filter_toolkit\scripts\oauth_login.py
```

Depois:

```powershell
python poe_market_filter_toolkit\scripts\fetch_character.py
```

### `oauth_refresh.py`

Renova `secrets/tokens.json` quando houver `refresh_token`. O `fetch_character.py` tambem tenta renovar automaticamente quando o token salvo estiver vencido ou perto de vencer.

```powershell
python poe_market_filter_toolkit\scripts\oauth_refresh.py
```

### `parse_character.py`

Converte o JSON cru da API oficial em arquivos normalizados:

```text
poe_market_filter_toolkit/data/current/player_items.json
poe_market_filter_toolkit/data/current/player_stats.json
poe_market_filter_toolkit/data/current/player_passives.json
poe_market_filter_toolkit/data/current/player_skills.json
```

Use `--update-builds` para copiar `player_items.json` e `player_stats.json` para `poe_market_filter_toolkit/builds/`. Se quiser preservar a versao anterior antes de sobrescrever, adicione `--backup-builds`.

### `switch_build.py`

Gerencia multiplas builds alvo. Cada build fica em:

```text
poe_market_filter_toolkit/builds/profiles/<slug>/
```

Cada perfil guarda:

```text
build_profile.json
target_build_items.json
target_build_stats.json
upgrade_rules.json
```

Ao ativar uma build, o script copia esses tres arquivos alvo para `poe_market_filter_toolkit/builds/`, que e o local lido pelo comparador, recomendador e planejador de compras. O link ou codigo do PoB fica salvo em `build_profile.json`; parsing automatico completo de PoB ainda deve ser tratado como etapa futura, entao revise os arquivos alvo quando criar uma build nova.

Comandos uteis:

```powershell
python poe_market_filter_toolkit\scripts\switch_build.py --list
python poe_market_filter_toolkit\scripts\switch_build.py --name "Nova Build" --pob-url "https://pobb.in/..." --from-current --activate
python poe_market_filter_toolkit\scripts\switch_build.py --switch-to nova_build
python poe_market_filter_toolkit\scripts\switch_build.py --delete-build nova_build
```

Se a build estiver ativa, troque para outra antes de apagar ou use `--force`.

Perfis de personagem atual tambem podem ser salvos, carregados e removidos:

```powershell
python poe_market_filter_toolkit\scripts\switch_build.py --create-character "Meu Slayer" --character-from-current
python poe_market_filter_toolkit\scripts\switch_build.py --list-characters
python poe_market_filter_toolkit\scripts\switch_build.py --switch-character meu_slayer
python poe_market_filter_toolkit\scripts\switch_build.py --delete-character meu_slayer
```

Cada personagem pode ser associado a uma build alvo. Ao carregar o personagem, a build associada tambem e ativada por padrao:

```powershell
python poe_market_filter_toolkit\scripts\switch_build.py --create-character "Meu Deadeye" --character-from-current --character-build maxroll_maobaf03
python poe_market_filter_toolkit\scripts\switch_build.py --set-character-build meu_deadeye maxroll_maobaf03
python poe_market_filter_toolkit\scripts\switch_build.py --switch-character meu_deadeye
```

Se quiser carregar o personagem sem trocar a build alvo:

```powershell
python poe_market_filter_toolkit\scripts\switch_build.py --switch-character meu_deadeye --no-switch-character-build
```

### `run_build_matrix.py`

Executa a analise para varias builds alvo e salva uma copia dos HTML/JSON/Markdown de cada uma em:

```text
poe_market_filter_toolkit/data/generated/builds/<slug>/
```

Tambem gera:

```text
poe_market_filter_toolkit/data/generated/multi_build_dashboard.html
```

Esse HTML tem seletor de build e links para dashboard, plano de compra, recomendacoes e PoB de cada perfil. E o caminho recomendado quando voce quer acompanhar sua build e a build de um amigo na mesma sessao.

Exemplos:

```powershell
python poe_market_filter_toolkit\scripts\run_build_matrix.py --builds all --budget 500c --max-fetch 9
python poe_market_filter_toolkit\scripts\run_build_matrix.py --builds minha_build,build_do_amigo --budget 1d
```

### `compare_current_to_target.py`

Compara o estado atual com as metas da build alvo.

Gera:

```text
poe_market_filter_toolkit/data/generated/gap_analysis.json
poe_market_filter_toolkit/data/generated/gap_analysis.md
```

### `recommend_next_steps.py`

Le `gap_analysis.json` e gera uma recomendacao deterministica, sem IA, para servir como MVP do futuro agente local.

Gera:

```text
poe_market_filter_toolkit/data/generated/next_searches.md
poe_market_filter_toolkit/data/generated/upgrade_recommendations.md
poe_market_filter_toolkit/data/generated/upgrade_report.json
```

### `generate_dashboard.py`

Junta gaps, proximas buscas, recomendacoes e plano de compra em um HTML unico.

Gera:

```text
poe_market_filter_toolkit/data/generated/build_dashboard.html
```

Ele usa `market/reports/upgrade_plan.json` quando disponivel, entao os botoes do dashboard apontam para os arquivos corretos e os cards de compra mostram preco, vendedor, ganhos, alertas, busca no trade, JSON tecnico da listagem e whisper.

Tambem gera paginas HTML auxiliares para `Recomendacoes`, `Proximas buscas` e `Mercado`, evitando abrir Markdown cru no navegador. A pagina `Mercado` usa dados estruturados de `latest_market.json` para montar resumo por categoria, cards de itens relevantes, busca, filtros e ordenacao. A auditoria do filtro continua apenas como relatorio tecnico em Markdown.

### Testes

Os testes ficam em:

```text
poe_market_filter_toolkit/tests/
```

Eles validam regras de seguranca como slots sensiveis, Strength sem valor de vida com Brass Dome e prioridade correta das recomendacoes.

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

6. Para rodar tudo em uma so chamada:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --upgrade-plan --budget 251c
```

7. Antes de comprar, confira no trade, no PoE Overlay e, se for item de equipamento, no PoB.

## Cuidados Importantes

- Preco de mercado muda rapido. Relatorios sao fotografia do momento.
- Nem todo item caro usa `BaseType` valido no filtro.
- Alguns recursos do filtro sao sensiveis a nomes exatos, principalmente `BaseType`, `HasExplicitMod` e `EnchantmentPassiveNode`.
- Itens unicos especificos, mapas unicos e nomes de divination cards podem exigir regra por `Class` ou outra condicao, nao apenas `BaseType`.
- O buscador de upgrades avalia custo-beneficio por regras simples. Ele ajuda a cortar lixo, mas ainda pode deixar passar item ruim ou ignorar item bom.

## Estado Atual Da Build

Resumo do personagem usado como base atual:

- Accuracy resolvida para o momento: 2543 de Accuracy Rating e 96% de chance de acerto.
- Gargalos principais: Impale, Vulnerability on Hit, jewels/cluster, Spell Block, ailment avoidance e Chaos Resistance.
- As luvas atuais tem papel importante na build; podem ser trocadas, mas so quando a melhora for clara e nao quebrar accuracy, vida ou resistencias.
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
poe_market_filter_toolkit/market/reports/upgrade_plan.html
poe_market_filter_toolkit/market/reports/upgrade_plan.json
poe_market_filter_toolkit/filters/current/*.filter
```

## Referencia Da Build

```text
https://mobalytics.gg/poe/builds/ronarray-shockwave-cyclone-generals-cry-slayer
```
