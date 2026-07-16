# ADR 0002 — Proteção do OAuth e minimização de dados do Gmail

- Status: aceito
- Data: 2026-07-14

## Contexto

A Fase 2 precisa manter acesso offline ao Gmail, impedir ataques de replay no callback OAuth, evitar processamento duplicado e reduzir a exposição de conteúdo sensível dos e-mails.

## Decisão

1. Solicitar somente o escopo `gmail.readonly` nesta fase.
2. Gerar `state` OAuth aleatório, persistir apenas seu SHA-256, definir expiração curta e consumi-lo uma única vez com atualização atômica.
3. Criptografar access e refresh tokens com Fernet antes de gravá-los no PostgreSQL.
4. Não registrar tokens nem corpo completo das mensagens nos logs.
5. Não armazenar `body_text` por padrão. O corpo é normalizado em memória para cálculo de hash e descartado quando `GMAIL_STORE_BODY_TEXT=false`.
6. Garantir idempotência com a restrição única `(google_account_id, provider_message_id)` e `ON CONFLICT DO NOTHING`.
7. Executar o SDK síncrono do Google em threads auxiliares para não bloquear o event loop do FastAPI.

## Consequências

- Uma nova autorização será necessária se a chave Fernet for perdida ou trocada sem migração dos tokens.
- Mensagens continuam não lidas no Gmail porque a Fase 2 possui acesso somente de leitura.
- A mesma mensagem pode continuar aparecendo na consulta de não lidas, mas não será persistida novamente.
- Habilitar armazenamento do corpo aumenta o risco de privacidade e deve ser uma decisão consciente.
- Permissões de rascunho e envio serão solicitadas somente na fase correspondente.
