"""Conservative, reproducible exploratory text-only coding for the Point 4 Stage 4 sample.
This is a single coding pass, not an independent human validation or a trained predictor.
It deliberately abstains on opaque or underdetermined messages.
"""
import re, unicodedata, csv, sys
from pathlib import Path
from collections import defaultdict
import pandas as pd

SOURCE=Path('data/interim/point4/full_analysis/stage4_probability_sample/stage4_annotation_blind.csv')
OUT=Path('data/interim/point4/full_analysis/stage4_probability_sample/stage4_labeled.csv')

FUNCS=['Substantive discussion/opinion','Question or help request','Information/news sharing','Greeting/social interaction','Promotion/solicitation','Moderation/security','Other/unclear']
THEMES=['Crypto/markets','Technical/blockchain/wallet','Platform/rewards','Scams/security','Politics/government','War/geopolitics','Health/medicine','Religion/spirituality','Migration/identity','History/conspiracy claims','Platform/community operations','Technology/software/privacy','Work/commerce/services','Media/arts/gaming','Daily life/personal','Science/environment','History/culture (non-conspiratorial)','Other specific topic','No clear theme','Unclear']
# More specific patterns receive larger scores; generic words are downweighted.
RULES={
'Crypto/markets':[
(r'\b(bitcoin|btc|eth(?:ereum)?|solana|dogecoin|altcoin|cryptocurrency|crypto|usdt|usdc|defi|bnb|xrp|memecoin|tokenomics|token price|coinmarketcap)\b',2.6),
(r'\b(trading|trade|trader|forex|stocks?|market|bullish|bearish|candles?|technical analysis|price action|short squeeze|pump and dump|market cap|liquidat(?:ion|ed)|portfolio|long setup|short setup|leverage|stop loss|take profit)\b',1.7),
(r'\b(kurs|бирж|крипт|биткоин|трейд|монет|криптовалют|торгов|investissement|inversiones|mercado|precio|kript|handel|tendenz)\w*',1.6),
(r'币|币圈|交易|仓位|行情|加密货币|比特币',1.8)],
'Technical/blockchain/wallet':[
(r'\b(seed phrase|private key|public key|on.chain|smart contract|metamask|trustwallet|gas fees?|gas limit|block explorer|blockchain|ethereum network|rpc|web3|onchain|testnet|mainnet|txhash|txid|transaction hash|wallet|bridging|bridge tokens|erc20|bep20|chain id|node operator|validator)\b',2.9),
(r'\b(withdrawal|withdraw|deposit|transfer|address|confirmations?|staking|swap|liquidity pool)\b',1.3),
(r'\b(кошелек|кошел[ьё]к|транзакц|вывод|депозит|блокчейн|перевод|сеть|адрес)\w*',2.0),
(r'钱包|转账|提币|充币|链上|主网|跨链|智能合约',2.7)],
'Platform/rewards':[
(r'\b(airdrop|air drop|reward|rewards|galxe|zealy|quest|quests|task|tasks|xp|point ranking|points ranking|leaderboard|campaign reward|claim points|claim reward|daily check.in|giveaway|voucher|token distribution|claimable|eligible|allocation|whitelist|minting)\b',2.6),
(r'\b(winners?|prizes?|referral|bonus|redeem|claim|distribution|campaign|points?)\b',1.1),
(r'奖励|空投|积分|任务|领币|claim|бонус|награда',1.9)],
'Scams/security':[
(r'\b(scam(?:mer|mers|ming|med|s)?|phishing|fraud(?:ulent)?|fake admin|impersonat|stolen funds|wallet drainer|hacked account|malware|rug pull|ponzi|scam alert|scam policy|fake website|spam storm|scam bots)\w*',3.1),
(r'\b(suspicious dm|scammers? in dm|do not click links|never send.*private key|reported for fraud|security breach)\b',2.8),
(r'\b(мошенник|обман|скам|фишинг|fraude|estafa|golpe|betrug|scammer)\w*',2.5)],
'Politics/government':[
(r'\b(election|elections|voting|vote|ballot|president|parliament|congress|senator|prime minister|government|politics|politician|policymaker|democrat|republican|dsa|trump|biden|macron|merz|taxpayer|constitution|legislation|political party|referendum|mayor|dictator|protest|diplomatic sanction)\b',2.2),
(r'\b(beleid|regierung|bundeskanzler|staat|wahl|partei|presidente|gobierno|pol[ií]tica|pol[ií]tico|elecci[oó]n|senador|manifestaci[oó]n|prezident|правительств|президент|выбор|политик)\w*',2.1),
(r'民主党|政府|总统|选举|投票|国会|共和党',2.3)],
'War/geopolitics':[
(r'\b(ukrain(?:e|ian)|russia(?:n)?|putin|zelensk|nato|gaza|palestine|israel|iran|hezbollah|hamas|warfare|invasion|military|missile|rocket attack|airstrike|bombing|battlefront|air defense|frontline|artillery|troops|combat|army|soldiers|drone strike|war crimes|armed forces|geopolitic)\b',2.8),
(r'\b(guerra|ucrania|rusia|russie|ukraine|krieg|russland|ukraina|война|военн|армия|ракет|украин|росси|боев|израил|palestina|krieg)\w*',2.6),
(r'俄罗斯|乌克兰|战争|导弹|以色列|伊朗|战机|轰炸|军队',2.7)],
'Health/medicine':[
(r'\b(covid|coronavirus|pandemic|vaccine|vaccination|vaccinated|immunization|hospital|doctor|medical|medicine|health|mental health|illness|cancer|autism|virus|disease|pharma|pharmaceutical|fentanyl|drug overdose|antidepressant|treatment|nursing|patient|therapy|healing|dietary)\b',2.7),
(r'\b(salud|enfermedad|medicina|vacuna|pandemia|m[eé]dico|kranken|gesundheit|impfung|arzt|лечени|здоровь|вакцин|болезн|medizin|krankheit)\w*',2.6),
(r'疫苗|病毒|医生|癌症|健康|生病|医药',2.8)],
'Religion/spirituality':[
(r'\b(jesus|christ|god|lord|bible|biblical|scripture|pray|prayer|faith|church|holy spirit|spiritual|spirituality|religion|christian|muslim|islam|quran|theology|theological|prophet|satan|demon|exorcis|salvation|angel|gnostic|archon|astrolog|zodiac|horoscope|mars enters cancer|venus retrograde|ascension|christianity)\w*',2.4),
(r'\b(kirche|jesus|gott|glauben|islam|religione|dio|ges[uù]|religion|iglesia|dios|biblia|бог|церк|христ|аллах|молитв|religieux|spirituel)\w*',2.2),
(r'佛|上帝|耶稣|圣经|宗教|教会|阿拉|真主',2.3)],
'Migration/identity':[
(r'\b(immigrat|migrants?|immigrant|refugee|asylum|ethnic|racis|racial|racist|nationalis|nationality|white supremac|antisemit|anti.semit|aryan|maghreb|muslim migrants|border control|foreigners|citizenship|deportation|indigenous|transphob|gender identity)\w*',2.7),
(r'\b(migranti|immigrazione|migraci[oó]n|inmigrantes|fl[uü]chtling|migranten|ausl[aä]nder|национал|мигрант|беженц|расизм)\w*',2.5)],
'History/conspiracy claims':[
(r'\b(conspirac|cover.up|psy.?op|false flag|deep state|cabal|illuminati|tartaria|flat earth|chemtrail|secret society|agenda 2030|elite control|fake moon landing|qanon|q.drop|qalerts|qresearch|shadow government|globalist|plandemic|new world order|weather manipulation|reptilian|aliens? controlling|ufo coverup|ufos? are|hidden truth|freemasons?|occultism)\w*',2.9),
(r'\b(verschw[oö]rung|geheimregierung|plandemia|conspiraci[oó]n|conspiraci|teor[ií]a de|истин|заговор)\w*',2.5)],
'Platform/community operations':[
(r'\b(telegram group|group chat|channel (?:link|admin|ban|rules)|admin|moderator|banned|unbanned|restricted from sending|terms of service|user verification|account verification|community safety|group rules|support team|support ticket|account suspended|group guidelines|telegram setting|support status|team is checking|group access|telegram premium)\b',2.8),
(r'\b(bot commands?|dm from group|join the channel|join our group|chat support|contact the admin|please unban|report spam|spam warning|disable non contacts)\b',2.2),
(r'\b(админ|правила чата|канал|групп|модератор|спам|soporte|administrador|groupenregeln|群聊|管理员|账号)\w*',1.7)],
'Technology/software/privacy':[
(r'\b(artificial intelligence|\bai\b|algorith|software|technology|app|application|internet|digital|wifi|router|starlink|cyber|privacy|surveillance|encryption|e2ee|browser|laptop|computer|operating system|iphone|android|ios|vpn|data collect|machine learning|chatgpt|webcam|robot|neural network|software update|coding|password)\w*',2.0),
(r'\b(software|applicaci[oó]n|technologie|k[uü]nstliche intelligenz|технолог|программ|интернет|цифров|компьютер|приват|зашифров)\w*',1.8),
(r'人工智能|隐私|网络|软件|算法|应用程序|电脑',2.0)],
'Work/commerce/services':[
(r'\b(employment|recruit|hiring|job offer|job opening|work with us|work for us|partnership|marketing service|advertising|promotion service|premium service|subscription service|credit card|gift card|cash payment|payment solutions|payment processor|loan|money laundering|commercial offer|supplier|customer|seller|shipping|product available|trade discount|business opportunity|buying usdt above)\b',2.5),
(r'\b(services?|customers?|clients?|business|companies|selling|purchase|discounts?|sale|buy now|buy from|earn money|earn [\d,]+|earnings|for sale|paid service|payment|online income|costs|jobs?)\b',1.3),
(r'\b(verkaufe|verkaufen|dienstleistung|betrieb|geschäft|vendo|venta|servicio|empresa|trabajo|работа|услуги|продам|куплю|бизнес)\w*',1.9)],
'Media/arts/gaming':[
(r'\b(movie|movies|film|cinema|hollywood|music|song|singer|actor|album|concert|books?|novel|poem|literature|artist|tv show|video game|gaming|gameplay|playstation|xbox|minecraft|star trek|fallout|oblivion|comic|meme|netflix|streaming|youtube video|tiktok video|podcast|interview|documentary)\b',2.3),
(r'\b(pel[ií]cula|cine|m[uú]sica|can[cç][aã]o|videojuego|lied|musik|kino|film|песн|музык|фильм|игр|livestream)\w*',1.8),
(r'电影|音乐|视频|游戏|直播|歌曲',2.0)],
'Daily life/personal':[
(r'\b(family|husband|wife|mom|dad|children|school|weekend|birthday|married|marriage|relationship|romance|friendship|friends|sleep|slept|breakfast|lunch|dinner|cooking|car repair|my car|working day|my day|my home|daily life|holiday|my job|feelings|workout|football|sports|your weekend|how are you|new friends)\b',1.8),
(r'\b(familia|amigos|escuela|fin de semana|hoy|trabajo|famille|week.end|familie|друзья|семья|выходной|мама|папа)\w*',1.4)],
'Science/environment':[
(r'\b(climate|global warming|environment|pollution|chemical|physics|astronom|cosmos|galaxy|satellite|planet|orbit|scientist|geology|evolution|radiation|green energy|carbon emission|ecosystem|solar system|heliocentric|earth rotate|weather forecast|meteorology|heatwave|contamination|mars probe|environmental)\w*',2.3),
(r'\b(klima|umwelt|wissenschaft|science|climat|ecolog|ciencia|cient[ií]fic|environnement|окружающ|климат|эколог|научн)\w*',2.0)],
'History/culture (non-conspiratorial)':[
(r'\b(medieval|ancient roman|roman empire|archaeolog|historical records|heritage|century ago|history museum|historic battle|historian|old manuscript|historical event|archaeological site|history of|world war ii|wwii|middle ages|historical artifact)\w*',2.3),
(r'\b(geschichte|geschicht|historia|histoire|археолог|истори|древн|historisch)\w*',1.4)],
}
COMPILED={cat:[(re.compile(p,re.I|re.U),float(s)) for p,s in rules] for cat,rules in RULES.items()}
URL_RE=re.compile(r'https?://\S+|\bt\.me/\S+|\bwww\.\S+',re.I)
MENTION_RE=re.compile(r'(?<!\w)@[\w_]{3,}')
JUST_GREET=re.compile(r'^(?:(?:hello|hi|hey|yo|g+\s?m+|gm|gn|good\s*(?:morning|night|evening|afternoon)|morning|night|hola|hola a todos|bonjour|salut|thanks?|thank you|cheers|welcome|good day|how are you|nice|okay?|ok|yes|no|yep|yup|lol|lmao|haha|frens|guys|hi everyone|salam|peace be upon you|good project|bullish|gracias|merci|grazie|danke|привет|доброе утро|добрый день|спасибо|всем привет|大家好|你好|谢谢|早上好|晚安)(?:\W+|\s+))*$', re.I|re.U)
GREET_PATTERN=re.compile(r'\b(hello|hi (?:there|guys|all|everyone)|hey (?:guys|team|everyone)|good (?:morning|night|evening|afternoon)|gm|gn|frens|thanks|thank you|cheers|welcome|lol|lmao|haha|ahah|nice project|god bless|how are you|hola|bonjour|salut|gracias|merci|grazie|danke|peace be upon you|assalamu alaikum|доброе утро|добрый день|спасибо|привет)\b|谢谢|大家好|你好',re.I|re.U)
PROMO_STRONG=re.compile(r'\b(dm(?:\s+me)?(?:\s+for\s+(?:details|rates|prices))|contact (?:me|us|our team)|sign up|subscribe|join(?:\s+our|\s+us|\s+now)|register now|limited offer|buy now|sell(?:ing)? (?:iptv|accounts?|cards?|tokens?|crypto)|we (?:offer|provide)|available now|claim your (?:reward|bonus)|get (?:paid|rich|free money)|earn (?:up to|\d+[kKmM]?\s*(?:usd|usdt|dollars))|money laundering services|marketing (?:services|campaigns)|%\s*(?:return|profit|daily))\b|联系我|私信|加我|保证盈利|\b(GAN[AÁ]|GANA)\b',re.I)
PROMO_MILD=re.compile(r'\b(follow (?:me|us|our|trn)|check (?:out|this link)|referral code|vip group|premium membership|service|promo code|free trial|your opportunity|discount|advertising|sponsored|click (?:here|the link)|whatsapp\s*[:+]|join:|dm\s+@|buying\s+usdt)\b',re.I)
MODERATE=re.compile(r'\b(do not (?:send|post|advertise|spam)|not allowed in (?:the|this) group|banned from (?:the|this) (?:group|chat)|group rules|community guidelines|please (?:stop|avoid|respect)|respect the rules|spam(?:mers)? (?:will|are) (?:be|being) (?:banned|removed)|ban(?:ning)? (?:this|that) (?:user|account)|unban\s+@|/unban|rules prohibit|you have been muted|report (?:spam|the user)|moderator notice|safety update|community safety update|verification requirement|\badmin spam\b)\b|общаемся и пишем без мата|оскорбления других|запрещены',re.I)
QUESTION_RE=re.compile(r'\?|\b(why|how|what|when|where|who|does anyone|can anyone|anyone know|could someone|please help|i need help|need assistance|can you help|help me|help mee|please explain|is it possible|how to|what about|would it|may i know|how long|where can|did you|is there|does it|i wonder|sabes|puedes|c[oó]mo|qu[eé]|cu[aá]ndo|por qu[eé]|wer|warum|wie|wann|kann ich|pourquoi|comment|когда|почему|зачем|как|можно ли|помогите|объясните|сколько|什么|怎么|为什么|可以吗)\b',re.I)
NEWS_RE=re.compile(r'\b(breaking|update:|reportedly|according to|reports? (?:that|say|have)|in the us|in [a-z]+,?\s+(?:\d+|officials|police)|the (?:government|minister|president|court|police|military) (?:said|has|announced)|new report|source:|published|\bnews\b|via Reuters|the article|state media|intelligence has confirmed|news agency)\b|🇺🇦|🇷🇺|🇵🇸|🇮🇱',re.I)

