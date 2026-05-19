# Secrets

Esta pasta nao deve ser versionada.

Crie `tokens.json` neste formato:

```json
{
  "access_token": "COLE_O_TOKEN_OAUTH_AQUI"
}
```

Alternativa: defina a variavel de ambiente `POE_OAUTH_TOKEN`.

O script `scripts/oauth_login.py` tambem pode criar esse arquivo automaticamente depois que voce tiver um `client_id` aprovado pela GGG.
