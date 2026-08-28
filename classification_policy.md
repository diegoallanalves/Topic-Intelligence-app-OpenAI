# Topic Intelligence classification policy

## Context
Classify U.S. Congressional actions for a DAQO Group study. Assign ONE topic only. Do not judge relevance, risk, opportunity or policy stage.

## Input order
Read fields in this exact order:
1. **Mechanism** — first source and preferred when it plainly states the instrument.
2. **Analytical Summary** — use only to fill a gap or confirm the Mechanism.
3. **Title** — use only for the title rules below or fallback.

Separate what the bill legally does from consequence language about DAQO. Never classify from a sentence that merely says what a bill could/may/might mean for DAQO.

## Step 1 — extract the provision
Write one `PROVISION` sentence saying what the bill obliges, prohibits, taxes, funds, authorises or conditions, and on whom.

The provision:
- must not contain DAQO;
- must not contain could, may, might, potentially, likely, reflects, signals, sentiment or risk;
- must contain a legal-effect verb such as prohibits, bars, requires, imposes, levies, authorises, appropriates, funds, establishes, directs, restricts, suspends, withdraws, designates, amends, conditions, screens, certifies, repeals, waives, allocates or maintains;
- must come from Mechanism, Summary, or failing both, Title;
- must never be invented.

If Mechanism and Summary state no provision, write exactly `PROVISION: NONE STATED` and classify from Title alone.

## Step 2 — classify only the provision
Choose the topic that matches the extracted provision. A word excluded from the provision cannot drive the topic.

## Transformer trap
Words such as transformer, market access, supply chain, grid, electrical equipment and tariffs often occur only in machine-written DAQO consequence clauses. They must not drive classification unless the bill's own provision actually acts on that thing. If `transformer` survives into a provision, check carefully that the provision itself regulates/funds transformers.

## Words carrying no subject
Never classify on these alone: America, American, Asia, security, infrastructure, innovation, technology, science, leadership, threat, foreign, strategic, competition, CCP, China, influence, data, space, ports.

## The 22 topics — copy exactly
1. **Forced Labor & Xinjiang** — forced-labour import bans, rebuttable presumptions, Xinjiang entity lists, supply-chain forced-labour disclosure.
2. **Hong Kong** — autonomy certification, separate customs/export-control status, sanctions on officials.
3. **Taiwan** — Taiwan relations, arms sales, international participation, trade/investment agreements, UNGA Resolution 2758.
4. **Human Rights & Political Repression** — Tibet, organ harvesting, religious freedom, genocide determinations, political prisoners, censorship, Congressional Gold Medals, transnational repression. Use only when there is no economic, trade or sanctions instrument.
5. **COVID-19 & Pandemic Accountability** — origins investigations, WHO, pandemic liability, PPE/medical-supply dependence.
6. **Narcotics & Fentanyl** — fentanyl/precursor scheduling, trafficking, cartels, drug-related money laundering.
7. **Technology Competition, Telecom & Strategic Sectors** — Huawei/ZTE, 5G, telecom/network equipment, undersea cables, equipment authorisation/covered-entity lists, semiconductors, quantum, AI, biotech, drones, aerospace, technical standards.
8. **Energy, Grid & Electrical Infrastructure** — bulk-power system, transformers, substations, switchgear, transmission, generation, solar/renewables, nuclear, oil/gas, critical minerals/metals.
9. **Foreign Investment in the US** — who may own/acquire something real in the US: CFIUS, acquisitions, farmland, real estate, strategic assets, joint ventures, eligibility of foreign-owned firms for US programmes.
10. **Information & Technology Security** — IP/trade-secret theft, counterfeiting, academic/research security, Confucius Institutes, talent programmes, espionage, counterintelligence, foreign agents, cyber intrusion, personal data, apps/platforms, and visa screening of PRC nationals/researchers/students/military-affiliated applicants.
11. **Sanctions & Export Controls** — entity designations, asset freezes, entity lists, denial orders, export licensing, dual-use controls. Use when sanction/control is the instrument.
12. **Tariffs, Trade Remedies & Market Access** — tariffs, duties, customs enforcement, de minimis, Section 301, AD/CVD, normal trade relations, market-economy/developing-country status, unfair trade/subsidies, USTR authority.
13. **Supply Chain Security & Reshoring** — critical supply-chain reviews, reshoring/onshoring/nearshoring incentives, relocation incentives, domestic manufacturing support, industrial base, stockpiles.
14. **Federal Procurement & Buy American** — what government/contractors may buy: procurement prohibitions, Buy American/domestic-content rules, FAR rules, funding conditions on public works.
15. **Defense, Military & Territorial Disputes** — defence authorisation/posture, PLA, weapons, South China Sea/maritime disputes, and third-country bills where China is context rather than target.
16. **Border Security & Migration** — physical US-Mexico border and migration through it: enforcement, wall, border patrol/technology, ports-of-entry staffing, asylum, migration surges. PRC visa screening belongs in topic 10.
17. **Cross-Border Infrastructure** — ports of entry, cross-border rail, trucking/freight corridors, border water, sanitation/environment.
18. **USMCA & North American Trade** — USMCA implementation, rules of origin, foreign-trade zones, US-Mexico bilateral economic partnership, regional development, agricultural trade with Mexico.
19. **Political / Foreign Influence** — CCP propaganda, disinformation, united-front/influence operations, influence transparency/disclosure, general CCP condemnation. Last resort; not a residual bucket.
20. **Currency, Financial & Funding** — money rather than ownership: exchange rates, currency manipulation, capital markets, listings/delisting, pension/index-fund exposure, payment systems, sovereign debt, IMF/World Bank/IDB.
21. **Appropriations Vehicles** — omnibus/agency appropriations, continuing resolutions and supplementals whose China/Mexico content is an attached clause rather than bill purpose.
22. **State Department & Foreign Aid** — State Department authorisation bills, restrictions on US assistance to PRC, Countering PRC Influence Fund, embassy/diplomatic provisions; not appropriations acts.

