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

## `coppie_valide_2026-10-17.csv` — punto di partenza per arrivare a 100 coppie crypto

Tutte le coppie che oggi riteniamo valide, una riga per coppia (un canale può avere 2 gruppi).
`stato`: `1_validata_review` = `final=valida` in `pairs_reviewed.csv`; `2_lista_marco_e_regole` =
nella lista di Marco (`shared/Marco/100_CRYPTO.txt`) e passa le regole, mai in review;
`3_da_controllare` = passa le regole, non l'ha mai visto nessuno. Regole (provvisorie, da
fissare in `decisions.md`): gruppo collegato al canale o con nome simile, condiviso da ≤ 2 canali,
≥ 10 msg da ≥ 5 utenti /7g, < 50% msg da bot, canale ≥ 1000 iscritti e post dal 15/09, gruppo
non privato. `flags` = motivi di dubbio; `gruppo_cita_canale` = la pagina t.me del gruppo
nomina il canale (link reciproco). `decisione` / `note`: da compilare.
