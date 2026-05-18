# Plano de automação — PoE Build Agent

Este documento descreve um plano técnico para automatizar o acompanhamento de uma build de Path of Exile usando:

- personagem real pela API oficial da GGG;
- build-alvo via PoB/pobb.in;
- guia humano da Mobalytics;
- mercado via poe.ninja;
- agente de IA local, como Llama/Ollama, para gerar regras e recomendações.

Build-alvo:

```text
Ronarray Shockwave Cyclone / General's Cry Slayer
Fonte humana: Mobalytics
Fonte mecânica: PoB / pobb.in
```

Fonte da build:

```text
https://mobalytics.gg/poe/builds/ronarray-shockwave-cyclone-generals-cry-slayer
```

Para o estágio atual do personagem, usar como alvo principal:

```text
Lvl 92+ Endgame
```

Evitar como alvo principal imediato:

```text
Lvl 96 - UBER
Final - MB
```

Essas versões finais devem ser tratadas como referência de longo prazo, não como objetivo imediato de compra.

---

# 1. Objetivo geral

Criar um sistema que acompanhe automaticamente a build do jogador e gere:

```text
player_items.json
player_stats.json
player_passives.json
target_build_items.json
target_build_stats.json
target_build_passives.json
upgrade_rules.json
next_searches.md
upgrade_recommendations.md
```

A ideia é combinar:

```text
GGG Official API       -> estado real do personagem
PoB / pobb.in          -> build-alvo e cálculo mecânico
Mobalytics             -> notas humanas e prioridade do autor
poe.ninja              -> preços de mercado
Agente de IA           -> interpretação, pesos, regras e recomendação final
```

O agente de IA não deve ser o calculador principal de mecânicas. Ele deve atuar como interpretador/orquestrador. O cálculo mecânico pesado deve vir do Path of Building sempre que possível.

---

# 2. Fontes de dados

## 2.1 Personagem real do jogador

Fonte preferida:

```text
Path of Exile Official API
```

Endpoint principal:

```text
GET /character[/<realm>]/<name>
```

Escopo OAuth necessário:

```text
account:characters
```

A API oficial retorna dados do personagem, incluindo:

```text
equipment
inventory
jewels
passives
```

Em `passives`, usar dados como:

```text
hashes
hashes_ex
mastery_effects
bandit_choice
pantheon_major
pantheon_minor
jewel_data
```

O campo `jewel_data` é importante para detectar sockets, jewels e cluster jewels.

Não usar leitura de memória do jogo nem automação do client. O caminho correto é API oficial ou importação via Path of Building.

---

## 2.2 Build-alvo

Fonte principal:

```text
pobb.in / Path of Building code
```

Fonte humana complementar:

```text
Mobalytics
```

Usar a Mobalytics para informações interpretativas:

```text
- versão recomendada;
- ordem de progressão;
- avisos sobre itens caros;
- prioridades escritas pelo autor;
- observações sobre Overlord, block, chaos resistance, mana issues etc.
```

Usar o PoB/pobb.in como fonte mecânica:

```text
- árvore;
- itens-alvo;
- gemas;
- configurações;
- auras;
- flasks;
- passivas;
- estatísticas calculadas.
```

Ordem de qualidade das fontes:

```text
1. PoB code / pobb.in da build
2. Export do Path of Building
3. Página do guia, como Mobalytics
4. Texto/scraping do guia
5. Prints manuais
```

---

## 2.3 Mercado

Fonte principal:

```text
poe.ninja
```

Objetivo:

```text
- preços de currency;
- scarabs;
- divination cards;
- essences;
- fossils;
- resonators;
- oils;
- omens;
- tattoos;
- mapas;
- unique maps;
- gems;
- uniques;
- fragments;
```

Usar mercado para ranquear upgrades dentro do orçamento.

---

## 2.4 Dados manuais opcionais

Alguns dados podem precisar de entrada manual ou cálculo via PoB:

