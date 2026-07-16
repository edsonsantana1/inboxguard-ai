# ADR 0001 — Monólito modular com limites hexagonais

- Status: aceito
- Data: 2026-07-14

## Contexto

O produto precisa integrar Gmail, IA, Telegram, PostgreSQL e processamento agendado. Separar tudo em microserviços no MVP aumentaria implantação, observabilidade e consistência transacional sem benefício proporcional.

## Decisão

Usar um monólito modular em FastAPI, orientado por casos de uso e contratos (`Protocol`). O domínio e os casos de uso não dependerão de SDKs externos nem do SQLAlchemy. Adaptadores concretos serão injetados na composição da aplicação.

## Consequências

- Testes unitários podem substituir Gmail, IA, Telegram e banco por fakes.
- A implantação inicial permanece simples.
- Fronteiras claras permitem extrair workers ou serviços no futuro.
- Imports entre módulos deverão respeitar a direção domínio → aplicação → adaptadores/composição.
