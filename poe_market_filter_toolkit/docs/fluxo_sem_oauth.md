# Fluxo Sem OAuth

Este e o fluxo oficial enquanto nao houver acesso OAuth aprovado.

O usuario mantem arquivos locais com o estado atual do personagem e a build alvo. O toolkit usa esses arquivos, atualiza o mercado publico, busca ofertas no trade oficial e gera HTMLs para revisao humana.

## Arquivos do personagem

```text
poe_market_filter_toolkit/builds/characters/<personagem>/
  character_profile.json
  player_items.json
  player_stats.json
```

`character_profile.json` associa o personagem a uma build:

```json
{
  "schema_version": 1,
  "name": "Meu Personagem",
  "build_slug": "ronarray_shockwave_cyclone_slayer"
}
```

## Arquivos da build alvo

```text
poe_market_filter_toolkit/builds/profiles/<build>/
  build_profile.json
  target_build_items.json
  target_build_stats.json
  upgrade_rules.json
```

## Atualizar dados manualmente

Editar item/status com assistente:

```powershell
python poe_market_filter_toolkit\scripts\edit_character.py --character aron_shockwave_cyclone_slayer
```

Editar apenas alguns slots:

```powershell
python poe_market_filter_toolkit\scripts\edit_character.py --character aron_shockwave_cyclone_slayer --items --slots ring_1,ring_2,belt
```

Editar apenas status agregados:

```powershell
python poe_market_filter_toolkit\scripts\edit_character.py --character aron_shockwave_cyclone_slayer --stats
```

## Validar antes de rodar

```powershell
python poe_market_filter_toolkit\scripts\validate_character.py --character aron_shockwave_cyclone_slayer
```

Com warnings como erro:

```powershell
python poe_market_filter_toolkit\scripts\validate_character.py --character aron_shockwave_cyclone_slayer --strict
```

## Rodar tudo para um personagem

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --open
```

Modo rapido para testar HTML sem bater no mercado/trade:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --skip-market-update --skip-filter-reports --skip-upgrade-plan --open
```

## Limites conhecidos

- O script nao sabe tudo que o PoB sabe.
- Alguns mods sao interpretados por texto e podem exigir revisao manual.
- Links do trade podem apontar para a busca/listagem retornada, mas o item pode ter vendido ou mudado.
- Rate limit da API de trade pode deixar o plano incompleto.
- OAuth nao e necessario para o fluxo local.
