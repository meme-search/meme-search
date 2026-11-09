# A Meme Search Engine built to self-host in Python, Ruby, and Docker

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-7289da?style=flat&logo=discord&logoColor=white)](https://discord.gg/7xsxU4ZG6A)

Use AI to index your memes by their content and text, making them easily retrievable for your meme warfare pleasures.

By default, processing from image-to-text extraction, to vector embedding, to search is performed locally. You can also use an OpenAI-compatible vision API for description generation while keeping embeddings and search local.

Visit the [Meme Search project site](https://meme-search.neonwatty.com/) for a visual feature overview, or continue below for installation and configuration details.

> **Search beyond the web app.** Meme Search now includes a documented,
> token-authenticated [Search API v1](docs/search-api.md), a
> [dependency-free local CLI](integrations/cli/README.md), and an
> [experimental unpacked Chromium popup](integrations/browser-extension/README.md).
> The API is read-only and officially supported on loopback; it also gives
> community integrations a stable boundary that does not expose your database.

[Watch the 16-second app-and-CLI demo](https://meme-search.neonwatty.com/#integrations).

  <p align="center">
    <img src="https://github.com/user-attachments/assets/0529764f-a009-4e17-8947-63c7c96075a5"
  alt="meme-search-2.0-demo">
  </p>
  
This repository contains the services and web app for indexing, searching, and retrieving your memes with semantic and keyword search.

## Quick start

```sh
git clone https://github.com/meme-search/meme-search.git
cd meme-search
docker compose up
```

Open <http://localhost:3000>, then drag, drop, or paste images on the upload page. The first local description generation downloads the selected model, so it takes longer than later generations.

The web UI binds to `127.0.0.1` by default because it does not include user
authentication. Official support is loopback-only for API v1 and the included
clients. API bearer tokens protect only the versioned integration
endpoints; they do not protect the web UI or settings. Direct public exposure
is unsupported. Proxy/VPN operation is advanced and unsupported; its
authentication, TLS, and network controls are entirely the operator's
responsibility.

A table of contents for the remainder of this README:

- [Meme search](#meme-search)

  - [Features](#features)
  - [Requirements](#requirements)
  - [Installation instructions](#installation-instructions)
  - [Time to first generation / downloading models](#time-to-first-generation--downloading-models)
  - [Index your memes](#index-your-memes)
  - [Search API and local integrations](#search-api-and-local-integrations)
  - [Custom bind address and app port](#custom-bind-address-and-app-port)
  - [Building the app locally with Docker](#building-the-app-locally-with-docker)
  - [Running tests](#running-tests)
- [Discord server](#discord-server)
- [Changelog](#changelog)
- [Feature requests and contributing](#feature-requests-and-contributing)


## Meme search

### Features

<p align="center">
  <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
    <figure>
      <img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme-search-pro-search-example.gif" height="225">
      <figcaption>Search</figcaption>
    </figure>
    <figure>
      <img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme-search-pro-edit-example.gif" height="225">
      <figcaption>Edit</figcaption>
    </figure>
    <figure>
      <img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme-search-pro-filters-example.gif" height="225">
      <figcaption>Filter</figcaption>
    </figure>
    <figure>
      <img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme-search-generate-example.gif" height="225">
      <figcaption>Generate</figcaption>
    </figure>
    <figure>
      <img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme-search-2.0-bulk.gif" height="225">
      <figcaption>Bulk Generation</figcaption>
    </figure>
    <figure>
      <img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme-search-2.0-dark-mode.gif" height="225">
      <figcaption>Dark Mode</figcaption>
    </figure>
    <figure>
      <img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme-search-2.0-rescan.png" height="225">
      <figcaption>Rescan</figcaption>
    </figure>
    <figure>
      <img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme-search-2.0-rescan-show.png" height="225">
      <figcaption>Rescan Status</figcaption>
    </figure>
    <figure>
      <img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme-search-2.0-rescan-options.png" height="225">
      <figcaption>Rescan Options</figcaption>
    </figure>
    <figure>
      <img align="center" src="https://github.com/neonwatty/readme_gifs/blob/main/uploads-trimmed.gif" height="225">
      <figcaption>Drag-and-Drop Upload</figcaption>
    </figure>
  </div>
</p>

Features of Meme Search include:

1. **Multiple Image-to-Text Models**

   Choose the right size image to text model for your needs / resources - from small (~200 Million parameters) to large (~2 Billion parameters).

   Current available image-to-text models for Meme Search include the following, starting with the default model:

   - [Florence-2-base](https://huggingface.co/microsoft/Florence-2-base) - a popular series of small vision language models built by Microsoft, including a 250 Million (base) and a 700 Million (large) parameter variant. \*This is the default model used in Meme Search\*.
   - [Florence-2-large](https://huggingface.co/microsoft/Florence-2-large) - the 700 Million parameter vision language model variant of the Florence-2 series
   - [SmolVLM-256](https://huggingface.co/collections/HuggingFaceTB/smolvlm-256m-and-500m-6791fafc5bb0ab8acc960fb0) - a 256 Million parameter vision language model built by Hugging Face
   - [SmolVLM-500](https://huggingface.co/collections/HuggingFaceTB/smolvlm-256m-and-500m-6791fafc5bb0ab8acc960fb0) - a 500 Million parameter vision language model built by Hugging Face
   - [Moondream2](https://huggingface.co/vikhyatk/moondream2) - a 2 Billion parameter vision language model used for image captioning / extracting image text
   - [Moondream2-INT8](https://huggingface.co/vikhyatk/moondream2) - INT8 quantized version of Moondream2 for memory-constrained hardware. Reduces memory from ~5GB to ~1.5-2GB with minimal quality loss. Ideal for CPU-only machines.

2. **Auto-Generate Meme Descriptions**

   Target specific memes for auto-description generation (instead of applying to your entire directory).

3. **Manual Meme Description Editing**

   Edit or add descriptions manually for better search results, no need to wait for auto-generation if you don't want to.

4. **Tags**

   Create, edit, and assign tags to memes for better organization and search filtering.

5. **Fast Vector Search**

   Powered by Postgres and pgvector, enjoy faster keyword and vector searches with streamlined database transactions.

6. **Directory Paths**

   Organize your memes across multiple subdirectories—no need to store everything in one folder.

7. **New Organizational Tools**

   Filter by tags, directory paths, and description embeddings, plus toggle between keyword and vector search for more control.

8. **Bulk Description Generation**

   Generate descriptions for multiple memes at once for faster indexing.

9. **Dark Mode**

   Toggle between light and dark themes for comfortable viewing in any environment.

10. **Directory Rescan**

   Automatically detect and index new memes added to your directories.

11. **Drag-and-Drop Upload**

   Upload memes directly through the web interface with drag-and-drop and clipboard paste support. Files are stored in the `direct-uploads` directory (configurable via Docker volume mount) and automatically scanned for indexing. Supports JPG, PNG, WEBP, and GIF formats with bulk upload (up to 50 files), real-time progress tracking, and automatic duplicate filename handling. Animated GIFs remain animated when displayed; descriptions and search indexing use the first frame.

### Requirements

**For Docker deployment** (recommended):
- Docker and Docker Compose

**For local development**:
- Ruby 3.4.2
- Rails 8.0.4
- Python 3.12
- Node.js 20 LTS
- PostgreSQL 17 with pgvector extension

We recommend using [mise](https://mise.jdx.dev/) for managing Ruby, Python, and Node.js versions. See [CLAUDE.md](CLAUDE.md) for detailed setup instructions.

### Installation instructions

From the repository root, start the server cluster with Docker Compose:

```sh
docker compose up
```

This pulls and starts containers for the app, database, Solid Queue job worker, and local auto description generator. The app runs on port `3000` and is available locally at:

```sh
http://localhost:3000
```

The Compose files store app data in local bind-mounted directories so upgrades keep using the same files:

- `./meme_search/db_data/meme-search-db` for Postgres data
- `./meme_search/direct-uploads` for drag-and-drop uploads
- `./meme_search/db_data/image_to_text_generator` for generator queue data
- `./meme_search/models` for model downloads

Most Docker installations create missing bind-mount directories automatically. Some Docker frontends, including Synology Container Manager, require the directories to exist before startup.
Compose also runs a short setup container at startup to make the upload directory writable by the non-root Rails containers, so the configured upload path may be owned by UID/GID `1000` after the first run.

If you want these persistent files visible on a NAS path, set the storage path variables in `.env` or directly in your Compose UI:

```sh
MEME_SEARCH_DB_PATH=/volume1/docker/meme-search/db
MEME_SEARCH_DIRECT_UPLOADS_PATH=/volume1/docker/meme-search/direct-uploads
MEME_SEARCH_GENERATOR_DB_PATH=/volume1/docker/meme-search/image-to-text-db
MEME_SEARCH_MODELS_PATH=/volume1/docker/meme-search/models
```

For Docker frontends that require bind-mount directories to exist first, create them before starting:

```sh
mkdir -p ./meme_search/db_data/meme-search-db ./meme_search/direct-uploads ./meme_search/db_data/image_to_text_generator ./meme_search/models
mkdir -p /volume1/docker/meme-search/db /volume1/docker/meme-search/direct-uploads /volume1/docker/meme-search/image-to-text-db /volume1/docker/meme-search/models
```

To start the app alone pull the repo and cd into the `meme_search/meme_search/meme_search_app`. Once there execute the following to start the app in development mode

```sh
./bin/dev
```

When doing this ensure you have an available Postgres instance running locally on port `5432`.

**Note Linux users:** you may need to add the following `extra_hosts` to your `meme_search` service for inter-container communication

```sh
extra_hosts:
    - "host.docker.internal:host-gateway"
```

### Time to first generation / downloading models

The first auto generation of description of a meme takes longer than average, as image-to-text model weights are downloaded and cached. Subsequent generations are faster.

The local generator keeps the loaded model in memory between descriptions and releases it after 5 idle minutes. Set `MODEL_IDLE_TIMEOUT` in `.env` to change that (seconds, `0` keeps the model loaded); see the [image to text generator README](meme_search/image_to_text_generator/README.md#model-memory).

You can download additional models in the settings tab of the app.

### Description generation providers

Meme Search supports two providers for automatic meme descriptions:

- `IMAGE_DESCRIPTION_PROVIDER=local` uses the bundled Python `image_to_text_generator` service. This is the default and keeps description generation local.
- `IMAGE_DESCRIPTION_PROVIDER=openai` calls an OpenAI-compatible `/chat/completions` vision API directly from Rails. In this mode the Python generator service is not required.

Descriptions from every provider are normalized to the app's description length limit before saving. Bulk generation queues durable Solid Queue background jobs for external providers so the web request does not wait on one API request per image.

When an external provider is selected, images chosen for description generation are sent to the configured API endpoint. Embeddings, metadata, and search remain local.

For OpenAI-compatible mode, set these environment variables in your `.env` file:

```sh
IMAGE_DESCRIPTION_PROVIDER=openai
OPENAI_API_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your_api_key
OPENAI_VISION_MODEL=gpt-4o-mini
```

Then start Rails, the Solid Queue worker, and the database without the Python generator:

```sh
docker compose -f docker-compose.yml -f docker-compose.openai.yml up meme_search meme_search_jobs meme_search_db
```

To smoke-test a real OpenAI-compatible call before starting a bulk run, run this from the Rails app directory:

```sh
cd meme_search/meme_search_app
OPENAI_API_KEY=your_api_key mise exec -- bin/smoke_openai_description
```

The smoke test uses the first indexed sample image that exists under `public/memes`, runs the same job/provider path as background generation, and rolls back database changes after the API call succeeds.

For local inference mode, keep the default `docker compose up` command so the `image_to_text_generator` service starts and can access the same meme volumes as Rails.

### Index your memes

You can index your memes by creating your own descriptions, or by generating descriptions automatically, as illustrated below.

<img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme-search-generate-example.gif" height="225">

To start indexing your own memes, first adjust the [compose file](https://github.com/meme-search/meme-search/blob/main/docker-compose.yml) by adding `volume` mount to the `meme_search` and `image_to_text_generator` services to properly connect your local meme subdirectory to the app.

For example, if suppose (one of your) meme directories was called `new_memes` and was located at the following path on your machine: `/local/path/to/my/memes/new_memes`.

To properly mount this subdirectory to the `meme_search` service adjust the `volumes` portion of its configuration to the following:

```yaml
volumes:
  - ./meme_search/memes/:/app/public/memes # <-- example meme directory from the repository
  - /local/path/to/my/memes/new_memes/:/rails/public/memes/new_memes # <-- personal meme collection - must be placed inside /rails/public/memes in the container
```

Note: your `new_memes` directory must be mounted internally in the `/rails/public/memes` directory, as shown above.

To properly mount this same subdirectory to the `image_to_text_generator` service adjust the `volumes` portion of its configuration to the following:

```yaml
volumes:
  - ./meme_search/memes/:/app/public/memes # <-- example meme directory from the repository
  - /local/path/to/my/memes/new_memes/:/app/public/memes/new_memes # <-- personal meme collection - must be placed inside /app/public/memes in the container
...
```

Note: your `new_memes` directory must be mounted internally in the `/app/public/memes` directory, as shown above.

If you are concerned about the application altering your existing meme library, as a precaution you can make the mount read only by adding "ro" to the volume line as follows:

```yaml
volumes:
  - ./meme_search/memes/:/app/public/memes # <-- example meme directory from the repository
  - /local/path/to/my/memes/new_memes/:/app/public/memes/new_memes:ro
...
```

Read-only mounts can be indexed and searched, but the Delete action in the web UI cannot remove their source files. The UI reports a clear error and keeps the database record when the mount is not writable.

Now restart the app, and register the `new_memes` via the UX by traversing to the `settings -> paths -> create new` as illustrated below.  Type in `new_memes` in the field provided and press `enter`.

<img align="center" src="https://github.com/jermwatt/readme_gifs/blob/main/meme-search-add-new-memes.webp" height="225">

Once registered in the app, your memes are ready for indexing / tagging / etc.,!

### Search API and local integrations

Search, inspect metadata, and fetch authorized media through the stable,
read-only `/api/v1` contract—without giving clients PostgreSQL credentials,
Docker-network access, schema knowledge, or filesystem paths.

- Follow the [Search API guide](docs/search-api.md) for scoped-token setup,
  endpoint examples, the OpenAPI contract, upgrade steps, security boundaries,
  demos, and troubleshooting.
- Search and fetch from a terminal with the
  [dependency-free Python CLI](integrations/cli/README.md).
- Search from an [experimental unpacked Chromium popup](integrations/browser-extension/README.md).
- Measure UI-independent search behavior with the optional, non-gating
  relevance evaluator documented in the API guide.
- Propose a local client or conversation workflow in
  [community integration issue #197](https://github.com/meme-search/meme-search/issues/197).

API v1 is officially supported only on loopback and is permanently read-only.
Its bearer tokens do not authenticate the web UI or settings, so do not expose
the app directly to a public network.

### Model downloads

The image-to-text models used to auto generate descriptions for your memes are all open source, and vary in size.

### Custom bind address and app port

Easily customize the app's port to more easily use the it with tools like [Unraid](https://unraid.net/?srsltid=AfmBOorvWvSZbCHKnqdR__AcllotnsLR6did_FhAaNfUowqqU2IprD1v) or [Portainer](https://www.portainer.io/), or because you already have services running on the default `meme_search` app port `3000`.

To customize the bind address or main app port, copy `.env.example` to `.env` in the repository root and adjust:

```sh
APP_BIND_ADDRESS=127.0.0.1
APP_PORT=3000
```

This value is automatically detected and loaded into each service via the Compose files. The Postgres service is only exposed on Docker's internal network, so app containers always talk to it at `meme-search-db:5432`.

Changing `APP_BIND_ADDRESS` away from loopback is advanced and unsupported. A
trusted LAN is not an authentication boundary, and API tokens do not protect
the web UI or settings. If an operator chooses to use a private VPN or
authenticated TLS reverse proxy, that operator owns the full configuration and
security review. Direct public exposure remains unsupported.

Rails rejects unrecognized `Host` headers to prevent DNS rebinding. Advanced
reverse proxies must opt an exact hostname into the comma-separated
`MEME_SEARCH_ALLOWED_HOSTS` setting. Wildcards, URLs, ports, and CIDR ranges are
rejected. Allowing a host does not authenticate the web UI or make non-loopback
exposure supported.

### Building the app locally with Docker

Docker images are built manually before a release because multi-platform model builds are resource intensive. The release workflow verifies both `latest` images carry the exact release commit revision before it creates versioned tags, preventing a Git tag from pointing at images built from different source.

Maintainers should follow the [`RELEASING.md`](RELEASING.md) checklist.

To build the app - including all services defined in the `docker-compose.yml` file - locally run the local compose file at your terminal as

```sh
docker compose -f docker-compose-local-build.yml up --build
```

For multi-platform builds (AMD64 + ARM64) and pushing to GitHub Container Registry, use the local build script:

```sh
bash scripts/build_and_push.sh
```

This will build the docker images for the app, database, and auto description generator, and start the app at `http://localhost:3000`.

### Running tests

To run tests locally pull the repo and cd into the `meme_search/meme_search/meme_search_app` directory. Install the required gems as

```sh
bundle install
```

Tests can then be run as

```sh
bash run_tests.sh
```

When invoking this app-local script directly, ensure PostgreSQL with pgvector
is available through the Rails database configuration. The root `npm test`
runner instead provisions an isolated loopback-only test database unless
`DATABASE_URL` is supplied.

Run linting tests on the `/app` subdirectory as

```sh
rubocop app
```

to ensure the code is clean and well formatted.

#### Running CI Locally (Optional)

You can run the complete GitHub Actions CI workflow locally using [act](https://github.com/nektos/act):

```bash
# Install act (macOS)
brew install act

# Run all CI jobs
act --container-architecture linux/amd64 -P ubuntu-latest=catthehacker/ubuntu:act-latest

# Run specific job
act -j pro_app_unit_tests --container-architecture linux/amd64 -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

This validates your changes match CI before pushing to GitHub.

#### Docker E2E Tests (Local Validation Only)

**Docker E2E tests validate the complete microservices stack** (Rails + Python + PostgreSQL) in isolated Docker containers. These tests run against fresh Docker builds and test cross-service communication, webhooks, and production-like deployment.

**Current Status**: 6/7 smoke tests passing (85% coverage) - see `playwright-docker/README.md` for details

```bash
# Run all Docker E2E tests
npm run test:e2e:docker

# Run with UI mode (recommended for debugging)
npm run test:e2e:docker:ui
```

**What these tests cover**:
- Complete image processing pipeline (Rails → Python → Rails webhooks)
- Vector search with embedding generation
- Keyword search functionality
- Concurrent processing and job queueing
- Embedding refresh operations

**Important**: These tests **DO NOT run in CI** due to Docker build time (~10-15 minutes) and resource requirements. **Contributors MUST run these tests locally** before submitting PRs that affect:
- Docker configurations
- Cross-service communication
- Image-to-text generation workflow
- Embedding generation

See `playwright-docker/README.md` for comprehensive documentation.

## Discord server

Join our Discord server [![Discord](https://img.shields.io/badge/Discord-Join%20Server-7289da?style=flat&logo=discord&logoColor=white)](https://discord.gg/7xsxU4ZG6A) to discuss new features, bug fixes, and other open source projects (like [ytgify](https://chromewebstore.google.com/detail/ytgify/dnljofakogbecppbkmnoffppkfdmpfje) - a browser extension for clipping GIFs from YouTube right from the YT Player!).

## Changelog

Meme Search is under active development! See the `CHANGELOG.md` in this repo for a record of the most recent changes.

## Feature requests and contributing

Feature requests and contributions are welcome!

See [the discussion section of this repository](https://github.com/meme-search/meme-search/discussions) for suggested enhancements to contribute to or weigh in on.

Please see [`CONTRIBUTING.md`](CONTRIBUTING.md) for setup, testing, and contribution guidance. Security-sensitive reports should follow [`SECURITY.md`](SECURITY.md) instead of being filed publicly.

Below is a nice diagram of the repo [generated using gitdiagram](https://github.com/ahmedkhaleel2004/gitdiagram), laying out its main components and interactions.

```mermaid
flowchart TD
    %% Global Entities
    User["User"]:::user

    %% Docker & Compose Orchestration
    Docker["Docker & Compose Orchestration"]:::docker

    %% Main Services
    Rails["Rails Meme Search Application"]:::rails
    Python["Image-to-Text Generator (Python)"]:::python
    DB["PostgreSQL Database (with pgvector)"]:::database

    %% Shared File Volumes Subgraph
    subgraph "Shared Meme Files"
        PublicMemes["Public Memes"]:::volume
        MemeDir["Meme Directory"]:::volume
    end

    %% Interactions
    User -->|"interaction"| Rails
    Rails -->|"DBQueryUpdate"| DB
    Rails -->|"APIRequest"| Python
    Python -->|"APIResponse"| Rails

    %% Volume Access
    Rails ---|"VolumeMountAccess"| PublicMemes
    Python ---|"VolumeMountAccess"| MemeDir

    %% Docker Orchestration Links
    Docker ---|"orchestrates"| Rails
    Docker ---|"orchestrates"| Python
    Docker ---|"orchestrates"| DB

    %% Click Events
    click Rails "https://github.com/meme-search/meme-search/tree/main/meme_search/meme_search_app"
    click Python "https://github.com/meme-search/meme-search/tree/main/meme_search/image_to_text_generator"
    click DB "https://github.com/meme-search/meme-search/blob/main/meme_search/meme_search_app/config/database.yml"
    click Docker "https://github.com/meme-search/meme-search/blob/main/docker-compose.yml"
    click PublicMemes "https://github.com/meme-search/meme-search/tree/main/meme_search/meme_search_app/public/memes"
    click MemeDir "https://github.com/meme-search/meme-search/tree/main/meme_search/memes"

    %% Styles
    classDef user fill:#fceabb,stroke:#d79b00,stroke-width:2px;
    classDef rails fill:#c8e6c9,stroke:#388e3c,stroke-width:2px;
    classDef python fill:#bbdefb,stroke:#1976d2,stroke-width:2px;
    classDef database fill:#ffe082,stroke:#f9a825,stroke-width:2px,stroke-dasharray: 5 5;
    classDef docker fill:#d1c4e9,stroke:#673ab7,stroke-width:2px,stroke-dasharray: 3 3;
    classDef volume fill:#ffcdd2,stroke:#e53935,stroke-width:2px,stroke-dasharray: 2 2;
```
