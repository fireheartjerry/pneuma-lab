# 33 — Execution Journal

> **NON-AUTHORITATIVE EVIDENCE INDEX AND CURRENT VOLUME.** This journal records
> execution evidence but does not amend or outrank repository authority.

## Sharded recording contract

The user authorized a byte-preserving storage migration after the original
journal became costly to load. Events through `EJ-20260728-0468` and the original
prologue are stored as immutable historical segments in `execution-journal/`.
Their ordered concatenation reconstructs the exact pre-migration file with
SHA-256 `ecddbb64c20323a0200131a6181215b344105ec211080703ae374e96360b618c`.

New receipts append only below `## Current volume`. A rotation may move complete
event ranges into new immutable segments, but it must preserve event bytes,
update the machine-readable manifest, and pass the repository checker before
release. Published event content is never silently edited, deleted, reordered,
duplicated, or renumbered. Corrections remain later events. Event allocation
must scan the archived manifest and current volume as one logical sequence.

The detailed capture, no-clobber allocation, compact-receipt, raw-retention,
two-commit delivery, and non-authority rules in the archived prologue remain in
force. Routine full stdout/stderr stays local under ignored `build/`; committed
receipts remain compact and content-addressed.

## Immutable archive manifest

- Machine-readable manifest: `execution-journal/manifest.json`
- Archived event count: `468`
- Archived range: `EJ-20260728-0001` through `EJ-20260728-0468`
- Exact reconstructed bytes: `686661`
- Exact reconstructed lines: `10419`
- Exact reconstructed SHA-256: `ecddbb64c20323a0200131a6181215b344105ec211080703ae374e96360b618c`

| Segment | Range | Bytes | Lines | SHA-256 |
|---|---:|---:|---:|---|
| prologue.md | prologue | 5591 | 94 | `8c52e02244f6a489d1d9939d69f29feca396b2c43522f44c4a45dae595eb3ad5` |
| events-20260728-0001-0050.md | EJ-20260728-0001–EJ-20260728-0050 | 100202 | 1891 | `8bec600956bd17584efd48677f4a7cbdad3f4bcdbd11368caff8796c0eac62af` |
| events-20260728-0051-0100.md | EJ-20260728-0051–EJ-20260728-0100 | 68420 | 1423 | `ae684a8cd9e7f2ed79931e129a71df21f86cc91393140d7fd8f72fe6bd78090d` |
| events-20260728-0101-0150.md | EJ-20260728-0101–EJ-20260728-0150 | 58775 | 1280 | `4ea5abfe6277f50b120c96d1eb726ef6ba9900ba6e393971d86e084158d67859` |
| events-20260728-0151-0200.md | EJ-20260728-0151–EJ-20260728-0200 | 78897 | 1609 | `f226f43c4a8843e876686d807085fe6c88b6dc74c434f49c30faf9618d070652` |
| events-20260728-0201-0250.md | EJ-20260728-0201–EJ-20260728-0250 | 83647 | 1569 | `1590527a4d505121b22a48a409897d26d3898e886803cfc49ebdaf95237a0dab` |
| events-20260728-0251-0300.md | EJ-20260728-0251–EJ-20260728-0300 | 62691 | 614 | `05325cccf338be3cc2235b5c9f9786516931d5ce77debc7b4f47f617f11e17af` |
| events-20260728-0301-0350.md | EJ-20260728-0301–EJ-20260728-0350 | 67097 | 531 | `5f0bec9bae995c37bc4793e50d140fd758dd162a25b7ef20db8e00c18093fba2` |
| events-20260728-0351-0400.md | EJ-20260728-0351–EJ-20260728-0400 | 64790 | 564 | `6989ae2e5630a70ea22ca33b13df43405206fa6fef494b5c45e4dd6d3b9a39b8` |
| events-20260728-0401-0450.md | EJ-20260728-0401–EJ-20260728-0450 | 73729 | 632 | `cf15230a1fb058bff579744f8985ce3707fd18c63609d7803ccca289670fdf4b` |
| events-20260728-0451-0468.md | EJ-20260728-0451–EJ-20260728-0468 | 22822 | 212 | `b4650b694d1ae64110288a094a1dc315f38e7a505a2228dd16c1fe5d3ba106c4` |

Run `.venv/bin/python -m scripts.research.execution_journal check` to verify
segment hashes, exact historical reconstruction, and global event continuity.

## Current volume

The next event after the archived migration boundary is appended below.

### EJ-20260728-0469 — migrate canonical execution journal into verified shards

