# Path of Exile — Shockwave Cyclone / General's Cry Slayer Loot Filter

Repositório para documentar e versionar o filtro de loot usado na build **Ronarray Shockwave Cyclone / General's Cry Slayer**, com foco em **Path of Exile 1 — 3.28 Mirage**, mapas **T9/T10** e estratégia de Atlas voltada para **Breach Hives / Wombgifts**.

Build de referência:

```text
https://mobalytics.gg/poe/builds/ronarray-shockwave-cyclone-generals-cry-slayer
```

Filtro atual recomendado:

```text
void_shockwave_cyclone_slayer_lvl89_t9_t10_breach_hives_market_v18_reviewed.filter
```

---

## 1. Objetivo do projeto

Este projeto existe para manter um histórico organizado do desenvolvimento do filtro de loot da build, evitando perder decisões importantes tomadas durante a progressão do personagem.

O filtro foi ajustado para:

- manter **currency mais aberta**, porque a build ainda precisa de upgrades frequentes;
- deixar **equipamentos comuns/raros mais estritos**, para não poluir mapas;
- destacar itens ligados ao farm de **Breach Hives**;
- destacar itens caros identificados pelo mercado do **PoE Overlay / Overwolf**;
- manter visíveis itens de ligas antigas e mecânicas secundárias com potencial de venda;
- evitar erros de parser causados por `BaseType` inválido, item class removida ou nomes incompletos;
- acompanhar o estado real do personagem, atualmente em mapas de tier 9 e 10.

---

## 2. Estado atual do personagem

> Observação: parte do histórico antigo mencionava level 90+, mas a informação mais recente usada no filtro v18 é **level 89**, fazendo mapas **T9/T10**.

```text
Classe: Slayer
Build: Shockwave Cyclone / General's Cry Slayer
Conteúdo atual: mapas T9/T10
Atlas: foco em Breach Hives
Estratégia: farmar Wombgifts/Hives e vender itens de alto valor
Tipo de dano: físico
Arma: staff
Defesas principais: armour, block, leech, The Brass Dome
Gargalos principais: Accuracy, Impale e Spell Block
```

A build gira em torno de:

```text
Cyclone
Shockwave / Void Shockwave
General's Cry
Dano físico
Staff
Block
Leech
Impale
Attack Speed
Accuracy
```

---

## 3. Equipamentos atuais conhecidos

### Arma

```text
Hate Mast
Ezomyte Staff

+25% Chance to Block Attack Damage while wielding a Staff
127% increased Physical Damage
21% chance to Impale Enemies on Hit with Attacks
55% increased Physical Damage
Adds 39 to 69 Physical Damage
+16% to Global Critical Strike Multiplier
+130 to Accuracy Rating
20% increased Attack Speed
```

Avaliação: boa o suficiente para o momento. Não era prioridade trocar com orçamento baixo.

### Capacete

```text
Miracle Visage
Penitent Mask

18% increased Attack Damage
21% reduced Mana Cost of Attacks
+91 Armour
62% increased Armour and Evasion
+52 maximum Life
+41% Fire Resistance
+40% Cold Resistance
+44% Lightning Resistance
```

Avaliação: funcional, mas com vida baixa. Pode ser upgrade futuro.

### Peitoral

```text
The Brass Dome
Gladiator Plate
```

Avaliação: peça defensiva forte. Mantém alta armour, máximo de resistências elementais e proteção contra dano extra de críticos. Não trocar com orçamento baixo.

### Anel comprado

```text
Doom Knot
Two-Stone Ring

Adds 4 to 10 Physical Damage to Attacks
+110 maximum Life
+14% to all Elemental Resistances
+31% Cold Resistance
Gain 48 Mana per Enemy Killed
Channelling Skills have -3 to Total Mana Cost crafted

Preço pago: 45 chaos
```

Avaliação: excelente compra. Resolve vida, resistência, dano físico e custo de Cyclone.

### Outro anel atual

```text
Ghoul Grip
Amethyst Ring

+23% Chaos Resistance implicit
+36 Dexterity
7% increased Attack Speed
+94 maximum Life
+29 maximum Mana
+30% Chaos Resistance
Adds 5 to 9 Physical Damage to Attacks
```