# Manual review decisions for an initial set of diagnostic examples; input-only (no keys).
OVERRIDES={
 'S4-0001':('Greeting/social interaction','No clear theme','YES','NO','Acknowledgement; no distinct subject.'),
 'S4-0002':('Greeting/social interaction','History/conspiracy claims','YES','NO','Anon/self-identification, no independent claim about content.'),
 'S4-0003':('Substantive discussion/opinion','Politics/government','YES','NO','Discussion of French public finances and political risks.'),
 'S4-0004':('Question or help request','Migration/identity','YES','NO','Question about transphobia; missing surrounding context.'),
 'S4-0005':('Greeting/social interaction','No clear theme','YES','NO','Greeting.'),
 'S4-0006':('Information/news sharing','War/geopolitics','YES','NO','Spanish report about Russian military electronic warfare.'),
 'S4-0010':('Moderation/security','Platform/community operations','YES','NO','Explicit group conduct rule.'),
 'S4-0012':('Question or help request','History/culture (non-conspiratorial)','YES','NO','Question about building symbol; no explicit conspiracy claim.'),
 'S4-0017':('Other/unclear','Health/medicine','UNSURE','NO','Filename alone does not reveal document contents.'),
 'S4-0019':('Substantive discussion/opinion','Migration/identity','YES','NO','Racialized comment about taxation and protests.'),
 'S4-0025':('Substantive discussion/opinion','Science/environment','YES','NO','Claims about planetary rotation and heliocentric model.'),
 'S4-0032':('Information/news sharing','Media/arts/gaming','YES','UNSURE','Music break/link; video content unseen.'),
 'S4-0034':('Substantive discussion/opinion','History/culture (non-conspiratorial)','YES','NO','Historical reference used rhetorically.'),
 'S4-0040':('Information/news sharing','Platform/community operations','YES','NO','Platform terms of service status.'),
 'S4-0046':('Information/news sharing','Media/arts/gaming','YES','NO','Italian music history article.'),
 'S4-0049':('Moderation/security','Technology/software/privacy','YES','NO','Advice on Telegram privacy settings.'),
 'S4-0053':('Promotion/solicitation','Crypto/markets','YES','YES','Solicits purchase of USDT; not automatically fraudulent.'),
 'S4-0056':('Substantive discussion/opinion','War/geopolitics','YES','NO','Spanish political comment about defense manufacturing.'),
 'S4-0057':('Information/news sharing','Politics/government','YES','NO','Long commentary quoting political television remarks.'),
 'S4-0061':('Question or help request','Daily life/personal','YES','NO','Social question about personal preferences.'),
 'S4-0068':('Substantive discussion/opinion','Religion/spirituality','YES','NO','Exorcism and prayer.'),
 'S4-0073':('Promotion/solicitation','Work/commerce/services','YES','YES','Advertisement for credit card services.'),
 'S4-0079':('Promotion/solicitation','Work/commerce/services','YES','YES','Advertisement of payment service.'),
 'S4-0080':('Promotion/solicitation','Work/commerce/services','YES','YES','Advertisement of dating/adult content.'),
 'S4-0082':('Information/news sharing','Politics/government','YES','NO','Report about violence at a protest.'),
 'S4-0087':('Question or help request','Science/environment','YES','NO','Long question about diving.'),
 'S4-0089':('Greeting/social interaction','Religion/spirituality','YES','NO','Religious expression of thanks.'),
 'S4-0090':('Information/news sharing','Politics/government','YES','NO','German report about investment summit and government.'),
 'S4-0093':('Substantive discussion/opinion','History/conspiracy claims','YES','NO','Gnostic interpretation of algorithmic confinement.'),
 'S4-0094':('Question or help request','Technical/blockchain/wallet','YES','NO','Transaction deposit confirmation question.'),
 'S4-0095':('Substantive discussion/opinion','Crypto/markets','YES','NO','Trading-market commentary.'),
 'S4-0097':('Moderation/security','Platform/community operations','YES','NO','Community safety notice.'),
 'S4-0099':('Promotion/solicitation','Work/commerce/services','YES','YES','Solicitation for illicit financial service as self-described.'),
 'S4-0112':('Promotion/solicitation','Crypto/markets','YES','YES','Investment returns solicitation.'),
 'S4-0116':('Moderation/security','Platform/community operations','YES','NO','Spam report addressed to admin.'),
 'S4-0118':('Question or help request','Platform/community operations','YES','NO','Question about posting restriction.'),
 'S4-0119':('Promotion/solicitation','Platform/community operations','YES','YES','Advertisement for account/channel takedown service.'),
 'S4-0121':('Information/news sharing','Politics/government','YES','NO','Public debt reporting.'),
 'S4-0122':('Information/news sharing','Science/environment','YES','NO','Water pollution article.'),
 'S4-0123':('Moderation/security','Platform/community operations','YES','NO','Russian chat rule about insults.'),
 'S4-0125':('Information/news sharing','Religion/spirituality','YES','NO','Astrology forecast.'),
 'S4-0128':('Promotion/solicitation','Platform/community operations','YES','YES','Invitation to external group.'),
 'S4-0135':('Promotion/solicitation','Media/arts/gaming','YES','YES','Invites users to history-themed channel.'),
 'S4-0143':('Question or help request','Technology/software/privacy','YES','NO','Question about AI agent feature.'),
 'S4-0152':('Information/news sharing','Religion/spirituality','YES','NO','Occult interpretation of alcohol.'),
 'S4-0155':('Question or help request','Platform/rewards','YES','NO','Help with points claiming.'),
 'S4-0159':('Promotion/solicitation','Work/commerce/services','YES','YES','Endorsement encouraging paid VIP subscription.'),
 'S4-0165':('Information/news sharing','Migration/identity','YES','NO','French news about migrant deaths.'),
 'S4-0166':('Information/news sharing','Religion/spirituality','YES','NO','Spiritual channeling claim.'),
 'S4-0167':('Question or help request','Media/arts/gaming','YES','NO','Video-game comparison.'),
 'S4-0177':('Information/news sharing','Politics/government','YES','NO','Link title about voter ID.'),
 'S4-0179':('Promotion/solicitation','Work/commerce/services','YES','YES','Marketing-service promotion.'),
 'S4-0180':('Question or help request','Crypto/markets','YES','NO','Russian question about unified trading account.'),
 'S4-0187':('Information/news sharing','Technology/software/privacy','YES','NO','Spanish discussion of WiFi sensing and surveillance.'),
 'S4-0193':('Substantive discussion/opinion','Scams/security','YES','NO','Complains about scammers and spam.'),
 'S4-0195':('Information/news sharing','Religion/spirituality','YES','NO','German article about church-related financial losses.'),
 'S4-0199':('Information/news sharing','Technology/software/privacy','YES','NO','Canadian end-to-end encryption context.'),
 'S4-0202':('Moderation/security','Scams/security','YES','NO','Warns against unsolicited private messaging.'),
 'S4-0206':('Question or help request','Platform/rewards','YES','NO','Asks about reward timing.'),
 'S4-0218':('Information/news sharing','Science/environment','YES','NO','Quotation about climate-linked heatwaves.'),
 'S4-0222':('Question or help request','Technical/blockchain/wallet','YES','NO','Asks about mainnet timing.'),
 'S4-0228':('Information/news sharing','War/geopolitics','YES','NO','French report on military experience.'),
 'S4-0229':('Information/news sharing','Health/medicine','YES','NO','Legal news on social-media mental health effects.'),
 'S4-0236':('Information/news sharing','History/conspiracy claims','YES','NO','German speculative report on foreknowledge of attacks.'),
 'S4-0240':('Information/news sharing','Politics/government','YES','NO','Report about Brazilian senator and political events.'),
 'S4-0244':('Question or help request','Technology/software/privacy','YES','NO','Troubleshooting an internet connection.'),
 'S4-0245':('Substantive discussion/opinion','Scams/security','YES','NO','Russian spam/bots complaint.'),
 'S4-0247':('Information/news sharing','Crypto/markets','YES','NO','Trading signal with entry and stop levels.'),
 'S4-0252':('Substantive discussion/opinion','War/geopolitics','YES','NO','Observation on Russian battlefield tactics.'),
 'S4-0255':('Information/news sharing','War/geopolitics','YES','NO','Military-political Ukraine news report.'),
 'S4-0258':('Promotion/solicitation','Work/commerce/services','YES','YES','Commercial payment offer.'),
 'S4-0262':('Promotion/solicitation','Platform/community operations','YES','YES','Telegram Premium/Stars service advertisement.'),
 'S4-0268':('Promotion/solicitation','Work/commerce/services','YES','YES','Commercial account offer.'),
}