```text
DPS da aba do jogo
chance to hit
chance to hit evasive
effective hit pool
uptime real de flasks
sensação de mana
problemas de sobrevivência
```

A API oficial entrega dados crus, mas não deve ser tratada como calculadora completa da build.

---

# 3. Estrutura recomendada do repositório

```text
poe-build-agent/
├─ README.md
├─ .gitignore
├─ config/
│  ├─ account_config.example.json
│  ├─ account_config.json              # não versionar
│  ├─ agent_config.json
│  ├─ market_config.json
│  ├─ build_source.json
│  └─ protected_slots.json
├─ secrets/
│  └─ tokens.json                      # não versionar
├─ data/
│  ├─ raw/
│  │  ├─ character_api_raw.json
│  │  ├─ target_pob_raw.xml
│  │  ├─ target_pob_raw.txt
│  │  ├─ mobalytics_raw.html
│  │  └─ market_raw.json
│  ├─ current/
│  │  ├─ player_items.json
│  │  ├─ player_stats.json
│  │  ├─ player_passives.json
│  │  ├─ player_skills.json
│  │  └─ player_snapshot.md
│  ├─ target/
│  │  ├─ target_build_items.json
│  │  ├─ target_build_stats.json
│  │  ├─ target_build_passives.json
│  │  ├─ target_build_skills.json
│  │  └─ target_build_notes.json
│  ├─ market/
│  │  ├─ latest_market.json
│  │  └─ snapshots/
│  └─ generated/
│     ├─ upgrade_rules.json
│     ├─ next_searches.md
│     ├─ upgrade_recommendations.md
│     ├─ upgrade_report.json
│     └─ agent_reasoning_summary.md
├─ scripts/
│  ├─ fetch_character.py
│  ├─ parse_character.py
│  ├─ fetch_target_pob.py
│  ├─ parse_pob.py
│  ├─ fetch_mobalytics_notes.py
│  ├─ fetch_market.py
│  ├─ normalize_market.py
│  ├─ compare_current_to_target.py
│  ├─ generate_upgrade_rules.py
│  ├─ recommend_upgrades.py
│  ├─ run_agent.py
│  └─ run_all.py
└─ tests/
   ├─ test_parse_items.py
   ├─ test_parse_passives.py
   └─ test_upgrade_rules.py
```

`.gitignore` recomendado:

```text
secrets/
config/account_config.json
data/raw/
*.log
.env
tokens.json
```

---

# 4. Configuração principal

## 4.1 `config/build_source.json`

```json
{
  "build_name": "Ronarray Shockwave Cyclone / General's Cry Slayer",
  "guide_url": "https://mobalytics.gg/poe/builds/ronarray-shockwave-cyclone-generals-cry-slayer",
  "target_variant": "Lvl 92+ Endgame",
  "pob_source_priority": [
    "3.28 Updated Guide POB Separately",
    "Lvl 92+ Endgame"
  ],
  "avoid_as_primary_target": [
    "Lvl 96 - UBER",
    "Final - MB"
  ],
  "notes": [
    "Use a variante 92+ Endgame como alvo intermediário.",
    "Não usar Progenesis, Forbidden Flame/Flesh e Mageblood como metas imediatas.",
    "A versão Uber serve como referência final, não como objetivo de compra atual."
  ]
}
```

## 4.2 `config/account_config.example.json`

```json
{
  "account_name": "ACCOUNT#0000",
  "character_name": "NOME_DO_PERSONAGEM",
  "realm": "pc",
  "league": "Mirage"
}
```

## 4.3 `config/agent_config.json`

```json
{
  "model_provider": "ollama",
  "model": "llama3.1:8b",
  "temperature": 0.2,
  "max_context_files": [
    "data/current/player_items.json",
    "data/current/player_stats.json",
    "data/current/player_passives.json",
    "data/target/target_build_items.json",
    "data/target/target_build_stats.json",
    "data/target/target_build_passives.json",
    "data/market/latest_market.json"
  ],
  "outputs": [
    "data/generated/upgrade_rules.json",
    "data/generated/next_searches.md",
    "data/generated/upgrade_recommendations.md"
  ]
}
```

