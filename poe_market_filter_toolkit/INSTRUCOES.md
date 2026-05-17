# Instrucoes do PoE Market Filter Toolkit

## Objetivo

Automatizar a coleta de precos do poe.ninja para reduzir o trabalho manual de ler prints do PoE Overlay.

Fluxo esperado:

```text
1. Rodar o toolkit.
2. Baixar precos da liga configurada.
3. Gerar relatorios Markdown/CSV.
4. Revisar sugestoes e auditoria.
5. Ajustar o filtro manualmente quando fizer sentido.
6. Testar o filtro dentro do jogo.
```

## Primeiro uso

Na raiz do repositorio:

```powershell
python poe_market_filter_toolkit\scripts\run_all.py
```

Alternativa:

```powershell
.\poe_market_filter_toolkit\run_all.ps1
```

O script ja procura o filtro `.filter` da raiz do repositorio, entao nao e necessario copiar o filtro para dentro da pasta do toolkit.

## Configurar a liga

Edite:

```text
poe_market_filter_toolkit/config/market_config.json
```

Campo principal:

```json
"league": "Mirage"
```

## Relatorios principais

```text
poe_market_filter_toolkit/market/reports/market_report.md
poe_market_filter_toolkit/market/reports/market_report.csv
poe_market_filter_toolkit/market/reports/filter_suggestions.md
poe_market_filter_toolkit/market/reports/filter_audit.md
```

## Como interpretar

`market_report.md` e o panorama completo do mercado coletado.

`filter_suggestions.md` e o mais importante para revisar o filtro. Ele mostra itens caros ausentes e itens caros ja presentes.

`filter_audit.md` aponta riscos estruturais. Nem toda duplicata e erro, porque este filtro usa regras de override no inicio e regras genericas mais tarde.

## Boas praticas

- Confirme nomes exatos antes de criar `BaseType`.
- Trate preco alto com baixa liquidez como alerta, nao como verdade absoluta.
- Nao aplique sugestoes automaticamente sem revisar.
- Rode `git diff` antes de commitar ajustes no filtro.
- Teste no jogo depois de qualquer alteracao relevante.
