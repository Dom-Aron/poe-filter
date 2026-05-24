# Arquitetura Interna

O projeto agora segue uma separacao simples:

```text
core/
  paths.py       caminhos canonicos do toolkit
  io.py          leitura/escrita JSON e copia segura
  profiles.py    helpers de personagem/build
  validation.py  validacao do fluxo local sem OAuth

scripts/
  CLIs e orquestradores
```

## Regra de ouro

Personagem e a unidade de trabalho. O fluxo recomendado nunca deve depender dos arquivos globais em `builds/player_items.json` ou `data/generated/gap_analysis.json` como fonte de verdade.

Entrada:

```text
builds/characters/<personagem>/
builds/profiles/<build>/
```

Saida:

```text
data/generated/characters/<personagem>/
```

## Scripts

Scripts devem ser finos:

1. ler argumentos;
2. chamar funcoes de `core/` quando houver logica compartilhada;
3. executar outros scripts quando forem orquestradores;
4. escrever artefatos no diretorio do personagem.

## Estado global legado

Alguns scripts ainda aceitam defaults globais para compatibilidade. Isso e legado. Novas mudancas devem preferir caminhos explicitos por personagem/build.

## Proximas extrações naturais

Ainda faz sentido mover no futuro:

```text
plan_upgrade_path.py -> core/scoring.py e core/trade_planning.py
generate_dashboard.py -> core/html.py ou ui/dashboard.py
market_report.py/update_market.py -> core/market.py
```

Essas extracoes devem ser incrementais, sempre com testes passando entre uma etapa e outra.
