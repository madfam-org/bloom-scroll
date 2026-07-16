# Product Requirements Document (PRD): The Bloom Scroll
**Version:** 1.1 | **Status:** Product intent + implementation notes | **Classification:** Internal

**Current-state reference:** See [CURRENT_STATE.md](CURRENT_STATE.md), last audited 2026-05-28, for observed repository and `almanac.solar` production behavior. Items below describe the product target; not every integration is implemented in this repo.

## 1. Executive Summary
The **Bloom Scroll** is a mobile-first content aggregator designed to counter "doom scrolling"—the compulsive consumption of negative news—by engineering a feed rooted in **epistemic progress**, **aesthetic novelty**, and **constructive perspective**.

Unlike traditional aggregators that optimize for engagement (time-on-site) via outrage, the Bloom Scroll optimizes for **enrichment** and **serendipity**. It functions as a "Perspective Engine," synthesizing raw statistical truth (Our World in Data), frontier science (OpenAlex), and decentralized creativity (Neocities) into a finite, high-value daily digest. It complements "blindspot" analysis tools (like Ground News) by adding a layer of historical context and visual culture, ensuring users leave the app feeling more informed and optimistic than when they arrived.

---

## 2. Core Product Principles (The "Slow Web" Framework)
To differentiate from engagement-bait platforms, the application adheres to these design tenets:

1.  **Finite Feeds:** The feed must have a definitive "End" state after a set number of items (e.g., 20 cards) to signal completion and respect the user's time.[1]
2.  **Upward Scrolling:** A UX metaphor where users "plant" ideas and scroll "up" to see them bloom, reversing the psychological "descent" of standard feeds.[2]
3.  **Raw over Cooked:** Whenever possible, render data from the source (CSV/JSON) rather than static images, allowing users to interact with the "ground truth".[3]
4.  **Serendipity over Similarity:** The recommendation algorithm explicitly penalizes repetitiveness, prioritizing high-value "outliers" (e.g., a 19th-century aesthetic followed by a fusion energy breakthrough).[4]

---

## 3. Functional Specifications

### 3.1. Content Ingestion Layer ("The Root System")
The system requires a polymorphic scraper/API client capable of normalizing six distinct content types into a unified `BloomCard` object.

| Source Category | Primary Target | Integration Strategy | Data Payload |
| :--- | :--- | :--- | :--- |
| **Macro-Data** | `ourworldindata.org` | **Direct ETL:** Bypass RSS. Use OWID's CSV/JSON endpoints and `owid-content` repo to fetch raw datasets for local rendering.[5, 3] | Interactive Charts, "Progress Threshold" Alerts (e.g., "Child mortality dropped below X%"). |
| **Science** | `oa.mg` / `openalex.org` | **Concept Monitoring:** Use OpenAlex API (with "polite pool" email auth) to filter for high-impact papers (high citation velocity) in positive fields (e.g., renewables, medicine).[6, 7] | Abstract summaries, "breakthrough" tags, direct PDF links. |
| **Aesthetic** | `aesthetics.wiki` / `cari.institute` | **MediaWiki REST API:** Poll `RecentChanges` on Aesthetics Wiki. Scrape CARI's Are.na channels via Are.na API for high-res visual artifacts.[8, 9] | High-res images, genre definitions, "Vibe" tags. |
| **Indie Web** | `neocities.org` | **Webring Traversal:** Parse `sort_by=last_updated` on Neocities browse and ingest `webring.json` files to find active, human-curated sites.[10, 11] | Screenshots, "Site of the Day" features, blog excerpts. |
| **Narrative** | `tvtropes.org` | **Mirror API:** Use **All The Tropes** (MediaWiki fork) to avoid scraping blocks. Match news events to narrative tropes (e.g., "The Underdog").[12] | Trope cards explaining the narrative structure of current events. |
| **Education** | `my-mooc.com` | **Structured Scraping:** Parse Class Central/My-Mooc for "Free Certificates" and "New & Popular" to suggest micro-learning slots.[13, 14] | Course cards with "Time to Complete" metadata. |

### 3.2. The Perspective Engine (Analysis Microservice)
To fulfill the requirement of "getting every side of the story," this service processes incoming news items before they hit the feed.

*   **Bias Classification:**
    *   **Model:** Implement `PoliticalBiasBERT` (or `Qwen3-4B-BiasExpert`) to score article text. Detects 18 types of bias including "Sensationalism" and "Omission".[15, 16]
    *   **Output:** A "Constructiveness Score" (0-100). Articles below a threshold are discarded or flagged.
*   **Blindspot Detection:**
    *   **Clustering:** Use **HDBSCAN** (Hierarchical Density-Based Clustering) on Sentence-BERT embeddings to group articles about the same event.[17, 18]
    *   **Source Diversity Calculation:** If a cluster contains only "Left-Leaning" sources (based on domain ratings from Ad Fontes/AllSides), tag as "Blindspot: Right".[19, 20]
*   **Factfulness Check:**
    *   **Cross-Reference:** If a news article makes a statistical claim (e.g., "Crime is up"), the engine queries the local OWID/Gapminder dataset for the relevant indicator and appends a "Data Context" card (e.g., "Long-term trend: Crime is down 20% since 1990").[21]