---

# 5. Pipeline completo

## Etapa 1 — Capturar personagem real

Script:

```text
scripts/fetch_character.py
```

Entrada:

```text
config/account_config.json
secrets/tokens.json
```

Saída:

```text
data/raw/character_api_raw.json
```

Responsabilidades:

```text
1. Autenticar na API da GGG via OAuth.
2. Usar escopo account:characters.
3. Chamar GET /character[/<realm>]/<name>.
4. Salvar resposta crua.
5. Preservar headers úteis de rate limit, se disponíveis.
```

---

## Etapa 2 — Normalizar personagem

Script:

```text
scripts/parse_character.py
```

Entrada:

```text
data/raw/character_api_raw.json
```

Saídas:

```text
data/current/player_items.json
data/current/player_passives.json
data/current/player_skills.json
```

Extrair:

```text
- classe;
- level;
- league;
- equipamentos por slot;
- flasks;
- jewels;
- abyss jewels;
- cluster jewels;
- skills/gemas equipadas;
- passivas alocadas;
- masteries;
- bandits;
- pantheon;
- sockets de jewel;
- cluster subgraphs.
```

Normalizar cada item para este padrão:

```json
{
  "slot": "gloves",
  "name": "Death Knuckle",
  "base": "Precursor Gauntlets",
  "rarity": "Rare",
  "locked": false,
  "mods_raw": [],
  "stats_normalized": {
    "life": 113,
    "accuracy": 599,
    "fire_resistance": 34
  },
  "tags": [
    "attack",
    "physical",
    "staff_build"
  ]
}
```

---

## Etapa 3 — Capturar build-alvo via pobb.in

Script:

```text
scripts/fetch_target_pob.py
```

Entrada:

```text
config/build_source.json
```

Saída:

```text
data/raw/target_pob_raw.xml
```

Processo:

```text
1. Ler URL do pobb.in da variante escolhida.
2. Baixar o PoB code/raw.
3. Salvar conteúdo bruto.
4. Registrar qual variante foi usada.
```

---

## Etapa 4 — Parsear PoB-alvo

Script:

```text
scripts/parse_pob.py
```

Entrada:

```text
data/raw/target_pob_raw.xml
```

Saídas:

```text
data/target/target_build_items.json
data/target/target_build_passives.json
data/target/target_build_skills.json
data/target/target_build_stats.json
```

Extrair:

```text
- variantes/loadouts;
- itens por slot;
- gemas e links;
- árvore/passivas;
- masteries;
- configuração de auras;
- config de boss/flasks/charges;
- stats finais, quando disponíveis;
- itens caros marcados como endgame.
```

Classificar itens-alvo:

```text
early_map
midgame
lvl_92_endgame
uber
luxury
do_not_target_yet
```

Exemplo de lógica:

```text
Progenesis -> luxury / do_not_target_yet
Forbidden Flame/Flesh -> luxury / do_not_target_yet
Mageblood -> luxury / do_not_target_yet
Overlord cluster -> realistic_endgame
Watcher’s Eye Pride Impale -> realistic_endgame
Vulnerability on Hit ring -> realistic_endgame
```

---

## Etapa 5 — Capturar notas humanas da Mobalytics

Script:

```text
scripts/fetch_mobalytics_notes.py
```

Entrada:

```text
guide_url
```

Saída:

```text
data/target/target_build_notes.json
```

Extrair manualmente ou por parser:

```text
- versão da build;
- variantes;
- avisos importantes;
- prioridades de item stats;
- mana issues;
- Fortify/Overlord;
- chaos cap;
- block;
- skills principais.
```

Exemplo de regras derivadas da fonte:

```json
{
  "guide_notes": {
    "target_variant": "Lvl 92+ Endgame",
    "fortify": "Para versões 90+/Uber, buscar Overlord em Cluster Jewel.",
    "mana": "Se houver problema de mana, usar redução de custo ou craft de minus mana cost.",
    "luxury_last": [
      "Forbidden Flame",
      "Forbidden Flesh",
      "Progenesis"
    ]
  }
}
```

