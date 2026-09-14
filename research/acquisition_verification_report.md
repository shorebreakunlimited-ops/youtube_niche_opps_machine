# Acquisition and verification pass

**Scope:** Bernard Mael / Jonathan Murphy (Bethel, Alaska) and Nakia Porter (Solano County, California) only.  
**Research cutoff:** 2026-09-14 UTC.  
**Rule:** “Located” means a stable, complete URL was found. “Verified” does not mean production rights are cleared.

## Executive decision

| Case | Previous posture | Corrected decision | Reason |
|---|---|---|---|
| Bernard Mael / Jonathan Murphy | Provisional primary | **HOLD** | Reporting confirms a strong narrative and criminal outcome, but no native body-camera file, complete public angle, case-specific KYUK license, criminal primary-record package, civil complaint, or executed settlement was acquired. [BET-P01, BET-S01–BET-S07] |
| Nakia Porter | Provisional backup | **HOLD** | The 18:47 agency bodycam and 43:01 in-car uploads are accessible, but native continuity is unverified, McDowell’s angle is unresolved, and deposition and executed-settlement records remain missing. [SOL-Y01, SOL-Y02, SOL-S01, SOL-S04, SOL-P01, SOL-P03] |

Neither case is production ready. Bethel Episode 1 must not be declared ready until its footage gate is cleared.

## A. Corrected conditional-pass ledger

| Gate | Bethel | Solano |
|---|---|---|
| Identifiable incident and outcome | Pass: Murphy was convicted of fourth-degree assault, providing false information implicating another, and second-degree tampering with public records. [BET-P01] | Pass: federal case 2:21-cv-01473-KJM-JDP reached a $17 million settlement, with the minor compromise approved by the court. [SOL-P03, SOL-P04] |
| Core footage publicly accessible | **Fail:** KYUK reports obtaining footage, but this pass found no stable, discrete raw-video URL. [BET-S01, BET-S03, BET-S04] | Conditional: agency uploads exist at 18:47 and 43:01. [SOL-Y01, SOL-Y02] |
| Every angle/officer identified | **Fail:** Murphy and Bouma are identified; reporting says three officers recorded, but the third officer is unnamed. [BET-S01, BET-S02] | **Fail:** McCampbell bodycam and an in-car view are public; McDowell’s bodycam is not accounted for. [SOL-Y01, SOL-Y02, SOL-S04] |
| Native completeness/authenticity | **Fail:** no native files, metadata, audit logs, or evidence index. | **Fail:** “full-length/unedited” is an agency characterization, not independent forensic verification. [SOL-S01, SOL-S02] |
| Primary legal records | **Fail:** exact criminal/civil docket numbers, charging document, judgment, sentencing order, civil complaint, and executed settlements were not acquired. [BET-P08, BET-S01–BET-S05] | Conditional: operative complaint and dispositive order are located; deposition exhibits and executed settlement remain missing. [SOL-A02, SOL-P01, SOL-P03] |
| Rights/licensing | **Fail:** KYUK’s general sharing policy requires credit but is not a case-specific commercial license or warranty that KYUK controls BPD footage rights. [BET-S06, BET-S07] | **Fail:** public availability does not itself clear copyright, privacy, or reuse rights. [SOL-Y01, SOL-Y02] |
| Saturation | Low relevant YouTube saturation in the recorded queries: 0 relevant of 25 raw results. [YT-EXP-01] | High under the declared rule: 22 relevant videos and a 435,478-view maximum. [SOL-Y01–SOL-Y22] |

## B. Complete source registry

The complete registry is [`source_registry.csv`](./source_registry.csv). Every source has one unique ID, a complete URL, a document classification, and a separate evidentiary-treatment field.

Classification rules used:

- Government, court, legislative, and agency-published records are **primary**.
- News reports, publisher policies, and third-party video publications are **secondary**.
- A complaint is labeled **allegations** even though it is a filed court record; filing does not establish its factual assertions. [SOL-A01, SOL-A02]
- A court order is primary, but only holdings and expressly undisputed facts are treated as findings. [SOL-P01]

## C. Claim-to-source verification

The sentence-level ledger is [`claim_verification.csv`](./claim_verification.csv). Its material corrections are:

1. The official Alaska release states that body-worn footage showed Mael raise his hands, Murphy strike him twice at the first stop, and Murphy later deliver more than 20 head strikes; it also states that the footage did not show the vehicle strike or drag Murphy. [BET-P01]
2. Permanent brain damage, negligent hiring, retention, and training remain allegations attributed to Mael’s civil pleading; no finding establishing them was located. [BET-S01]
3. Bethel’s settlement is **$7 million to Bernard Mael plus $3 million to Nicholas Kerr, totaling $10 million across two separate incidents**. [BET-S03]
4. Murphy’s conviction is established by an Alaska Department of Law release; the later report says Judge Nelson Traverso imposed 100 days of confinement, 150 hours of Bethel community service, and a suspended imposition of sentence. [BET-P01, BET-S05]
5. In Porter, the court granted plaintiffs summary judgment on the unlawful-search claim against McCampbell, granted defendants judgment on several other claims, and left disputed claims unresolved; the result was mixed. [SOL-P01]
6. No source supports saying body-camera footage “automatically defeated qualified immunity.” That statement is removed for both cases. [BET-P01, SOL-P01]
7. Porter’s allegations of punching, hair pulling, unlawful seizure, excessive force, and false reporting are attributed to pleadings rather than presented as adjudicated facts. [SOL-A01, SOL-A02]
8. The Solano agency/deputies said Porter resisted and struck a deputy, while public reporting says the released images do not clearly resolve the core struggle; this remains a disputed account. [SOL-S02, SOL-S04]