Avaliação: bom anel. Entrega vida, dexterity, chaos resistance, attack speed e physical damage.

### Amuleto

```text
Carnage Heart
Onyx Amulet
```

Avaliação: útil por atributos, resistências, leech e dano enquanto está leeching. Upgrade futuro possível, mas não imediato.

### Cinto comprado

```text
Bramble Tether
Stygian Vise

+35 Dexterity
+96 maximum Life
+46% Fire Resistance
+46% Lightning Resistance
1 Abyssal Socket

Preço: 65 chaos
```

Avaliação: upgrade defensivo importante em relação ao The Magnate. Abriu espaço para Abyss Jewel.

### Abyss Jewel comprada

```text
Ancient Arbiter
Murderous Eye Jewel

+14 Dexterity
+30 maximum Life
2 to 3 Added Physical Damage with Staff Attacks
Regenerate 0.8% of Life per second while moving

Preço: 19 chaos
```

Avaliação: compra econômica e coerente com a build.

### Luvas atuais

```text
Mind Grip
Precursor Gauntlets

10% chance to Impale Enemies on Hit with Attacks
Gain 1 Rage on Attack Hit
Adds 5 to 10 Physical Damage to Attacks
63% increased Armour
+90 maximum Life
+41% Fire Resistance
+29% Lightning Resistance
+35% Chaos Resistance
```

Avaliação: boas luvas, mas a prioridade futura é encontrar luvas com **Accuracy + Life + Attack Speed / Damage while Leeching**, sem perder defesas demais.

### Botas

```text
Grim Pace
Titan Greaves

16% chance to Avoid Elemental Ailments
4% increased Action Speed
+50 Strength
+115 Armour
+89 maximum Life
+46% Lightning Resistance
+30% Chaos Resistance
25% increased Movement Speed
```

Avaliação: boas. Não trocar agora.

### Flask comprado

```text
Rumi's Concoction
Rolls: 12 attack block / 4 spell block
Preço: 40 chaos
Corrupted: Sim
```

Avaliação: útil, mas por estar corrompido não aceita enchant automático. Futuramente, comprar um Rumi's não corrompido e aplicar:

```text
Used when Charges reach full
```

---

## 4. Status conhecidos do personagem

### Ofensivos

```text
DPS mostrado: 7162.43
Main Hand Chance to Hit: 77%
Main Hand Chance to Hit Evasive Monsters: 66%
Attacks per Second: 2.31
Main Hand Total Combined Damage: 1802–4887
Main Hand Physical Damage: 1802–4887
Accuracy Rating: 1229
Attack Speed Modifier: +54%
Critical Strike Chance: 21.25%
Critical Strike Multiplier: 196%
Chance to Impale: 56%
```

Interpretação:

- a **Accuracy** está baixa;
- a chance real de acerto prejudica dano, leech, crit e aplicação de Impale;
- antes de investir em dano bruto, corrigir chance to hit deve trazer ganho real maior;
- **Impale** também está baixo para uma build física.

### Defensivos

```text
Armour: 18438
Estimated Physical Damage Reduction: 75%
Evasion Rating: 868
Life Regeneration per Second: 32.4
Mana Regeneration per Second: 23.4

Fire Resistance: 81% (141%)
Cold Resistance: 80% (91%)
Lightning Resistance: 80% (185%)
Chaos Resistance: 58% (58%)

Chance to Block Attack Damage: 62%
Chance to Block Spell Damage: 17%

Cannot be Stunned: Yes
Elemental Ailment Avoidance: 16%
Movement Speed Modifier: +25%
Action Speed Modifier: +4%
```

Com Rumi's ativo:

```text
Attack Block: ~74%
Spell Block: ~21%
```

---

## 5. Ordem de upgrades da build

Ordem de prioridade documentada durante a progressão:

```text
1. Anel para substituir Le Heup
2. Cinto Stygian Vise
3. Abyss Jewel para o Stygian
4. Rumi's Concoction
5. Luvas com Accuracy + Life + Attack Speed/Damage while Leeching
6. Jewel normal com Life + Accuracy + dano
7. Corrigir Impale
8. Cluster Jewel físico
9. Capacete ou Abyssus, dependendo de defesa/dano
10. Amuleto raro melhor
11. Peitoral raro ou outro 6L
12. Staff melhor, só mais tarde
```