---

## Etapa 6 — Capturar mercado

Script:

```text
scripts/fetch_market.py
```

Saídas:

```text
data/market/latest_market.json
data/market/snapshots/market_YYYY-MM-DD.json
```

Categorias:

```text
Currency
Fragment
Scarab
DivinationCard
Essence
Fossil
Resonator
Oil
DeliriumOrb
Omen
Tattoo
Map
UniqueMap
SkillGem
ClusterJewel
UniqueArmour
UniqueWeapon
UniqueAccessory
```

Normalizar:

```json
{
  "name": "Watcher's Eye",
  "category": "UniqueJewel",
  "chaos_value": 40,
  "divine_value": 0.09,
  "listing_count": 23,
  "source": "poe.ninja"
}
```

---

## Etapa 7 — Comparar personagem com build-alvo

Script:

```text
scripts/compare_current_to_target.py
```

Entrada:

```text
data/current/*
data/target/*
data/market/latest_market.json
```

Saída:

```text
data/generated/gap_analysis.json
```

O arquivo deve responder:

```text
1. O que já está resolvido?
2. O que está abaixo do mínimo?
3. O que está abaixo da meta?
4. Quais slots são protegidos?
5. Quais upgrades são realistas dentro do orçamento?
6. Quais upgrades são luxo/finais?
```

Exemplo de saída:

```json
{
  "solved": {
    "impale_chance": {
      "current": 91,
      "goal": 80,
      "status": "solved"
    },
    "chance_to_hit": {
      "current": 94,
      "goal": 95,
      "status": "near_goal"
    }
  },
  "risks": {
    "life": {
      "current": 3951,
      "goal": 4500,
      "status": "needs_improvement"
    },
    "chaos_resistance": {
      "current": 23,
      "goal": 40,
      "status": "needs_improvement"
    },
    "spell_block": {
      "current": 17,
      "goal": 30,
      "status": "needs_improvement"
    }
  },
  "protected_slots": {
    "body_armour": "The Brass Dome",
    "gloves": "Death Knuckle"
  }
}
```

---

# 6. Papel do agente de IA

Script:

```text
scripts/run_agent.py
```

Modelo sugerido:

```text
Ollama / Llama
```

Entrada compactada para o agente:

```text
1. player_items.json
2. player_stats.json
3. player_passives.json
4. target_build_items.json
5. target_build_stats.json
6. target_build_notes.json
7. latest_market.json
8. gap_analysis.json
```

Saídas:

```text
upgrade_rules.json
next_searches.md
upgrade_recommendations.md
agent_reasoning_summary.md
```

---

## 6.1 Instruções fixas do prompt do agente

O prompt deve conter regras duras:

```text
Você é um analisador de build de Path of Exile.
Não invente mods que não estejam nos dados.
Não recomende trocar slots protegidos sem justificativa forte.
Não trate Strength como fonte de vida se The Brass Dome estiver equipado.
Não recomende itens de luxo como prioridade se orçamento for baixo/médio.
Não valorize Impale acima de 100%.
Não valorize projectile, spell, minion, elemental damage se a build for física de staff/cyclone.
Priorize upgrades com boa relação custo/benefício.
Gere arquivos JSON válidos.
Explique recomendações em Markdown.
```

---

# 7. Geração automática de `upgrade_rules.json`

Entrada:

```text
gap_analysis.json
target_build_notes.json
current gear
market
budget
```

Saída esperada:

```json
{
  "schema_version": 2,
  "budget": {
    "currency": "chaos",
    "amount": 171,
    "allow_partial_budget": true
  },
  "locked_slots": {
    "body_armour": "The Brass Dome é peça defensiva central.",
    "gloves": "Death Knuckle já resolve accuracy, vida e damage while leeching."
  },
  "current_priorities": {
    "maximum_life": "very_high",
    "chaos_resistance": "high",
    "spell_block": "medium",
    "corrupted_blood_immunity": "high",
    "vulnerability_on_hit": "medium_high",
    "impale_chance": "low",
    "accuracy": "medium"
  },
  "do_not_overvalue": [
    "strength_as_life_because_of_brass_dome",
    "projectile_speed",
    "spell_damage",
    "minion_damage",
    "extra_impale_above_100_percent"
  ],
  "minimums": {
    "life": 3800,
    "chance_to_hit": 90,
    "fire_resistance": 75,
    "cold_resistance": 75,
    "lightning_resistance": 75,
    "chaos_resistance": 0
  },
  "goals": {
    "life": 4500,
    "chance_to_hit": 95,
    "chance_to_hit_evasive": 90,
    "impale_chance": 90,
    "chaos_resistance": 40,
    "spell_block": 30,
    "elemental_ailment_avoidance": 50
  },
  "weights": {
    "maximum_life_percent": 120,
    "life": 1.4,
    "chaos_resistance": 2.0,
    "corrupted_blood_immunity": 120,
    "vulnerability_on_hit": 140,
    "attack_speed": 4,
    "crit_multiplier": 3,
    "physical_damage": 2,
    "accuracy": 0.02,
    "impale_chance": 1
  },
  "penalties": {
    "replacing_locked_slot": 1000,
    "missing_mana_cost_when_replacing_ring_1": 120,
    "losing_chaos_resistance_below_zero": 150,
    "no_life_on_jewel": 60,
    "luxury_item_too_early": 300
  }
}
```

---

# 8. Geração automática de `next_searches.md`

O agente deve gerar buscas práticas para o trade.

Exemplo:

```markdown
# Próximas buscas recomendadas

## 1. Jewel com Corrupted Blood immunity

Prioridade: alta

Buscar:
- Corrupted Blood cannot be inflicted on you
- 6% ou 7% increased maximum Life
- Attack Speed with Two Handed Melee Weapons
- Critical Strike Multiplier with Two Handed Melee Weapons
- Physical Damage / Melee Damage

Preço alvo:
- Até 60c: boa
- 60–100c: comprar só se tiver vida + dano real
- Acima de 100c: evitar, salvo jewel excelente

## 2. Jewel para substituir Soul Eye

Motivo:
Soul Eye tem dano, mas não tem maximum Life.

Buscar:
- 6–7% maximum Life
- Crit Multiplier
- Attack Speed
- Physical/Melee/Staff Damage

## 3. Abyss Jewel do cinto

Buscar:
- +35 ou mais maximum Life
- Adds Physical Damage to Staff Attacks
- Attack Speed if killed recently
- Chaos Resistance
```

---

# 9. Geração automática de `upgrade_recommendations.md`

Formato desejado:

```markdown
# Recomendações de upgrade

## Estado atual resumido

- Life: 3951
- Chaos Resistance: 23%
- Chance to Impale: 91%
- Chance to Hit: 94%
- Spell Block: 17%

## O que já está resolvido

- Impale está resolvido.
- Accuracy está aceitável.
- Luvas estão protegidas.
- Peitoral está protegido.

## Gargalos

1. Vida ainda baixa para progressão segura.
2. Chaos Resistance abaixo da meta de 40%.
3. Spell Block baixo.
4. Falta Corrupted Blood immunity permanente.

## Compra recomendada

### 1. Jewel com Life + Corrupted Blood immunity

Motivo:
Aumenta segurança sem mexer em slots protegidos.

### 2. Jewel com Life + Crit Multi + Attack Speed

Motivo:
Substitui Soul Eye, mantendo dano e ganhando vida.

### 3. Abyss Jewel melhor

Motivo:
Ancient Arbiter é funcional, mas fácil de melhorar.
```

---

# 10. Regras específicas para esta build

## 10.1 Slots protegidos

