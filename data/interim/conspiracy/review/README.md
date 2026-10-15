# Coppie canale → gruppo da controllare a mano

`pairs_to_review_<data>.csv` (creati da `scripts/make_review.py`): coppie con gruppo attivo trovate dagli audit
(`master.csv`) che non sono ancora in `data/processed/pairs_reviewed.csv`.
Stesse prime 10 colonne di `pairs_reviewed.csv`, così le righe controllate si
possono copiare lì.

- `final`: vuota, da compilare (`valida`, `altro_progetto`, `dubbia`, `dubbia_soglia`, `esclusa`).
- `pair_type`: **ipotesi dello script**, da correggere. `own_community` = chat
  collegata ufficialmente al canale; `same_project_group` / `other_project` =
  gruppo linkato nei post, stimato dal nome.
- `riccardo` / `marco` / `simone`: una nota per chi controlla.
- `flags`: perché la riga è dubbia (gruppo condiviso da più canali, gruppo
  enorme di un altro progetto, possibile imitazione, fuori tema...).
- `link_channel` (anteprima web `t.me/s/`) e `link_group`: aprili da un browser
  **non loggato** a Telegram, così non si consumano resolve degli account.

Prima le `own_community`, poi le altre, ordinate per canale: ci si può dividere a blocchi.
