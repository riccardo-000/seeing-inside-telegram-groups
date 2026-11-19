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
  text(s, "Marco · Simone · Riccardo", { x: 0.6, y: 4.3, w: 6, h: 0.35, fontSize: 16, color: C.background1, bold: true });
  text(s, "Research Topics in Cybersecurity · DTU · November 2026", { x: 0.6, y: 4.65, w: 7, h: 0.3, fontSize: 12, color: C.accent6 });
  s.addNotes("RICCARDO (0:00-0:20). Hi, we are Marco, Simone and Riccardo. Our project looks inside Telegram groups: the discussion groups linked to public channels.");

  // ================= 2. Question =================
  s = S("Channels broadcast; linked groups talk back", "Setup");
  card(s, 0.5, 1.35, 3.6, 2.35, "channel card");
  badge(s, ic.channel, 0.75, 1.6, 0.6, GRAY, "channel");
  text(s, "Channel", { x: 1.5, y: 1.7, w: 2.4, h: 0.4, fontSize: 18, bold: true });
  text(s, [
    { text: "Broadcast: only admins post", options: { bullet: true, breakLine: true } },
    { text: "What most studies (and TGDataset) see", options: { bullet: true } },
  ], { x: 0.75, y: 2.4, w: 3.2, h: 1.1, fontSize: 14, paraSpaceAfter: 6 });
  s.addImage({ data: ic.arrow, x: 4.3, y: 2.35, w: 0.4, h: 0.4, objectName: "arrow" });
  card(s, 4.9, 1.35, 4.6, 2.35, "group card");
  badge(s, ic.group, 5.15, 1.6, 0.6, CORAL, "group");
  text(s, "Linked discussion group", { x: 5.9, y: 1.7, w: 3.5, h: 0.4, fontSize: 18, bold: true });
  text(s, [
    { text: "Anyone can write: admins, users, bots", options: { bullet: true, breakLine: true } },
    { text: "Comments on posts + free chat", options: { bullet: true } },
  ], { x: 5.15, y: 2.4, w: 4.2, h: 1.1, fontSize: 14, paraSpaceAfter: 6 });
  text(s, [
    { text: "Question: ", options: { bold: true, color: CORAL } },
    { text: "what happens in the group that the channel alone does not show? We compare each channel with its own group, in two communities: crypto (scam invitations) and conspiracy (toxicity)." },
  ], { x: 0.5, y: 4.0, w: 9.0, h: 0.9, fontSize: 15 });
  s.addNotes("RICCARDO (0:20-1:10). Telegram channels are one-way: only admins post. Most measurement work, including TGDataset, looks only at channels. But many channels have a linked discussion group where anyone can write. Our question: what happens there that you cannot see from the channel? We always compare a channel with its own group, so each channel is the control for its group. We studied two communities with two deep dives: in crypto we look at invitations to register on platforms, a common scam vector; in conspiracy we look at toxicity.");

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
  s.addNotes("RICCARDO (1:10-2:00). Starting from TGDataset we selected about 100 crypto and 100 conspiracy channels that have a public linked group: 195 pairs, 3.8 million messages over 14 weeks. Collection was strictly passive: we joined only public chats and never sent a message. Every message gets a role: the channel itself, admins writing in the group, regular users, and bots, which we keep apart.");

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
    { text: "Channel posts: 79% (crypto), 50% (consp.) carry a link. Group messages: 2% and 16%.", options: {} }],
    { x: 6.3, y: 1.45, w: 3.0, h: 1.4, fontSize: 13 });
  card(s, 6.1, 3.15, 3.4, 1.65, "media card");
  text(s, [{ text: "Media", options: { bold: true, breakLine: true } },
    { text: "Channels are polished (≈97% media); groups are mostly plain text (8% / 47% media).", options: {} }],
    { x: 6.3, y: 3.3, w: 3.0, h: 1.4, fontSize: 13 });
  s.addNotes("RICCARDO (2:00-3:00). First, the structure. In the typical pair the group is far more active than the channel: about 10 times in conspiracy and 50 times in crypto. And it is a different kind of content: channel posts are polished, almost always with media and often with a link; group messages are mostly short plain text. These directions hold in every robustness check: without truncated chats, without the largest group, and with only true discussion groups. Now Marco on what the groups talk about.");

  // ================= 5. Point 4 =================
  pres.addSection({ title: "Content and crypto" });
  s = S("Three in four group messages match no channel post", "Content and crypto");
  [[0.5, "74.7%", "Crypto groups"], [3.4, "76.1%", "Conspiracy groups"]].forEach(([x, big, lab], i) => {
    card(s, x, 1.35, 2.7, 2.1, "stat card " + i);
    text(s, big, { x: x + 0.25, y: 1.6, w: 2.3, h: 0.9, fontSize: 44, bold: true, color: CORAL, fontFace: "Arial" });
    text(s, lab, { x: x + 0.25, y: 2.55, w: 2.3, h: 0.35, fontSize: 15, bold: true });
    text(s, "of eligible group messages", { x: x + 0.25, y: 2.9, w: 2.3, h: 0.35, fontSize: 12, color: C.accent5 });
  });
  text(s, [
    { text: "How", options: { bold: true, breakLine: true } },
    { text: "Each group message is embedded (Qwen3, multilingual) and compared with every post of its channel; below cosine 0.52 = not aligned.", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "Reading", options: { bold: true, breakLine: true } },
    { text: "Groups mostly talk about other things than the channel. Same in both communities (+1.4 pp, n.s.).", options: {} },
  ], { x: 6.4, y: 1.35, w: 3.1, h: 3.2, fontSize: 13 });
  text(s, "445,584 eligible messages · threshold calibrated on 100 hand-checked pairs · 0.50 / 0.55 as sensitivity", { x: 0.5, y: 3.75, w: 5.6, h: 0.6, fontSize: 11, color: C.accent5 });
  s.addNotes("MARCO (3:00-4:30). To see whether groups just echo their channel, I embedded every group message with a multilingual model, Qwen3, and found its most similar channel post. If the similarity is below a calibrated threshold of 0.52, the message is not aligned with anything the channel published. About three in four group messages are not aligned: 75% in crypto and 76% in conspiracy. The difference between the two communities is not significant. Important caveat: this measures semantic distance from the observed channel posts, not that the topic was born in the group.");

  // ================= 6. Functions =================
  s = S("What the unmatched messages do", "Content and crypto");
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
    { text: "Conspiracy groups ", options: { bold: true } }, { text: "share news and argue.", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "Exploratory: 1,170 messages, 6 per pair, single coding pass.", options: { color: C.accent5, fontSize: 12 } },
  ], { x: 6.9, y: 1.55, w: 2.45, h: 3.0, fontSize: 14 });
  s.addNotes("MARCO (4:30-5:15). What are these unmatched messages? On a sample of six per pair we coded their communicative function. Crypto groups are social: greetings, questions, help. Conspiracy groups share news and argue: news sharing is 22% against 3% in crypto. Promotion is a small share in both. These estimates are exploratory: one coding pass, no second annotator.");

  // ================= 7. Crypto invitations =================
  s = S("Crypto: channels invite, suspicious invites cluster", "Content and crypto");
  s.addChart(pres.charts.BAR, [
    { name: "Share of messages that invite to register", labels: ["Channel posts", "Group messages"], values: [3.72, 0.04] },
  ], { x: 0.4, y: 1.2, w: 4.3, h: 3.75, barDir: "col", barGapWidthPct: 70, chartColors: [GRAY, CORAL],
    showLegend: false, showTitle: true, title: "Invitations to register (median per pair, %)", titleFontSize: 12, titleColor: HEX.dk1,
    dataLabelPosition: "outEnd", dataLabelFormatCode: '0.00"%"', ...chartBase() });
  const inv = [
    ["71 / 98", "pairs: group invites less than its channel"],
    ["7,438 / 7,731", "suspicious invitations in groups come from one group"],
    ["10,534", "bot invitations (token alerts) reported apart"],
  ];
  inv.forEach(([big, lab], i) => {
    const y = 1.3 + i * 1.2;
    card(s, 5.0, y, 4.5, 1.05, "inv card " + i);
    text(s, big, { x: 5.2, y: y + 0.15, w: 1.9, h: 0.75, fontSize: 22, bold: true, color: i === 1 ? CORAL : C.text2, fontFace: "Arial", valign: "middle" });
    text(s, lab, { x: 7.15, y: y + 0.15, w: 2.2, h: 0.75, fontSize: 13, valign: "middle" });
  });
  s.addNotes("MARCO (5:15-6:00). For crypto, the deep dive is invitations to register on a platform: referral links, sign-up links, deposit wording. The surprise: it is the channel that invites, about 4% of its posts, while group members almost never do. Suspicious invitations, to unknown platforms or with promises of fixed returns, are rare and concentrated: of 7,731 in groups, 7,438 are in a single referral group. Token-alert bots post another 10,000 invitations, which we report separately. Detector quality is moderate, precision about 0.6 against an LLM annotator. Now Simone on conspiracy.");

  // ================= 8. Voices =================
  s = S("Who speaks: channels promote, members talk", "Content and crypto");
  s.addChart(pres.charts.BAR, [
    { name: "Crypto", labels: ["Channel", "Admins in group", "Users"], values: [78.3, 8.6, 0.3] },
    { name: "Conspiracy", labels: ["Channel", "Admins in group", "Users"], values: [41.0, 8.8, 11.9] },
  ], { x: 0.4, y: 1.2, w: 5.8, h: 3.75, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: [INK, CORAL], showLegend: true, legendPos: "t", legendFontSize: 11, legendColor: HEX.accent5,
    showTitle: true, title: "Messages with a link, by voice (median %)", titleFontSize: 12, titleColor: HEX.dk1,
    dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"', ...chartBase() });
  card(s, 6.5, 1.35, 3.0, 3.3, "voices card");
  text(s, [
    { text: "Three voices per pair", options: { bold: true, breakLine: true } },
    { text: "Channel, admins writing in the group, regular users.", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "Crypto: links come from the channel, almost never from users. Conspiracy users share links as often as admins.", options: { breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "Pairs with ≥ 30 admin messages: 84 crypto, 73 conspiracy.", options: { color: C.accent5, fontSize: 12 } },
  ], { x: 6.7, y: 1.55, w: 2.65, h: 3.0, fontSize: 14 });
  s.addNotes("MARCO or RICCARDO (optional, cut if short on time). Splitting each pair into three voices confirms it: the channel is where links and promotion live, especially in crypto where almost 80% of posts carry a link; admins in the group post far fewer links, and crypto users almost none. In conspiracy, users share links about as often as admins: news links.");

  // ================= 9. Toxicity =================
  pres.addSection({ title: "Conspiracy and wrap-up" });
  s = S("Conspiracy: groups are 4× as toxic as their channels", "Conspiracy and wrap-up");
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
  text(s, "pairs: group more toxic", { x: 7.75, y: 2.1, w: 1.65, h: 0.6, fontSize: 12 });
  card(s, 7.6, 3.05, 1.9, 1.6, "diff card");
  text(s, "+2.7 pp", { x: 7.75, y: 3.2, w: 1.65, h: 0.6, fontSize: 24, bold: true, color: C.text2, fontFace: "Arial" });
  text(s, "median paired gap (CI 2.2–4.3)", { x: 7.75, y: 3.8, w: 1.65, h: 0.7, fontSize: 12 });
  s.addNotes("SIMONE (6:00-7:30). For conspiracy we classified about one million messages with Toxicity-Lens, a multilingual model with seven categories. In channels 2% of messages are toxic, in groups 8.6%, roughly four times more. Pair by pair, the group is more toxic in 82 of 96 pairs, with a median gap of 2.7 percentage points; insults and profanity drive most of it. Splitting by voice: the channel is the cleanest, admins in the group are in between, regular users are the most toxic. The result holds when we change the threshold or drop the largest group.");

  // ================= 10. Conversations =================
  s = S("Toxicity attracts toxic replies", "Conspiracy and wrap-up");
  s.addChart(pres.charts.BAR, [
    { name: "Toxic replies (%)", labels: ["Replies to non-toxic messages", "Replies to toxic messages"], values: [7.92, 20.52] },
  ], { x: 0.4, y: 1.2, w: 5.0, h: 3.75, barDir: "col", barGapWidthPct: 60, chartColors: [GRAY, CORAL],
    showLegend: false, showTitle: true, title: "Share of replies that are toxic (%)", titleFontSize: 12, titleColor: HEX.dk1,
    dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"', ...chartBase() });
  const conv = [["384 k", "reply pairs rebuilt from Telegram's reply links"], ["51 / 51", "groups show the same direction"], ["+7.5 pp", "median gap per group (CI 6.4–8.9)"]];
  conv.forEach(([big, lab], i) => {
    const y = 1.3 + i * 1.2;
    card(s, 5.7, y, 3.8, 1.05, "conv card " + i);
    text(s, big, { x: 5.9, y: y + 0.15, w: 1.4, h: 0.75, fontSize: 22, bold: true, color: i === 1 ? CORAL : C.text2, fontFace: "Arial", valign: "middle" });
    text(s, lab, { x: 7.35, y: y + 0.15, w: 2.05, h: 0.75, fontSize: 13, valign: "middle" });
  });
  s.addNotes("SIMONE (7:30-8:30). Groups are conversations, so we rebuilt who replies to whom from Telegram's reply links: 384 thousand reply pairs. A reply to a toxic message is toxic 21% of the time, against 8% for a reply to a non-toxic one, and this holds in all 51 groups with enough replies. This is an association, not causation: topic, recurring users and moderation can all play a role. We also labelled each community's topic: political and geopolitical communities show the largest gaps, but the numbers per topic are small.");

  // ================= 11. Conclusions =================
  s = pres.addSlide({ masterName: "Title Dark", sectionTitle: "Conspiracy and wrap-up" });
  text(s, "What groups add", { x: 0.6, y: 0.4, w: 8.8, h: 0.7, fontSize: 32, bold: true, color: C.background1, fontFace: "Arial" });
  const take = [
    [ic.group, "Volume and new topics", "10–50× more messages; 3 in 4 off the channel's topics"],
    [ic.channel, "Promotion stays upstream", "Crypto invitations come from channels; scams cluster in few groups"],
    [ic.users, "Tone gets rougher", "Groups 4× more toxic; users > admins > channel; toxicity attracts toxicity"],
  ];
  take.forEach(([img, head, sub], i) => {
    const x = 0.6 + i * 3.0;
    badge(s, img, x, 1.35, 0.6, i === 2 ? CORAL : HEX.accent5, "take " + i);
    text(s, head, { x, y: 2.1, w: 2.75, h: 0.4, fontSize: 16, bold: true, color: C.background1 });
    text(s, sub, { x, y: 2.5, w: 2.75, h: 0.9, fontSize: 13, color: C.accent6 });
  });
  text(s, [
    { text: "Limits: ", options: { bold: true, color: C.background1 } },
    { text: "classifiers not hand-validated; topics labelled with an LLM; 195 non-random pairs, 14 weeks.", options: { breakLine: true } },
    { text: "Next: ", options: { bold: true, color: C.background1 } },
    { text: "unsolicited DMs to our passive accounts (23 crypto, 17 conspiracy so far) and the paper (January).", options: {} },
  ], { x: 0.6, y: 3.75, w: 8.8, h: 0.9, fontSize: 13, color: C.accent6, paraSpaceAfter: 6 });
  text(s, "Thank you · questions?", { x: 0.6, y: 4.85, w: 5, h: 0.35, fontSize: 14, bold: true, color: CORAL });
  s.addNotes("SIMONE or RICCARDO (8:30-10:00). To sum up: looking inside the groups adds three things. Volume and new topics: groups are 10 to 50 times more active and mostly discuss things the channel never posted. Promotion stays upstream: in crypto, invitations to register come from the channel, and suspicious ones cluster in a handful of groups. And the tone gets rougher: conspiracy groups are four times as toxic as their channels, users more than admins, and toxic messages attract toxic replies. Limits: our classifiers are not validated by hand, and topics were labelled with an LLM. Next we analyse the unsolicited DMs our passive accounts received, and write the paper. Thank you.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