def theme_candidates(t):
 scores=defaultdict(float); hits=defaultdict(list)
 for theme, pats in COMPILED.items():
  for pat,wt in pats:
   matches=pat.findall(t)
   if matches:
    # cap repetitions (especially pasted spam) to avoid repeated terms overwhelming the subject
    scores[theme]+=wt*(1.0 + min(0.6,0.18*(len(matches)-1)))
    hits[theme].append((pat.pattern[:40],len(matches)))
 return scores,hits

def label_one(msg):
 raw=str(msg or '').strip(); t=unicodedata.normalize('NFKC',raw)
 no_urls=MENTION_RE.sub(' ',URL_RE.sub(' ',t)); cleaned=re.sub(r'[^\w\s]',' ',no_urls,flags=re.UNICODE)
 alpha=re.findall(r'[^\W\d_]+',cleaned,flags=re.UNICODE)
 # Interpretable message can be short, but require readable content not just URL, commands or IDs.
 if not alpha or (len(''.join(alpha))<3 and not GREET_PATTERN.search(t)):
  return ('Other/unclear','Unclear','NO','UNSURE','Opaque link, command, identifier, or non-verbal content; subject not recoverable.','low')
 # Structured noise, e.g. base58 address + a few words
 if len(raw)>65 and re.fullmatch(r'[A-Za-z0-9/+_=\-\s]{75,}',raw):
  return ('Other/unclear','Unclear','UNSURE','UNSURE','Structured/encoded content without sufficient prose.','low')
 scores,hits=theme_candidates(t)
 # Decision threshold: at least one specific signal, or two generic ones.
 ordered=sorted(scores.items(),key=lambda x:-x[1]); best,score=(ordered[0] if ordered else ('',0))
 runner_up=ordered[1][1] if len(ordered)>1 else 0
 charcount=len(t)
 # High priority for obvious greeting/social messages only when there is no substantive theme.
 is_salutation=bool(JUST_GREET.fullmatch(t.strip())) or (charcount<=42 and bool(GREET_PATTERN.search(t)) and score<2.8)
 if score>=2.0:
  theme=best
  if runner_up>=score*0.86 and score-runner_up<1.3:
   # Close semantic competition between two domains: if message is long enough choose subject, note uncertainty
   weak_topic=True
  else: weak_topic=False
 else:
  theme='No clear theme' if charcount<=95 else 'Unclear'
  weak_topic=True
 if is_salutation:
  fun='Greeting/social interaction'
  if score<3.3: theme='No clear theme'
 elif MODERATE.search(t):
  fun='Moderation/security'
 elif PROMO_STRONG.search(t) or re.search(r'\b(?:earn (?:[0-9]+|up to|extra)|high.yield|send (?:me )?a (?:pm|dm)|send me a message|want to (?:make|earn) money|for more details|contact @|get paid|visit our|limited spots|no investment required|investment platform|start earning|guaranteed returns|join (?:the|this|my) (?:group|channel)|paying in usdt|exclusive offer|order now)\b',t,re.I) or (PROMO_MILD.search(t) and (charcount>70 or bool(MENTION_RE.search(t)))):
  fun='Promotion/solicitation'
 elif QUESTION_RE.search(t) and (charcount<400 or t.strip().endswith('?')):
  fun='Question or help request'
 elif NEWS_RE.search(t) or (charcount>170 and (URL_RE.search(t) or '\n' in t or t.startswith('🇺'))):
  fun='Information/news sharing'
 elif charcount>70:
  fun='Substantive discussion/opinion'
 elif charcount<65:
  social=bool(re.search(r'^(?:great|yes|yess|yup|no|nah|lol|lmao|haha|nice|okay|ok|alright|sure|totally|exactly|right|agreed|agree|thanks|thank|welcome|good|gm|gn|hello|hey|hi|yo|cheers|wow|awesome|love it|me too|i see|i know|congrats|well said|hope|good luck|same|indeed|haha|frens|have a|sorry|not bad|i am fine|how are you)\b',t.strip(),re.I))
  fun='Greeting/social interaction' if social else ('Substantive discussion/opinion' if len(alpha)>=5 else 'Other/unclear')
 else:
  fun='Substantive discussion/opinion'
 promo='YES' if fun=='Promotion/solicitation' or (PROMO_STRONG.search(t) and fun!='Moderation/security') else ('UNSURE' if PROMO_MILD.search(t) and fun not in ('Promotion/solicitation','Moderation/security') else 'NO')
 # For uninformative phrases, do not infer topic from single generic word 'group', 'team' etc.
 if charcount<=55 and score<3.2 and (fun in ('Greeting/social interaction','Other/unclear') or (theme=='Platform/community operations' and not MODERATE.search(t))):
  theme='No clear theme';weak_topic=True
 # Content may be in unfamiliar scripts; the readable function is often still identifiable, but topic may be uncertain.
 non_latin_count=len(re.findall(r'[\u0400-\u052F\u0600-\u06FF\u4E00-\u9FFF\u0E00-\u0E7F\u1200-\u137F]',t))
 if non_latin_count>5 and score<2.3:
  theme='Unclear'
  if charcount>45 and not GREET_PATTERN.search(t): fun='Other/unclear'
  weak_topic=True
 # Generic promotional offers without a subject are commerce/services.
 if fun=='Promotion/solicitation' and theme in ('No clear theme','Unclear') and re.search(r'\b(service|offer|discount|buy|selling|premium|subscription|payment)\b',t,re.I):
  theme='Work/commerce/services'
 # No forced theme for generic reactions/questions.
 if theme=='Unclear':
  interp='UNSURE' if fun!='Other/unclear' else 'UNSURE'
 elif theme=='No clear theme' and fun in ('Other/unclear',):
  interp='UNSURE' if charcount<10 else 'YES'
 else:
  interp='YES'
 conf='high' if (not weak_topic and score>=3.4 and score-runner_up>=1.4) or (is_salutation and charcount<50) else ('medium' if score>=2.2 or fun in ('Greeting/social interaction','Promotion/solicitation') else 'low')
 note=''
 if weak_topic and theme=='Unclear': note='Visible text does not establish a reliable subject; no contextual inference.'
 elif weak_topic and theme=='No clear theme': note='No distinct subject recoverable from the visible message.'
 elif weak_topic: note='Subject may overlap another taxonomy category.'
 return fun,theme,interp,promo,note,conf

