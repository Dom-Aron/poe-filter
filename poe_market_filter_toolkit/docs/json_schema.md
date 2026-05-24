# Estrutura Dos JSONs

Este documento descreve o contrato pratico usado pelos scripts. Nao e um JSON Schema formal, mas serve como checklist.

## `player_items.json`

```json
{
  "schema_version": 1,
  "character": "Nome ou descricao",
  "updated": "2026-05-23",
  "items": {
    "ring_1": {
      "name": "Doom Knot",
      "base": "Two-Stone Ring",
      "locked": false,
      "protect_reason": "Mantem -mana cost.",
      "stats": {
        "life": 110,
        "cold_resistance": 60,
        "mana_cost_channeling": -3
      }
    }
  }
}
```

Slots comuns:

```text
weapon, helmet, body_armour, gloves, boots, belt, amulet, ring_1, ring_2,
quiver, flask_rumi, jewel_1, abyss_jewel_1, large_cluster_1
```

## `player_stats.json`

```json
{
  "schema_version": 1,
  "character": "Nome",
  "stats": {
    "life": 3410,
    "chance_to_hit": 96,
    "fire_resistance": 75,
    "chaos_resistance": 15
  }
}
```

Use stats agregados do PoB quando possivel. A API oficial do personagem nao entrega todos esses calculos.

## `target_build_stats.json`

```json
{
  "schema_version": 1,
  "minimums": {
    "life": 3200,
    "chance_to_hit": 92
  },
  "goals": {
    "life": 3800,
    "chance_to_hit": 100,
    "chaos_resistance": 50
  }
}
```

`minimums` sao pisos que nao devem quebrar. `goals` sao metas usadas para priorizar compras.

## `upgrade_rules.json`

Campos principais:

```json
{
  "schema_version": 1,
  "max_combo_size": 3,
  "minimum_plan_score": 50,
  "minimum_guarded_slot_score": 50,
  "soft_minimum_stats": ["chance_to_hit"],
  "guarded_slots": {
    "gloves": "Trocar apenas com melhoria clara."
  },
  "weights": {
    "life": 1.1,
    "chaos_resistance": 1.7,
    "crit_multiplier": 2.0
  },
  "trade_profiles": {
    "jewel_damage": {
      "label": "Jewel raro",
      "replacement_slots": ["jewel_1"],
      "min_score": 30
    }
  },
  "search_library": {
    "life": {
      "title": "Jewel com maximum life",
      "profiles": ["jewel_damage"]
    }
  }
}
```

Convenções de nome:

```text
critical_strike_chance, nao crit_chance
crit_multiplier, nao critical_multiplier
elemental_damage_with_attacks para ataques
elemental_damage para dano elemental generico
```
