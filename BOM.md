# Software Bill of Materials (SBOM)

**Project:** SOC Incident Response Evidence & Timeline Reporter  
**Repository:** `aircooledcafe/incident-reporter`  
**Architecture:** Decoupled React 19 SPA + Django 5.1 REST API + SQLite3 (WAL Mode)  
**Date Generated:** 2026-11-11  

---

## 1. Summary of Dependencies

| Category | Component Count | Primary Licenses |
|---|---|---|
| **Backend Direct Dependencies (Python)** | 6 | BSD-3-Clause, MIT, Apache-2.0 / LGPL-2.1+, HPND |
| **Backend Transitive Dependencies (Python)** | 3 | BSD-3-Clause, PSFL |
| **Frontend Direct Dependencies (Production)** | 6 | MIT, ISC |
| **Frontend Development Dependencies (Build)** | 2 | MIT |
| **Container & OS Base Images** | 3 | Python / Debian, Alpine / Node, Alpine / Nginx |
| **System / Native C Libraries** | 2 | IJG, zlib |

---

## 2. Backend Dependencies (Python)

### 2.1 Direct Dependencies (`backend/requirements.txt`)

| Package | Version | License | Purpose / Role |
|---|---|---|---|
| **Django** | `5.1.14` | BSD-3-Clause | Core web framework, ORM, database migrations, authentication (`auth_user`), session management (`django_session`), and Django Admin interface. |
| **djangorestframework** | `3.17.2` | BSD-3-Clause | REST API framework, request validation serializers, API viewsets, and token-based authentication (`authtoken_token`). |
| **django-cors-headers** | `4.9.0` | MIT | Cross-Origin Resource Sharing (CORS) header handling for API requests from the React frontend SPA. |
| **odfpy** | `1.4.1` | Apache-2.0 / LGPL-2.1+ / GPL-2.0+ | Generation and manipulation of OpenDocument Format (`.odt`) files for incident executive report exports. |
| **pillow** | `13.0.0` | HPND / MIT-CMU | Image processing library for user avatar uploads, screenshot validation, and aspect ratio/thumbnail handling. |
| **gunicorn** | `23.0.0` | MIT | Production WSGI HTTP application server running Django behind Docker and Nginx. |

### 2.2 Transitive / Sub-Dependencies (Python Runtime)

| Package | Version | License | Direct Parent | Purpose |
|---|---|---|---|---|
| **asgiref** | `3.12.1` | BSD-3-Clause | `Django` | Asynchronous Server Gateway Interface (ASGI) specs and async-to-sync adapters. |
| **sqlparse** | `0.6.0` | BSD-3-Clause | `Django` | Non-validating SQL parser used by Django for SQL formatting and schema migrations. |
| **defusedxml** | `0.7.1` | Python Software Foundation (PSFL) | `odfpy` | XML bomb protection and entity-expansion vulnerability mitigations for OpenDocument parsing. |
| **sqlite3** | `3.40+` | Public Domain | Python standard library | Embedded relational database engine configured in WAL mode (`journal_mode=WAL;`). |

---

## 3. Frontend Dependencies (JavaScript / Node.js)

### 3.1 Direct Production Runtime Dependencies (`frontend/package.json`)

| Package | Requested | Resolved (Lockfile) | License | Purpose / Role |
|---|---|---|---|---|
| **react** | `19.2.6` | `19.2.6` | MIT | Core UI component model and reactive rendering engine. |
| **react-dom** | `19.2.6` | `19.2.6` | MIT | DOM rendering and browser mount targets for React 19. |
| **react-bootstrap** | `2.10.10` | `2.10.10` | MIT | React UI component library (modals, dropdowns, forms, cards, tabs, responsive grids). |
| **bootstrap** | `^5.3.3` | `5.3.8` | MIT | Base CSS framework, LevelBlue dark theme foundation, and layout classes. |
| **lucide-react** | `^1.16.0` | `1.59.0` | ISC | UI iconography (terminals, shields, locks, tags, timeline icons, chevron menus). |
| **@restart/hooks** | `0.4.16` | `0.4.16` | MIT | React utility hooks for overlay positioning, dropdown triggers, and DOM event handling. |

### 3.2 Development & Build Dependencies (`frontend/package.json`)

| Package | Requested | Resolved (Lockfile) | License | Purpose / Role |
|---|---|---|---|---|
| **vite** | `^6.3.0` | `6.4.4` | MIT | Next-generation frontend tooling, dev server with HMR, and production asset bundler. |
| **@vitejs/plugin-react** | `^5.0.0` | `5.2.0` | MIT | Babel and React Fast Refresh support for Vite. |

### 3.3 Key Transitive Build Tooling

| Package | Version | License | Purpose |
|---|---|---|---|
| **esbuild** | `0.25.0` | MIT | High-performance JavaScript/TypeScript bundler & minifier powering Vite. |
| **rollup** | `4.34.8` | MIT | Production module bundler and tree-shaking compiler inside Vite. |
| **@babel/core** | `7.29.7` | MIT | JavaScript compiler and JSX transformer used by `@vitejs/plugin-react`. |

---

## 4. Container & Infrastructure Dependencies

### 4.1 Base Container Images (`Dockerfile` & `docker-compose.yml`)

| Image | Base OS | Layer / Stage | Purpose |
|---|---|---|---|
| **`python:3.12-slim`** | Debian 12 (Bookworm) | Backend Container | Minimal CPython runtime for Django, Gunicorn, and SQLite. |
| **`node:22-alpine`** | Alpine Linux | Frontend (Build Stage) | Node.js 22 LTS environment for installing dependencies and compiling React SPA with Vite. |
| **`nginx:1.27-alpine`** | Alpine Linux | Frontend (Runtime) | Lightweight Nginx web server for static SPA assets and reverse proxy (`/api`, `/artifacts`, `/admin`). |

### 4.2 System Native Libraries (Installed via `apt` in `backend/Dockerfile`)

| Package | License | Purpose |
|---|---|---|
| **`libjpeg62-turbo-dev`** | IJG License | JPEG codec support required for Pillow avatar and screenshot decoding. |
| **`zlib1g-dev`** | zlib License | Compression library required for PNG/DEFLATE processing in Pillow. |

---

## 5. Storage & Persistence Layout

| Store | Technology | Path / Location | Purpose |
|---|---|---|---|
| **Relational Database** | SQLite3 (`PRAGMA journal_mode=WAL;`) | `./data/db.sqlite3` (`/data/db/db.sqlite3` in container) | Accounts, role profiles, active sessions, API tokens, investigations, timeline events, and escalation contacts. |
| **File Artifacts** | Host Filesystem / Mapped Volume | `./artifacts` (`/data/artifacts` in container) | User avatars, per-investigation evidence folders, screenshots, PCAP files, and generated `.odt`/`.csv`/`.zip` exports. |

---

## 6. License Compliance Overview

All direct and transitive runtime dependencies in this project use standard, permissive open-source licenses:
- **MIT / BSD-3-Clause / ISC**: Permissive licenses allowing commercial use, distribution, and modification with attribution.
- **Apache-2.0 / LGPL-2.1+ / PSFL**: Permissive / weak-copyleft libraries (`odfpy`, `defusedxml`) used strictly as runtime utilities without requiring proprietary modifications or copyleft contamination.
- **Public Domain**: SQLite database engine.
