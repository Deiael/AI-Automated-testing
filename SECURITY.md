# Security Policy

## Reporting

If you discover a vulnerability, please **do not** open a public issue.  
Contact the maintainers privately and include steps to reproduce.

## Secrets

| Secret | Where it belongs |
|---|---|
| LLM API Key (DeepSeek / OpenAI …) | `engine/.env` only |
| Gateway API Key | `gateway/.env` (`API_KEY`) |
| DB credentials | `gateway/.env` (`DATABASE_URL`) |

Never commit:

- `engine/.env`, `gateway/.env`, root `.env`
- SQLite / vector data under `gateway/data/`
- Production tokens in docs or screenshots

## Production checklist

- [ ] Change default `API_KEY=dev-key`
- [ ] Restrict CORS and network exposure (engine should not be public)
- [ ] Use HTTPS in front of the gateway
- [ ] Rotate LLM keys regularly