- **Prior event:** `EJ-20260728-0468` (archived)
- **Local interval:** `2026-07-28T22:11:47-07:00` to `2026-07-28T22:11:47-07:00`
- **UTC interval:** `2026-07-29T05:11:47+00:00` to `2026-07-29T05:11:47+00:00`
- **Action:** Ran `.venv/bin/python -m scripts.research.execution_journal migrate --cutoff EJ-20260728-0468 --shard-size 50` against the canonical journal after serialized no-clobber event allocation.
- **Result:** GREEN, exit `0`, zero stderr. The migration archived `468` contiguous events plus the original prologue into byte-exact segments, replaced the canonical path with this lightweight index/current volume, and immediately passed its built-in integrity verifier.
- **Exact historical reconstruction:** `ecddbb64c20323a0200131a6181215b344105ec211080703ae374e96360b618c` SHA-256; last archived event `EJ-20260728-0468`; current-event count before this receipt `0`.
- **Compact receipt:** stdout `196` bytes / `1` line / SHA-256 `672b6935eab7edf36fbc36e066044a9ff9a8073f7bfadb00f11901e79e3b5180`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0469/` (local, ignored, retained through `2026-11-27`).
- **Authority effect:** storage-only, explicitly user-authorized. No design, plan, scientific claim, spend gate, training state, or Slice 4 source byte changed.
- **Next gate:** rerun the checker with this first live event present, inspect exact shard sizes/hashes and Git diff statistics, then commit the isolated journal infrastructure without staging Slice 4.

### EJ-20260728-0470 — verify canonical shards with the first live event

- **Prior event:** `EJ-20260728-0469`
- **Local interval:** `2026-07-28T22:12:20-07:00` to `2026-07-28T22:12:20-07:00`
- **UTC interval:** `2026-07-29T05:12:20+00:00` to `2026-07-29T05:12:20+00:00`
- **Action:** Ran the repository journal checker, measured/hash-addressed the live index and manifest, enumerated every historical segment, checked whitespace, and inspected worktree scope.
- **Result:** GREEN, exit `0`, zero stderr. The checker reconstructed all `468` archived events to SHA-256 `ecddbb64c20323a0200131a6181215b344105ec211080703ae374e96360b618c`, then observed exactly one live event and global last ID EJ-0469. The live journal is now `5398` bytes / `67` lines—under 1% of the former monolith. Its SHA-256 before this receipt was `fe6eb36af5f75804fa68c30936ff41399a77a5dbe2f6b09ab5d54015aba75fa4`; manifest SHA-256 is `32eff486c2faf2465302551d9a165c61a374fd4821d69b5a97bd97668e6f0cae`.
- **Shard inventory:** ten event shards (`22822`–`100202` bytes), one `5591`-byte exact prologue, and one `3258`-byte manifest. All remain below the old monolith size by a wide margin and are independently hash-addressed.
- **Compact receipt:** stdout `1365` bytes / `24` lines / SHA-256 `8e6bdb01330a5b0fdef69b0295e6bb5a9d1d7ce0750fbdb630a7a7f59aa4f584`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0470/` (local, ignored, retained through `2026-11-27`).
- **Scope proof:** only journal infrastructure is new; the pre-existing Slice 4 source/test modifications remain unstaged and were not altered by migration.

### EJ-20260728-0471 — capture GitHub workflow skill before visibility change

- **Prior event:** `EJ-20260728-0470`
- **Local interval:** `2026-07-28T22:12:58-07:00` to `2026-07-28T22:12:58-07:00`
- **UTC interval:** `2026-07-29T05:12:58+00:00` to `2026-07-29T05:12:58+00:00`
- **Action:** Captured the complete connected GitHub skill instructions before taking repository visibility action.
- **Result:** GREEN, exit `0`, zero stderr. The skill is `4356` bytes / `74` lines and directs connector-first work while permitting local `gh` when the connector does not cover the operation well; exact repository/branch resolution and verification remain required.
- **Compact receipt:** stdout `4471` bytes / `75` lines / SHA-256 `f2d259ffdaaf5082b2c7a18a727d02ee90d41394d4122a7e5a2f7fed690ea48d`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0471/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** resolve the exact GitHub repository and visibility, then audit committed history for exposure blockers before changing state.

### EJ-20260728-0472 — complete direct read of GitHub workflow skill

- **Prior event:** `EJ-20260728-0471`
- **Local interval:** `2026-07-28T22:13:28-07:00` to `2026-07-28T22:13:28-07:00`
- **UTC interval:** `2026-07-29T05:13:28+00:00` to `2026-07-29T05:13:28+00:00`
- **Action:** Read all `74` lines of the GitHub skill directly into the active review context, supplementing the compact retained capture in EJ-0471.
- **Result:** GREEN, exit `0`, zero stderr. The task is an exact current-repository state change, not PR/issue triage, review follow-up, CI debugging, or a commit/push request. Local `gh` is the appropriate gap-filler if the connector lacks repository-visibility mutation.
- **Compact receipt:** stdout `4356` bytes / `74` lines / SHA-256 `81dbdd90934fe86a79ddc4790fd211e5fca866302a74090ad153395f56f2bd42`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0472/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** resolve remote/auth/visibility and run a committed-history exposure audit before publication.

### EJ-20260728-0473 — discover connector support for repository visibility

- **Prior event:** `EJ-20260728-0472`
- **Recorded at:** local `2026-07-28` / UTC `2026-07-29`; connector-call timing is retained by the active tool transcript rather than a shell timestamp.
- **Action:** Queried deferred GitHub connector capabilities for repository metadata and visibility mutation.
- **Result:** the connected GitHub app exposes authoritative repository metadata via `_get_repo` but no repository-visibility update operation. Per the GitHub skill's hybrid rule, use the connector for a read-side cross-check and authenticated local `gh` for the exact visibility mutation.
- **Evidence mode:** structured connector discovery response in the active session; no stdout/stderr or local raw stream exists for this non-shell call.
- **Next gate:** resolve the local remote and authenticated GitHub identity, then cross-check repository metadata through the connector.

### EJ-20260728-0474 — resolve exact GitHub target, authentication, and current visibility