Já concluído:

```text
Anel: Doom Knot comprado
Cinto: Bramble Tether comprado
Abyss Jewel: Ancient Arbiter comprada
Rumi's Concoction: 12/4 comprado
```

Próximo foco recomendado:

```text
1. Accuracy / luvas
2. Impale
3. Jewel normal ou cluster físico
4. Rumi's não corrompido com enchant automático
```

---

## 6. Estratégia de Atlas e Breach Hives

Foco atual:

```text
Breach Hives
Wombgifts
Hivebrain Gland
Breach Scarabs
```

Prioridade de Wombgifts:

```text
1. Lavish Wombgift
2. Mysterious Wombgift
3. Ancient Wombgift
4. Provisioning Wombgift
```

Interpretação:

```text
Lavish      -> melhor para currency estável
Mysterious  -> aposta variada com potencial
Ancient     -> aposta em uniques
Provisioning-> gear/craft
```

Scarabs ligados à estratégia:

```text
Breach Scarab of the Hive              -> usar no farm
Breach Scarab of Instability           -> útil
Breach Scarab of the Incensed Swarm    -> útil
Breach Scarab of the Marshal           -> útil
Breach Scarab of Resonant Cascade      -> caro; vender ou usar só com estratégia clara
```

---

## 7. Filosofia do filtro

O filtro segue a lógica:

```text
Currency: aberta, mas hierarquizada
Gear raro: estrito
Breach/Hives: destacado
Itens caros de mercado: override no topo
Itens de ligas antigas: visíveis quando têm valor ou bulk
Bases da build: visíveis, mas sem poluir
Divination Cards: todas aparecem, com tiers por valor
Frascos: visíveis apenas quando úteis ou com qualidade
Gemas: qualidade alta, suportes importantes e Imbued
Mapas: destaque para Mirage, T9/T10, T11+, T14+
```

Decisão central:

> O filtro não deve esconder oportunidades de venda/currency, mas deve esconder o máximo possível de equipamento raro irrelevante.

---

## 8. Mercado usado como base

Os preços foram calibrados com prints do **PoE Overlay / Overwolf**, em chaos.

### Currency geral

```text
Divine Orb ~463c
Exalted Orb ~3.3c
Ancient Orb ~2.9c
Orb of Annulment ~12c
Gemcutter's Prism ~1.5c
Stacked Deck ~5.7c
```

Decisões:

```text
Divine e currency especial -> destaque alto
Exalted/Ancient -> não tratar como jackpot
GCP -> visível, útil para gemas
Instilling/Glassblower -> visível, mas discreto
Scrolls/shards -> pequenos, sem som
```

### Scarabs

```text
Breach Scarab of Resonant Cascade ~83c
Breach Scarab of the Hive -> baixo valor, mas útil para a estratégia
Horned Scarabs caros -> vender/precificar
Ambush/Harvest caros -> vender/precificar
Scarabs comuns -> visíveis, discretos
```

### Essences

Essências de destaque:

```text
Essence of Desolation ~135c
Deafening Essence of Scorn ~34c
Essence of Horror ~33c
Essence of Insanity ~32c
Essence of Hysteria ~27c
Essence of Delirium ~26c
```

### Delve / Fossils / Resonators

Itens de destaque:

```text
Prime Chaotic Resonator ~432c
Faceted Fossil ~332c
Hollow Fossil ~225c
Sanctified Fossil ~56c
Fractured Fossil ~54c
```

---

## 9. Categorias principais do filtro v19-dev

Depois da reorganização por liga/mecânica, o filtro atual possui as seguintes seções:

```text
0) Sempre mostrar itens AlwaysShow
0.5) Economia global — currency e itens de alto valor
0.6) Ligas antigas — Blight/Oils, Delirium, Legion e fragments/bosses
0.7) Ligas antigas — Metamorph/Catalysts, Ancestor/Omen/Tattoo, Expedition, Harvest/Lifeforce e Runegrafts
0.8) Ligas antigas — Allflame Embers e Djinn Coins
0.9) Ligas antigas — Essences e Delve/Fossils/Resonators
1) Liga atual — Miragem / Breach Hives
1.5) Atlas/Scarabs — por liga e preço
2) Economia global — currency aberta, mas hierarquizada por preço
3) Fallbacks de ligas antigas / temporadas anteriores
4) Mapas e progresso do Atlas
5) Links, sockets e receitas relevantes
6) Gemas importantes
7) Únicos
8) Frascos
9) Divination Cards
10) Bases raras/craft alinhadas com Cyclone físico + block por staff
11) Esconder equipamentos comuns/raros fora da whitelist
12) Filtro final: esconder tudo que não foi explicitamente mostrado
```

---

## 10. Histórico de versões

### v1 — base original

```text
void_shockwave_cyclone_slayer_lvl90_breach_hives_strict_currency_open_v1.filter
```

Características:

```text
Itens mais estritos
Currency mais aberta
Itens de ligas antigas visíveis
Breach Hives destacado
Wombgifts e Hivebrain Gland destacados
```

### v2 — foco em accuracy e currency

```text
void_shockwave_cyclone_slayer_lvl90_breach_hives_accuracy_currency_v2.filter
```

Mudanças:

```text
Lavish/Mysterious Wombgift com destaque maior
Currency reorganizada
Gemas importantes destacadas
Luvas/accuracy passaram a ser prioridade
6-socket ficou menos barulhento
```

### v3 — mercado de currency

```text
void_shockwave_cyclone_slayer_lvl90_breach_hives_market_v3.filter
```

Mudanças:

```text
Currency calibrada por preço em chaos
Divine destacado
Exalted rebaixado
Ancient rebaixado
GCP/Instilling/Glassblower tratados como úteis, mas não jackpot
```

### v4 — scarabs

```text
void_shockwave_cyclone_slayer_lvl90_breach_hives_scarabs_v4.filter
```

Mudanças:

```text
Scarabs calibrados
Breach/Hive scarabs destacados para uso
Breach Resonant Cascade destacado como caro
Scarabs caros fora da estratégia destacados para vender
```

### v5/v6 — divination cards

```text
void_shockwave_cyclone_slayer_lvl90_breach_hives_cards_v5.filter
void_shockwave_cyclone_slayer_lvl90_breach_hives_cards_v6.filter
```

Mudanças:

```text
Divination Cards por tiers de preço
Cartas caras com alerta forte
Cartas médias visíveis
Cartas baixas discretas
Fallback para todas as cartas
```

### v7 — Delirium, Legion, Oils e Fragments

```text
void_shockwave_cyclone_slayer_lvl90_breach_hives_market_fragments_oils_v7.filter
```

Mudanças:

```text
Delirium Orbs
Simulacrum
Legion Emblems/Splinters
Oils
Fragmentos
```

### v8 — mecânicas diversas

```text
void_shockwave_cyclone_slayer_lvl90_breach_hives_market_full_v8.filter
```

Mudanças:

```text
Catalysts
Omens
Tattoos
Expedition
Harvest/Lifeforce
Runegrafts
```

### v9 — Allflame Embers e Djinn Coins

```text
void_shockwave_cyclone_slayer_lvl90_breach_hives_market_complete_v9.filter
```

Problema corrigido depois:

```text
Erro de BaseType em Legion com Unrelenting Timeless...
```

### v10 — correção Legion

```text
void_shockwave_cyclone_slayer_lvl90_breach_hives_market_complete_v10_fixed_legion.filter
```

Correção:

```text
Usar Timeless Eternal Emblem
Remover Timeless Eternal Empire Emblem inválido
Manter Timeless Eternal Empire Splinter quando válido
```

### v11/v13 — Essences e Delve

Mudanças:

```text
Essences adicionadas
Fossils adicionados
Resonators adicionados
BaseTypes parciais removidos para evitar erro
```

### v12 — Tattoo de Valako

Correção:

```text
Nome válido: Tattoo of the Valako Shieldbearer
```

### v14 — checagem de nomes de liga

Mudanças:

```text
Allflame Embers conferidos
Djinn Coins conferidos
Breach Scarabs revisados
BaseTypes legados/duvidosos removidos
```

