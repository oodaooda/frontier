# Milestone Todo: RSS Feeds, Settings & Backup
Milestone ID: `M007`
Status: `planned`
Owner: Frontier
Linked PR(s): TBD
Release tag: TBD

## Goal

Add automated RSS feed polling for model release news, a settings page for API keys and configuration, and database backup functionality.

## Spec Reference
- `docs/specs/M001_benchmark-platform_prd.md`

## Phase A: RSS Feed Polling
- [ ] RSS feed parser (feedparser library)
- [ ] Feed sources configuration in database:
  - Anthropic blog: `https://www.anthropic.com/research/rss`
  - OpenAI blog: `https://openai.com/blog/rss`
  - Google AI blog RSS
- [ ] Keyword filtering: surface posts mentioning "model", "vision", "document", "release", "API", "benchmark"
- [ ] Background polling: check feeds on configurable interval (default: every 6 hours)
- [ ] Auto-create News/Intel entries from matching feed items
- [ ] Mark auto-created entries as "Needs Evaluation" by default
- [ ] De-duplication: don't re-add entries that already exist
- [ ] Manual "Check Now" button on News page
- [ ] Unit tests for feed parsing and keyword filtering
- [ ] Commit checkpoint after Phase A

## Phase B: Settings Page
- [ ] Settings page in web UI
- [ ] API key management: view (masked), set, test connection for each provider
- [ ] Model configuration: add/edit/remove models, set pricing
- [ ] Rendering settings: default DPI, text DPI
- [ ] RSS feed management: add/remove feeds, set polling interval, manage keywords
- [ ] Port configuration display (informational, requires restart)
- [ ] Store settings in database (override config.yaml at runtime)
- [ ] Commit checkpoint after Phase B

## Phase C: Database Backup
- [ ] Backup button on settings page: copies frontier.db to backups/ with timestamp
- [ ] Auto-backup before destructive operations (delete document, delete run)
- [ ] List existing backups with restore option
- [ ] Configurable backup retention (default: keep last 10)
- [ ] Commit checkpoint after Phase C

## Phase D: Tests
- [ ] Unit tests for RSS parsing with mock feed data
- [ ] Unit tests for settings CRUD
- [ ] Unit tests for backup/restore
- [ ] Playwright tests: settings page, RSS entries appearing on News page
- [ ] Commit checkpoint after Phase D

## Release Gate
- [ ] All Phase A-D checkboxes complete
- [ ] RSS feeds polling and creating News entries automatically
- [ ] Settings page functional for API keys and model config
- [ ] Backup/restore working
- [ ] Playwright tests passing
- [ ] Add changelog entry
- [ ] Merge to `main`