- **Prior event:** `EJ-20260728-0473`
- **Local interval:** `2026-07-28T22:14:18-07:00` to `2026-07-28T22:14:19-07:00`
- **UTC interval:** `2026-07-29T05:14:18+00:00` to `2026-07-29T05:14:19+00:00`
- **Action:** Resolved origin, current branch, authenticated GitHub identity/scopes, authoritative `gh repo view` metadata, and local dedicated secret-scanner availability.
- **Result:** GREEN, exit `0`, zero stderr. Exact target is `fireheartjerry/pneuma-lab` at `https://github.com/fireheartjerry/pneuma-lab`; current branch is `codex/neurips-2026-empirical`; default branch is `main`; GitHub reports `PRIVATE` / `isPrivate: true`. The active account is `fireheartjerry` with repository scope sufficient for the requested mutation. Neither `gitleaks` nor `trufflehog` is installed.
- **Credential handling:** `gh auth status` emitted only GitHub's masked token representation; no credential value was committed or exposed in this receipt.
- **Compact receipt:** stdout `534` bytes / `9` lines / SHA-256 `359fee36f0bc762360c558d299eabd180d28b777dab72c0997acfd596dd751e0`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0474/` (local, ignored, retained through `2026-11-27`; contains only GitHub's masked token line).
- **Next gate:** connector metadata cross-check, followed by a full committed-object exposure audit without printing matched secret values.

### EJ-20260728-0475 — cross-check GitHub repository through connected app

- **Prior event:** `EJ-20260728-0474`
- **Action:** Read `fireheartjerry/pneuma-lab` metadata through the connected GitHub app using the exact owner/name resolved locally.
- **Result:** connector repository ID `1291362530`; visibility `private`; default branch `main`; repository not archived; authenticated principal has `admin`, `maintain`, `push`, `pull`, and `triage` permissions. Clone URL matches local origin exactly.
- **Evidence mode:** structured connector response in the active session; wall time `0.5758 s`; no shell stdout/stderr or local raw stream exists for this call.
- **Cross-check disposition:** connector and `gh repo view` agree on target identity and private state. Target ambiguity is closed.
- **Next gate:** inspect all locally reachable Git blobs and historical filenames for high-confidence credential material or private-key artifacts before public exposure.

### EJ-20260728-0476 — pass reachable-history credential and key-material audit

- **Prior event:** `EJ-20260728-0475`
- **Local interval:** `2026-07-28T22:15:56-07:00` to `2026-07-28T22:16:25-07:00`
- **UTC interval:** `2026-07-29T05:15:56+00:00` to `2026-07-29T05:16:25+00:00`
- **Action:** Scanned every unique blob reachable from every local ref for high-confidence private-key headers, GitHub/OpenAI/AWS/Slack/Google token forms, named cloud/API secrets, and credential-bearing database URLs. Separately audited historical filenames for `.env`, private-key, certificate-key, credential, and service-account artifacts. Match contents were never printed.
- **Result:** GREEN, exit `0`, zero stderr. `1441` unique reachable blobs scanned; `0` high-confidence content hits; `0` suspicious historical filenames. Largest-object inventory was retained to expose hidden binary/data risk; the largest reachable blob is a `4,892,408`-byte research JSON artifact, followed by historical journal/decision/plan blobs.
- **Limit:** no scanner proves absence of all sensitive or personal information. This is a broad high-confidence credential/key audit plus the repository's standing assertion that migration material contains no private data; it is not a semantic proof over every prose sentence.
- **Compact receipt:** stdout `2302` bytes / `26` lines / SHA-256 `b07c2c5f75fba08f2377c8fd42a7ad2cc11c82ea93688cf9c81cd055379f2582`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** identifiers-only hit lists, scanned-blob inventory, and streams at `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0476/` (local, ignored, retained through `2026-11-27`).
- **Disposition:** no detected blocker to the user's explicit public-visibility request. Proceed with the exact resolved repository and verify independently afterward.

### EJ-20260728-0477 — change `fireheartjerry/pneuma-lab` visibility to public

- **Prior event:** `EJ-20260728-0476`
- **Local interval:** `2026-07-28T22:17:07-07:00` to `2026-07-28T22:17:07-07:00`
- **UTC interval:** `2026-07-29T05:17:07+00:00` to `2026-07-29T05:17:07+00:00`
- **Action:** Executed `gh repo edit fireheartjerry/pneuma-lab --visibility public --accept-visibility-change-consequences` under the user's explicit instruction.
- **Result:** command accepted, exit `0`, zero stdout, zero stderr.
- **Compact receipt:** stdout `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0477/` (local, ignored, retained through `2026-11-27`).
- **Verification posture:** an exit-zero mutation is not enough. Independently verify authenticated metadata, unauthenticated public API accessibility, and connected-app metadata before declaring completion.

### EJ-20260728-0478 — verify public visibility through authenticated and unauthenticated paths

- **Prior event:** `EJ-20260728-0477`
- **Local interval:** `2026-07-28T22:17:41-07:00` to `2026-07-28T22:17:42-07:00`
- **UTC interval:** `2026-07-29T05:17:41+00:00` to `2026-07-29T05:17:42+00:00`
- **Action:** Queried repository metadata with authenticated `gh`, then queried GitHub's public REST endpoint with GitHub token environment variables explicitly removed and no authorization header.
- **Result:** GREEN, exit `0`, zero stderr. Authenticated metadata reports `PUBLIC` / `isPrivate: false`. The unauthenticated public API returns repository ID `1291362530`, `private: false`, and `visibility: public`, proving public discoverability independently of owner credentials.
- **Compact receipt:** stdout `302` bytes / `2` lines / SHA-256 `30fce6561dd4760a7541fe6a8002ecaa4f38fadc1a1cdbd2b0879e2b0e463301`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0478/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** final connected-app metadata cross-check, then return to committing the isolated journal-sharding infrastructure.

### EJ-20260728-0479 — final connected-app verification of public repository state

- **Prior event:** `EJ-20260728-0478`
- **Action:** Re-read the exact repository through the connected GitHub app after the visibility mutation.
- **Result:** repository ID remains `1291362530`; owner/name remains `fireheartjerry/pneuma-lab`; visibility is now `public`; default branch remains `main`; repository remains unarchived; authenticated admin permissions remain available. Connector wall time `0.5826 s`.
- **Evidence mode:** structured connector response in the active session; no shell stdout/stderr or local raw stream exists for this call.
- **Conclusion:** requested visibility change is complete and independently confirmed through authenticated CLI metadata, unauthenticated REST accessibility, and connected-app metadata.
- **Next gate:** isolate, validate, commit, and push the journal-sharding infrastructure without staging the in-progress Slice 4 files.

### EJ-20260728-0480 — pass final pre-commit journal-sharding gate

- **Prior event:** `EJ-20260728-0479`
- **Local interval:** `2026-07-28T22:18:38-07:00` to `2026-07-28T22:18:38-07:00`
- **UTC interval:** `2026-07-29T05:18:38+00:00` to `2026-07-29T05:18:38+00:00`
- **Action:** Ran one fail-closed aggregate gate: journal reconstruction/global continuity check, four focused migration tests, Ruff, mypy, full-worktree whitespace validation, and authority-hash verification.
- **Result:** GREEN, exit `0`, zero stderr. Checker sees `468` archived plus `11` live events through EJ-0479; historical SHA-256 remains `ecddbb64c20323a0200131a6181215b344105ec211080703ae374e96360b618c`. Tests: `4 passed`. Ruff and mypy pass. Plan/design hashes remain exactly `a2ca4fc419f353e9a38350025e1e2996fd21d66eb16b2d8d011af2c2e1d491b1` and `d2a3c5a20059574ab8dad92a45b29f06aeeaf2bd9dafbc8716c5449848a687db`.
- **Compact receipt:** stdout `615` bytes / `7` lines / SHA-256 `00e5bab9615310fde055ebec952a8dd2899ddc36a16acf20933040ba9058c83b`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0480/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** stage only the canonical live journal, immutable shards/manifest, checker, and focused tests; prove Slice 4 remains unstaged.

### EJ-20260728-0481 — staged whitespace gate rejects byte-exact shard boundaries

- **Prior event:** `EJ-20260728-0480`
- **Local interval:** `2026-07-28T22:19:13-07:00` to `2026-07-28T22:19:13-07:00`
- **UTC interval:** `2026-07-29T05:19:13+00:00` to `2026-07-29T05:19:13+00:00`
- **Action:** Staged only journal infrastructure paths, then ran the staged whitespace gate before producing staged stats/name-status.
- **Result:** RED, exit `2`, zero stderr. Staging itself completed, but `git diff --cached --check` flagged a blank line at EOF in the exact prologue and three exact event shards. Those blank boundaries are inherited bytes required to reconstruct the original SHA-256; deleting them would falsify the byte-preservation claim. Fail-fast prevented the later staged-scope displays.
- **Compact receipt:** stdout `426` bytes / `4` lines / SHA-256 `4d17b6d0a075aa6d8c6be66c2685f72cb990d70c797d984bba84114bc554b03b`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0481/` (local, ignored, retained through `2026-11-27`).
- **Disposition:** do not mutate historical bytes to appease a presentation-oriented whitespace heuristic. Mark immutable archive Markdown as non-diff payloads in repository attributes, then rerun both integrity and staged-scope gates.

