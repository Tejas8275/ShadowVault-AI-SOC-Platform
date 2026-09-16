# Screenshot capture checklist

Preparation only: no images or recordings have been captured by this phase. Use the [manual synthetic scenario](demo-guide.md) in a dedicated installation. No real investigation data or live-provider configuration is needed.

## Before capture

- [ ] Use a dedicated browser profile, close unrelated tabs and disable notifications/clipboard overlays.
- [ ] Use consistent legible desktop dimensions (for example1440×900), plus one separate mobile capture at390px. Keep captions/alt text accessible.
- [ ] Hide private terminals/environment files and pause before credential entry. Never capture token values, provisioning responses or developer tools.
- [ ] Verify every visible case/file/indicator is synthetic. Do not edit displayed counts, hashes, timestamps or responses to make the demo look populated.

## Required shots

- [ ] **Login/operator flow:** empty masked token input and guidance, then separately connected status. Capture neither typing nor clipboard. Explain in-memory token access, not password sessions.
- [ ] **Dashboard:** healthy connection and authorized case counts with the synthetic case. Keep live-count caveat; newest cases are not an activity feed.
- [ ] **Case workspace:** demo title, description, manually selected severity/status, revision and update time. This is the preferred hero.
- [ ] **Evidence upload:** show the resulting evidence details after the real synthetic collector upload. No browser upload wizard exists. Do not photograph credential-bearing CLI output or source paths. Caption selected-file CLI acquisition and server SHA-256 verification accurately.
- [ ] **Indicators:** show evidence relationship, source metadata, filter and original/corrected observation. Caption recorded indicators, not malicious verdicts.
- [ ] **Timeline:** show occurrence timestamps, provenance and source links. Explain manual investigator observations; keep recording-time distinctions.
- [ ] **Reports:** show case identity, draft/snapshot label and expanded citations. Text export is local and the report is transient, not a persisted final PDF.
- [ ] **AI boundary panel:** show advisory/no-raw-evidence guidance and truthful unavailable state. If using an existing deterministic test fixture separately, visibly label it “Synthetic deterministic provider — not a live model result.” Never relabel it Gemini/OpenAI output.
- [ ] **Optional custody/history:** capture each separately and explain its meaning. Retrieval records verified-copy preparation, not proof of delivery.

## After capture

- [ ] Review every frame at full resolution for credentials, local paths, identities, notifications and unrelated data. Discard and rotate any exposed credential; blur alone is not incident recovery.
- [ ] Crop for focus without removing safety disclosures or misleading the viewer about outcomes.
- [ ] Include accurate captions, synthetic-data labels, alt text and video transcript.
- [ ] Match publication assets to the current build; keep screenshots out of documentation until reviewed and actually present.
- [ ] Follow the channel-specific [publication checklist](release-checklist.md). Capture does not authorize posting, release or hosting.