def main():
 import argparse
 p=argparse.ArgumentParser(description='Reproduce text-only exploratory Stage 4 annotations')
 p.add_argument('--source',type=Path,default=SOURCE)
 p.add_argument('--out',type=Path,default=OUT)
 args=p.parse_args()
 a=pd.read_csv(args.source,dtype=str,keep_default_na=False,encoding='utf-8-sig')
 assert len(a)==1170 and len(a.ITEM_ID.unique())==1170
 outputs=[]
 for row in a.itertuples():
  fun,theme,interpretable,promotional,notes,conf=label_one(row.GROUP_MESSAGE)
  if row.ITEM_ID in OVERRIDES:
   fun,theme,interpretable,promotional,notes=OVERRIDES[row.ITEM_ID];conf='reviewed'
  assert fun in FUNCS and theme in THEMES and interpretable in ('YES','NO','UNSURE') and promotional in ('YES','NO','UNSURE')
  outputs.append({'ITEM_ID':row.ITEM_ID,'GROUP_MESSAGE':row.GROUP_MESSAGE,'FUNCTION_LABEL':fun,'THEME_LABEL':theme,'INTERPRETABLE':interpretable,'PROMOTIONAL':promotional,'NOTES':notes,'CODING_CONFIDENCE':conf})
 out=pd.DataFrame(outputs)
 args.out.parent.mkdir(parents=True,exist_ok=True)
 out.to_csv(args.out,index=False,encoding='utf-8-sig')
 print('Wrote',args.out,'rows',len(out))
 print('Function:\n',out.FUNCTION_LABEL.value_counts().to_string())
 print('Theme:\n',out.THEME_LABEL.value_counts().to_string())
 print('Interpretable:\n',out.INTERPRETABLE.value_counts().to_string())
 print('Conf:\n',out.CODING_CONFIDENCE.value_counts().to_string())