### v17 — correção The Tinker's Table

Arquivo anterior anexado na migração:

```text
void_shockwave_cyclone_slayer_lvl90_breach_hives_market_complete_v17_fixed_tinkerers_table.filter
```

Observação: o nome do arquivo indicava v17, mas o cabeçalho interno ainda carregava parte do texto da v14. A v18 corrigiu e consolidou o cabeçalho.

### v18 — versão revisada para level 89 / T9-T10

Arquivo atual recomendado:

```text
void_shockwave_cyclone_slayer_lvl89_t9_t10_breach_hives_market_v18_reviewed.filter
```

Mudanças principais:

```text
Ajustado para level 89 e mapas T9/T10
Removido Cartographer's Chisel
Hivebrain Gland movido antes do fallback genérico de Map Fragments
Adicionado destaque para MirageMap
Adicionado destaque para gemas Imbued
Adicionados scarabs novos de Mirage/3.28
Reclassificadas cartas, omens e runegrafts com mercado atual
Mantida filosofia: strict gear / open currency
```

### v19-dev — reorganização por ligas

Mudanças principais:

```text
Filtro reorganizado por liga/mecânica
Tiers de preço mantidos dentro de cada liga
Miragem marcada como liga atual nas regras relevantes
Breach Hives/Wombgifts preservados como foco de Atlas
Blight/Oils, Delirium, Legion e fragments/bosses separados em blocos próprios
Metamorph/Catalysts, Ancestor/Omen/Tattoo, Expedition, Harvest/Lifeforce e Runegrafts separados em blocos próprios
Allflame Embers e Djinn Coins separados por mecânica
Nome duplicado Fire Of Unknown Origin consolidado como Fire of Unknown Origin
```

### v19-dev mercado — Runegrafts, Harvest e Tattoos

Mudanças principais:

```text
Runegrafts atualizados pelos prints do PoE Overlay
Harvest/Lifeforce conferido com preços em chaos
Tattoos adicionadas em tiers de preço
Runegraft of the Combat corrigido para Runegraft of the Combatant
Runegrafts sem histórico de preço ficaram visíveis em tier baixo/situacional
```

### v19-dev mercado 2 — Omens, Catalysts, Oils e fragments

Mudanças principais:

```text
Omens atualizados pelos prints do PoE Overlay
Catalysts recalibrados por preço em chaos
Oils recalibrados com Tainted/Golden/Prismatic/Silver em destaque máximo
Fragments, Lab offerings e boss fragments reclassificados por preço
Itens sem histórico de preço ficaram visíveis em tier baixo/situacional
```

### v19-dev mercado 3 — Legion, Delirium e Delve

Mudanças principais:

```text
Legion Emblems e splinters recalibrados pelos prints do PoE Overlay
Delirium Orbs e Simulacrum recalibrados por preço em chaos
Delirium Orbs sem histórico ficaram visíveis em tier baixo/situacional
Fossils e resonators de Delve reclassificados por preço
Alchemical Resonators sem histórico ficaram visíveis em tier baixo/situacional
```

### v19-dev mercado 4 — Currency geral

Mudanças principais:

```text
Currency geral recalibrada pelos prints do PoE Overlay
Itens de 100c+ mantidos nos overrides de maior destaque
Currency util de craft/mapas mantida visível, mas sem som exagerado
Itens com preço em razão inversa, como varios orbs comuns por 1 chaos, mantidos discretos
Shards e scrolls ficaram no tier baixo para evitar poluição em Breach Hives
```

### v19-dev mercado 5 — Essences

Mudanças principais:

```text
Essences recalibradas pelos prints do PoE Overlay
Essence of Desolation isolada como T0
Essences especiais e Deafening caras reclassificadas em T1/T2
Essences medias e baixas separadas por preço real em chaos
Essences sem histórico ficaram visíveis em tier baixo/situacional
```

### v19-dev mercado 6 — Scarabs

Mudanças principais:

