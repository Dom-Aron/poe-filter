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
  - `scripts/compare_current_to_target.py`: `generated_at` da analise de gaps.
  - `scripts/recommend_next_steps.py`: relatorios Markdown e JSON de recomendacoes.
  - `scripts/plan_upgrade_path.py`: plano de compra Markdown, HTML e JSON.
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
- `run_character.py` agora pode bloquear execucoes com dados ruins:
  - `--fail-on-stale-market`;
  - `--max-market-age-minutes`;
  - `--fail-on-market-errors`.
- A suite de testes cobre o contrato minimo de observabilidade do `run_summary.json`.

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

## Flags De Qualidade

Para rodar de forma conservadora:

```powershell
python poe_market_filter_toolkit\scripts\run_character.py --character aron_shockwave_cyclone_slayer --budget 1000c --fail-on-stale-market --max-market-age-minutes 180 --fail-on-market-errors
```

Use `--fail-on-stale-market` quando quiser impedir recomendacoes com mercado antigo. Use `--fail-on-market-errors` quando qualquer erro de coleta precisar bloquear a execucao.

## Backlog Priorizado

### Curto Prazo

- Criar `scripts/health_check.py` unico para:
  - testes;
  - validacao de personagem;
  - smoke run com cache.
- Expandir o contrato do `run_summary.json` para validar tambem renderizacao do dashboard.

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