### EJ-20260728-0482 — inspect existing byte-preservation Git attributes and staged state

- **Prior event:** `EJ-20260728-0481`
- **Local interval:** `2026-07-28T22:19:47-07:00` to `2026-07-28T22:19:47-07:00`
- **UTC interval:** `2026-07-29T05:19:47+00:00` to `2026-07-29T05:19:47+00:00`
- **Action:** Read the existing `.gitattributes` completely and inspected staged/unstaged scope after the failed whitespace gate.
- **Result:** GREEN, exit `0`, zero stderr. The repository already uses explicit `text eol=lf` rules for byte-deterministic fixtures/artifacts. Journal infrastructure is staged; the live journal has additional unstaged receipts; all Slice 4 source/test paths remain unstaged.
- **Compact receipt:** stdout `2061` bytes / `32` lines / SHA-256 `d6d63a96516e6e95902dc92162fb877d3ef26a899e1ed45d5d690074be209b62`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0482/` (local, ignored, retained through `2026-11-27`).
- **Decision:** add LF preservation and `-diff` only for immutable archive Markdown. The live journal, manifest, checker, and tests remain ordinary reviewable text.

### EJ-20260728-0483 — pass staged integrity, whitespace, and isolation gates

- **Prior event:** `EJ-20260728-0482`
- **Local interval:** `2026-07-28T22:20:20-07:00` to `2026-07-28T22:20:20-07:00`
- **UTC interval:** `2026-07-29T05:20:20+00:00` to `2026-07-29T05:20:20+00:00`
- **Action:** Staged `.gitattributes` plus the exact journal infrastructure set; reran reconstruction/global continuity and staged whitespace checks; captured staged stats/name-status and all unstaged/untracked paths.
- **Result:** GREEN, exit `0`, zero stderr. Checker sees `468` archived plus `14` live events through EJ-0482 with unchanged historical SHA-256. Staged whitespace passes without altering archive bytes. Exactly `16` intended infrastructure paths are staged. Slice 4 remains isolated as three unstaged modified paths plus untracked `secrets.py`.
- **Diff disposition:** archive Markdown displays as binary payloads by design; main journal reduction is `10027` removed lines with history relocated, not deleted. Overall staged delta: `825 insertions`, `9823 deletions`; all deleted historical payload bytes are reconstructed by the staged shards and manifest.
- **Compact receipt:** stdout `2773` bytes / `40` lines / SHA-256 `c82a083b501224c044d165626c884e9dcf54452e9c509d1e2d8d6918674a1bd6`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0483/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** restage this receipt, commit journal sharding as isolated substantive commit A, push, verify the public remote ref, then record finite commit B.

### EJ-20260728-0484 — create isolated journal-sharding substantive commit A

- **Prior event:** `EJ-20260728-0483`
- **Local interval:** `2026-07-28T22:20:59-07:00` to `2026-07-28T22:20:59-07:00`
- **UTC interval:** `2026-07-29T05:20:59+00:00` to `2026-07-29T05:20:59+00:00`
- **Action:** Restaged the latest live receipt, asserted exactly 16 staged paths and zero staged Slice 4 paths, rechecked staged whitespace, then ran `git commit -m "docs(neurips): shard execution journal"`.
- **Result:** GREEN, exit `0`, zero stderr. Commit A is `91ee45a943b9a418dc855b366b33262656dbd771`; parent `3655b52b6e90b96f4fb1d8b9a895a208c1f46f24`; tree `8720264e8a59d89e365918bb2ffa4354de74b1e7`. Commit reports `837 insertions`, `9823 deletions` across 16 intended files.
- **Compact receipt:** stdout `1637` bytes / `20` lines / SHA-256 `29cf3ee1bd6205a746e57c98304cf6b47774b0640ba42d974cb61deb1e71e747`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0484/` (local, ignored, retained through `2026-11-27`).
- **Scope:** commit A contains journal infrastructure only. Slice 4 remains in the working tree.
- **Next gate:** push commit A to the now-public branch and compare the remote ref exactly.

