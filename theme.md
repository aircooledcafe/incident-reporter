# SOC Investigations — Theme & Color System

This document outlines the LevelBlue-inspired dark theme and color palette used across the **SOC Investigations** web application.

---

## 1. Browser & Chrome Theming

The application sets the browser tab, header, and system chrome styling to match the top navigation bar.

| Target | Hex / Value | Description |
|---|---|---|
| `<meta name="theme-color">` | `#091834` | Controls browser tab / title bar background color (Arc, Safari, Chromium mobile/desktop) |
| `<meta name="msapplication-TileColor">` | `#091834` | Windows tile color |
| Navbar Gradient | `linear-gradient(90deg, #001338 0%, #091834 100%)` | Top application navigation bar |
| Global Background | `#060b17` | Full-page background color (`--lb-bg-deep`) |

---

## 2. Core Color Tokens (CSS Variables)

Defined in [`frontend/src/App.css`](frontend/src/App.css):

| CSS Variable | Hex Code | Swatch / Usage |
|---|---|---|
| `--lb-bg-deep` | `#060b17` | Global canvas / page background |
| `--lb-navy-dark` | `#001338` | Navbar gradient start, active project sidebar highlight |
| `--lb-card-bg` | `#0c1528` | Cards, modals, dropdown menus, table background |
| `--lb-subbox-bg` | `#080f1e` | Inner section sub-boxes, project list items, user trigger |
| `--lb-border` | `#1e2d4a` | Borders, dividers, card outlines |
| `--lb-blue` | `#3564F3` | Primary brand blue, action buttons, active tab indicators |
| `--lb-blue-hover` | `#2043B0` | Hover state for primary action buttons |
| `--lb-cyan` | `#0096b3` | Accent borders, focus rings, hover glow |
| `--lb-lime` | `#9CEF69` | Highlighted timeline evidence, active "Investigating" status badge |
| `--lb-text-primary` | `#f1f5f9` | Primary readable text, titles, headings |
| `--lb-text-secondary`| `#cbd5e1` | Secondary labels, descriptions, inactive tabs |
| `--lb-text-muted` | `#94a3b8` | Timestamps, metadata, subtle hints |

---

## 3. Surface & Elevation Hierarchy

| Level | Background Hex | Border Hex | Description |
|---|---|---|---|
| **Canvas** | `#060b17` | None | Base page background (`--lb-bg-deep`) |
| **Auth Canvas** | Radial gradient `#0b1c3d` to `#060b17` | None | Dedicated login / registration backdrop |
| **Cards & Panels** | `#0c1528` | `#1e2d4a` | Primary card surfaces (`--lb-card-bg`) |
| **Card Headers** | `rgba(0, 19, 56, 0.75)` | `#1e2d4a` | Frosted dark navy card top header |
| **Sub-boxes / Insets** | `#080f1e` | `#1e2d4a` | Inner panels, nested containers (`--lb-subbox-bg`) |
| **Code / Terminal Blocks** | `#040811` | `#1e2d4a` | Raw logs, commands, and multi-select input containers |
| **Dropdown Menus** | `#0c1528` / `#0b1426` | `#1e2d4a` / `#0096b3` | Floating option lists & user menu |

---

## 4. Buttons & Interactive States

| Element | Background | Border | Text | Hover / Focus |
|---|---|---|---|---|
| **Primary Button** (`.btn-lb-primary`) | `#3564F3` | `#3564F3` | `#ffffff` | Background: `#2043B0` |
| **Green CTA** (`.btn-lb-green`) | `#16a34a` | `#16a34a` | `#ffffff` | Background: `#15803d` ("New Investigation") |
| **Cyan Outline** (`.btn-lb-cyan`) | Transparent | `#0096b3` | `#38bdf8` | Background: `rgba(0, 150, 179, 0.18)` |
| **Form Controls** | `#040811` | `#1e2d4a` | `#f1f5f9` | Focus: `#060d1b`, Border: `#0096b3`, Glow: `rgba(0, 150, 179, 0.22)` |
| **Active Nav Tab** | `#0c1528` | `#1e2d4a` | `#ffffff` | Top border: `2px solid #3564F3` |
| **Interactive Rows** | Transparent | — | — | Hover: `rgba(0, 150, 179, 0.12)` |
| **Key Timeline Evidence** | `rgba(53, 100, 243, 0.1)` | Left: `3px solid #9CEF69` | — | Starred timeline entries |

---

## 5. Status Badges & Accents

### Investigation Statuses
| Status | Badge Classes / Styling | Visual Appearance |
|---|---|---|
| `OPEN` (Triage) | `border-secondary text-lb-cyan` | Slate border with bright sky cyan text (`#38bdf8`) |
| `INVESTIGATING` | `border-lb-lime text-lb-lime` | Neon lime border & text (`#9CEF69`) |
| `AWAITING_CUSTOMER` | `border-secondary text-lb-cyan` | Slate border with bright sky cyan text (`#38bdf8`) |
| `CONTAINED` | `border-secondary text-lb-cyan` | Slate border with bright sky cyan text (`#38bdf8`) |
| `ARCHIVED` (Closed) | `bg-secondary text-light` | Muted dark slate background |

### User Role Badges
| Role | Badge Style | Color |
|---|---|---|
| `SUPER_ADMIN` | `bg-danger text-white` | Red (`#dc3545`) |
| `ADMIN` | `btn-lb-primary` | LevelBlue Primary (`#3564F3`) |
| `ANALYST` | `bg-info text-dark` | Cyan / Sky Blue (`#0dcaf0`) |
| `EXECUTIVE` | `bg-secondary text-light` | Muted Slate (`#6c757d`) |

### Escalation Contact Tiers
| Tier | Badge Style | Meaning |
|---|---|---|
| Primary | `bg-danger text-white` | Primary contact (High urgency) |
| Secondary | `bg-warning text-dark` | Secondary contact |
| Tertiary | `bg-info text-dark` | Tertiary / general escalation |

---

## 6. Favicon & Branding Assets

Located in `frontend/assets/`:
- `terminal_64.png` (64×64) — Standard desktop favicon
- `terminal_128.png` (128×128) — High-DPI icon
- `terminal_256.png` (256×256) — High-resolution application icon
- `terminal_512.png` (512×512) — PWA / Apple Touch Icon
