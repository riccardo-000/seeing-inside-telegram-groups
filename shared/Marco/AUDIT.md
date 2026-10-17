from pathlib import Path

content = """# Audit delle coppie Channel–Group

## Obiettivo

Questo documento riassume il controllo manuale delle coppie `channel → group` presenti nella lista corrente.

L'obiettivo dell'audit è verificare che il gruppo associato sia sufficientemente correlato al canale di origine. In particolare, la corrispondenza dovrebbe essere supportata da almeno uno dei seguenti elementi:

- forte somiglianza tra nome/username del canale e nome/username del gruppo;
- chiara appartenenza allo stesso progetto o brand;
- relazione esplicita e plausibile tra canale di announcement/news e relativa community/chat;
- verifica manuale diretta su Telegram.

La similarità nominale viene usata come **sanity check**, non come unico criterio assoluto.

---

## Coppie da scartare

### Riga 44 — `@kucoin_news → @kumining_en`

- **Channel:** `@kucoin_news`
- **Channel title:** `KuCoin Announcement`
- **Group:** `@kumining_en`
- **Group title:** `KuMining Official Group`
- **Esito:** **DA SCARTARE**
- **Motivazione:** la relazione non è sufficientemente forte per il nostro obiettivo. La coppia era già stata segnalata come basata principalmente sulla somiglianza nominale e senza link reciproco. Inoltre, dalla verifica manuale il gruppo risulta in russo, rendendolo ancora meno adatto al corpus che vogliamo costruire.
- **Azione:** cercare un'altra community/group chiaramente associata a `@kucoin_news`, oppure lasciare il canale senza pair se non ne esiste una adeguata.

---

### Riga 78 — `@radar_rashiddarsigov → @gonkaprotocol`

- **Channel:** `@radar_rashiddarsigov`
- **Channel title:** `RADAR | Rashid Darsigov`
- **Group:** `@gonkaprotocol`
- **Group title:** `GNK | Территория Майнинга`
- **Esito:** **DA SCARTARE**
- **Motivazione:** non esiste una correlazione nominale o di identità sufficientemente evidente tra il canale e il gruppo. La coppia è stata inoltre verificata manualmente e confermata come non adatta.
- **Azione:** effettuare una nuova discovery per `@radar_rashiddarsigov` alla ricerca di un gruppo/community realmente associato.

---

## Coppie con gruppo senza username pubblico

Le righe **79–85** rappresentano un caso distinto. In questi record il gruppo non dispone di un username Telegram pubblico e nel dataset è identificato solamente tramite un ID interno.

Queste coppie **non vengono scartate automaticamente**, perché in diversi casi il gruppo è stato individuato tramite `linked_chat`, cioè come discussion group direttamente collegato al canale da Telegram. Tuttavia, l'assenza di un username pubblico rende più difficile:

- verificare la coppia tramite ricerca manuale;
- produrre un link pubblico stabile al gruppo;
- usare la similarità tra username come controllo;
- ricostruire facilmente la relazione in una verifica futura.

Per questo motivo vengono mantenute temporaneamente in stato **PENDING / DA DECIDERE**.

| Riga | Channel | Group ID | Channel title | Group title | Stato |
|---|---|---|---|---|---|
| 79 | `@keeper_cis` | `id1524291072` | Новости Keeper | Чат Кипера | Pending |
| 80 | `@respawn` | `id2475709957` | Respawn | Chatroom | Pending |
| 81 | `@cryptoquant_official` | `id1534080402` | CryptoQuant | CryptoQuant | Pending |
| 82 | `@itsgawsita` | `id3142935699` | Sita Giveaway & CV Crypto | Sita | Pending |
| 83 | `@tradeid1` | `id2544397031` | TradeID 2026 | TradeID 2026 | Октябрь | Москва | | Pending |
| 84 | `@bisrat_sport_433eth2` | `id3607156278` | 4-3-3 ስፖርት በኢትዮጵያ™ | መወያያ | Pending |
| 85 | `@brokeactivities` | `id2740606426` | broke activities | Paranomia Gambling Chat 🎯 | Pending |

### Decisione da prendere

Prima di includere queste 7 coppie nel corpus finale, conviene fissare una regola metodologica comune, ad esempio:

> Accettare anche gruppi senza username pubblico quando Telegram li espone direttamente come `linked_chat` del canale e il gruppo è pubblicamente leggibile tramite il canale.

Se questa regola viene approvata, alcune o tutte queste coppie possono rimanere nel dataset anche senza similarità nominale forte.

---

## Coppia precedentemente sospetta ma confermata

### Riga 106 — `@weexnews → @weex_official`

Questa coppia **non deve essere inclusa tra le anomalie**.

Dopo verifica manuale è stata considerata valida e viene quindi mantenuta nel corpus.

---

## Resoconto numerico

La lista contiene **105 coppie channel–group** complessive.

Dopo questo audit:

- **96 coppie** risultano attualmente **valide / accettabili**;
- **2 coppie** risultano **da scartare** e richiedono una nuova discovery:
  - `@kucoin_news → @kumining_en`
  - `@radar_rashiddarsigov → @gonkaprotocol`
- **7 coppie** restano **pending** perché il gruppo non ha username pubblico ed è rappresentato solo tramite ID.

Quindi:

```text
Totale coppie:             105
Valide / accettabili:       96
Da scartare e ricercare:     2
Pending (ID-only):            7
```

In percentuale:

```text
Valide / accettabili:       91.4%
Da scartare:                 1.9%
Pending:                     6.7%
```

---


"""

path = Path("/mnt/data/channel_group_pair_audit.md")
path.write_text(content, encoding="utf-8")
print(path)
