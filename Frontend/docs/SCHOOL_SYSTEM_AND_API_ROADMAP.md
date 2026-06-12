# School management domain & API roadmap

This document describes how the **current frontend** maps to a **school operations** model (students, classes, courses, payments, commission, teachers, audit) and what the backend can implement **later** without changing existing UI routes or screens.

**Scope:** The app is being used as a **school / training center** system, not a generic e-commerce product catalog. Some **legacy names** remain in code (`Product`, `/products`) for historical reasons; behaviour in UI is already school-oriented where noted below.

---

## 1. Module map (screen → domain)

| Screen / route | Domain purpose | Primary data concept today (`app/types`) | HTTP surface today (`app/utils/api`) |
|----------------|----------------|------------------------------------------|--------------------------------------|
| `/` Dashboard | KPIs / overview | Mixed dashboard composables | Varies |
| `/category` | **Program/category** taxonomy | `Category` | `GET/POST/PUT/DELETE /categories` |
| `/courses` | **Course catalogue** (template: name, schedule fields) | `Course` | `GET/POST/PUT/DELETE /courses` |
| `/allclass` | **Classes** offered (sections), enrollment wizard, invoices | `Product` (“class listing”) | `GET /products-view`, `GET/POST/PUT/DELETE /products`, enrollments via `GET /products/:id/enrollments` |
| `/allstudent` | **Student registry** | Same row shape reused as `Product` + student fields | `GET /products-view`, mutates via `/products` |
| `/report` | **Sales / enrollment report** lines | `ReportRow` | `GET /reports-view`, export `/reports-view/export` |
| `/comission` | **Commission** by seller/teacher lines | `ComissionEntry` | `GET /commission-view` |
| `/finance` | **Finance** summary rows | `FinanceEntry` | `GET /finance-view`, `PUT /finance-view/:id` |
| `/history` | **Audit / action log** | `AuditLog` | `GET /histories` |
| `/settings/user-management` | **Users** (staff) | `SystemUser` | `GET/POST/PUT/DELETE /users` |
| `/settings/role-management` | **Roles & page access** | `SystemRole` | `GET/POST/PUT/DELETE /roles` |

**Note:** `/history` is permission-gated (`history:view`) but may not appear in the sidebar menu; deep link `/history` still applies.

---

## 2. Legacy naming (do not confuse with “shop” UX)

| Code / path | Intended school meaning |
|-------------|-------------------------|
| `Product` type, `/products`, `/products-view` | **Class offering** and/or **student row** persistence (backend may split into true `classes` + `students` later; UI unchanged). |
| Stock fields (`inStock`, `sold`, …) on same type | Often repurposed as **capacity / enrolled counts** for classes. |
| `ReportRow.customer`, `seller` | **Student payer** vs **seller/teacher/agent** depending on invoice model. |

Normalizers (`mapProductViewStudentRow`, `mapReportViewRow`, `mapCommissionViewRow`) already adapt common API aliases; extend those when backend stabilizes field names.

---

## 3. Permissions (already in frontend)

Defined in `app/utils/auth/permissions.ts` and matched to routes in `app/utils/auth/routes.ts`. Backend should:

- Issue JWT (or session) with `pageAccess` / permission strings compatible with `PERMISSIONS.*`.
- Enforce the same rules server-side for every mutating and sensitive read endpoint.

---

## 4. Recommended API evolution (backend), UI paths unchanged

Below, **“keep path”** means the frontend continues calling the existing URL until you deliberately version; **“alias optional”** means you can introduce `/students` etc. behind a gateway that still proxies old paths.

### 4.1 Core academic structure

| Resource | Suggested REST (new) | Current FE path (keep for compatibility) |
|----------|----------------------|--------------------------------------------|
| Categories | `GET/POST/PUT/DELETE /api/v1/categories` | `/categories` |
| Courses | `GET/POST/PUT/DELETE /api/v1/courses` | `/courses` |
| Classes (sections tied to course/category/teacher) | `GET/POST/PUT/DELETE /api/v1/classes` | Can remain `/products` or parallel implement + proxy |
| Students | `GET/POST/PUT/DELETE /api/v1/students` | Can remain `/products-view` list + `/products` CRUD or dedicated paths |
| Enrollments | `GET /api/v1/classes/:classId/enrollments` (+ filters `dateFrom`/`dateTo`) | `/products/:id/enrollments` |

### 4.2 Commercial / reporting

| Resource | Suggested REST | Current FE |
|----------|----------------|------------|
| Report lines | `GET /api/v1/reports/sales-lines` (+ `page`, `search`, `dateFrom`, `dateTo`, `product` filter) | `/reports-view` |
| CSV export | `GET .../export` | `/reports-view/export` |
| Commission lines | `GET /api/v1/commissions` | `/commission-view` |
| Finance rows | `GET` + `PATCH/PUT` line | `/finance-view` |

### 4.3 Staff & access control

| Resource | Suggested REST | Current FE |
|----------|----------------|------------|
| Users | CRUD users, assign roles | `/users` |
| Roles | CRUD roles + `pageAccess[]` | `/roles` |

### 4.4 Audit / history (“track all actions”)

| Capability | Suggested REST | Current FE |
|------------|----------------|------------|
| Immutable audit log | `GET /api/v1/audit-logs` with filters (`typeAction`, user, date range, entity type/id) | `/histories` |

**Backend checklist for audit:**

- Write **after** successful mutations (create/update/delete) on categories, courses, classes, students, enrollments, payments, finance, roles, users.
- Store: actor user id, timestamp, action, entity type, entity id, optional JSON `metadata`.
- Optionally correlate with reporting (same `invoiceNo` keys as `ReportRow`).

---

## 5. Query parameters the UI already sends

Shared shape: `ApiQueryParams` (`page`, `limit`, `sortBy`, `sortOrder`, `search`, `dateFrom`, `dateTo`, …).

Implement these on list endpoints backend-side for pagination, global date filter (header), and search.

---

## 6. What we are **not** changing now

- No changes to **Vue pages, components, or layout** as part of this roadmap document.
- Implementing new REST resources is **backend work**; the frontend can keep current URLs until you add a thin BFF or change `app/utils/api/index.ts` in a follow-up task.

---

## 7. Suggested next step (engineering)

1. Backend: define OpenAPI for the tables in section 4, keeping response shapes compatible with existing `app/types` (or version + update mappers only).
2. Enable **audit middleware** on all mutating routes.
3. Optionally split `Product` into `Class` + `Student` in the API while keeping **response mapping** so the UI file tree stays the same.

This file is the single reference for “school system + API later” aligned with **current** Domnak Frontend behaviour.