### Solano fact separation

| Category | Verified treatment |
|---|---|
| Visible/audible on public video | Commands, handcuffing/ground struggle, statements that Porter was unconscious, later checks, and portions of the roadside aftermath are recorded; the core struggle is shaky or partly out of the dashcam view. [SOL-Y01, SOL-Y02, SOL-S02, SOL-S03] |
| Plaintiff allegations | Deputies punched Porter, pulled her hair, used excessive force, searched unlawfully, and falsified reports. [SOL-A01, SOL-A02] |
| Judicial findings/rulings | Unlawful-search summary judgment against McCampbell; defense judgments on specified claims; numerous remaining disputes were not resolved on summary judgment. [SOL-P01] |
| Deputy/agency statements | Porter resisted, slipped a cuff, and struck a deputy; the Sheriff characterized the uploads as full-length. [SOL-S01, SOL-S02, SOL-S04] |
| Unresolved | Exact force during obscured frames, McDowell-camera existence/completeness, all native-file continuity, and full settlement terms. [SOL-S02, SOL-S04, SOL-P03] |

## D. Footage acquisition matrix

The full matrix is [`footage_acquisition.csv`](./footage_acquisition.csv).

### Bethel angles

- **Jonathan Bouma BWC:** reporting identifies Bouma’s camera at the first stop and says it did not show the vehicle hitting Murphy; no duration or complete public file was located. [BET-S01, BET-S02]
- **Jonathan Murphy BWC:** reporting says it was not activated during the initial encounter and does not establish precisely when it began recording; no complete public file was located. [BET-S01, BET-S02]
- **Third-officer BWC:** the charging-document report says all three officers at the scene captured footage, but the third officer is not named in the located sources. [BET-S02]
- **KYUK copy/excerpts:** KYUK obtained BPD footage by public-records request and published descriptions/stills, but no longest discrete version was located. [BET-S01, BET-S03, BET-S04]

The longest publicly accessible version of each Bethel angle therefore remains **not established**. News broadcasts must not substitute for native footage; if used as research screeners, provenance and KYUK’s written restrictions must be retained. [BET-S06, BET-S07]

### Solano angles

- **McCampbell bodycam:** 18:47 agency upload, `9rFwYkl5BZQ`. [SOL-Y01, SOL-S01]
- **Patrol in-car/dash camera:** 43:01 agency upload, `0Yb_EMkSeyQ`; reporting says the core ground struggle is not clearly shown from this view. [SOL-Y02, SOL-S02]
- **McDowell bodycam:** not released/located; reporting describes inconsistent public information about whether it was activated or existed. [SOL-S04]
- **Post-incident discussion:** a 1:22 public clip shows Stockton speaking with McCampbell and McDowell, but the native parent file and camera provenance are not established. [SOL-Y11, SOL-Y12]

The claimed “full 18-minute agency release” is genuinely an agency-channel upload and runs 18:47. [SOL-Y01] It cannot yet be called independently verified unedited because YouTube provides a transcoded publication, not the native file, hash, AXON audit trail, or proof that every camera segment was included. [SOL-S01, SOL-S04]

## E. Corrected saturation table

Recorded searches were run on 2026-09-14. The raw export is [`youtube_saturation_raw.json`](./youtube_saturation_raw.json); the manually relevance-checked result table is [`youtube_saturation_corrected.csv`](./youtube_saturation_corrected.csv).

Declared rule:

- **LOW:** 0–5 relevant videos and highest view count below 50,000.
- **MODERATE:** 6–14 relevant videos, or highest view count from 50,000 through 249,999.
- **HIGH:** at least 15 relevant videos, or any relevant video at or above 250,000 views.

| Case | Raw result rows | Unique raw IDs | Relevant competing videos | 2025–2026 outcome videos | Highest observed views | Result |
|---|---:|---:|---:|---:|---:|---|
| Bethel | 25 | 25 | 0 | 0 | N/A | **LOW** |
| Solano | 41 | 36 | 22 | 4 | 435,478 | **HIGH** |

The Bethel search’s 25 returned videos were false positives such as unrelated people named Bernard Mael or Jonathan Murphy; result count is not treated as relevant competition. [YT-EXP-01] The Solano maximum belongs to `Q7TEFAoX4Cc`, which covers the incident and $17 million settlement; the count, threshold, and classification therefore agree. [SOL-Y19]

This is a reproducible query sample, not a claim about the entire YouTube catalog. View counts are observations as of the cutoff date and will change.

