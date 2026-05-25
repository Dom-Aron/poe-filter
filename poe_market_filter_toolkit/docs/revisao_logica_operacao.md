# Revisao De Logica E Operacao

Este documento registra o diagnostico operacional do fluxo por personagem.

## Estado Atual

O toolkit ja funciona sem OAuth: o personagem e a build alvo vivem em arquivos locais, o mercado e atualizado por fontes publicas e o resultado final e gerado em HTML por personagem.

A unidade operacional recomendada e:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --open
```

## Melhorias Implementadas

- Timestamps criticos agora usam UTC:
  - `core/validation.py`: `generated_at` do relatorio de validacao.
  - `scripts/update_market.py`: `generated_at` do snapshot de mercado e nome do snapshot.
- `run_summary.json` passou para `schema_version: 2`.
- `run_summary.json` registra:
  - `generated_at`;
  - contexto de execucao (`execution`);
  - observabilidade operacional (`observability`);
  - personagem, build, budget, etapas e dashboard.
- O dashboard mostra um painel de saude da execucao com:
  - status da validacao;
  - idade do mercado;
  - origem dos dados de mercado;
  - origem do relatorio de mercado;
  - quantidade de itens e erros de mercado.

## Objetivo

Reduzir ambiguidade operacional. Depois de uma execucao, deve ser rapido responder:

- os dados de mercado foram atualizados agora ou reaproveitados?
- o mercado esta velho?
- a validacao local passou?
- houve erro na coleta de mercado?
- o fluxo foi rodado com etapas puladas?

## Limiar Operacional Sugerido

- Mercado saudavel: ate 180 minutos.
- Mercado stale: acima de 180 minutos.
- Erro de mercado: qualquer `market_errors > 0` merece revisao.
- Validacao `warning`: pode seguir, mas revise antes de comprar item caro.
- Validacao `failed`: nao confiar nas recomendacoes.

## Backlog Priorizado

### Curto Prazo

- Adicionar flags de bloqueio:
  - `--fail-on-stale-market`;
  - `--max-market-age-minutes`.
- Criar `scripts/health_check.py` unico para:
  - testes;
  - validacao de personagem;
  - smoke run com cache.
- Formalizar contrato do `run_summary.json` em teste automatizado.

### Medio Prazo

- Reduzir subprocessos entre scripts.
- Mover logica principal para uma camada importavel de services.
- Deixar scripts CLI como wrappers finos.

### Longo Prazo

- Melhorar parsing do PoB para requisitos de build cada vez mais genericos.
- Evoluir scoring para explicar melhor por que uma troca e upgrade real.
- Separar ainda mais saidas permanentes de artefatos puramente locais.

## Riscos Atuais

- O fluxo ainda depende de arquivos intermediarios entre scripts.
- Mudancas silenciosas no contrato de um JSON podem afetar outro script.
- Sem OAuth, os dados atuais do personagem dependem de export/import manual pelo PoB.
- Links do trade podem ficar obsoletos rapidamente.