### EJ-20260728-0485 — push journal-sharding commit A and verify remote ref

- **Prior event:** `EJ-20260728-0484`
- **Local interval:** `2026-07-28T22:21:32-07:00` to `2026-07-28T22:21:34-07:00`
- **UTC interval:** `2026-07-29T05:21:32+00:00` to `2026-07-29T05:21:34+00:00`
- **Action:** Pushed `HEAD` to `refs/heads/codex/neurips-2026-empirical`, then queried that exact remote ref and compared it to commit A.
- **Result:** GREEN, exit `0`. GitHub advanced the branch from `3655b52` to `91ee45a`; expected and observed full SHA are both `91ee45a943b9a418dc855b366b33262656dbd771`.
- **Compact receipt:** stdout `100` bytes / `2` lines / SHA-256 `23326b1e85f90a88f588af88bcc84322c5ac4e969d0e74680821881aa927bcd5`; stderr `110` bytes / `2` lines / SHA-256 `5b1c8385dcfefefa9f5093f4fa2dad7961605b602a3463726cc1d48ccdefee67` (normal Git push progress).
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0485/` (local, ignored, retained through `2026-11-27`).
- **Public-state note:** because the repository is now public, commit A and its checker/shards are publicly retrievable on this branch.

### EJ-20260728-0486 — pre-record finite journal-only delivery commit B

- **Prior event:** `EJ-20260728-0485`
- **Delivery facts:** substantive commit A `91ee45a943b9a418dc855b366b33262656dbd771` is pushed and exactly observed at `origin/refs/heads/codex/neurips-2026-empirical`.
- **Planned B mechanics:** `git add -- docs/research/neurips-2026-workshop/33-execution-journal.md`; `git diff --cached --check`; `git commit -m "docs(neurips): record journal sharding delivery"`; `git push origin HEAD:refs/heads/codex/neurips-2026-empirical`.
- **Scope assertion:** B must contain only the live journal receipts EJ-0484 through EJ-0486. Slice 4 remains unstaged.
- **Self-reference break:** B's resulting SHA and push result cannot be embedded in B before Git content addressing creates it. Per the recording contract, these exact mechanics are exempt from an immediate recursive receipt and must be reconciled by the opening receipt of the next substantive work.
- **Next gate:** execute exactly the planned B mechanics, then resume Slice 4 by reconciling B and freshly verifying the remote ref before any Slice 4 command.

### EJ-20260728-0487 — reconcile journal-sharding delivery commit B

- **Prior event:** `EJ-20260728-0486`
- **Local interval:** `2026-07-28T22:22:36-07:00` to `2026-07-28T22:22:37-07:00`
- **UTC interval:** `2026-07-29T05:22:36+00:00` to `2026-07-29T05:22:37+00:00`
- **Action:** Reconciled the exempt B mechanics before resuming Slice 4: inspected HEAD identity/parent/tree/subject, queried the exact public remote branch, reran journal integrity, and inspected worktree scope.
- **Result:** GREEN, exit `0`, zero stderr. B is `453b0ec9e954d7f3c193d67e106502b1a26f0cfa`; parent A `91ee45a943b9a418dc855b366b33262656dbd771`; tree `71211841a12f25efc2ddfc3a9526bb10c8d3d9ff`; remote ref exactly equals B. Journal checker sees `468` archived plus `18` live events through EJ-0486. Only the four intended Slice 4 paths remain dirty.
- **B raw mechanics:** `build/research/neurips-2026-workshop/execution-journal/B-after-EJ-20260728-0486/`; exit `0`; stdout `121` bytes / `2` lines / SHA-256 `b5c2e6df605656900f3ecd0edcd2f9128a111e80310e39afae4abf34f692f1ec`; stderr `110` bytes / `2` lines / SHA-256 `4c935c770e98d982af22b59ca17e01a93694ff45723d33cb88a7dd2b39b231f0`.
- **Current compact receipt:** stdout `626` bytes / `10` lines / SHA-256 `a2284a456a886e829a8b97f9fcb56d43830279f0ea9684ff8cdb42b928d56235`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0487/` plus the B path above (local, ignored, retained through `2026-11-27`).
- **Next gate:** resume the paused complete Slice 4 source/test diff capture and hostile review.

### EJ-20260728-0488 — capture complete Slice 4 diff after journal/publication interruption

- **Prior event:** `EJ-20260728-0487`
- **Local interval:** `2026-07-28T22:23:23-07:00` to `2026-07-28T22:23:23-07:00`
- **UTC interval:** `2026-07-29T05:23:23+00:00` to `2026-07-29T05:23:23+00:00`
- **Action:** Captured the complete tracked Slice 4 diff plus the untracked `secrets.py` diff against `/dev/null`; emitted only compact stats/hashes to the console while retaining all `827` diff lines locally.
- **Result:** GREEN, exit `0`, zero stderr. Tracked delta is `458` insertions across package exports, assignment integration, and tests; `secrets.py` is `305` lines / `10339` bytes. File SHA-256 values: package init `4ffe3685...`; assignment `a35946f7...`; secrets `99d5f77b...`; tests `c5c8d59...`.
- **Compact receipt:** full diff stdout `28435` bytes / `827` lines / SHA-256 `0bda8c05a319d519e237dbecb59628aa04925857aa342041f2880351aa82427a`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0488/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** inspect the full secret-store implementation line-by-line, then turn hostile findings into tests before repairs.

### EJ-20260728-0489 — line-by-line raw inspection of secret-store implementation