## F. Missing-assets and legal-risk ledger

The detailed ledger is [`missing_assets_legal_risk.csv`](./missing_assets_legal_risk.csv). Blocking items are:

- Bethel native footage, third-officer identity, criminal and civil primary-record packages, executed settlement agreements, and a case-specific KYUK license. [BET-S01–BET-S07]
- Solano native/hash/audit evidence, McDowell footage or a documented nonexistence record, public deposition excerpts, and the executed settlement agreement. [SOL-S04, SOL-P01, SOL-P03]
- Both cases require a written rights analysis; public access does not equal production permission. [BET-S06, SOL-Y01, SOL-Y02]
- Alaska production may incur staff charges if search/copying exceeds five person-hours, and City forms warn that redaction and copying can cost money. [BET-P02, BET-P06, BET-P07]
- California permits privacy redaction of critical-incident recordings if the result remains comprehensible; agency publication does not eliminate privacy review for republication. [SOL-P08]

## Bethel public-records request draft

**Custodian:** Bethel Police Department through the official police-records form, with a copy to `police@cityofbethel.net`; if routing is disputed, copy the City Clerk through the official public-records page. [BET-P02–BET-P05]

> Subject: Narrow public-records request — Bernard Mael incident, December 23, 2023
>
> Under the Alaska Public Records Act and Bethel’s public-records procedures, I request existing records concerning the Bethel Police Department encounter with Bernard Mael on December 23, 2023, limited to the initial vehicle stop, ensuing pursuit, second stop/arrest, and immediate post-incident reporting:
>
> 1. Native or highest-quality export of every body-worn-camera video and audio file recorded by Jonathan Murphy, Jonathan Bouma, and every other responding officer, including pre-event buffer and post-incident segments.
> 2. The evidence index, AXON/export audit trail, original filenames, recording start/stop times, device/user assignment, checksums if maintained, and any redaction/export log for those files.
> 3. Dash/in-car video, dispatch/CAD audio and event chronology, and 911/non-emergency audio associated with the incident.
> 4. Final incident, supplemental, use-of-force, arrest, property/evidence, and supervisory-review reports, including releasable photographs and diagrams.
> 5. Affidavits or sworn statements used to seek charges against Mael, and releasable exhibits attached to or incorporated in those affidavits.
> 6. Policies in effect on December 23, 2023 governing body-camera activation, force, Tasers, pepper spray, vehicle pursuits, report review, evidence retention, and public release.
>
> Please produce records electronically by secure download in rolling batches. I do not ask the City to create a new summary. If any part is withheld or redacted, please produce segregable portions and identify the legal basis for each withholding. Before incurring more than $100 in fees, provide an itemized estimate and identify lower-cost narrowing options. Please preserve all responsive records while this request is pending.

The request deliberately excludes medical records, unrelated personnel files, and all unrelated incidents to reduce privacy, redaction, and cost burdens. It should not be submitted if the requester cannot truthfully complete Bethel’s non-litigation-affiliation certification. [BET-P02]

## KYUK license inquiry

Send a case-specific inquiry to `news@kyuk.org` and `office@kyuk.org`, referencing the exact Mael stories and asking for a screener or timecoded inventory. [BET-S07] The written response must state whether KYUK can license the underlying BPD footage or only its own edit, permitted platforms, monetization, territory, term, credit, source-file delivery, edits/redactions, third-party restrictions, and fee. KYUK’s public policy supports sharing with credit and no paywall, but does not answer those case-specific rights questions. [BET-S06]

## Solano records follow-up

Use the Sheriff’s official GovQA route and copy the Records and Warrants Bureau at `SHFRecords@SolanoCounty.gov`. [SOL-P06, SOL-P07] Request native McCampbell BWC and in-car files, McDowell BWC or a custodian declaration explaining nonexistence, device assignment and activation/docking/deletion logs, full evidence index, redaction/export logs, reports, CAD/dispatch, and written publication/reuse terms.

For the litigation file, obtain ECF 144, ECF 199, public exhibits containing material deposition excerpts, ECF 256 and attachments, the final dismissal/judgment, and any County-executed settlement/payment authorization. [SOL-A02, SOL-P01, SOL-P03, SOL-P04]

## G. Final decisions

### Bernard Mael / Jonathan Murphy — **HOLD**

The criminal outcome and separate $7 million Mael settlement are well supported, and sampled YouTube competition is low. [BET-P01, BET-S03, YT-EXP-01] The case nevertheless fails the acquisition gate because raw footage, every angle/officer, primary court records, executed settlement, and production rights are unresolved.

### Nakia Porter — **HOLD**

The official 18:47 bodycam and 43:01 in-car releases make this case materially closer to acquisition-ready than Bethel. [SOL-Y01, SOL-Y02] Missing McDowell footage/proof of nonexistence, native continuity evidence, deposition material, executed settlement terms, and rights clearance prevent a conditional production pass. [SOL-S04, SOL-P01, SOL-P03]

No additional candidates should be researched until one of these two cases clears its open acquisition items.
