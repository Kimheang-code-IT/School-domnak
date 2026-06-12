# PDME-Revenue Operations Management Platform

**PDME-Revenue** is an advanced, enterprise-grade frontend platform designed for Customs and Excise Cambodia management systems. 

## Technology Stack

The application has been engineered for maximum scalability, adhering to modern best practices:
- **Core Engine:** Nuxt 4, Vue 3, Composition API
- **UI Framework & Styling:** Nuxt UI v3 (Pro features enabled), TailwindCSS v4
- **State Management:** Pinia
- **Tables & Grids:** TanStack Vue Table v8
- **Data Visualization:** Apache ECharts
- **Internationalization:** `@nuxtjs/i18n` with support for English (`en`) and Khmer (`km`). Advanced typography overrides ensure "Siemreap" is injected for optimal Khmer rendering.

## Current Architectural State

The UI is entirely decoupled from the backend. 
- All component views strictly consume data from `app/composables/table/` and state logic. 
- All default mock datasets are located in `app/data/` representing exactly what the API JSON schema should return. This guarantees a highly accelerated transition phase when plugging into a live backend server.
- The UI leverages a generic, unified `CommonAppExport` capability to allow instant `.csv` extractions for all data components based on a custom global Date-Range filter.

## Future Improvement & API Roadmap
1. **Backend Fetch Integration:** Replace statically imported `app/data/` objects with `useAsyncData()` or `$fetch()` queries inside the composables to hydrate tables directly from your database endpoints.
2. **Server-Side Rendering/Pagination:** Upgrade TanStack tables configuration to pass `page`, `limit`, and `sorting` parameters explicitly to the API rather than filtering local arrays when arrays scale past 10,000 entries.
3. **Authorization Routing:** Incorporate `middleware/auth.global.ts` to strictly lock administrative pages (e.g. `/settings`) requiring JWT Bearer token authentication via `NuxtAuth`.
4. **Zod Validation:** Formally introduce robust client-side validation logic utilizing Zod to provide schema definitions for the various Create/Update modals before transmission to APIs.

## API-First Frontend Policy

- Frontend should not own authoritative business logic, pricing rules, or persistent CRUD rules.
- `app/data/*` files are temporary mock sources only until backend endpoints are ready.
- New feature work should use API clients in `app/utils/api/` and `useApi()` wrapper.
- Toggle backend mode with:
  - `NUXT_PUBLIC_USE_BACKEND_API=true`
  - `NUXT_PUBLIC_API_BASE=http://your-api-host/api`

---

## Setup & Development

Make sure to install the dependencies:

```bash
pnpm install
```

Start the development server on `http://localhost:3000`:

```bash
pnpm dev
```

## Production

Build the application for production:

```bash
pnpm build
```

Locally preview production build:

```bash
pnpm preview
```