- **Prior event:** `EJ-20260728-0488`
- **Local interval:** `2026-07-28T22:23:55-07:00` to `2026-07-28T22:23:55-07:00`
- **UTC interval:** `2026-07-29T05:23:55+00:00` to `2026-07-29T05:23:55+00:00`
- **Action:** Opened all `305` numbered lines of `secrets.py` for direct hostile review. This was an explicit raw inspection; the committed receipt contains only counts/hashes.
- **Result:** exit `0`, zero stderr. Review confirmed descriptor/path/owner/mode/link/purpose/context defenses and identified attack surfaces requiring cross-file confirmation: assignment consumption appears typed broadly enough to accept an unblind handle if the caller skips binding; no context-manager lifecycle exists despite the selected design; cleanup stops on the first descriptor-close error; binding inputs are not exact-type-checked before equality; handles remain attribute-mutable.
- **Compact receipt:** stdout `12474` bytes / `305` lines / SHA-256 `a36f62c71baa63ac1117d123d40738869be8b3734a270e975899bcc60c75c9e0`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0489/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** inspect the assignment integration and the exact tests around destination wiping, purpose rejection, and lifecycle before classifying these as defects.

### EJ-20260728-0490 — inspect assignment integration and Slice 4 behavioral tests

- **Prior event:** `EJ-20260728-0489`
- **Local interval:** `2026-07-28T22:24:53-07:00` to `2026-07-28T22:24:53-07:00`
- **UTC interval:** `2026-07-29T05:24:53+00:00` to `2026-07-29T05:24:53+00:00`
- **Action:** Opened the complete assignment integration diff plus contextual excerpts for every Slice 4 test involving reads, binding, unblind purpose, wiping, replacement, and close behavior.
- **Result:** exit `0`, zero stderr. The assignment wrapper validates/wipes the application buffer on every consumption failure. Tests intentionally use the shared master read for both nominal handle types, so union typing is deliberate; purpose separation is enforced by `_require_handle_binding` before future transaction use, not by the byte-read primitive. Malformed-length, reused, identity-changed, and close-invalidated handles all wipe the destination.
- **Remaining hostile findings:** lifecycle context-manager support is still absent; exact-type validation at the binding boundary can be strengthened; mutable handle internals and first-error cleanup are defense-in-depth issues rather than demonstrated authority bypasses under the stated non-hostile-process boundary.
- **Compact receipt:** stdout `23160` bytes / `666` lines / SHA-256 `87500a45bbce0f38a5cb24cb44828e663d96c80b1719494be087a331e357b40e`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0490/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** re-read the exact Slice 4 authority paragraph to distinguish required behavior from optional hardening, then add RED tests only for justified requirements.

### EJ-20260728-0491 — re-bind hostile findings to Slice 4 authority

- **Prior event:** `EJ-20260728-0490`
- **Local interval:** `2026-07-28T22:25:23-07:00` to `2026-07-28T22:25:23-07:00`
- **UTC interval:** `2026-07-29T05:25:23+00:00` to `2026-07-29T05:25:23+00:00`
- **Action:** Searched the immutable plan/design for every Slice 4 secret-store, lifecycle, no-follow, handle, and unblind requirement; retained broad contextual excerpts.
- **Result:** exit `0`, zero stderr. Authority requires the concrete store as the only opener; exact OS identity plus manifest/schedule/run-root/purpose registry binding; nominal non-subclassable purpose handles; repeated membership/unused checks; wrong-purpose/cross-context/copy/stale/reuse rejection; exact unbuffered 32-byte read plus overread; outer transaction wiping; and separate assignment/unblind derivation scopes. It does not explicitly require a context-manager protocol.
- **Disposition:** do not inflate Slice 4 API based on an earlier implementation preference. Exact-type binding hardening is directly aligned with cross-context rejection; cleanup and handle immutability remain defense-in-depth candidates. Inspect the plan's exact skeleton/acceptance block before tests.
- **Compact receipt:** stdout `49546` bytes / `354` lines / SHA-256 `94021226042be5d18685b67fe5e2597603eceae6d120db08ca56ff203d652003`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0491/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** read the narrow plan skeleton and Slice 4 acceptance criteria, not another broad grep.

### EJ-20260728-0492 — inspect exact Slice 4 skeleton and acceptance language

- **Prior event:** `EJ-20260728-0491`
- **Local interval:** `2026-07-28T22:25:55-07:00` to `2026-07-28T22:25:55-07:00`
- **UTC interval:** `2026-07-29T05:25:55+00:00` to `2026-07-29T05:25:55+00:00`
- **Action:** Read the narrow plan skeleton and its complete secret-store acceptance prose.
- **Result:** exit `0`, zero stderr. The accepted public skeleton exposes only `claim_assignment` and `claim_unblind`; context management is not part of it. Authority explicitly places total buffer cleanup in the later core transaction's outer `finally`, while Slice 4 owns concrete store opening, identity/purpose/context registry binding, nominal single-use handles, exact unbuffered read, and failure before draw/parse. Hostile Python already inside the trusted controller is explicitly out of scope.
- **Disposition:** do not add context-manager API, attribute-freezing machinery, or adversarial in-process equality defenses to this slice. They increase surface without closing an in-scope rejection argument. Existing behavior satisfies the skeleton; remaining review focuses on prohibited key propagation/logging, OS-source edge cases, and regressions.
- **Compact receipt:** stdout `4762` bytes / `127` lines / SHA-256 `39c6a645502430889b13174b96d8f0be25272569d97ae1e4e779d67be562ae94`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0492/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** statically scan Slice 4 source for forbidden key propagation, logging, serialization, argv/environment use, and public key-returning APIs.

### EJ-20260728-0493 — pass forbidden key-propagation and exception-surface scan

