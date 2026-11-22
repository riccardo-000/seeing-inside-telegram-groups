const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require(process.env.SKILL + "/scripts/apply_theme.js");

const OUT = process.argv[2];
const THEME = {
  name: "Telegram Groups",
  headFontFace: "Arial",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B1F2E", lt1: "FFFFFF", dk2: "14213D", lt2: "EEF1F5",
    accent1: "E4572E", accent2: "8D99AE", accent3: "2A9D8F", accent4: "F2A541",
    accent5: "5C6B8A", accent6: "B8C1D1", hlink: "2A9D8F", folHlink: "5C6B8A",
  },
};
const HEX = THEME.colors;
const CORAL = HEX.accent1, GRAY = HEX.accent2, TEAL = HEX.accent3, INK = HEX.dk2;

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625
  pres.title = "Seeing Inside Telegram Groups";
  pres.author = "Marco, Simone, Riccardo";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  // ---------- layouts ----------
  pres.defineSlideMaster({
    title: "Title Dark",
    background: { color: C.text2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 1.55, w: 8.8, h: 1.2,
        fontSize: 40, bold: true, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 2.75, w: 8.8, h: 0.6,
        fontSize: 18, color: C.accent6, valign: "top", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "Content",
    background: { color: C.background1 },
    margin: [0.5, 0.5, 0.5, 0.5],
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9.0, h: 0.75,
        fontSize: 24, bold: true, color: C.text2, valign: "top", align: "left", margin: 0 }, text: "" } },
      { text: { text: "Seeing Inside Telegram Groups · DTU", options: { x: 0.5, y: 5.2, w: 5, h: 0.25,
        fontSize: 9, color: C.accent5, margin: 0 } } },
    ],
    slideNumber: { x: 9.1, y: 5.2, w: 0.4, h: 0.25, fontSize: 9, color: C.accent5, align: "right" },
  });

  const ic = {
    channel: await icon(fa.FaBullhorn, "FFFFFF"), group: await icon(fa.FaComments, "FFFFFF"),
    db: await icon(fa.FaDatabase, "FFFFFF"), eye: await icon(fa.FaEye, "FFFFFF"),
    clock: await icon(fa.FaRegClock, "FFFFFF"), users: await icon(fa.FaUsers, "FFFFFF"),
    robot: await icon(fa.FaRobot, "FFFFFF"), shield: await icon(fa.FaUserShield, "FFFFFF"),
    user: await icon(fa.FaUser, "FFFFFF"), arrow: await icon(fa.FaArrowRight, GRAY),
    arrowW: await icon(fa.FaArrowRight, HEX.accent6), mail: await icon(fa.FaEnvelope, "FFFFFF"),
    flask: await icon(fa.FaFlask, "FFFFFF"), file: await icon(fa.FaFileAlt, "FFFFFF"),
    check: await icon(fa.FaCheck, "FFFFFF"), cal: await icon(fa.FaRegCalendarAlt, "FFFFFF"),
  };
  // icon in a colored circle (the deck's motif)
  const badge = (slide, img, x, y, d, fill, name) => {
    slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: name + " circle" });
    const p = d * 0.27;
    slide.addImage({ data: img, x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, objectName: name + " icon" });
  };
  const text = (slide, t, o) => slide.addText(t, { isTextBox: true, margin: 0, valign: "top", color: C.text1, fontSize: 14, ...o });
  const chartBase = () => ({
    catAxisLabelColor: HEX.accent5, valAxisLabelColor: HEX.accent5,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
    legendFontFace: "+mn-lt", titleFontFace: "+mn-lt",
    catAxisLabelFontSize: 11, valAxisLabelFontSize: 10, dataLabelFontSize: 11, dataLabelColor: HEX.dk1,
    valGridLine: { color: "E3E7EE", size: 0.5 }, catGridLine: { style: "none" },
    showValue: true, valAxisHidden: true, catAxisLineShow: false, valAxisLineShow: false,
  });
  const S = (title, section) => {
    const s = pres.addSlide({ masterName: "Content", sectionTitle: section });
    s.addText(title, { placeholder: "title" });
    return s;
  };
  const card = (slide, x, y, w, h, name, fill = HEX.lt2) =>
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill }, objectName: name });

  // ================= 1. Title =================
  pres.addSection({ title: "Setup" });
  let s = pres.addSlide({ masterName: "Title Dark", sectionTitle: "Setup" });
  s.addText("Seeing Inside Telegram Groups", { placeholder: "title" });
  s.addText("What linked discussion groups reveal that channels don't", { placeholder: "body" });
  badge(s, ic.channel, 0.6, 0.55, 0.7, GRAY, "channel");
  s.addImage({ data: ic.arrowW, x: 1.45, y: 0.75, w: 0.3, h: 0.3, objectName: "arrow" });
  badge(s, ic.group, 1.9, 0.55, 0.7, CORAL, "group");
  text(s, "Research progress presentation · empirical technical paper", { x: 0.6, y: 3.45, w: 8.8, h: 0.35, fontSize: 14, color: CORAL, bold: true });
  text(s, "Marco · Simone · Riccardo", { x: 0.6, y: 4.3, w: 6, h: 0.35, fontSize: 16, color: C.background1, bold: true });
  text(s, "Research Topics in Cybersecurity · DTU · November 2026", { x: 0.6, y: 4.65, w: 7, h: 0.3, fontSize: 12, color: C.accent6 });
  s.addNotes("RICCARDO (0:00-0:15). Hi everyone, we are Marco, Simone and Riccardo. Today we'll present our research project, the main findings obtained so far, and our plan for completing the final paper.");

  // ================= 2. Problem, gap, contribution =================
  s = S("Channels broadcast; linked groups talk back", "Setup");
  card(s, 0.5, 1.2, 3.6, 1.75, "channel card");
  badge(s, ic.channel, 0.7, 1.35, 0.5, GRAY, "channel");
  text(s, "Channel", { x: 1.35, y: 1.43, w: 2.5, h: 0.35, fontSize: 17, bold: true });
  text(s, [
    { text: "Broadcast: only admins post", options: { bullet: true, breakLine: true } },
    { text: "Well covered by datasets such as TGDataset", options: { bullet: true } },
  ], { x: 0.7, y: 2.0, w: 3.25, h: 0.9, fontSize: 13, paraSpaceAfter: 4 });
  s.addImage({ data: ic.arrow, x: 4.3, y: 1.9, w: 0.4, h: 0.4, objectName: "arrow" });
  card(s, 4.9, 1.2, 4.6, 1.75, "group card");
  badge(s, ic.group, 5.1, 1.35, 0.5, CORAL, "group");
  text(s, "Linked discussion group", { x: 5.75, y: 1.43, w: 3.6, h: 0.35, fontSize: 17, bold: true });
  text(s, [
    { text: "Anyone can write: admins, users, bots", options: { bullet: true, breakLine: true } },
    { text: "Comments on posts + free chat", options: { bullet: true } },
  ], { x: 5.1, y: 2.0, w: 4.25, h: 0.9, fontSize: 13, paraSpaceAfter: 4 });
  text(s, [
    { text: "Research gap: ", options: { bold: true, color: CORAL } },
    { text: "channels and groups have both been studied, but rarely is each channel compared with its own discussion group across several dimensions.", options: { breakLine: true } },
    { text: "Our contribution: ", options: { bold: true, color: CORAL } },
    { text: "a paired measurement study of 195 crypto and conspiracy pairs: content, author roles, promotion and toxicity.", options: { breakLine: true } },
    { text: "Deliverable: ", options: { bold: true, color: CORAL } },
    { text: "technical paper (empirical measurement study).", options: {} },
  ], { x: 0.5, y: 3.15, w: 9.0, h: 1.45, fontSize: 13, paraSpaceAfter: 5 });
  text(s, "La Morgia et al., TGDataset, KDD 2025 · Slobozhan et al., SNAM 2023 · Alvisi et al., J. Big Data 2026", { x: 0.5, y: 4.75, w: 8.4, h: 0.3, fontSize: 10, color: C.accent5 });
  s.addNotes("RICCARDO (0:15-1:05). Telegram channels are mainly used for broadcasting: only the admins post. Their linked discussion groups let regular users, administrators and bots interact. Previous research has already studied Telegram channels, public groups, scams and harmful content; for example TGDataset collects the channels, and Slobozhan and Alvisi compare or link channels and groups. Our specific goal is to compare each channel systematically with its own discussion group, across several dimensions: what becomes visible when we look at the discussion layer and not only at the official channel? We do it in two communities, crypto and conspiracy. Our final deliverable will be a technical paper based on this empirical measurement study.");

  // ================= 3. Data =================
  s = S("Data: 195 channel–group pairs, observed passively", "Setup");
  const stats = [
    [ic.db, "195", "channel–group pairs", "98 crypto · 97 conspiracy", INK],
    [ic.file, "3.8 M", "messages", "2.3 M crypto · 1.5 M conspiracy", INK],
    [ic.clock, "14 weeks", "observation window", "30 Jul – 4 Nov 2026", INK],
    [ic.eye, "0", "messages sent", "read-only, public chats only", CORAL],
  ];
  stats.forEach(([img, big, label, sub, col], i) => {
    const x = 0.5 + i * 2.3;
    badge(s, img, x, 1.35, 0.55, col, "stat " + i);
    text(s, big, { x, y: 2.05, w: 2.1, h: 0.7, fontSize: 32, bold: true, color: C.text2, fontFace: "Arial" });
    text(s, label, { x, y: 2.75, w: 2.1, h: 0.3, fontSize: 14, bold: true });
    text(s, sub, { x, y: 3.05, w: 2.1, h: 0.5, fontSize: 12, color: C.accent5 });
  });
  card(s, 0.5, 3.85, 9.0, 1.05, "roles card");
  text(s, "Every message gets a role:", { x: 0.75, y: 4.0, w: 2.4, h: 0.3, fontSize: 14, bold: true });
  const roles = [[ic.channel, "Channel", GRAY], [ic.shield, "Admins in group", INK], [ic.user, "Users", CORAL], [ic.robot, "Bots (apart)", HEX.accent5]];
  roles.forEach(([img, lab, col], i) => {
    const x = 0.75 + i * 2.2;
    badge(s, img, x, 4.35, 0.4, col, "role " + i);
    text(s, lab, { x: x + 0.5, y: 4.43, w: 1.65, h: 0.3, fontSize: 13 });
  });
  s.addNotes("RICCARDO (1:05-1:55). We collected data from 195 channel-group pairs: 98 crypto and 97 conspiracy, starting from TGDataset. The dataset contains about 3.8 million messages over fourteen weeks, from late July to early November 2026. Collection was passive: we monitored public communities without posting messages or interacting with users. A key part of our approach is to distinguish the channel's official posts, administrators writing inside the group, regular users, and bots.");

  // ================= 4. Structure =================
  s = S("Groups carry the volume: 10–50× more messages", "Setup");
  s.addChart(pres.charts.BAR, [
    { name: "Channel", labels: ["Crypto", "Conspiracy"], values: [0.9, 3.7] },
    { name: "Group", labels: ["Crypto", "Conspiracy"], values: [38.6, 37.2] },
  ], { x: 0.4, y: 1.2, w: 5.4, h: 3.75, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: [GRAY, CORAL], showLegend: true, legendPos: "t", legendFontSize: 11, legendColor: HEX.accent5,
    showTitle: true, title: "Messages per day (median per chat)", titleFontSize: 12, titleColor: HEX.dk1,
    dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0", ...chartBase() });
  card(s, 6.1, 1.3, 3.4, 1.65, "links card");
  text(s, [{ text: "Links", options: { bold: true, breakLine: true } },
    { text: "Channel posts: 79% (crypto), 50% (consp.) carry a link. Group messages: 2% and 16% (medians).", options: {} }],
    { x: 6.3, y: 1.45, w: 3.0, h: 1.4, fontSize: 13 });
  card(s, 6.1, 3.15, 3.4, 1.65, "media card");
  text(s, [{ text: "Media", options: { bold: true, breakLine: true } },
    { text: "Channel posts almost always carry media (≈97%); group messages far less often (8% / 47%).", options: {} }],
    { x: 6.3, y: 3.3, w: 3.0, h: 1.4, fontSize: 13 });
  s.addNotes("RICCARDO (1:55-3:00). The first result concerns activity. In the typical pair, groups are much more active than their channels: about fifty times more messages per day in crypto and ten times more in conspiracy. The format also differs: channel posts carry links and media much more often, while group messages are mostly conversational text. These differences hold across our robustness checks, for example without truncated observation windows or without the largest group. Now Marco will present what we found about the content of these discussions.");

  // ================= 5. Point 4 =================
  pres.addSection({ title: "Content and crypto" });
  s = S("~75% of group messages are semantically non-aligned", "Content and crypto");
  [[0.5, "74.7%", "Crypto groups"], [3.4, "76.1%", "Conspiracy groups"]].forEach(([x, big, lab], i) => {
    card(s, x, 1.35, 2.7, 2.1, "stat card " + i);
    text(s, big, { x: x + 0.25, y: 1.6, w: 2.3, h: 0.9, fontSize: 44, bold: true, color: CORAL, fontFace: "Arial" });
    text(s, lab, { x: x + 0.25, y: 2.55, w: 2.3, h: 0.35, fontSize: 15, bold: true });
    text(s, "mean of pair-level rates", { x: x + 0.25, y: 2.9, w: 2.3, h: 0.35, fontSize: 12, color: C.accent5 });
  });
  text(s, [
    { text: "Method", options: { bold: true, breakLine: true } },
    { text: "Qwen3 multilingual embeddings; max cosine similarity to the observed posts of its channel; threshold 0.52.", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 5 } },
    { text: "Finding", options: { bold: true, breakLine: true } },
    { text: "Same level in both communities (+1.4 pp, n.s.).", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 5 } },
    { text: "Caveat", options: { bold: true, breakLine: true } },
    { text: "Non-alignment does not show where a topic originated.", options: {} },
  ], { x: 6.4, y: 1.35, w: 3.1, h: 3.4, fontSize: 13 });
  text(s, "445,584 eligible group messages · threshold calibrated on 100 hand-checked examples · 0.50 / 0.55 as sensitivity", { x: 0.5, y: 3.75, w: 5.6, h: 0.6, fontSize: 11, color: C.accent5 });
  s.addNotes("MARCO (3:00-4:10). To check whether groups simply repeat what their channels publish, we used Qwen3, a multilingual embedding model. For each eligible group message we computed its maximum cosine similarity to the observed posts of its own channel. Using a threshold of 0.52, calibrated on a separate set of one hundred examples, messages below the threshold are semantically non-aligned. The result is about 75% in crypto and 76% in conspiracy, with no significant difference between the pair-level means. So a large share of group discussion is not closely represented in the channel's posts. However, this does not prove that these topics originated in the groups.");

  // ================= 6. Functions =================
  s = S("What the non-aligned messages do", "Content and crypto");
  const fl = ["Discussion / opinion", "Greeting / social", "Question / help", "News sharing", "Promotion"];
  s.addChart(pres.charts.BAR, [
    { name: "Crypto", labels: fl, values: [25.9, 20.9, 15.0, 2.6, 5.3] },
    { name: "Conspiracy", labels: fl, values: [32.0, 4.3, 14.8, 22.3, 9.1] },
  ], { x: 0.4, y: 1.15, w: 6.0, h: 3.85, barDir: "bar", barGrouping: "clustered", barGapWidthPct: 50,
    chartColors: [INK, CORAL], showLegend: true, legendPos: "t", legendFontSize: 11, legendColor: HEX.accent5,
    dataLabelPosition: "outEnd", dataLabelFormatCode: '0"%"', catAxisOrientation: "maxMin", ...chartBase() });
  card(s, 6.7, 1.35, 2.8, 3.3, "reading card");
  text(s, [
    { text: "Crypto groups ", options: { bold: true } }, { text: "socialise and ask (gm, help, prices).", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "Conspiracy groups ", options: { bold: true } }, { text: "share more news and express opinions.", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "Exploratory coding · 1,170 messages · 6 per pair · no independent label validation.", options: { color: C.accent5, fontSize: 12 } },
  ], { x: 6.9, y: 1.55, w: 2.45, h: 3.0, fontSize: 14 });
  s.addNotes("MARCO (4:10-4:55). What are these non-aligned messages doing? We coded a separate sample of 1,170 messages, six per channel-group pair. Crypto groups show more greetings and social interaction, while conspiracy groups share much more news: about 22% of the coded conspiracy messages, against 3% in crypto. These findings are exploratory: a single coding pass without independent validation, so they are not definitive prevalence estimates.");

  // ================= 7. Crypto invitations =================
  s = S("Crypto: channels invite more, flagged invites cluster", "Content and crypto");
  s.addChart(pres.charts.BAR, [
    { name: "Share of messages that invite to register", labels: ["Channel posts", "Group messages (non-bot)"], values: [3.72, 0.04] },
  ], { x: 0.4, y: 1.2, w: 4.3, h: 3.75, barDir: "col", barGapWidthPct: 70, chartColors: [GRAY, CORAL],
    showLegend: false, showTitle: true, title: "Invitation rate (median per pair, %)", titleFontSize: 12, titleColor: HEX.dk1,
    dataLabelPosition: "outEnd", dataLabelFormatCode: '0.00"%"', ...chartBase() });
  const inv = [
    ["71 / 98", "pairs: the group has a lower invitation rate than its channel"],
    ["96.2%", "of group invitations flagged as suspicious come from one group"],
    ["10,534", "bot invitations (token alerts), reported separately"],
  ];
  inv.forEach(([big, lab], i) => {
    const y = 1.3 + i * 1.2;
    card(s, 5.0, y, 4.5, 1.05, "inv card " + i);
    text(s, big, { x: 5.2, y: y + 0.15, w: 1.55, h: 0.75, fontSize: 22, bold: true, color: i === 1 ? CORAL : C.text2, fontFace: "Arial", valign: "middle" });
    text(s, lab, { x: 6.8, y: y + 0.12, w: 2.55, h: 0.8, fontSize: 13, valign: "middle" });
  });
  s.addNotes("MARCO (4:55-5:40). For the crypto deep dive we focused on invitations to register on platforms: referral links, sign-up links and related wording. In the typical pair the channel has a much higher invitation rate: about 3.7% of posts, against 0.04% of non-bot group messages. In absolute numbers groups still contain more invitations, because they have far more messages. The most striking result is concentration: of about 7,700 group invitations flagged as suspicious under our definition, more than 7,400, that is 96%, come from a single referral group. Flagged does not mean confirmed scam. We also report over 10,500 bot invitations separately.");

  // ================= 8. Voices =================
  s = S("Who posts links: channels, then admins, then users", "Content and crypto");
  s.addChart(pres.charts.BAR, [
    { name: "Crypto", labels: ["Channel", "Admins in group", "Users"], values: [78.3, 8.6, 0.3] },
    { name: "Conspiracy", labels: ["Channel", "Admins in group", "Users"], values: [41.0, 8.8, 11.9] },
  ], { x: 0.4, y: 1.2, w: 5.8, h: 3.75, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: [INK, CORAL], showLegend: true, legendPos: "t", legendFontSize: 11, legendColor: HEX.accent5,
    showTitle: true, title: "Messages with any link, by voice (median %)", titleFontSize: 12, titleColor: HEX.dk1,
    dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"', ...chartBase() });
  card(s, 6.5, 1.35, 3.0, 3.3, "voices card");
  text(s, [
    { text: "Three voices per pair", options: { bold: true, breakLine: true } },
    { text: "Channel, admins writing in the group, regular users.", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "Any link, not only invitations. Crypto users almost never post links; conspiracy users as often as admins.", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "Pairs with ≥ 30 admin messages: 84 crypto, 73 conspiracy.", options: { color: C.accent5, fontSize: 12 } },
  ], { x: 6.7, y: 1.55, w: 2.65, h: 3.0, fontSize: 14 });
  s.addNotes("MARCO (5:40-6:00, cut first if short on time). Separating the three voices gives more context. In crypto almost 80% of channel posts contain a link, against about 9% of admin messages in the group and less than 1% of regular users' messages, as median rates across eligible pairs. This counts any link, not only invitations. Now Simone will discuss toxicity in conspiracy communities.");

  // ================= 9. Toxicity =================
  pres.addSection({ title: "Conspiracy and wrap-up" });
  s = S("Conspiracy: groups are 4 times as toxic as their channels", "Conspiracy and wrap-up");
  s.addChart(pres.charts.BAR, [
    { name: "Toxic messages (%)", labels: ["Channels", "Groups"], values: [2.02, 8.56] },
  ], { x: 0.4, y: 1.2, w: 3.6, h: 3.75, barDir: "col", barGapWidthPct: 60, chartColors: [GRAY, CORAL],
    showLegend: false, showTitle: true, title: "Toxic messages, all pairs (%)", titleFontSize: 12, titleColor: HEX.dk1,
    dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"', ...chartBase() });
  s.addChart(pres.charts.BAR, [
    { name: "Toxic messages by voice (median %)", labels: ["Channel", "Admins", "Users"], values: [1.56, 3.72, 4.87] },
  ], { x: 4.1, y: 1.2, w: 3.3, h: 3.75, barDir: "col", barGapWidthPct: 60, chartColors: [GRAY, INK, CORAL],
    showLegend: false, showTitle: true, title: "By voice (median %, 72 pairs)", titleFontSize: 12, titleColor: HEX.dk1,
    dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"', ...chartBase() });
  card(s, 7.6, 1.35, 1.9, 1.5, "pairs card");
  text(s, "82 / 96", { x: 7.75, y: 1.5, w: 1.65, h: 0.6, fontSize: 24, bold: true, color: CORAL, fontFace: "Arial" });
  text(s, "pairs with higher group toxicity", { x: 7.75, y: 2.1, w: 1.65, h: 0.6, fontSize: 12 });
  card(s, 7.6, 3.05, 1.9, 1.6, "diff card");
  text(s, "+2.7 pp", { x: 7.75, y: 3.2, w: 1.65, h: 0.6, fontSize: 24, bold: true, color: C.text2, fontFace: "Arial" });
  text(s, "median group–channel difference", { x: 7.75, y: 3.8, w: 1.65, h: 0.7, fontSize: 12 });
  s.addNotes("SIMONE (6:00-7:10). For conspiracy communities we analysed about one million messages with Toxicity-Lens, a multilingual classifier for several forms of harmful language. At our main threshold, about 2% of channel posts and 8.6% of group messages are classified as toxic. Across the 96 completed pairs, the group is more toxic in 82 cases, with a median paired increase of about 2.7 percentage points. By voice, channels have the lowest classified toxicity, then group administrators, then regular users. These are model-based findings: independent human validation remains a limitation.");

  // ================= 10. Conversations =================
  s = S("Toxic messages are more likely to receive toxic replies", "Conspiracy and wrap-up");
  s.addChart(pres.charts.BAR, [
    { name: "Toxic replies (%)", labels: ["Replies to non-toxic messages", "Replies to toxic messages"], values: [7.92, 20.52] },
  ], { x: 0.4, y: 1.2, w: 5.0, h: 3.75, barDir: "col", barGapWidthPct: 60, chartColors: [GRAY, CORAL],
    showLegend: false, showTitle: true, title: "Share of replies that are toxic (%)", titleFontSize: 12, titleColor: HEX.dk1,
    dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"', ...chartBase() });
  const conv = [["384k", "analysed parent–reply pairs"], ["51 / 51", "groups show the same direction"], ["+7.5 pp", "median difference across groups"]];
  conv.forEach(([big, lab], i) => {
    const y = 1.3 + i * 1.2;
    card(s, 5.7, y, 3.8, 1.05, "conv card " + i);
    text(s, big, { x: 5.9, y: y + 0.15, w: 1.4, h: 0.75, fontSize: 22, bold: true, color: i === 1 ? CORAL : C.text2, fontFace: "Arial", valign: "middle" });
    text(s, lab, { x: 7.35, y: y + 0.15, w: 2.05, h: 0.75, fontSize: 13, valign: "middle" });
  });
  s.addNotes("SIMONE (7:10-8:10). We also looked at how toxicity relates to conversations. Using Telegram's reply references we analysed about 384,000 parent-reply pairs. A reply to a message classified as toxic was itself toxic about 21% of the time, against about 8% after a non-toxic message. This positive association appears in all 51 groups that meet our minimum sample size. It does not establish causation: recurring users, discussion topics and moderation can also contribute.");

  // ================= 11. Takeaways =================
  s = pres.addSlide({ masterName: "Title Dark", sectionTitle: "Conspiracy and wrap-up" });
  text(s, "What groups add", { x: 0.6, y: 0.4, w: 8.8, h: 0.7, fontSize: 32, bold: true, color: C.background1, fontFace: "Arial" });
  const take = [
    [ic.group, "Additional discussion", "10–50× more active; ~75% of messages semantically non-aligned with the channel"],
    [ic.channel, "Different promotional roles", "Channels have higher invitation rates; flagged invitations cluster in few groups"],
    [ic.users, "Different toxicity patterns", "Conspiracy groups ≈4× more toxic; toxic messages more likely to get toxic replies"],
  ];
  take.forEach(([img, head, sub], i) => {
    const x = 0.6 + i * 3.0;
    badge(s, img, x, 1.35, 0.6, i === 2 ? CORAL : HEX.accent5, "take " + i);
    text(s, head, { x, y: 2.1, w: 2.75, h: 0.4, fontSize: 16, bold: true, color: C.background1 });
    text(s, sub, { x, y: 2.5, w: 2.75, h: 1.0, fontSize: 13, color: C.accent6 });
  });
  text(s, [
    { text: "Limits: ", options: { bold: true, color: C.background1 } },
    { text: "classifiers not hand-validated; topics labelled with an LLM; 195 non-random pairs, 14 weeks; associations, not causes.", options: {} },
  ], { x: 0.6, y: 4.0, w: 8.8, h: 0.6, fontSize: 13, color: C.accent6 });
  s.addNotes("SIMONE (8:10-8:45). Overall, our findings show three differences between channels and their groups. First, groups contain much more activity and a large share of semantically non-aligned discussion. Second, promotion differs between channels, administrators and users, and suspicious invitation signals are concentrated in a few crypto groups. Third, conspiracy groups show higher classified toxicity, and toxic replies are associated with toxic parent messages. Riccardo will close with our status and plan.");

  // ================= 12. Status, plan, team =================
  s = S("Project status and roadmap to 3 January", "Conspiracy and wrap-up");
  const cols = [
    [ic.check, "Completed", TEAL, [
      "Data collection (195 pairs, 3.8 M messages)",
      "Structure and robustness checks",
      "Semantic non-alignment",
      "Crypto invitations and three voices",
      "Conspiracy toxicity and replies",
    ]],
    [ic.cal, "Remaining", CORAL, [
      "Until 1 Dec: DM monitoring",
      "December: analyse unsolicited DMs",
      "December: related work, limitations, ethics",
      "3 Jan 2027: final technical paper",
    ]],
    [ic.users, "Team", INK, [
      "Equal contribution by all three",
      "Marco: pair review, semantic content analysis",
      "Simone: toxicity, topics, conversations",
      "Riccardo: collection, structure, invitations, coordination",
      "All three: DMs, writing, final review",
    ]],
  ];
  cols.forEach(([img, head, col, items], i) => {
    const x = 0.5 + i * 3.075;
    card(s, x, 1.2, 2.85, 3.55, "status card " + i);
    badge(s, img, x + 0.2, 1.38, 0.45, col, "status " + i);
    text(s, head, { x: x + 0.75, y: 1.45, w: 2.0, h: 0.35, fontSize: 14, bold: true });
    text(s, items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < items.length - 1 } })),
      { x: x + 0.2, y: 2.0, w: 2.5, h: 2.65, fontSize: 12, paraSpaceAfter: 5 });
  });
  text(s, "Thank you · questions and feedback welcome", { x: 4.6, y: 4.85, w: 4.9, h: 0.3, fontSize: 12, bold: true, color: CORAL, align: "right" });
  s.addNotes("RICCARDO (8:45-10:00). These are our main findings so far, but the project is not finished. We have completed the data collection and the main structural, semantic, promotional and toxicity analyses. What remains: we keep monitoring unsolicited private messages until the first of December, then we analyse those contacts, write the related work, limitations and ethics, and integrate everything into our final technical paper, due on the third of January. We contributed equally: Marco focused on the pair review and the semantic content analysis, Simone on toxicity, topics and conversations, and I on data collection, structural measures, invitations and coordination. The DM analysis and the final writing and review we do together. Our goal is to show not only what Telegram channels publish, but what researchers miss when they do not look at the associated discussion groups. Thank you, we welcome your questions and feedback.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
