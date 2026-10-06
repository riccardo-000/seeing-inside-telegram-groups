# Segnalazioni 2026-10-06 (Riccardo + Claude Code)

Osservazioni fatte a mano nell'app (account di ricerca, nessun join, nessun click su link sospetti)
e verificate dalle pagine web pubbliche `t.me` (senza account). Utili per il paper (sezione scam /
risultati qualitativi). Nessun dato personale: solo nomi di canali/gruppi/bot pubblici.

## 1. Impersonificazione di MEXC (exchange)

Cercando `MEXCofficialNews` nella ricerca globale di Telegram compaiono, sotto il canale vero,
account con nome quasi identico e il link del canale vero **scritto nel titolo**:

| Username | Titolo mostrato | Iscritti | Note |
|---|---|---|---|
| @MEXCofficialNews | MEXC Community Channel | 98.699 | **vero** (link "Telegram" nei post → @MEXCEnglish) |
| @MEXCofficialNewsES | MEXC - Canal de la Comunidad | 111 | da verificare se ufficiale |
| @MEXCofficialNewsgroup | `https://t.me/MEXCofficialNews` | 19 | titolo = link del canale vero → imitazione |
| @MEXCofficialNewsbot | `MEXC English (Official) https://t.me/MEXCofficialNews` | 8 | **bot** che si spaccia per il gruppo ufficiale |
| @MEXCofficialNewsnowc | MEXC مجتمع قناة | 5 | imitazione probabile |

Schema: chi cerca "MEXC" trova nomi quasi uguali e li scambia per ufficiali. Stesso fenomeno del bot
`@moneroeconomicforumtgbot` visto il 29/09. Related work: canali clone/fake (La Morgia et al.).
**Non aprire né contattare** questi account.

## 2. Promozione di "segnali VIP" dentro un canale news (BSC Daily)

- Canale: @bsc_dailyann ("BSC Daily - Announcements", ~16.600 iscritti), post del ~23/04/2025.
- Post sponsorizzato ("Our partner") per **@cryptoninjas_trading_ann** ("CryptoNinjas Trading 🥷🏿",
  ~20.300 iscritti): "premium signals boasting an **80% win rate**", sconto 50% "until April 30",
  screenshot di trade a +959% / +121%, invito a pagare l'accesso al gruppo privato.
- Il canale CryptoNinjas non ha anteprima web pubblica; il link del post (`t.me/cryptoninjas_trading…`)
  oggi non porta a un canale/gruppo (nell'app: schermata grigia) → rinominato, rimosso o limitato.
- Disclaimer tipico: "for educational purposes only… does not constitute financial advice".

Schema: canale con molti iscritti e aspetto legittimo vende spazio a gruppi di segnali a pagamento.

## 3. Coppie verificate a mano oggi

- @MEXCofficialNews → @MEXCEnglish: **valida** (canale attivo, link esplicito nei post).
- @bsc_dailyann → @bsc_daily: **valida** (descrizioni che si linkano a vicenda; canale con post il 29/09).

## 4. Confronto con `shared/Marco/report_prime_90_righe_master.txt`

| # Marco | Canale | Marco | Script (master.csv / groups.csv) | Da decidere |
|---|---|---|---|---|
| 2 | @AirdropDetective | t.me/emberwing_group | @AirdropDetectiveSupport (96 utenti/7g); emberwing non visto | aggiungere emberwing? |
| 4 | @unitsnews | @unitsnetwork | community collegata, **sotto soglia** (7 utenti, 5 msg liberi al 30/09) | soglie |
| 5 | @airdropinspector | + t.me/StarPhoneCC | StarPhoneCC è la chat di @StarPhone_CC (altro progetto), sotto soglia | non è del canale |
| 6 | @bitcoin_industry | OpenledgerKorea **gestito da bot** | coerente: escluso | — |
| 7 | @AirdropO | @AirdropNinjaGroup **gestito da bot**; trovato t.me/cryptogamingtech | AirdropNinjaGroup: 74 msg liberi da soli 9 utenti (coerente con bot); cryptogamingtech: 58 membri, 4 utenti | **togliere @AirdropO dalle coppie strette** |
| 13 | @iotradersio | community su X, non Telegram | — | nessuna coppia |
| 15 | @CryptoWorldNews | @zcash_community_chat attivo | attivo ma è la chat di un altro progetto (Zcash) | coppia o no? |
| 19 | @daomaker_ann | t.me/daomaker | community collegata, **sotto soglia** (5 utenti, 4 msg liberi al 28/09) | soglie |

Su tutte le altre righe del report di Marco lo script e il controllo manuale coincidono.
Il caso AirdropNinjaGroup conferma il limite noto: lo script **conta anche i bot** come utenti →
da correggere prima del prossimo controllo (escludere i mittenti bot).
