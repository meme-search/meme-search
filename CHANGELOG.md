# Change Log

All notable changes to this project will be documented in this file.

## [Unreleased]

Local description generation:

- Fixed the image-to-text service reloading model weights from disk for every
  image. The selected model is now loaded once and reused across jobs; a model
  switch in Settings releases the old model before loading the new one.
- Added `MODEL_IDLE_TIMEOUT` (seconds, default `300`, `0` keeps the model
  loaded) to release the model's RAM or GPU memory after the queue has been
  idle that long.

This change does not touch the database schema, the job queue, or the Search
API contract.

## [2.3.2] - 2026-08-04

Dependency and CI maintenance:

- Updated the image-to-text runtime floor to PyTorch 2.13, bitsandbytes 0.50,
  and psutil 7.2.2, with the image-to-text test suite passing on the combined
  dependency set.
- Updated Ruby OpenSSL to 4.0.2, SimpleCov to 1.0.3, the frontend test
  dependencies, and GitHub Actions Python setup to v7.
- Fixed the image-to-text Ruff workflow so its component-specific configuration
  and source path are honored instead of linting unrelated repository files.

This patch does not change the database schema or Search API contract. See the
[v2.3.2 release and upgrade notes](docs/releases/v2.3.2.md).

## [2.3.1] - 2026-07-30

Docker startup reliability:

- Fixed a transient fresh-install race when the web and jobs containers run
  `db:prepare` concurrently while PostgreSQL is enabling pgvector.
- The Rails server and job-worker entrypoints now retry database preparation up
  to five times with a two-second delay. Persistent preparation failures still
  stop the container with a nonzero exit instead of hiding the error.
- Added deterministic entrypoint coverage for transient recovery, retry
  exhaustion, both application processes, and commands that do not prepare the
  database.

This patch does not change the database schema or Search API contract. See the
[v2.3.1 release and upgrade notes](docs/releases/v2.3.1.md).

## [2.3.0] - 2026-07-30

Search beyond the web app:

- **Search API v1**: Added a documented, stable, additive, and permanently
  read-only `/api/v1` contract for keyword and vector search, meme metadata,
  tags, and authenticated original-media retrieval.
- **Scoped API tokens**: Added hashed, expiring, individually revocable tokens
  with separate `search:read` and `media:read` permissions.
- **Local CLI**: Added a dependency-free Python client for searching collections,
  producing human-readable or JSON results, and safely fetching media.
- **Chromium popup**: Added an experimental unpacked browser extension for
  loopback search, explicit copy, and download actions. It is not published to
  an extension store.
- **Integration readiness**: Added an OpenAPI 3.1 contract, shared
  client-conformance fixtures, security and migration coverage, and an optional
  UI-independent relevance evaluator.
