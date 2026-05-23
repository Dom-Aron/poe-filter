# PoE Filter Toolkit

Projeto para manter filtros de loot do Path of Exile, gerar relatorios de mercado e planejar upgrades por personagem.

Filtro principal:

```text
active_loot_filter.filter
```

Contexto atual:

```text
Path of Exile 1 - 3.28 Mirage
Conteudo: mapas T9/T10
Atlas: Breach Hives / Wombgifts + Delirium
Fluxo recomendado: poe_market_filter_toolkit/scripts/run_character.py
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
  "request_delay_seconds": 1.5,
  "timeout_seconds": 30
}
```

## Como Usar

### Fluxo recomendado por personagem

O comando principal para upgrades agora e por personagem. Ele le o personagem e a build associada diretamente das pastas de perfil, atualiza/usa os dados atuais, compara com a build alvo, gera gaps, busca mercado, monta o plano de compra, gera os HTMLs e salva tudo separado em:

```text
poe_market_filter_toolkit/data/generated/characters/<personagem>/
```

Rodar o fluxo completo para um personagem salvo:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --open
```

Se a API oficial de trade responder com rate limit, o script agora espera ate 90s por padrao quando o servidor pedir. Para reduzir chamadas em uma rodada de teste:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --max-fetch 10 --request-delay 2 --open
```

Por padrao, a secao "melhor compra barata ignorando budget" reaproveita os itens ja buscados para evitar chamadas extras. Se quiser forcar buscas sem budget para essa secao, sabendo que isso aumenta o risco de rate limit:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --best-any-budget-mode extra --open
```

Usar o mercado ja baixado e nao rodar auditoria do filtro:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --skip-market-update --skip-filter-reports --open
```

Atualizar o personagem pela API oficial antes de comparar:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --fetch-character --parse-character --character-name "NomeDoPersonagem" --budget 1000c --open
```

Por padrao, o parser preserva `player_stats.json` manual porque a API oficial nao entrega todos os calculos de PoB. Para sobrescrever mesmo assim:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --fetch-character --parse-character --overwrite-manual-stats
```

Atalho equivalente pelo `run_all.py`:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --character aron_shockwave_cyclone_slayer --budget 1000c --open
```

Rodar para varios personagens salvos e gerar uma pagina indice:

```powershell
python poe_market_filter_toolkit\scripts\run_character_matrix.py --characters all --budget 1000c
start poe_market_filter_toolkit\data\generated\character_matrix_dashboard.html
```

Rodar mercado/filtro sem mexer nas builds/personagens:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py --skip-update
```

Listar builds alvo salvas:

```powershell
python poe_market_filter_toolkit\scripts\switch_build.py --list
```

Criar/editar perfis continua possivel com `switch_build.py`, mas o fluxo principal nao depende mais de build ativa global. Depois de criar a build, associe um personagem a ela e rode `run_character.py`.

Buscar upgrades no trade diretamente com as regras de uma build especifica:

```powershell
python poe_market_filter_toolkit\scripts\find_upgrade_deals.py --budget 251c --rules poe_market_filter_toolkit\builds\profiles\ronarray_shockwave_cyclone_slayer\upgrade_rules.json
```

Planejar compras diretamente para arquivos especificos e sem usar estado global:

```powershell
python poe_market_filter_toolkit\scripts\plan_upgrade_path.py --budget 251c --player-items poe_market_filter_toolkit\builds\characters\aron_shockwave_cyclone_slayer\player_items.json --player-stats poe_market_filter_toolkit\builds\characters\aron_shockwave_cyclone_slayer\player_stats.json --target-items poe_market_filter_toolkit\builds\profiles\ronarray_shockwave_cyclone_slayer\target_build_items.json --target-stats poe_market_filter_toolkit\builds\profiles\ronarray_shockwave_cyclone_slayer\target_build_stats.json --rules poe_market_filter_toolkit\builds\profiles\ronarray_shockwave_cyclone_slayer\upgrade_rules.json
```

Scripts legados que usam estado global ficam bloqueados por padrao quando oferecem risco de misturar builds:

```powershell
python poe_market_filter_toolkit\scripts\run_build_matrix.py --builds all
```

Para usar o fluxo legado intencionalmente, passe `--allow-legacy-global-state`. O caminho recomendado continua sendo por personagem.

Rodar os testes de seguranca:

```powershell
python -m unittest discover -s poe_market_filter_toolkit\tests
```

O parser nao deve mais atualizar os arquivos globais usados pelo planejador. Salve o parse dentro de `builds/characters/<personagem>/` ou use `run_character.py --parse-character`. O antigo `--update-builds` exige confirmacao explicita por flag de legado.

```powershell
python poe_market_filter_toolkit\scripts\parse_character.py --update-builds --allow-legacy-global-state
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

Quando chamado diretamente sem parametros de saida, gera:

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

### `run_character.py`

Orquestra o fluxo completo para **um personagem**. Este e o caminho mais seguro para evitar mistura entre builds/personagens, porque nao depende de `builds/active_build.json` nem dos arquivos globais `builds/player_items.json`, `builds/target_build_items.json`, etc. como fonte de verdade.

Entrada principal:

```text
poe_market_filter_toolkit/builds/characters/<personagem>/
poe_market_filter_toolkit/builds/profiles/<build_associada>/
```

Saida isolada:

```text
poe_market_filter_toolkit/data/generated/characters/<personagem>/
```

Dentro dessa pasta ficam:

```text
active_character.json
active_build.json
character/player_items.json
character/player_stats.json
build/target_build_items.json
build/target_build_stats.json
build/upgrade_rules.json
gap_analysis.json
upgrade_report.json
upgrade_plan.json
build_dashboard.html
upgrade_recommendations.html
next_searches.html
upgrade_plan.html
market_report.html
run_summary.json
```

Ordem executada:

```text
1. le o perfil do personagem e a build associada;
2. opcionalmente busca/parseia o personagem pela API oficial;
3. opcionalmente atualiza mercado;
4. gera relatorio de mercado;
5. opcionalmente gera relatorios tecnicos do filtro;
6. compara personagem atual com build alvo;
7. gera recomendacoes e proximas buscas;
8. busca itens no trade e testa planos 1x1, 2x2 e 3x3;
9. copia entradas e metadados para a pasta do personagem;
10. gera HTMLs do personagem e, com `--open`, abre o dashboard.
```

Exemplo:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --open
```

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

Arquivos de entrada padrao quando chamado diretamente:

```text
poe_market_filter_toolkit/builds/player_items.json
poe_market_filter_toolkit/builds/player_stats.json
poe_market_filter_toolkit/builds/target_build_items.json
poe_market_filter_toolkit/builds/target_build_stats.json
poe_market_filter_toolkit/builds/upgrade_rules.json
```

No fluxo recomendado `run_character.py`, esses caminhos sao substituidos por arquivos do personagem e da build associada, e as saidas sao gravadas em `data/generated/characters/<personagem>/`.

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

Gerencia cadastro de multiplas builds alvo e personagens. Ele ainda pode ativar/copiar arquivos para compatibilidade com scripts antigos, mas o fluxo recomendado `run_character.py` usa os perfis diretamente e nao precisa dessa ativacao global. Cada build fica em:

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

Ao ativar uma build, o script copia esses tres arquivos alvo para `poe_market_filter_toolkit/builds/` para manter compatibilidade com comandos antigos. O link ou codigo do PoB fica salvo em `build_profile.json`; parsing automatico completo de PoB ainda deve ser tratado como etapa futura, entao revise os arquivos alvo quando criar uma build nova.

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

### `run_character_matrix.py`

Executa `run_character.py` para varios personagens salvos e cria um indice em:

```text
poe_market_filter_toolkit/data/generated/character_matrix_dashboard.html
```

Esse e o caminho para acompanhar seu personagem e o personagem de um amigo sem misturar arquivos:

```powershell
python poe_market_filter_toolkit\scripts\run_character_matrix.py --characters all --budget 1000c --max-fetch 10
start poe_market_filter_toolkit\data\generated\character_matrix_dashboard.html
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
