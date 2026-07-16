# InboxGuard AI

Plataforma segura, modular e auditável para gerenciamento inteligente de e-mails com Gmail, inteligência artificial e Telegram.

> Estado atual: **Fase 3 — classificação determinística, resumo estruturado, AI Provider e persistência explicável**.

As Fases 1 e 2 permanecem integradas: FastAPI, PostgreSQL assíncrono, Alembic, Google OAuth, leitura do Gmail, normalização MIME, idempotência, logs estruturados, health checks, Docker e testes.

## O que a Fase 3 adiciona

- Categorias padronizadas: trabalho, financeiro, cobrança, compromisso, faculdade, pessoal, propaganda, newsletter, notificação, suspeito e desconhecido.
- Prioridades `low`, `medium`, `high` e `critical`.
- Regras determinísticas executadas antes de qualquer chamada de IA.
- Chamada ao provedor de IA somente quando a confiança das regras ficar abaixo do limiar configurado.
- Interface `AIProvider`, mantendo o caso de uso independente da OpenAI.
- Saída da IA validada por Pydantic, com campos extras rejeitados.
- Isolamento explícito de conteúdo de e-mail não confiável.
- Fallback determinístico quando a IA estiver ausente, indisponível ou retornar saída inválida.
- Persistência de categoria, prioridade, necessidade de resposta, confiança, resumo, motivo, riscos, modelo e versão do prompt.
- Reutilização da classificação existente para evitar custo duplicado.
- Reclassificação controlada por `force=true`.
- Endpoints para classificar e consultar a classificação.

## Fluxo de classificação

```mermaid
flowchart TD
    A[E-mail armazenado] --> B[Regras determinísticas]
    B --> C{Confiança >= limiar?}
    C -- Sim --> D[Persistir resultado determinístico]
    C -- Não --> E{IA configurada?}
    E -- Não --> F[Persistir resultado determinístico de baixa confiança]
    E -- Sim --> G[OpenAI via AIProvider]
    G --> H{Saída Pydantic válida?}
    H -- Sim --> I[Persistir resultado da IA]
    H -- Não --> J[Fallback determinístico]
```

## Segurança contra prompt injection

O prompt separa regras fixas e conteúdo do e-mail:

```text
SYSTEM RULES:
regras imutáveis da aplicação

UNTRUSTED EMAIL CONTENT:
conteúdo usado somente para análise
```

O modelo é instruído a não seguir comandos presentes no e-mail, não executar ações, não enviar mensagens, não revelar prompts e não inventar informações.

## Privacidade

Por padrão:

```env
GMAIL_STORE_BODY_TEXT=false
```

Assim, a classificação usa remetente, assunto e snippet armazenados. Caso o corpo seja habilitado, ele também poderá entrar na análise, aumentando a responsabilidade sobre retenção e proteção de dados.

## Estrutura relevante

```text
inboxguard-ai/
├── app/
│   ├── application/use_cases/
│   │   ├── classify_email.py
│   │   └── get_email_classification.py
│   ├── domain/
│   │   ├── entities/
│   │   ├── enums/
│   │   ├── ports/ai_provider.py
│   │   └── services/deterministic_classifier.py
│   ├── infrastructure/
│   │   ├── ai/
│   │   │   ├── openai_provider.py
│   │   │   ├── prompt.py
│   │   │   └── schemas.py
│   │   └── database/
│   │       ├── models/email_classification.py
│   │       └── repositories/classification_repository.py
│   └── presentation/api/
├── alembic/versions/
├── docs/adr/
├── docs/bruno/
├── tests/
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

# Atualização da Fase 2 para a Fase 3

Todos os comandos devem ser executados no PowerShell, dentro da pasta que contém `docker-compose.yml`.

## 1. Pare o projeto atual

```powershell
docker compose down
```

Não use `docker compose down -v`, pois isso apagaria o PostgreSQL, a conta Gmail conectada e os e-mails sincronizados.

## 2. Preserve seu `.env`

O ZIP não contém `.env`. Ao substituir a pasta do projeto, copie o arquivo antigo para a nova pasta.

Exemplo:

```powershell
Copy-Item `
  ".\inboxguard-ai-fase-2-backup\.env" `
  ".\inboxguard-ai\.env"
```

## 3. Adicione as variáveis da Fase 3

Abra:

```powershell
notepad .env
```

Acrescente:

```env
AI_PROVIDER=openai
AI_DETERMINISTIC_THRESHOLD=0.88
AI_TIMEOUT_SECONDS=30
AI_RETRY_ATTEMPTS=3
AI_MAX_INPUT_CHARACTERS=12000
AI_PROMPT_VERSION=email-classification-v1
OPENAI_MODEL=gpt-5-mini
OPENAI_API_KEY=
```

### Executar sem API paga

Use:

```env
AI_PROVIDER=disabled
OPENAI_API_KEY=
```

Nesse modo, as regras determinísticas continuam funcionando. Mensagens inconclusivas permanecem com confiança menor e categoria possivelmente `desconhecido`.

### Executar com OpenAI

Use:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=SUA_CHAVE_REAL
OPENAI_MODEL=gpt-5-mini
```

Nunca publique a chave no GitHub, em screenshots ou em mensagens.

## 4. Reconstrua e aplique a migração

```powershell
docker compose up -d --build
```

O entrypoint executa automaticamente:

```text
alembic upgrade head
```

A nova revisão cria:

```text
email_classifications
```

## 5. Aguarde e confira

```powershell
Start-Sleep -Seconds 20
docker compose ps
```