## Strict tie-break ladder — first match wins
1. Title contains `Appropriations Act`, `continuing resolution`, `continuing appropriations`, `making appropriations` or `supplemental appropriations` → **Appropriations Vehicles**.
2a. Title names Taiwan or Hong Kong → **Taiwan** or **Hong Kong**. If Title names Uyghur/Xinjiang: import ban/entity list/rebuttable presumption/supply-chain disclosure → **Forced Labor & Xinjiang**; genocide determination/sanctions on officials/condemnation without trade instrument → **Human Rights & Political Repression**. If no instrument is stated, use Human Rights & Political Repression.
2b. Provision acts on an energy/electrical thing (grid, bulk-power, transmission, substation, transformer, switchgear, generation, solar, photovoltaic, nuclear, oil, gas, SPR, critical minerals) → **Energy, Grid & Electrical Infrastructure**. This beats procurement.
3. Provision restricts what government/contractors may buy → **Federal Procurement & Buy American**, unless rule 2b applies.
4. Provision restricts who may own/acquire a US asset → **Foreign Investment in the US**. Provision restricts money, its price or access to capital → **Currency, Financial & Funding**.
5. Visa screening: PRC nationals/researchers/students/military-affiliated applicants → **Information & Technology Security**; southern-border migration/asylum/wall/border patrol → **Border Security & Migration**.
6. Bill subject is a third country and China is only context → **Defense, Military & Territorial Disputes**, unless the provision itself imposes a sanction, tariff or export control on Chinese entities; then classify the instrument.
7. **Political / Foreign Influence** is last resort, never first.

## Confidence rubric
Use only these four values:
- **95** — provision explicitly names an instrument and exactly one topic covers it; no tie-break needed.
- **85** — provision names an instrument, multiple topics were plausible, and a numbered tie-break decided it. Append `(rule N)` to runner-up.
- **70** — no provision in Mechanism/Summary; provision built from Title, or loose paraphrase was required.
- **50** — `PROVISION: NONE STATED`.

Do not inflate confidence. Most rows should be 95/85 if Mechanism is read first.

## Output contract
Return exactly four lines and nothing else:

PROVISION: <one legal-effect sentence or NONE STATED>
TOPIC: <one verbatim topic name>
TOPIC_CONFIDENCE: <95, 85, 70 or 50>
TOPIC_RUNNER_UP: <different second-best verbatim topic; append (rule N) when a tie-break decided the row>