- **Documentation and demos**: Published the
  [Search API guide](docs/search-api.md), a
  [browser-playable app-and-CLI demo](https://meme-search.neonwatty.com/#integrations),
  and [issue #197](https://github.com/neonwatty/meme-search/issues/197) for
  coordinating community-built integrations.

Security and upgrade notes:

- Official support remains loopback-only. API bearer tokens protect `/api/v1`;
  they do not authenticate the web UI or settings, and direct public exposure
  remains unsupported.
- Clients should use one least-privilege token per integration and must not
  connect directly to PostgreSQL, internal Docker services, or the meme
  filesystem.
- The release adds the `api_tokens` table. Back up the database before
  upgrading and follow the
  [v2.3.0 release and upgrade notes](https://github.com/neonwatty/meme-search/releases/tag/v2.3.0).

## [2.0.0] - 2025-11-03

Testing infrastructure and quality improvements:

- **Playwright E2E Testing**: Complete migration from Capybara to Playwright
  - 16 E2E tests with 100% passing rate (vs 13/15 with Capybara)
  - Zero flakiness (vs 13% flakiness rate with Capybara)
  - Better debugging with traces and time-travel inspector
  - Page Object Model pattern for improved maintainability
  - Full CI/CD integration with browser caching
- **Rails 8 Upgrade**: Updated from Rails 7.2 to 8.0.4 with optimized configuration
- **Development Tools**: Added mise for consistent development environment (Ruby 3.4.2, Python 3.12, Node 20)
- **Testing Infrastructure**: New rake tasks for E2E test database management
- **Code Cleanup**: Removed Capybara and Selenium dependencies (614 lines of code removed)
- **Documentation**: Comprehensive testing documentation in `playwright/README.md` and `CLAUDE.md`

Technical improvements:
- Enhanced CI pipeline with Playwright browser caching (saves 1-2 minutes per run)
- Test database seeding for isolated E2E tests
- Detailed test coverage comparison documentation

## 2025-2-15

Quality of life updates to the Pro version including:

- you can now [customize hosts names and ports](https://github.com/neonwatty/meme-search/tree/main?tab=readme-ov-file#custom-hosts-and-ports) for easier usage with NAS, Portainer, Unraid, or if you just need to customize! 
- 4 new image to text new models added ranging in size from 200M to 2B parameters: florence-2-base (new default), florence-2-large, smolvlm-256, smolvlm-500
- new model selection panel added in the pro app Settings so you select or change your image-to-text model
- moondream2 to current revision
- new test database added to image-to-text service for more comprehensive testing
- new [local docker compose files added](https://github.com/neonwatty/meme-search/tree/main?tab=readme-ov-file#building-the-app-locally-with-docker) for easier local building and testing
- gh action test and build scripts refactored for easier (local) testing


## 2025-1-30

Quality of life updates to the Pro version of Meme Search, including:

- bugfixes in the image-to-text service that makes cancelling failed jobs more reliable
- new custom ports / hosts options to more easily run the pro app with tools like Unraid and Portainer, or if you need to run its services on different ports / hosts
- new local build compose file for building and testing locally `docker-compose-pro-local-build.yml`
- new `grid view` in both home and search pages for a broader view of your memes (see animation below)

<p align="center">
<img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme-search-grid-view-medium.webp" height="225">
</p>

Administrative updates including:

- new github actions for building and pushing the pro app and image-to-text module images to the github container registry
- weights have been removed from the image-to-text image for a smaller image size

## 2024-11-08

New Pro Version 1.0 Release!

The Pro version of Meme Search introduces the following new features:

1.  **Auto-Generate Meme Descriptions**

    Target specific memes for auto-description generation (instead of applying to your entire directory).

2.  **Manual Meme Description Editing**

    Edit or add descriptions manually for better search results, no need to wait for auto-generation if you don't want to.

3.  **Tags**

    Create, edit, and assign tags to memes for better organization and search filtering.

4.  **Faster Vector Search**

    Powered by Postgres and pgvector, enjoy faster keyword and vector searches with streamlined database transactions.

5.  **Keyword Search**

    Pro adds traditional keyword search in addition to semantic/vector search.

6.  **Directory Paths**

    Organize your memes across multiple subdirectories—no need to store everything in one folder.

7.  **New Organizational Tools**

    Filter by tags, directory paths, and description embeddings, plus toggle between keyword and vector search for more control.

## 2024-07-24

Version 1.1.3 released with a range of great updates to docker version of app

- Ability to use Nvidia GPU inside Docker Container added to compose file + other helpful cleanup from @thijsvanloef
- new action for docker build / docker-compose now pulls image from ghcr repo by default thanks to @jasonyang-ee
- docker build size roughly cut in half thanks to staged build commit by @StroescuTheo

## 2024-07-17

### Added

- Core tests added for query, imgs modules, add images re-indexing, remove image re-indexing

- A new "refresh index" button has been introduced to update the index when images are added or removed from the data/input image directory, affecting only the newly added or removed images.

<p align="center">
<img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme_search_refresh_button.gif" height="200">
</p>
