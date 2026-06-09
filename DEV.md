# Desenvolvimento

Este projeto usa comandos Python diretos em vez de wrappers `.bat` ou `.ps1`.

## Checagem Local

```powershell
python -m unittest discover -s poe_market_filter_toolkit\tests
python -m compileall poe_market_filter_toolkit\core poe_market_filter_toolkit\scripts
git status --short
```

A suite de testes inclui integridade do repositorio, fixtures sinteticas e
complexidade ciclomatica maxima de 30 por funcao em `core/` e `scripts/`.

## Validar Personagem

```powershell
python poe_market_filter_toolkit\scripts\validate_character.py --character aron_shockwave_cyclone_slayer
```

## Revisar Mudancas

```powershell
git diff --stat
git diff --cached --stat
git ls-files -o -i --exclude-standard
```

## Limpeza Local

Arquivos gerados, snapshots de mercado, relatorios, exports crus do PoB,
credenciais e dados reais de personagem devem ficar ignorados. Antes de
commitar, confira se o diff contem apenas fonte, configuracoes exemplo,
documentacao ou presets anonimizados.
