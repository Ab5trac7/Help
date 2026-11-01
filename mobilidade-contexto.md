# Subsídio de Mobilidade — contexto (continuado de "Documentos de reembolso XQO4AU", 31/10–01/11/2026)

## Onde está tudo (no computador do utilizador, sessão Remote Control)
- Projeto: `~/mobilidade` (`watch.py` lê o email, `data/trips.json` tem as viagens, `data/docs/<uid>/` os anexos).
- `run.sh` corre diariamente às 07:47 pelo cron: `watch.py` e depois `nextcloud.py`. Há uma cópia do antigo em `run.sh.bak-2026-10-31`.
- `nextcloud.py` copia os documentos de cada viagem para o Nextcloud (utilizador `gantzias`, pasta `Mobilidade/`), uma pasta por reserva com o nome `<data> <rota> <companhia> <ref>`. Os emails são convertidos em PDF com chromium (`data/docs/<uid>/email-<uid>.pdf`). O envio é feito por tar para o contentor `nextcloud-app` como www-data e depois `occ files:scan`. O script só apaga os ficheiros que ele próprio cria.
- Memória da sessão local: `~/.claude/projects/-home-gantzias-mobilidade/memory/mobilidade-subsidy.md`.

## Regras do utilizador
1. Cada ficha por viagem é um Claude Doc só com os campos do formulário gov.pt, pela ordem da plataforma: a tabela do Passo 3 (com os nomes dos dois anexos) e a do Passo 4. Sem notas, prazos, avisos ou extras.
2. **O "Título(s) de Viagem" é o CARTÃO DE EMBARQUE**, nunca o email de reserva nem o recibo do e-ticket.
   - Os nomes no Nextcloud são `reserva*.pdf` (emails ou recibos de reserva), `fatura*.pdf` e `cartao-embarque*.*`.
   - Se não houver cartão de embarque, o campo fica como "em falta".
3. A tarifa é o valor do bilhete menos o desconto da fatura (exemplo: XQO4AU).

## Fichas feitas (Claude Docs)
| Reserva | Viagem | Título de Viagem | Documento |
| --- | --- | --- | --- |
| XQO4AU | FNC→LIS 04/06/2026 TAP TP1688 | `cartao-embarque.pdf` | doc 10a62823… |
| KDJQHMP | LIS⇄FNC 15–19/10/2026 easyJet EJU7625/EJU7624 | **em falta** | https://claude.ai/artifact/BYMSKtvdUEWvAC5c1ZDURd |
| KDLX7Z5 | LIS→FNC 27/10/2026 easyJet EJU7635 (19:20, fatura 2860768961, tarifa 81,99) | `cartao-embarque.png` | https://claude.ai/artifact/YRbmwNNrhyQoep26Bpc1UP |

Também existe um documento geral, com todas as viagens (doc a91747ea…).

## Pendente
- **KDJQHMP:** falta o cartão de embarque. É preciso arranjá-lo ou pedir à easyJet uma Confirmação de Comparência (como foi feito para a KD5FXNT). Depois, atualizar a ficha e a pasta no Nextcloud.
- A primeira cópia automática para o Nextcloud corre a 01/11 às 07:47. Confirmar em `~/.local/state/mobilidade/watch.log` e no Nextcloud.