```text
Scarabs recalibrados pelos prints do PoE Overlay
Scarabs de 100c+ ficaram em destaque máximo
Breach Scarab of Resonant Cascade mantido com alerta forte
Scarabs do farm Breach/Hive continuam destacados mesmo quando baratos
Scarabs baratos por razão inversa ficaram pequenos para não poluir
Scarabs sem histórico ficaram visíveis em tier baixo/situacional
```

---

## 11. Erros encontrados e lições aprendidas

### 1. Item class inexistente

Erro encontrado:

```text
No item class found matching Scarabs
```

Lição:

```text
Não usar Class "Scarabs" se o jogo não reconhecer essa classe.
Preferir BaseType específicos ou Class "Map Fragments" quando aplicável.
```

### 2. BaseType parcial ou inválido

Erros encontrados:

```text
BaseType error: Unrelenting Timeless...
BaseType rule Bower's Dream type not found
BaseType: The Tinker's Table
BaseType rule Charged Dash of Projection type not found
BaseType rule Doryani's Machinarium type not found
```

Lição:

```text
Nunca usar nomes cortados de prints no BaseType.
Só usar BaseType quando o nome estiver 100% confirmado.
Nomes parciais como "Allflame Ember of the Gil..." não devem entrar no filtro.
Nem todo nome de mercado do poe.ninja/PoE Overlay é um BaseType válido.
```

Estratégia segura:

```text
1. Categorias simples de exchange podem virar BaseType quando o item existe no chão:
   Currency, Fragment, Scarab, Fossil, Resonator, Essence, Oil, DeliriumOrb,
   Omen, Tattoo, Runegraft, AllflameEmber.

2. Categorias de stash exigem revisão manual antes de virar BaseType:
   UniqueMap, SkillGem, ClusterJewel, Beast e alguns Map.

3. UniqueMap:
   não listar nomes únicos como "Doryani's Machinarium" no BaseType.
   usar Class "Maps" + Rarity Unique.
   quando houver base real conhecida, como "Vaal Temple Map", usar essa base.

4. SkillGem:
   não transformar automaticamente nomes caros do mercado em BaseType.
   usar Class "Skill Gems" / "Support Gems" com GemLevel, Quality e Corrupted.

5. ClusterJewel:
   usar BaseType "Large Cluster Jewel" / "Medium Cluster Jewel" / "Small Cluster Jewel"
   junto com EnchantmentPassiveNode e EnchantmentPassiveNum.

6. Beast:
   tratar como dado de mercado, não como drop normal garantido do filtro.
```

### 3. Ordem de regras importa

Problema encontrado:

```text
Hivebrain Gland estava depois de uma regra genérica de Map Fragments.
```

Lição:

```text
Filtros param na primeira regra compatível, exceto quando se usa Continue.
Itens especiais precisam aparecer antes de fallbacks genéricos.
```

### 4. Cabeçalho e nome do arquivo precisam concordar

Problema:

```text
Arquivo com nome v17 ainda tinha cabeçalho interno mencionando v14.
```

Lição:

```text
Sempre atualizar o cabeçalho interno do filtro ao gerar uma nova versão.
```

---

## 12. Regras para futuras edições

Antes de adicionar novos itens:

```text
1. Confirmar o nome exato do BaseType.
2. Evitar nomes copiados de print quando estiverem cortados.
3. Colocar itens muito caros antes de fallbacks genéricos.
4. Colocar itens específicos de estratégia antes da classe genérica.
5. Não exagerar sons em itens baratos.
6. Manter currency baixa visível, mas discreta.
7. Manter gear comum escondido.
8. Atualizar cabeçalho, versão e changelog.
9. Testar o filtro no jogo após cada versão.
10. Se der erro, corrigir a linha exata antes de continuar adicionando conteúdo novo.
```

Padrão recomendado de versionamento:

```text
v18_reviewed
v19_dev_reorganized_by_league
v20_market_update
v21_accuracy_upgrade
v22_atlas_red_maps
v23_endgame_t16
```

---

## 13. Instalação do filtro no Path of Exile

Copiar o arquivo `.filter` para a pasta de filtros do Path of Exile.

No Windows, normalmente fica em:

```text
Documents\My Games\Path of Exile
```

Depois, no jogo:

```text
Options -> Game -> Item Filter
```

Selecionar o filtro:

```text
void_shockwave_cyclone_slayer_lvl89_t9_t10_breach_hives_market_v18_reviewed.filter
```

Se o jogo exibir erro:

```text
1. Anotar a linha exata.
2. Anotar a mensagem completa.
3. Corrigir o BaseType, Class ou condição problemática.
4. Recarregar o filtro no jogo.
```

---

## 14. Estrutura sugerida do repositório

Sugestão para organizar no GitHub:

```text
poe-shockwave-cyclone-slayer-filter/
|
|-- README.md
|-- filters/
|   |-- current/
|   |   `-- void_shockwave_cyclone_slayer_lvl89_t9_t10_breach_hives_market_v18_reviewed.filter
|   |
|   `-- archive/
|       |-- void_shockwave_cyclone_slayer_lvl90_breach_hives_market_complete_v17_fixed_tinkerers_table.filter
|       |-- void_shockwave_cyclone_slayer_lvl90_breach_hives_market_complete_v10_fixed_legion.filter
|       `-- older_versions/
|
|-- docs/
|   |-- contexto_poe_cyclone_slayer_breach_hives.md
|   |-- mercado.md
|   |-- changelog.md
|   `-- erros_corrigidos.md
|
`-- notes/
    |-- upgrades_build.md
    `-- atlas_breach_hives.md
```

---

## 15. Workflow Git recomendado

Trabalhar em branch de desenvolvimento:

```bash
git checkout dev
```

Adicionar README e filtro atual:

```bash
git add README.md
git add filters/current/void_shockwave_cyclone_slayer_lvl89_t9_t10_breach_hives_market_v18_reviewed.filter
```

Commit sugerido:

```bash
git commit -m "docs: document Shockwave Cyclone loot filter history"
```

Se também mover versões antigas para `archive`:

```bash
git add filters/archive/
git commit -m "chore: archive previous loot filter versions"
```

Enviar para o GitHub:

```bash
git push origin dev
```

Quando uma versão estiver estável e testada no jogo:

```bash
git checkout main
git merge dev
git push origin main
```

---

## 16. Próximos passos planejados

### Build

```text
1. Melhorar Accuracy / Chance to Hit.
2. Procurar luvas melhores com Accuracy + Life.
3. Corrigir Impale.
4. Buscar jewel normal com Life + Accuracy + Physical Damage.
5. Considerar cluster físico.
6. Comprar Rumi's não corrompido com enchant automático.
```

### Filtro

```text
1. Testar v19-dev no jogo.
2. Corrigir qualquer erro de parser restante.
3. Atualizar mercado após novos prints do PoE Overlay.
4. Recalibrar mapas quando o personagem sair de T9/T10 e entrar em red maps.
5. Reavaliar sons e tamanhos depois de algumas sessões de Breach Hives.
6. Criar changelog separado quando o repositório estiver estruturado.
```

---

## 17. Estado atual do projeto

Versão recomendada para uso:

```text
v19-dev
```

Estado:

```text
Pronto para teste no jogo.
```

Prioridade ao testar:

```text
1. Verificar se o filtro carrega sem erro.
2. Rodar alguns mapas T9/T10.
3. Observar se Breach Hives/Wombgifts aparecem com destaque suficiente.
4. Observar se currency baixa está visível sem poluir demais.
5. Verificar se Divination Cards aparecem de forma adequada.
6. Verificar se mapas T9/T10 estão mais visíveis que mapas baixos.
7. Confirmar se o filtro não está escondendo bases úteis de luvas, jewels e clusters.
```

---

## 18. Resumo executivo

Este filtro foi construído para uma build **Shockwave Cyclone / General's Cry Slayer** em progressão, com foco em:

```text
Breach Hives
Wombgifts
Currency aberta
Gear estrito
Accuracy como próximo upgrade
Impale como upgrade ofensivo seguinte
Mercado calibrado por PoE Overlay
Evitar erros de BaseType
```

A versão atual, **v19-dev**, parte da v18 consolidada para **level 89 em mapas T9/T10** e reorganiza o filtro por ligas/mecânicas, mantendo os tiers de preço dentro de cada uma.

---

## 19. Toolkit de mercado poe.ninja