### 3.3. The Recommendation Algorithm ("The Bloom Logic")
Unlike collaborative filtering (which creates echo chambers), this engine uses a **Metropolis-Hastings** sampling approach to ensure diversity.[22]

*   **Serendipity Score ($S$):** Calculated as $S = Relevance \times (1 - Similarity)$. The system purposely selects items that are semantically distant from the user's last 5 reads but high in global quality.[4]
*   **The "Robin Hood" Layout:** A layout algorithm (inspired by Flipboard) that balances "Rich" content (high-res art from CARI) with "Poor" content (text-heavy abstracts) to maintain visual rhythm and prevent fatigue.[22]

### 3.4. Implementation Notes as of 2026-07-16

- Implemented ingestion modules: OWID, Are.na aesthetics, and OpenAlex
  (`backend/app/ingestion/`). Neocities, TVTropes, and My-MOOC are NOT implemented.
- A daily ingestion CronJob (`infra/k8s/production/ingest-cronjob.yaml`) refreshes
  content through the authenticated ingest endpoints.
- Bias classification is currently a placeholder in `backend/app/analysis/processor.py`;
  perspective scores are only emitted/displayed when `score_provenance` is set.
- The finite feed endpoint is implemented at `GET /api/v1/feed` with a 20-card daily
  limit and duplicate-free pagination via `exclude_ids`.
- The daily limit is enforced client-side (localStorage read counts passed as
  `read_count`); the server trusts the client. This is an accepted privacy-first
  alpha trade-off (no accounts, no server-side read tracking) — recorded 2026-07-16.
- Frontend state management is Riverpod, not BLoC.

---

## 4. User Experience & Interface (UI/UX)

### 4.1. The Feed Experience
*   **Skeleton Screens:** Use gray-box placeholders instead of spinning loaders to reduce anxiety and perceived wait time.[23, 24]
*   **Masonry Grid:** A dynamic tile layout that adapts to the aspect ratio of the content (e.g., vertical for OWID charts, square for Aesthetic Wiki art).[25]
*   **"Mini-Bloom" Mode:** A dedicated button for a 3-minute, 5-card session designed for coffee breaks.

### 4.2. The "Perspective Overlay"
When viewing a news item, users can swipe left to reveal the **Perspective Dashboard**:
1.  **Bias Meter:** Visual gauge of the article's framing (Left/Center/Right + Constructive/Toxic).
2.  **The Data Layer:** Relevant charts from OWID that confirm or refute the article's premise.
3.  **Trope Scope:** A "TVTropes" tag identifying if the story is being framed via a specific narrative device (e.g., "Fear Mongering" or "David vs. Goliath").[26]

---

## 5. Technical Architecture

### 5.1. Backend Stack
*   **Language:** Python 3.11+ (FastAPI for API, Celery for background workers).[27]
*   **Orchestration:** Docker & Kubernetes for microservices scaling.
*   **Database:**
    *   **PostgreSQL:** User data, feed history, source metadata.
    *   **Vector DB (Milvus or pgvector):** Storing SBERT embeddings for article clustering and serendipity calculations.[28]
    *   **Redis:** Caching for "Hot Feeds" and Celery message broker.[29]

### 5.2. Integration Modules
*   **`news-please` Library:** For robust extraction of body text and metadata from general news URLs.[30, 31]
*   **RSS-Bridge:** Hosted instance to generate feeds for sites without native RSS (e.g., specific CARI pages or dynamic Neocities tags).[32, 33]

### 5.3. Client
*   **Framework:** Flutter (Dart) for high-performance rendering of custom charts (D3-like visualization on mobile) and consistent behavior across iOS/Android.

---

## 6. Roadmap

### Phase 1: The "Seed" (MVP)
*   Ingest OWID (Global Stats) and RSS-Bridge (General News).
*   Implement basic "Finite Feed" (20 items/day).
*   Simple Keyword-based filtering (Exclude "Crime", "Terror").

### Phase 2: The "Sprout" (Alpha)
*   Integrate OpenAlex (Science) and Neocities (Indie Web).
*   Deploy **Perspective Engine v1** (BERT Bias detection).
*   Implement "Robin Hood" masonry layout.

### Phase 3: The "Bloom" (Beta)
*   Full "Blindspot" analysis (Clustering).
*   Trope identification (TVTropes integration).
*   "Mini-Bloom" micro-sessions.
*   Public launch.

## 7. Current Hardening Priorities

- Keep production `/docs` and `/openapi.json` hidden through the API environment gate and `scripts/prod-smoke.sh`.
- Keep STORY-005 backend tests and the new frontend model/config/storage tests passing in CI.
- Keep Enclii CLI `v1.0.0-alpha.1` or newer available to operators so CLI status uses the same live health feed as `enclii observe health`; current CLI observation still requires `ENCLII_PROJECT=bloom-scroll`.
- Keep the precise production bundle check for `http://localhost:8000/api/v1` instead of broad `localhost:` assertions.