# The following text-only adjudications refine the initial conservative codebook
# after reviewing borderline examples; they do not use pair identities or post matches.
ADJUDICATIONS={
 273:('Promotion/solicitation','Work/commerce/services','Russian invitation to private messages for paid work.'),
 276:('Question or help request','Health/medicine','Health-related question about named doctor.'),
 279:('Information/news sharing','Religion/spirituality','Intergalactic spiritual council announcement.'),
 281:('Other/unclear','Unclear','Opaque array of addresses and identifiers; no prose.'),
 284:('Promotion/solicitation','Work/commerce/services','Solicits investors for a service.'),
 285:('Information/news sharing','Politics/government','Reporting on police arrests at a protest.'),
 290:('Question or help request','Science/environment','Question about brain science.'),
 291:('Information/news sharing','Crypto/markets','Forex trading entry and stop levels.'),
 295:('Information/news sharing','Media/arts/gaming','Music track shared.'),
 296:('Information/news sharing','War/geopolitics','Spanish report about German military plans.'),
 299:('Promotion/solicitation','Crypto/markets','Investment-platform testimonial with invitation.'),
 300:('Substantive discussion/opinion','Politics/government','Opinion on municipal political administration.'),
 305:('Promotion/solicitation','Work/commerce/services','Solicits recipients for paid referral work.'),
 306:('Substantive discussion/opinion','Religion/spirituality','Religious invocation about combat.'),
 308:('Question or help request','History/conspiracy claims','Explicit flat-earth claim and question.'),
 311:('Information/news sharing','Politics/government','Commentary on political spending and elections.'),
 316:('Information/news sharing','History/conspiracy claims','Chemtrails claim.'),
 317:('Substantive discussion/opinion','Migration/identity','Antisemitic historical framing.'),
 318:('Question or help request','Crypto/markets','Request for trading guidance.'),
 319:('Promotion/solicitation','Media/arts/gaming','Repeated advertised film-preview reward offer.'),
 322:('Information/news sharing','Health/medicine','German alternative-medical advice.'),
 326:('Promotion/solicitation','Work/commerce/services','Chinese offer of paid task.'),
 332:('Substantive discussion/opinion','History/conspiracy claims','Critique of awakening narratives.'),
 339:('Question or help request','Scams/security','Asks about safety protections.'),
 341:('Substantive discussion/opinion','Religion/spirituality','Devotional message.'),
 351:('Substantive discussion/opinion','Daily life/personal','Discussion of family crafts.'),
 353:('Substantive discussion/opinion','Platform/community operations','Opinion on lack of source references.'),
 355:('Substantive discussion/opinion','Scams/security','Disputes fraud allegation and directs to updates.'),
 361:('Information/news sharing','War/geopolitics','German text about Ukraine and British policy.'),
 365:('Substantive discussion/opinion','Scams/security','Comments on deleted scammer account.'),
 366:('Promotion/solicitation','Health/medicine','Advertises herbal remedy channel.'),
 367:('Question or help request','History/conspiracy claims','Question about Q drops and intelligence agencies.'),
 371:('Information/news sharing','Platform/community operations','Binance account/platform restriction.'),
 373:('Information/news sharing','Platform/rewards','Describes changes to reward distribution.'),
 375:('Promotion/solicitation','Work/commerce/services','Russian paid-task solicitation.'),
 376:('Substantive discussion/opinion','Technology/software/privacy','Spanish comment about phone malware.'),
 379:('Promotion/solicitation','Crypto/markets','Promotional investment testimony.'),
 384:('Information/news sharing','Health/medicine','Fauci-related public health content.'),
 386:('Promotion/solicitation','Health/medicine','Advertises health/immune-system channel.'),
 387:('Information/news sharing','History/conspiracy claims','Conspiracy claim about 9/11.'),
 389:('Information/news sharing','Technical/blockchain/wallet','Exchange deposit support news.'),
 407:('Other/unclear','Unclear','Insufficient context to identify subject.'),
 415:('Information/news sharing','Politics/government','Political reporting.'),
 436:('Promotion/solicitation','Health/medicine','Promotes medical treatment approach through a testimonial.'),
 440:('Information/news sharing','Politics/government','Spanish report of political action.'),
 445:('Promotion/solicitation','Work/commerce/services','Advertises currency-exchange service.'),
 448:('Promotion/solicitation','Work/commerce/services','Promotes gambling giveaway via profile.'),
 451:('Promotion/solicitation','Work/commerce/services','Financial-service advertisement.'),
 454:('Promotion/solicitation','Work/commerce/services','Gambling platform advertisement.'),
 458:('Question or help request','Crypto/markets','Question on crypto discussions.'),
 461:('Substantive discussion/opinion','Politics/government','German commentary on election tactics.'),
 463:('Substantive discussion/opinion','Health/medicine','Discussion of cancer and vaccination claims.'),
 468:('Promotion/solicitation','History/conspiracy claims','Promotes channel about conspiratorial mystery topics.'),
 471:('Information/news sharing','History/conspiracy claims','Promotes a UFO-themed livestream; visible topic.'),
 475:('Promotion/solicitation','Work/commerce/services','Arabic offer of financial returns.'),
 479:('Substantive discussion/opinion','Crypto/markets','Opinion about price action.'),
 481:('Substantive discussion/opinion','Technology/software/privacy','App usability feedback.'),
 484:('Substantive discussion/opinion','History/conspiracy claims','Claim about a cabal and political influence.'),
 487:('Question or help request','Platform/community operations','Complaint about response from admins.'),
 488:('Information/news sharing','Health/medicine','Message about medical establishments.'),
 489:('Substantive discussion/opinion','History/conspiracy claims','Historical conspiracy claim.'),
 492:('Substantive discussion/opinion','Technical/blockchain/wallet','Project vision beyond crypto wallet.'),
 493:('Substantive discussion/opinion','Religion/spirituality','Opinion on Christianity.'),
 494:('Substantive discussion/opinion','Health/medicine','COVID/vaccine discussion.'),
 497:('Substantive discussion/opinion','Crypto/markets','Comment on public crypto investment.'),
 498:('Promotion/solicitation','Work/commerce/services','Russian paid-office task.'),
 499:('Substantive discussion/opinion','Politics/government','Opinion about speech and policing.'),
 504:('Promotion/solicitation','Health/medicine','Promotes health/safety content.'),
 506:('Substantive discussion/opinion','Platform/community operations','Comment that a project seems abandoned.'),
 514:('Promotion/solicitation','Crypto/markets','Promotional call for early participation.'),
 516:('Substantive discussion/opinion','Scams/security','Opinion on breach response.'),
 524:('Question or help request','Technical/blockchain/wallet','Question about locked tokens.'),
 526:('Information/news sharing','Media/arts/gaming','Music-video link.'),
 535:('Moderation/security','Platform/community operations','Bot report command.'),
 537:('Substantive discussion/opinion','Platform/community operations','Russian discussion of project operations.'),
 539:('Question or help request','Platform/community operations','Asks development team for progress update.'),
 544:('Information/news sharing','War/geopolitics','Diplomatic foreign-exchange policy involving Russia.'),
 550:('Information/news sharing','Politics/government','Spanish political commentary.'),
 554:('Substantive discussion/opinion','Technology/software/privacy','Opinion on data center regulations.'),
 555:('Substantive discussion/opinion','Health/medicine','Opinion about healthcare cost.'),
 560:('Greeting/social interaction','No clear theme','Russian good-morning greeting.'),
 563:('Substantive discussion/opinion','Politics/government','Discussion about speech regulation.'),
 568:('Question or help request','Platform/rewards','Question about mining-reward distribution.'),
 574:('Question or help request','Religion/spirituality','Asks about origin of religious term rapture.'),
 581:('Information/news sharing','Health/medicine','Provides vaccination source URL.'),
 583:('Question or help request','Platform/community operations','Question about unsolicited private contact.'),
 588:('Greeting/social interaction','No clear theme','Russian well-wish greeting.'),
 589:('Question or help request','Crypto/markets','Russian inquiry about active traders.'),
 591:('Promotion/solicitation','Work/commerce/services','Chinese offer to collect payments.'),
 592:('Promotion/solicitation','Work/commerce/services','Exchange-listing commercial outreach.'),
 593:('Promotion/solicitation','Media/arts/gaming','Advertisement for image transformation service.'),
 596:('Information/news sharing','Politics/government','Report on ballot scanners.'),
 597:('Moderation/security','Scams/security','Warning about impersonation and wallet access.'),
 598:('Information/news sharing','Health/medicine','Public-health report.'),
 600:('Question or help request','Platform/community operations','Requests support-ticket status.'),
 607:('Substantive discussion/opinion','Health/medicine','Claims about microwave radiation and health.'),
 609:('Substantive discussion/opinion','Technical/blockchain/wallet','EVM sidechain compatibility.'),
 611:('Promotion/solicitation','Platform/community operations','Directed invitation to external contact.'),
 613:('Information/news sharing','Health/medicine','Health-emergency claim.'),
 616:('Substantive discussion/opinion','Crypto/markets','Trading with leverage opinion.'),
 620:('Information/news sharing','Scams/security','News about criminal call-center fraud.'),
 626:('Promotion/solicitation','Work/commerce/services','Repeated payment-service advertisement.'),
 627:('Substantive discussion/opinion','Politics/government','Opinion about border policy.'),
 631:('Information/news sharing','Politics/government','Reports protest and police clash.'),
 632:('Promotion/solicitation','Work/commerce/services','US-UK commercial outreach.'),
 634:('Information/news sharing','Politics/government','Spanish political report.'),
 638:('Information/news sharing','Health/medicine','Vaccine-related article.'),
 646:('Substantive discussion/opinion','Religion/spirituality','Spirituality and social control discussion.'),
 647:('Information/news sharing','Science/environment','Bacteria/mosquito environmental claim.'),
 649:('Question or help request','Platform/rewards','Question about reward eligibility.'),
 651:('Information/news sharing','Health/medicine','Alternative medical treatment claim.'),
 653:('Substantive discussion/opinion','Health/medicine','Opinion on health service competition.'),
 654:('Substantive discussion/opinion','Platform/community operations','Account banning and binding operations.'),
 655:('Substantive discussion/opinion','Scams/security','Comment on bots/spam.'),
 665:('Information/news sharing','Scams/security','Malware incident report.'),
 673:('Promotion/solicitation','Crypto/markets','Marketing crypto firm through referral.'),
 677:('Promotion/solicitation','Crypto/markets','Promotional investment testimonial.'),
 679:('Substantive discussion/opinion','Daily life/personal','Discussion of personal travel preparation.'),
 684:('Moderation/security','Platform/community operations','Direct complaint asking others to stop spamming.'),
 685:('Substantive discussion/opinion','Science/environment','Particle-accelerator scientific discussion.'),
 687:('Question or help request','Platform/community operations','Request for admin support.'),
 688:('Question or help request','Technical/blockchain/wallet','Phantom Solana connection troubleshooting.'),
 689:('Information/news sharing','Politics/government','British politics and leadership election.'),
 693:('Information/news sharing','Politics/government','Election postal ballot irregularities.'),
 694:('Information/news sharing','Health/medicine','Pandemic simulation claim.'),
 729:('Promotion/solicitation','Crypto/markets','Advertising USDT currency exchange.'),
 755:('Substantive discussion/opinion','Crypto/markets','Chinese comment about crypto liquidity.'),
 757:('Substantive discussion/opinion','Crypto/markets','Market stability statement.'),
 759:('Substantive discussion/opinion','Politics/government','Opinion supporting military coup.'),
 765:('Information/news sharing','History/conspiracy claims','Coronavirus conspiracy narrative about a novel.'),
 767:('Substantive discussion/opinion','Daily life/personal','Veganism as ethics and lifestyle.'),
 769:('Substantive discussion/opinion','History/conspiracy claims','Theory about subterranean bunkers.'),
 771:('Promotion/solicitation','Work/commerce/services','Russian recruitment for construction work.'),
 774:('Information/news sharing','Politics/government','German opinion on AfD public finance.'),
 777:('Promotion/solicitation','Work/commerce/services','Chatter-service solicitation.'),
 782:('Promotion/solicitation','Crypto/markets','Financial adviser promotional testimony.'),
 783:('Promotion/solicitation','Work/commerce/services','Russian paid card purchase offer.'),
 784:('Promotion/solicitation','Work/commerce/services','Personal financial donation solicitation.'),
 788:('Substantive discussion/opinion','History/conspiracy claims','Conspiracy claim involving children.'),
 792:('Information/news sharing','Scams/security','Cyberattack news about water infrastructure.'),
 793:('Information/news sharing','Politics/government','Political achievements compilation.'),
 797:('Substantive discussion/opinion','Technology/software/privacy','Italian discussion of AI governance.'),
 798:('Substantive discussion/opinion','Scams/security','Opinion on token migration scam risk.'),
 804:('Question or help request','Politics/government','Questions about ISIS, Merkel and migration.'),
 807:('Substantive discussion/opinion','Health/medicine','Claims about drug additives.'),
 810:('Moderation/security','Scams/security','Warning about scammers.'),
 811:('Substantive discussion/opinion','Politics/government','Opinion on European political protests.'),
 815:('Substantive discussion/opinion','Migration/identity','Gender-based stereotype.'),
 816:('Information/news sharing','Politics/government','Document on emergency economic legislation.'),
 819:('Promotion/solicitation','Technology/software/privacy','Marketing residential ISP proxies.'),
 820:('Promotion/solicitation','Work/commerce/services','Casino/gaming advertisement.'),
 827:('Substantive discussion/opinion','History/conspiracy claims','Theory about 7 October response.'),
 830:('Promotion/solicitation','Health/medicine','Advertises wellness product for sleep.'),
 834:('Promotion/solicitation','Health/medicine','Advertises health tea and channel.'),
 843:('Information/news sharing','Migration/identity','Immigration debate and politician quote.'),
 844:('Promotion/solicitation','Media/arts/gaming','Repeated film-preview advertisement.'),
 845:('Information/news sharing','War/geopolitics','Saudi oil shipments and regional tensions.'),
 847:('Substantive discussion/opinion','Health/medicine','Opinion on nutritional products.'),
 849:('Information/news sharing','Science/environment','Earthquake report.'),
 854:('Substantive discussion/opinion','Religion/spirituality','Religious statement on chaplains.'),
 858:('Information/news sharing','Crypto/markets','Bitcoin ETF flow report.'),
 862:('Information/news sharing','Technology/software/privacy','AI skills/training workforce report.'),
 866:('Information/news sharing','War/geopolitics','South Korean air defense system.'),
 867:('Promotion/solicitation','Work/commerce/services','Credit card trading advertisement.'),
 870:('Information/news sharing','History/conspiracy claims','Vaccine-passport conspiracy claim.'),
 874:('Promotion/solicitation','Religion/spirituality','Invites to religious discussion group.'),
 876:('Information/news sharing','History/conspiracy claims','QAnon-style political messaging.'),
 879:('Promotion/solicitation','Health/medicine','Advertises detoxification content.'),
 881:('Information/news sharing','Politics/government','Reports police arrest operation.'),
 884:('Information/news sharing','Politics/government','German article on China restrictions.'),
 885:('Substantive discussion/opinion','History/conspiracy claims','Water-rights theft claim.'),
 889:('Information/news sharing','Politics/government','US political administration comment.'),
 893:('Substantive discussion/opinion','Health/medicine','Discussion of sexually transmitted infections.'),
 894:('Information/news sharing','Health/medicine','Vaccine-related content.'),
 895:('Information/news sharing','History/conspiracy claims','Alien abduction claim.'),
 897:('Information/news sharing','Migration/identity','Race-based crime report.'),
 902:('Information/news sharing','Religion/spirituality','Religious current-affairs programme.'),
 903:('Substantive discussion/opinion','Health/medicine','MRI and healthcare opinion.'),
 906:('Promotion/solicitation','Crypto/markets','Investment testimonial with solicitation.'),
 908:('Promotion/solicitation','Crypto/markets','High-yield USDT buying advertisement.'),
 919:('Moderation/security','Platform/community operations','Says admin will remove user.'),
 923:('Information/news sharing','History/conspiracy claims','9/11 conspiracy claim shared.'),
 925:('Information/news sharing','Technology/software/privacy','Explanation of fuel technology.'),
 926:('Information/news sharing','Migration/identity','Migration article with inflammatory framing.'),
 931:('Promotion/solicitation','Media/arts/gaming','Repeated film-preview advertisement.'),
 932:('Substantive discussion/opinion','Religion/spirituality','German spiritual message.'),
 935:('Promotion/solicitation','Media/arts/gaming','Invites users to private viral-video channel.'),
 938:('Promotion/solicitation','Work/commerce/services','Gaming/casino promotion.'),
 940:('Question or help request','Science/environment','Flooding/earthquake question.'),
 943:('Information/news sharing','Politics/government','Report on German political trends.'),
 950:('Moderation/security','Platform/community operations','Directs questions to designated channel.'),
 958:('Promotion/solicitation','Technology/software/privacy','Free face-swap service offer.'),
 965:('Information/news sharing','War/geopolitics','French peace proposal for Ukraine.'),
 966:('Promotion/solicitation','Health/medicine','Health product advertisement.'),
 978:('Promotion/solicitation','Work/commerce/services','Russian paid assembly work offer.'),
 984:('Information/news sharing','Migration/identity','Hate-framed crime report.'),
 985:('Promotion/solicitation','Media/arts/gaming','Advertises musical show.'),
 992:('Promotion/solicitation','Migration/identity','Asks users to boost/follow political identity story.'),
 993:('Information/news sharing','Politics/government','News about Netanyahu and parliament.'),
 994:('Promotion/solicitation','Technology/software/privacy','Offers development service for crypto bots.'),
 999:('Information/news sharing','Religion/spirituality','Religious quotation.'),
 1064:('Information/news sharing','Religion/spirituality','Fire at religious pilgrimage site.'),
 1066:('Information/news sharing','Politics/government','Legal case involving member of Congress.'),
 1070:('Information/news sharing','Work/commerce/services','German report on business shutdown.'),
 1073:('Promotion/solicitation','Media/arts/gaming','Repeated movie-preview promotion.'),
 1076:('Substantive discussion/opinion','Media/arts/gaming','Reference to Star Wars scene.'),
 1082:('Promotion/solicitation','Crypto/markets','USDT returns solicitation.'),
 1083:('Information/news sharing','History/culture (non-conspiratorial)','Historical portrait provenance.'),
 1085:('Promotion/solicitation','Science/environment','Promotes online climate lesson.'),
 1089:('Substantive discussion/opinion','Technology/software/privacy','Observation on facial recognition surveillance.'),
 1090:('Information/news sharing','Health/medicine','Report claiming COVID/vaccine-related findings.'),
 1091:('Promotion/solicitation','Work/commerce/services','Casino advertisement.'),
 1092:('Information/news sharing','War/geopolitics','Hormuz and Iranian military tensions.'),
 1094:('Substantive discussion/opinion','Migration/identity','Interview about racial identity.'),
 1095:('Promotion/solicitation','Work/commerce/services','Commercial solicitation for adult services.'),
 1099:('Information/news sharing','Platform/community operations','Account login or rate-limit notice.'),
 1102:('Information/news sharing','Daily life/personal','Boat accident story.'),
 1109:('Information/news sharing','Religion/spirituality','Historical religious polemical book.'),
 1110:('Information/news sharing','Work/commerce/services','Microsoft employment report.'),
 1112:('Substantive discussion/opinion','Politics/government','German political party leadership commentary.'),
 1114:('Substantive discussion/opinion','Platform/community operations','Community scale and admin response.'),
 1121:('Promotion/solicitation','Scams/security','Offer for phishing and cyberattack services.'),
 1123:('Information/news sharing','War/geopolitics','Spanish intelligence and Iranian relations.'),
 1125:('Question or help request','Technical/blockchain/wallet','Trust Wallet transaction problem.'),
 1129:('Substantive discussion/opinion','Health/medicine','Vaccine-related conspiracy assertion.'),
 1133:('Moderation/security','Platform/community operations','Group spam moderation announcement.'),
 1134:('Promotion/solicitation','Health/medicine','Repeated prostate product advertisement.'),
 1135:('Promotion/solicitation','Work/commerce/services','Bengali app income solicitation.'),
 1137:('Information/news sharing','War/geopolitics','Lebanese-Israeli military report.'),
 1156:('Promotion/solicitation','Work/commerce/services','German financial support appeal.'),
 1159:('Information/news sharing','History/conspiracy claims','Chinese claim about concealed pilot incident.'),
 1161:('Information/news sharing','Religion/spirituality','Biblical passage shared.'),
 1164:('Substantive discussion/opinion','War/geopolitics','German hypothetical scenario of war with Russia.'),
 1167:('Information/news sharing','Politics/government','US election political news.'),
 1168:('Substantive discussion/opinion','Daily life/personal','Anecdote about eggs and farming.'),
 1169:('Information/news sharing','Politics/government','Spanish report of investigation handling.'),
}
ADJUDICATIONS.update({
  76:('Substantive discussion/opinion','Politics/government','Opinion about separatist political actors.'),
  126:('Substantive discussion/opinion','Crypto/markets','Opinion about a trading portfolio and risks.'),
  142:('Substantive discussion/opinion','Politics/government','Criticism of US political parties.'),
  178:('Substantive discussion/opinion','Religion/spirituality','Disagreement about religious views.'),
  212:('Information/news sharing','History/culture (non-conspiratorial)','Mentions old vehicles on a decommissioned airbase.'),
  223:('Substantive discussion/opinion','Daily life/personal','Opinion about leaving nature alone.'),
  304:('Information/news sharing','Politics/government','German report on Welsh premier and government.'),
  331:('Question or help request','Unclear','Seeks clarification of number in a news report; no specific subject.'),
  354:('Substantive discussion/opinion','Religion/spirituality','Religious quotation and discussion.'),
  356:('Substantive discussion/opinion','Work/commerce/services','Opinion on a national economy and prices.'),
  362:('Substantive discussion/opinion','Politics/government','Russian comment on state status in Japanese law.'),
  400:('Information/news sharing','Daily life/personal','French household-tip post.'),
  410:('Greeting/social interaction','Politics/government','Thanks for translation of a political rally speech.'),
  420:('Substantive discussion/opinion','Migration/identity','Identity-related political slogan about Ceuta.'),
  452:('Substantive discussion/opinion','Daily life/personal','Personal anecdote about choosing product flavors.'),
  538:('Substantive discussion/opinion','Politics/government','Opinion about authoritarian leftists.'),
  543:('Question or help request','Work/commerce/services','Russian text about a bank agreement; asks to clarify request.'),
  556:('Substantive discussion/opinion','Platform/community operations','Opinion about project team utility.'),
  575:('Substantive discussion/opinion','Platform/community operations','Discusses wording of project announcements.'),
  590:('Substantive discussion/opinion','History/conspiracy claims','Aircraft measurements in apparent technical dispute.'),
  612:('Substantive discussion/opinion','Platform/community operations','Discussion about sharing inspirational links in community.'),
  623:('Greeting/social interaction','No clear theme','Spanish teasing/reaction; no subject for taxonomy.'),
  641:('Question or help request','Platform/community operations','Request to share troubleshooting screenshots.'),
  686:('Question or help request','Media/arts/gaming','Question about seasons of a show or game.'),
  714:('Substantive discussion/opinion','Crypto/markets','Discussion of exchange accounts and trades.'),
  732:('Information/news sharing','Media/arts/gaming','Spanish report about sports award.'),
  739:('Promotion/solicitation','Platform/community operations','Links to an external private Telegram channel.'),
  745:('Greeting/social interaction','Technology/software/privacy','Welcoming Internet-related joke.'),
  772:('Substantive discussion/opinion','No clear theme','Reaction to long discussion thread.'),
  786:('Substantive discussion/opinion','Politics/government','Rhetorical question about political positions.'),
  787:('Question or help request','Health/medicine','Question about milk products.'),
  801:('Information/news sharing','Platform/community operations','Explains channel search and FAQ.'),
  860:('Information/news sharing','Politics/government','German news about AfD politician.'),
  924:('Substantive discussion/opinion','History/conspiracy claims','Critique of the Anon movement and evidence.'),
  947:('Substantive discussion/opinion','Politics/government','Russian opinion on French society and economy.'),
  951:('Substantive discussion/opinion','Work/commerce/services','Discussion about rental rates and budgets.'),
  969:('Substantive discussion/opinion','Crypto/markets','Opinion about market manipulation.'),
  987:('Substantive discussion/opinion','Crypto/markets','Market preparation comment.'),
  1011:('Substantive discussion/opinion','Technology/software/privacy','Personal report about ad targeting and earbuds.'),
  1030:('Substantive discussion/opinion','Politics/government','Opinion about political civic discourse.'),
  1036:('Promotion/solicitation','Work/commerce/services','Advertisement for purported earning opportunity.'),
  1038:('Information/news sharing','Health/medicine','Vaccine-related report/activism.'),
  1042:('Question or help request','Platform/rewards','Question about token buyback and burn timing.'),
  1046:('Substantive discussion/opinion','Health/medicine','Dutch COVID-era health-policy commentary.'),
  1048:('Substantive discussion/opinion','Platform/community operations','Reaction to requests for money in group.'),
  1057:('Promotion/solicitation','Work/commerce/services','Russian offer to buy NFTs.'),
  1059:('Greeting/social interaction','No clear theme','Russian good-morning greeting.'),
  1078:('Information/news sharing','Politics/government','Reports defamation claim relating to public figure.'),
  1081:('Substantive discussion/opinion','History/culture (non-conspiratorial)','Rosenbergs historical reference.'),
  1097:('Information/news sharing','History/culture (non-conspiratorial)','French Revolution historic reference.'),
  1154:('Substantive discussion/opinion','Daily life/personal','Personal plan for vehicle improvement.'),
})

# Delete erroneous placeholder IDs when necessary; independent of source group.
for idx,(fun,theme,note) in ADJUDICATIONS.items():
 if idx<=1170:
  key=f'S4-{idx:04d}'
  OVERRIDES[key]=(fun,theme,'YES','YES' if fun=='Promotion/solicitation' else 'NO',note)

if __name__=="__main__":
    main()
