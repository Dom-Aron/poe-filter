# Desenvolvimento

Este arquivo reune os atalhos para mexer no codigo sem depender de memoria ou de comandos longos.

## Atalhos

```powershell
.\dev.ps1 check
```

Roda a suite de testes, verifica sintaxe Python com `compileall` e mostra o estado do git.

```powershell
.\dev.ps1 validate aron_shockwave_cyclone_slayer
```

Valida os arquivos do personagem informado.

```powershell
.\dev.ps1 artifacts
```

Lista arquivos ignorados ou gerados localmente. Use antes de commits grandes para evitar sujeira acidental.

```powershell
.\dev.ps1 clean
```

Remove caches locais seguros, usando a mesma limpeza do `tasks.ps1`.

## Separacao mental

- `tasks.ps1`: atalhos para usar o projeto como jogador, rodando fluxo de personagem, filtro e relatorios.
- `dev.ps1`: atalhos para desenvolver o projeto, testar, validar, revisar diffs e localizar artefatos.

## Antes de commitar

1. Rode `.\dev.ps1 check`.
2. Rode `.\dev.ps1 changed` para revisar o tamanho da mudanca.
3. Evite commitar snapshots, HTMLs gerados, logs e caches locais.
4. Separe commits por assunto: scripts, docs, filtro, dados de personagem/build.

## Arquivos gerados

Os scripts podem atualizar relatorios em `poe_market_filter_toolkit/data/generated` e `poe_market_filter_toolkit/market/reports`. Quando um relatorio for apenas saida local, mantenha ignorado. Quando ele documentar uma decisao do projeto, commite conscientemente junto da mudanca que o gerou.