- **Prior event:** `EJ-20260728-0492`
- **Local interval:** `2026-07-28T22:26:58-07:00` to `2026-07-28T22:26:58-07:00`
- **UTC interval:** `2026-07-29T05:26:58+00:00` to `2026-07-29T05:26:58+00:00`
- **Action:** Scanned the full secret/assignment source for logging, printing, environment/argv access, JSON/pickle/subprocess use, and key/secret-return patterns; enumerated every exception, export, descriptor operation, registry access, and read site.
- **Result:** GREEN, exit `0`, zero stderr. No forbidden propagation candidate exists. Exceptions are constant/category messages or interpolate only the fixed field labels `run root` / `secret path`; no key bytes enter messages. Public exports are exactly the concrete store plus two opaque handle types. The sole key read is unbuffered `readinto` into caller-owned mutable storage followed by a one-byte overread.
- **Compact receipt:** stdout `4028` bytes / `84` lines / SHA-256 `04d10c3f4bed4c61b6774a54937331907242b52fe2c69651f61b96fc62b30017`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0493/` (local, ignored, retained through `2026-11-27`).
- **Hostile disposition:** no in-scope defect remains from the source audit. Defense-in-depth ideas that target already-compromised trusted-process Python are explicitly outside the design and are not smuggled into the public API.
- **Next gate:** rerun the exact Slice 4 focused command, then broaden to the full assignment module and repository suite.

### EJ-20260728-0494 — re-pass exact Slice 4 focused gate after hostile review

- **Prior event:** `EJ-20260728-0493`
- **Local interval:** `2026-07-28T22:27:29-07:00` to `2026-07-28T22:27:30-07:00`
- **UTC interval:** `2026-07-29T05:27:29+00:00` to `2026-07-29T05:27:30+00:00`
- **Action:** Ran the authority-prescribed `.venv/bin/python -m pytest tests/resampling_null/test_assignment.py -q -k t3_s04`.
- **Result:** GREEN, exit `0`, zero stderr: `19 passed, 61 deselected`.
- **Compact receipt:** stdout `114` bytes / `2` lines / SHA-256 `138da4f2e4e2d1c60a026ddf40f518195d7d36c7767975087c8a494ae51782d0`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0494/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** run all assignment tests without the slice selector.

### EJ-20260728-0495 — pass full assignment regression suite

- **Prior event:** `EJ-20260728-0494`
- **Local interval:** `2026-07-28T22:27:55-07:00` to `2026-07-28T22:27:56-07:00`
- **UTC interval:** `2026-07-29T05:27:55+00:00` to `2026-07-29T05:27:56+00:00`
- **Action:** Ran `.venv/bin/python -m pytest tests/resampling_null/test_assignment.py -q` without a slice selector.
- **Result:** GREEN, exit `0`, zero stderr: all `80` assignment tests passed.
- **Compact receipt:** stdout `179` bytes / `3` lines / SHA-256 `3fa77cd733a7cc4248276f5ba6a236a6b0f018fb0375e9629803f97341b05ce3`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0495/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** run the complete `tests/resampling_null/` package regression suite.

### EJ-20260728-0496 — pass complete resampling-null package suite

- **Prior event:** `EJ-20260728-0495`
- **Local interval:** `2026-07-28T22:28:24-07:00` to `2026-07-28T22:29:14-07:00`
- **UTC interval:** `2026-07-29T05:28:24+00:00` to `2026-07-29T05:29:14+00:00`
- **Action:** Ran `.venv/bin/python -m pytest tests/resampling_null/ -q`.
- **Result:** GREEN, exit `0`, zero stderr: all `382` resampling-null tests passed in `49.61 s`.
- **Compact receipt:** stdout `501` bytes / `7` lines / SHA-256 `e499419946e302ac5a6c215e6b9b2cd6b98a675462c043841e5b49dcd8f920bf`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0496/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** rerun both authority-prescribed static commands, then the repository-wide suite.

### EJ-20260728-0497 — pass authority-prescribed Ruff gate

- **Prior event:** `EJ-20260728-0496`
- **Local interval:** `2026-07-28T22:29:40-07:00` to `2026-07-28T22:29:40-07:00`
- **UTC interval:** `2026-07-29T05:29:40+00:00` to `2026-07-29T05:29:40+00:00`
- **Action:** Ran exact command `.venv/bin/python -m ruff check src/pneuma_lab/resampling_null tests/resampling_null`.
- **Result:** GREEN, exit `0`, zero stderr; all checks passed.
- **Compact receipt:** stdout `19` bytes / `1` line / SHA-256 `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0497/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** run the exact mypy command.

### EJ-20260728-0498 — pass authority-prescribed mypy gate

- **Prior event:** `EJ-20260728-0497`
- **Local interval:** `2026-07-28T22:30:04-07:00` to `2026-07-28T22:30:04-07:00`
- **UTC interval:** `2026-07-29T05:30:04+00:00` to `2026-07-29T05:30:04+00:00`
- **Action:** Ran exact command `.venv/bin/python -m mypy --ignore-missing-imports src/pneuma_lab/resampling_null`.
- **Result:** GREEN, exit `0`, zero stderr: no issues in five source files.
- **Compact receipt:** stdout `43` bytes / `1` line / SHA-256 `e317872697c2cbfdefa321527a6efe73290dff3a390b0fa8723b87092eccba6a`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0498/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** run the full repository test suite.

### EJ-20260728-0499 — repository-wide collection blocked by absent optional foundation dependency

- **Prior event:** `EJ-20260728-0498`
- **Local interval:** `2026-07-28T22:30:28-07:00` to `2026-07-28T22:30:30-07:00`
- **UTC interval:** `2026-07-29T05:30:28+00:00` to `2026-07-29T05:30:30+00:00`
- **Action:** Ran the standing full-suite command `.venv/bin/python -m pytest tests/ -q`.
- **Result:** INFRASTRUCTURE RED, exit `2`, zero stderr. Collection stopped with eight foundation-module import errors because optional `torch` is not installed. Every traceback terminates in the existing explicit error `pneuma_lab.foundation.core requires the optional foundation dependencies`; no Slice 4 module or assertion failed.
- **Scope:** this does not establish a green repository-wide suite. It also does not justify a heavyweight optional-foundation installation inside Task 3 Slice 4. The entire resampling-null package already passed `382/382`; run the full non-foundation suite next and preserve this limitation.
- **Compact receipt:** stdout `9716` bytes / `181` lines / SHA-256 `ab5251390d61ffb6ccd9c32147b5d592edcc5d4468d98c1886d717ac05c1187a`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0499/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** run all tests except the explicitly foundation-prefixed optional-dependency modules, then inspect final hashes/diff/staging.