```json
{
  "body_armour": {
    "item": "The Brass Dome",
    "reason": "Peça defensiva central; não trocar em orçamento baixo/médio."
  },
  "gloves": {
    "item": "Death Knuckle",
    "reason": "Resolvem accuracy, vida e damage while leeching."
  },
  "ring_1": {
    "item": "Doom Knot",
    "reason": "Contém -mana cost para Cyclone; só trocar se novo anel preservar mana."
  }
}
```

## 10.2 Aviso sobre Strength

Regra obrigatória:

```text
Se The Brass Dome estiver equipado, Strength não deve ser convertida em valor defensivo de vida.
```

Pontuar Strength apenas como:

```text
- requisito de equipamento;
- requisito de gemas;
- atributo auxiliar.
```

Não pontuar como:

```text
- fonte de maximum life.
```

## 10.3 Impale

Regra:

```text
Se chance_to_impale >= 90, reduzir peso de impale_chance.
Se chance_to_impale >= 100, peso de impale_chance = 0.
```

## 10.4 Accuracy

Regra:

```text
Se chance_to_hit >= 94, tratar accuracy como prioridade média/baixa.
Se chance_to_hit < 90, tratar accuracy como prioridade alta.
```

## 10.5 Vulnerability on Hit

Regra:

```text
Vulnerability on Hit é forte, mas anel novo não pode destruir vida, chaos resistance ou mana cost.
```

Se substituir `ring_1`:

```text
exigir mana_cost_channeling ou prefixo aberto/craft equivalente
```

Se substituir `ring_2`:

```text
exigir chaos_resistance razoável ou compensação em outro slot
```

---

# 11. Validação

Criar testes simples.

## 11.1 Teste de JSON válido

```text
Todo arquivo gerado precisa ser JSON válido.
```

## 11.2 Teste de slots protegidos

```text
O agente não pode recomendar trocar body_armour ou gloves se não houver justificativa explícita e ganho alto.
```

## 11.3 Teste de Brass Dome

```text
Se The Brass Dome estiver equipado, Strength não pode aparecer como fonte de life no scoring.
```

## 11.4 Teste de Impale

```text
Se impale_chance atual >= 90, itens com apenas mais impale não devem receber prioridade alta.
```

## 11.5 Teste de orçamento

```text
Itens acima do orçamento devem aparecer como “monitorar depois”, não como compra imediata.
```

---

# 12. Comando final esperado

O fluxo completo deveria rodar assim:

```powershell
python scripts/run_all.py --budget-chaos 171
```

Ou em etapas:

```powershell
python scripts/fetch_character.py
python scripts/parse_character.py
python scripts/fetch_target_pob.py
python scripts/parse_pob.py
python scripts/fetch_market.py
python scripts/compare_current_to_target.py
python scripts/run_agent.py --budget-chaos 171
```

Saída final:

```text
data/current/player_items.json
data/current/player_stats.json
data/current/player_passives.json

data/target/target_build_items.json
data/target/target_build_stats.json
data/target/target_build_passives.json

data/generated/upgrade_rules.json
data/generated/next_searches.md
data/generated/upgrade_recommendations.md
```

---

# 13. Decisão técnica principal

A arquitetura deve usar:

```text
GGG Official API
→ estado real do personagem

PoB / pobb.in
→ build-alvo e cálculo mecânico

Mobalytics
→ notas humanas e prioridade do autor

poe.ninja
→ preços de mercado

Agente IA
→ interpretação, pesos, regras e recomendação final
```

O agente de IA deve gerar regras e recomendações revisáveis, não tomar decisão automática de compra nem editar itens sem validação humana.

---

# 14. Próximo passo de implementação

A implementação mínima viável deve priorizar:

```text
1. fetch_character.py
2. parse_character.py
3. fetch_market.py
4. import_target_pob.py ou fetch_target_pob.py
5. compare_current_to_target.py
6. run_agent.py
```

Depois disso, adicionar:

```text
- testes automatizados;
- integração com GitHub Actions;
- histórico de snapshots;
- geração de relatórios Markdown;
- exportação para ZIP;
- comandos de commit/push.
```
