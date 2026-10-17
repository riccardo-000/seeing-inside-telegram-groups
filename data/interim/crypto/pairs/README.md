# Coppie canale → gruppo (crypto)

- **`final_pairs.csv`** — **lista ufficiale**: 100 canali crypto, un gruppo ciascuno (100 gruppi
  diversi). È l'input dei dump dei messaggi. Costruita il 2026-10-17 dalla lista di Marco
  (`shared/Marco/definitive_100_pairs.csv`) con 4 righe tolte e 8 canali aggiunti
  (vedi `memory/decisions.md`, 2026-10-17, e `../review/proposta_sostituzioni_2026-10-17.csv`).
  `stato` = da dove viene la coppia (`1_validata_review`, `2_lista_marco_e_regole`,
  `3_da_controllare`, `4_sostituto_A`, `5_nuovo_web`); `altri_gruppi` = secondo gruppo dello
  stesso canale, non usato.
- `active_channels.csv` — review a mano dei primi 42 canali (2026-09-29); letto da `build_master.py`.
- `chats.csv`, `pairs.csv` — prima ricerca per keyword (`find_pairs.py`, 2026-09-29), metodo
  abbandonato; `chats.csv` è ancora letto da `build_master.py` e `audit_channels.py`.