### EJ-20260728-0500 — terminate optional broad suite and adopt 60-second test ceiling

- **Prior event:** `EJ-20260728-0499`
- **Local interval:** `2026-07-28T22:31:08-07:00` to `2026-07-28T22:41:32-07:00`
- **UTC interval:** `2026-07-29T05:31:08+00:00` to `2026-07-29T05:41:32+00:00`
- **Action:** Attempted the non-foundation repository suite, then sent SIGINT immediately when the user clarified that long broad tests are optional and every test invocation must run at most one minute.
- **Result:** USER-TERMINATED / RED, exit `2`, zero stderr after `10m24s`. Before interruption, pytest reached approximately `54%` and had already displayed three environment/artifact errors for absent ignored `build/research/neurips-p0/p0-power-report.json` plus two failures not promoted or triaged from the interrupted run. This command is not a verification pass and will not be rerun in broad form.
- **New standing rule:** default to focused/high-signal tests; wrap every future test process in a hard `60 s` wall-clock ceiling unless the user explicitly authorizes a longer run. A timeout is recorded as timeout, never silently treated as pass.
- **Compact receipt:** stdout `14218` bytes / `267` lines / SHA-256 `b507fdb8745bde931c642fc3056aafbadcc49237accbc809c1dfc8d7dc933dc6`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0500/` (local, ignored, retained through `2026-11-27`).
- **Slice 4 status:** unaffected: focused `19/19`, assignment `80/80`, resampling-null `382/382`, Ruff, and mypy are green. Proceed to final diff/staging rather than spending more time on unrelated broad tests.

### EJ-20260728-0501 — stage permanent 60-second test policy in isolation

- **Prior event:** `EJ-20260728-0500`
- **Local interval:** `2026-07-28T22:42:32-07:00` to `2026-07-28T22:42:32-07:00`
- **UTC interval:** `2026-07-29T05:42:32+00:00` to `2026-07-29T05:42:32+00:00`
- **Action:** Verified journal integrity and whitespace, reviewed the exact `AGENTS.md` policy diff, then staged only `AGENTS.md` and the live journal.
- **Result:** GREEN, exit `0`, zero stderr. The permanent rule is concise: broad/long suites optional, narrow high-signal tests preferred, every test process hard-capped at 60 seconds absent explicit user approval, and timeouts never called passes. Slice 4 remains fully unstaged.
- **Compact receipt:** stdout `1229` bytes / `25` lines / SHA-256 `0e2009443446216740938ab38b2ddaa9c2602f6946421203216896934ca60dfa`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0501/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** commit/push this user-directed policy separately, then resume the already-verified Slice 4 delivery.

### EJ-20260728-0502 — commit permanent test-duration policy as isolated A

- **Prior event:** `EJ-20260728-0501`
- **Local interval:** `2026-07-28T22:43:04-07:00` to `2026-07-28T22:43:04-07:00`
- **UTC interval:** `2026-07-29T05:43:04+00:00` to `2026-07-29T05:43:04+00:00`
- **Action:** Restaged the latest journal receipt, asserted exactly two staged paths, checked whitespace, and ran `git commit -m "docs: cap test commands at 60 seconds"`.
- **Result:** GREEN, exit `0`, zero stderr. Commit A `f384dfb88f1aaa6b3b048efe6e423782b3aeb34e`; parent `453b0ec9e954d7f3c193d67e106502b1a26f0cfa`; tree `4b53bf8e42590170f4f631777c398671675be26d`.
- **Compact receipt:** stdout `301` bytes / `6` lines / SHA-256 `fa38ec8183869d5b368be23089cfb77860f166d1d53990a8712015b11aff037e`; stderr `0` bytes / `0` lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0502/` (local, ignored, retained through `2026-11-27`).
- **Next gate:** push A, verify the public remote ref, then make the finite receipt B.

### EJ-20260728-0503 — push test-duration policy A and verify remote ref

- **Prior event:** `EJ-20260728-0502`
- **Local interval:** `2026-07-28T22:43:32-07:00` to `2026-07-28T22:43:34-07:00`
- **UTC interval:** `2026-07-29T05:43:32+00:00` to `2026-07-29T05:43:34+00:00`
- **Action:** Pushed A to the exact public working branch and compared its full SHA with `git ls-remote`.
- **Result:** GREEN, exit `0`. Expected and observed remote SHA both equal `f384dfb88f1aaa6b3b048efe6e423782b3aeb34e`.
- **Compact receipt:** stdout `100` bytes / `2` lines / SHA-256 `3a838aaa38cb7b54bd34161cb688080fdad9e9fa04522a9ae0d7b8a374095c87`; stderr `110` bytes / `2` lines / SHA-256 `5af657865e7926bccad4bd3fa9ebc10d3ecf8690fdabb2c5364b0d8d3691c01f`.
- **Raw evidence:** `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0503/` (local, ignored, retained through `2026-11-27`).

### EJ-20260728-0504 — pre-record finite test-policy receipt commit B

- **Prior event:** `EJ-20260728-0503`
- **Delivery facts:** policy commit A `f384dfb88f1aaa6b3b048efe6e423782b3aeb34e` is pushed and exactly observed at the public working branch.
- **Planned B mechanics:** `git add -- docs/research/neurips-2026-workshop/33-execution-journal.md`; `git diff --cached --check`; `git commit -m "docs: record test-duration policy delivery"`; `git push origin HEAD:refs/heads/codex/neurips-2026-empirical`.
- **Scope assertion:** B contains only EJ-0502 through EJ-0504. Slice 4 remains unstaged.
- **Self-reference break:** reconcile B SHA/push/remote at the next substantive opening receipt before any further Slice 4 command.