Os serviços devem aparecer como `healthy`.

Teste:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
```

# Como testar a Fase 3

## 1. Liste os e-mails

Abra:

```text
http://localhost:8000/docs
```

Execute:

```text
GET /api/v1/emails
```

Copie o campo `id` de um e-mail armazenado. Use o UUID interno, não o `provider_message_id` do Gmail.

## 2. Classifique o e-mail

Execute:

```text
POST /api/v1/emails/{email_id}/classify
```

Na primeira execução, use:

```text
force = false
```

Exemplo de resposta:

```json
{
  "id": "uuid-da-classificacao",
  "email_id": "uuid-do-email",
  "category": "notificação",
  "priority": "low",
  "requires_reply": false,
  "confidence": 0.88,
  "summary": "Resumo curto e objetivo.",
  "reason": "Justificativa da decisão.",
  "risk_flags": [],
  "source": "deterministic",
  "model_name": "deterministic-rules-v1",
  "prompt_version": "rules-v1",
  "created_at": "2026-07-15T00:00:00Z",
  "updated_at": "2026-07-15T00:00:00Z"
}
```

Possíveis valores de `source`:

- `deterministic`: regras suficientes ou IA não configurada;
- `ai`: provedor externo retornou saída válida;
- `fallback`: a IA foi chamada, mas falhou ou retornou saída inválida.

## 3. Consulte sem recalcular

```text
GET /api/v1/emails/{email_id}/classification
```

Esse endpoint não chama a IA.

## 4. Teste a prevenção de custo duplicado

Execute novamente:

```text
POST /api/v1/emails/{email_id}/classify?force=false
```

A classificação existente será devolvida sem nova chamada externa.

## 5. Force uma reclassificação

```text
POST /api/v1/emails/{email_id}/classify?force=true
```

O registro será atualizado por `upsert` atômico.

# Endpoints atuais

| Método | Rota | Finalidade |
|---|---|---|
| GET | `/health` | Liveness da API. |
| GET | `/ready` | Readiness do PostgreSQL. |
| GET | `/auth/google/start` | Inicia Google OAuth. |
| GET | `/auth/google/callback` | Conclui OAuth. |
| POST | `/api/v1/emails/sync` | Sincroniza mensagens não lidas. |
| GET | `/api/v1/emails` | Lista e-mails persistidos. |
| GET | `/api/v1/emails/{email_id}` | Consulta um e-mail. |
| POST | `/api/v1/emails/{email_id}/classify` | Classifica e resume. |
| GET | `/api/v1/emails/{email_id}/classification` | Consulta a classificação atual. |
| GET | `/docs` | Swagger UI. |

# Regras determinísticas iniciais

As regras identificam indicadores relacionados a:

- cobrança e vencimento;
- pagamentos e dados financeiros;
- reuniões e compromissos;
- faculdade;
- trabalho e projetos;
- newsletters e propaganda;
- notificações automáticas;
- linguagem suspeita;
- urgência;
- solicitação de resposta.

As regras são transparentes, testáveis e não executam ações.

# Banco de dados

Verifique a revisão:

```powershell
docker compose exec api uv run alembic current
```

Consulte classificações:

```powershell
docker exec -it inboxguard-postgres psql -U inboxguard -d inboxguard
```

No `psql`:

```sql
SELECT
    email_id,
    category,
    priority,
    confidence,
    source,
    model_name,
    prompt_version
FROM email_classifications;
```

Para sair:

```sql
\q
```

# Testes e qualidade

```powershell
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
uv run pytest --cov=app --cov-report=term-missing
```

Os testes não chamam Gmail nem OpenAI reais. Os adapters são simulados.

# Bruno

Abra como coleção:

```text
docs/bruno/InboxGuard AI
```

Defina `emailId` no ambiente local com o UUID retornado por `GET /api/v1/emails`.

# Problemas comuns

## A resposta usa apenas regras

Confira:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=SUA_CHAVE_REAL
```

Depois recrie a API:

```powershell
docker compose up -d --force-recreate api
```

A IA só é chamada quando a confiança determinística fica abaixo de `AI_DETERMINISTIC_THRESHOLD`.

## `source` retorna `fallback`

A IA foi chamada, mas falhou, excedeu o timeout, atingiu rate limit ou retornou saída inválida. Veja logs seguros:

```powershell
docker compose logs --since 5m api
```

O conteúdo completo do e-mail e a chave da API não devem aparecer nos logs.

## Classificação não muda

Use:

```text
force=true
```

Sem isso, o sistema reutiliza o resultado existente para evitar custo duplicado.

## Migração não apareceu

```powershell
docker compose logs --tail 100 api
docker compose exec api uv run alembic current
```

# Roadmap

1. Fundação, banco, logs e health checks — concluída.
2. Gmail OAuth, normalização, sincronização e idempotência — concluída.
3. Regras, classificação, resumo estruturado e AI Provider — concluída.
4. Telegram, comandos, alertas, botões e autorização.
5. Respostas, rascunho, aprovação, envio e auditoria.
6. Resumos diário/semanal e APScheduler.
7. Celery, Redis, Gmail Push, observabilidade, deploy e CI/CD.

# Decisões arquiteturais

- `docs/adr/0001-modular-monolith-and-hexagonal-boundaries.md`
- `docs/adr/0002-oauth-token-and-email-data-protection.md`
- `docs/adr/0003-deterministic-first-and-structured-ai-output.md`

# Licença

MIT. Consulte `LICENSE`.