O repositorio agora inclui `poe_market_filter_toolkit/`, um conjunto de scripts Python para consultar o mercado atual da liga `Mirage` no poe.ninja e gerar relatorios de apoio para revisao manual do filtro.

Rodar tudo:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py
```

Relatorios principais:

```text
poe_market_filter_toolkit/market/reports/market_report.md
poe_market_filter_toolkit/market/reports/filter_suggestions.md
poe_market_filter_toolkit/market/reports/filter_audit.md
```

O toolkit nao edita o filtro automaticamente. Ele coleta precos, compara com os `BaseType` do filtro ativo na raiz do repositorio e gera sugestoes para revisao.

### Segurança de BaseType

Os relatorios do poe.ninja misturam itens que funcionam bem como `BaseType` com nomes comerciais que o parser do filtro nao aceita. A regra de manutencao e:

```text
Exchange simples -> pode virar BaseType depois de uma checagem visual.
Stash/nomes unicos -> preferir regra estrutural.
```

Exemplos aplicados no filtro:

```text
Unique maps caros:
Class "Maps"
Rarity Unique

Vaal Temple:
Class "Maps"
BaseType "Vaal Temple Map"

Gemas caras:
Class "Skill Gems" "Support Gems"
GemLevel / Quality / Corrupted

Clusters caros:
BaseType "Large Cluster Jewel"
EnchantmentPassiveNode
EnchantmentPassiveNum
```

Isso evita repetir erros como `Charged Dash of Projection` e `Doryani's Machinarium`, que aparecem no mercado mas nao sao `BaseType` validos para o parser.

### v20-dev — integração de mercado no filtro

O filtro passou a separar explicitamente duas camadas:

```text
VALOR DE MERCADO
BUILD - Shockwave Cyclone / General's Cry Slayer
```

A camada de mercado fica no topo do `.filter` e destaca itens caros mesmo quando não pertencem à build, como gemas 21/20+, supports awakened altos, mapas especiais, unique maps caros e clusters com enchant/passive count valiosos.

A camada da build continua destacando gemas, bases, clusters, frascos e itens úteis para o personagem mesmo quando o preço de mercado não justifica alerta forte.

Integração de atributos usada de forma segura:

```text
GemLevel
Quality
EnchantmentPassiveNode
EnchantmentPassiveNum
FracturedItem
SynthesisedItem
HasInfluence
```

`HasExplicitMod` não foi usado como regra obrigatória para rares, porque a maior parte dos rares cai não identificada e o filtro não deve depender de mods que o chão ainda não expõe.

### Triagem manual de rares identificados

Há um fluxo útil dentro do jogo:

```text
1. Pegue apenas bases que o filtro marcou como potencial.
2. Identifique o item.
3. Jogue o item no chão novamente.
4. Observe se o filtro destaca o item com alerta mais forte.
```

Se o item acender depois de identificado, ele entrou em uma regra de triagem por mods explícitos. Isso não garante venda imediata, mas indica que o item tem uma combinação que merece inspeção manual ou checagem no trade.

O filtro agora usa essa lógica para:

```text
Luvas da build:
- Accuracy
- Life
- Attack Speed
- Damage while Leeching
- Resistências
- Strength/Dexterity

Staffs:
- Physical Damage
- Added Damage
- Accuracy
- Attack Speed
- Critical Multiplier
- Impale
- Critical Strike Chance

Anéis, amuletos e cintos:
- Life
- Accuracy
- Attributes
- Resistências
- -mana cost para channeling
- Physical Damage
- Critical Multiplier

Jewels e Abyss Jewels:
- Life
- Accuracy
- Physical Damage
- Attack Speed
- Critical Multiplier
- Resistências
```

Limitação importante: o filtro consegue ler `HasExplicitMod` somente quando o item está identificado ou quando o jogo já expõe os mods daquele item no chão. Por isso a regra não substitui trade macro/PoE Overlay; ela serve como uma segunda peneira rápida depois da identificação.

Recomendação prática:

```text
Pegue bases boas marcadas pelo filtro.
Identifique em lote no fim do mapa ou em um canto seguro.
Jogue no chão.
Se continuar apagado/discreto, venda no NPC ou ignore.
Se acender forte, compare no trade.
```
