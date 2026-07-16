# ADR 0003 — Regras antes da IA e saída estruturada

## Status

Aceita.

## Contexto

A classificação de e-mails precisa ser explicável, econômica, testável e resistente a conteúdo malicioso. Chamar um modelo para todas as mensagens aumentaria custo, latência e dependência externa. Texto livre também seria inadequado para decisões de aplicação.

## Decisão

1. Executar regras determinísticas primeiro.
2. Chamar `AIProvider` somente abaixo de um limiar de confiança configurável.
3. Isolar o conteúdo do e-mail como dado não confiável.
4. Validar toda saída externa com Pydantic e rejeitar campos extras.
5. Persistir modelo, versão do prompt, confiança, motivo e indicadores de risco.
6. Reutilizar classificações existentes, salvo solicitação explícita de reclassificação.
7. Usar fallback determinístico quando o provedor falhar.

## Consequências

### Positivas

- Menor custo e latência.
- Comportamento previsível para casos óbvios.
- Testes sem serviços externos.
- Troca de provedor sem alterar o caso de uso.
- Proteção contra ações produzidas por texto livre.

### Negativas

- Regras exigem manutenção.
- Mensagens ambíguas sem provedor configurado podem permanecer como desconhecidas.
- O limiar precisa ser calibrado com feedback futuro.
