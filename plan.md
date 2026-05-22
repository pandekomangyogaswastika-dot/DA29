# plan.md — Production & Maklon Overhaul (Lanjutan)

## Objectives
- ✅ **Phase 5 Vendor CMT Portal (V1 core)** sudah delivered: vendor bisa login, lihat job, submit progress (tersimpan ke `dewi_cmt_progress_reports` + akumulasi ke `dewi_cmt_jobs.progress_by_step`).
- ✅ **Phase 2 Internal Production Unification (V1 core)** sudah delivered:
  - WIP cutting tercatat di **single source of truth** `rahaza_material_stock` dengan `inventory_category=wip_internal`.
  - FG hasil penerimaan/packing CMT tercatat di `rahaza_material_stock` dengan `inventory_category=fg_internal` (bukan `rahaza_fg_inventory`).
- ✅ **Phase 6 Online Order Bridge / Fulfillment (V1 backend + core UI)** sudah delivered:
  - Fulfillment queue dari `marketing_orders` → allocate FG → pick → pack → dispatch.
  - Dispatch menurunkan FG stock (`rahaza_material_stock`) dan mencatat movement.
  - COGS posting terhubung ke `rahaza_posting.post_cogs_shipment()` (graceful bila HPP snapshot belum ada).
- ✅ **P0 Fix selesai**: akses modul gudang sudah OK (Fulfillment dan menu operasional gudang muncul sesuai section pills). Tidak ada lagi blocking issue akses sidebar.
- ✅ **P0 Enhancement selesai**: **Unified Inventory Viewer** lengkap (frontend+backend) termasuk **Stock Adjustment/Opname**.
- ✅ **P1 Enhancement selesai**: **Vendor Portal DO (Surat Jalan)**: list + detail dialog + confirm receipt.
- ✅ **Phase 7 Reporting & Dashboard** sudah delivered: harian, bulanan, per PO, actual vs target, trend + export CSV/Excel/PDF.
- ✅ Tidak ada regresi pada Phase 1–4 (Maklon PO/Seri, Dispatch, Finance GL) — sudah lulus regression test.

---

## Implementation Steps

### Phase 1 — POC Core Flow (Vendor Portal + Inventory Unification)
**Goal:** buktiin core workflow jalan end-to-end sebelum UI/fitur lengkap.

**POC-1: Vendor CMT Portal core** ✅ **COMPLETED**
- Backend ✅
  - Role `cmt_vendor` + linking user→`dewi_cmt_partners` via field `cmt_partner_id` pada JWT payload.
  - Seed demo endpoint: `POST /api/dewi/cmt/seed/vendor-demo`
    - 3 CMT partners + 3 user vendor (`vendor1@cmt.com` / `Vendor@123`, dst)
    - 5 `dewi_cmt_jobs` assigned ke partner
  - Verifikasi endpoint vendor ✅
    - `GET /api/dewi/cmt/vendor/my-jobs`
    - `POST /api/dewi/cmt/vendor/progress` (force `is_vendor_self_report=true`)
- Frontend (POC minimal) ✅
  - Route `/vendor-cmt`
  - Halaman login vendor
  - Halaman “My Jobs” (list + stats)
  - Modal submit progress (validasi qty)

**POC-2: Internal inventory unification core** ✅ **COMPLETED**
- Backend ✅
  - Patch `dewi_cmt_packing`:
    - Approve CMT receipt → FG masuk ke `rahaza_material_stock` dengan:
      - `inventory_category=fg_internal`, `ownership=cv_da`, `type=finished_goods`
      - Idempotent: update qty bila existing
  - Patch `dewi_cutting`:
    - Saat cutting batch status → `cut_done` → create WIP ke `rahaza_material_stock` dengan:
      - `inventory_category=wip_internal`, `ownership=cv_da`, `type=wip`
      - `material_id=WIP-{batch_code}`
      - Idempotent: skip bila WIP sudah ada

**Exit gate Phase 1:** ✅ **PASSED**
- Vendor login → lihat job → submit progress → masuk ke `dewi_cmt_progress_reports` + update `dewi_cmt_jobs.progress_by_step`.
- FG output dari packing/receiving tercatat di `rahaza_material_stock` (bukan collection lama).
- WIP terbentuk dari cutting saat `cut_done`.

---

### Phase 2 — V1 App Development (Phase 5)
**User stories (Phase 5 V1)** ✅ **DONE + Enhancement delivered**
1. ✅ Vendor CMT bisa login di portal khusus vendor.
2. ✅ Vendor CMT bisa melihat daftar job assigned beserta deadline dan qty.
3. ✅ Vendor CMT bisa mengirim laporan progress harian per proses.
4. ✅ Vendor CMT bisa melihat DO/SJ read-only dan detail per item.
5. ✅ Vendor CMT bisa **confirm receipt DO** untuk DO status `issued`.
6. ✅ Admin tetap bisa input progress (sudah ada di modul admin, dan flag vendor self-report tercatat).

**Implementation**
- Backend ✅
  - Auth/role guard vendor portal endpoints: vendor hanya akses job/DO miliknya (via `cmt_partner_id`).
  - DO vendor endpoints (read-only + confirm):
    - `GET /api/dewi/cmt/delivery-orders/vendor/my-dos`
    - `GET /api/dewi/cmt/delivery-orders/vendor/my-dos/{do_id}`
    - `POST /api/dewi/cmt/delivery-orders/vendor/my-dos/{do_id}/confirm-receipt`
- Frontend ✅
  - `frontend/src/components/vendor-cmt/VendorCMTPortalApp.jsx` + routing di `App.js`.
  - Dashboard stats + jobs list + dialog submit progress.
  - ✅ DO view:
    - Render DO list saat `activeView='dos'`
    - `DODetailContent` dialog: item table, status, tanggal, notes
    - Confirm receipt (jika status `issued`)

**Exit gate Phase 2:** ✅ **PASSED**
- Vendor portal usable untuk operasional dasar (lihat job, update progress) + DO monitoring.

---

### Phase 3 — V1 App Development (Phase 2 Internal Production)
**User stories (Phase 2 V1)** ✅ **DONE + Enhancement delivered**
1. ✅ Admin produksi bisa menutup cutting batch dan otomatis menambah stok WIP.
2. ✅ Admin gudang melihat FG masuk ke inventori FG terpadu (tanpa duplikasi collection).
3. ✅ Finance/owner: source of truth FG hanya satu (terpadu di `rahaza_material_stock`).
4. ✅ Admin bisa melihat WIP/FG/material dalam satu viewer.
5. ✅ Admin bisa melakukan **stock adjustment/opname** untuk inventory terpadu.

**Implementation**
- Backend ✅
  - Trigger `cut_done` → create WIP (`rahaza_material_stock`, `wip_internal`).
  - Unifikasi FG: `dewi_cmt_packing` approve → `rahaza_material_stock` (`fg_internal`).
  - ✅ Unified Inventory API (baru): `/app/backend/routes/unified_inventory.py`
    - `GET  /api/wms/stock/unified`
    - `GET  /api/wms/stock/unified/summary`
    - `POST /api/wms/stock/unified/adjust` (opname_increase/decrease/damage/correction; backend enforce sign)
    - `GET  /api/wms/stock/unified/adjustments`
- Frontend ✅
  - `/app/frontend/src/components/erp/UnifiedInventoryModule.jsx`
    - Filter by category/ownership/search
    - Movements dialog
    - Export CSV
    - ✅ StockAdjustmentDialog (opname)
  - Registrasi modul:
    - `moduleRegistry.js`: module id `unified-inventory`
    - `PortalShell.jsx`: sidebar Gudang → INVENTORI → Unified Inventory Viewer

**Exit gate Phase 3:** ✅ **PASSED**
- WIP/FG internal unified stock terbentuk dan bisa dipantau/di-adjust via UI.

---

### Phase 4 — Comprehensive Testing & Regression
**Testing scope** ✅ **COMPLETED**
- Phase 5:
  - Vendor auth + my-jobs + submit progress (frontend+backend) ✅
- Phase 2:
  - WIP creation saat `cut_done` ✅
  - FG unified stock saat approve CMT receipt ✅
- Regression:
  - Maklon PO create/confirm + AR invoice generation/linking ✅

**Exit gate Phase 4:** ✅ **PASSED**
- Tidak ada error 500/regresi fatal.

---

### Phase 5 — Phase 6 Online Order Bridge (Marketing → Fulfillment → Inventory FG)
**Goal:** Order marketplace masuk fulfillment queue → FG di-scan-out → stock turun → COGS terposting.

**Status:** ✅ **COMPLETED (Backend + Frontend accessible)**

**User stories (Phase 6 V1)**
1. ✅ Admin gudang bisa melihat antrian order yang perlu dipenuhi.
2. ✅ Admin gudang bisa allocate FG secara manual (pilih item/stock yang dipakai).
3. ✅ Admin gudang bisa menjalankan status flow: allocate → pick → pack → dispatch.
4. ✅ Saat dispatch: FG stock berkurang dan movement tercatat.
5. ✅ COGS posting: berjalan bila HPP snapshot tersedia; jika tidak ada, error tersimpan di `marketing_orders.cogs_error` (dispatch tetap sukses).
6. ✅ User bisa mengakses modul Fulfillment dari sidebar Gudang (via section pills “OPERASIONAL GUDANG”).

**Implementation**
- Backend ✅
  - File: `/app/backend/routes/fulfillment.py`
  - Endpoints:
    - `GET /api/fulfillment/summary`
    - `GET /api/fulfillment/queue`
    - `GET /api/fulfillment/orders/{id}`
    - `GET /api/fulfillment/inventory/available`
    - `POST /api/fulfillment/orders/{id}/allocate`
    - `POST /api/fulfillment/orders/{id}/pick`
    - `POST /api/fulfillment/orders/{id}/pack`
    - `POST /api/fulfillment/orders/{id}/dispatch` (reduce stock + post COGS + update order)
  - Integrasi inventory:
    - Allocate: `available_quantity -= qty`, `reserved_quantity += qty`
    - Dispatch: `quantity -= qty`, `reserved_quantity -= qty` + insert `rahaza_material_movements`
  - Integrasi finance:
    - Call `post_cogs_shipment()` dari `rahaza_posting.py`.
- Frontend ✅
  - File: `/app/frontend/src/components/erp/FulfillmentModule.jsx`
  - Registry: module id `fulfillment` sudah ditambahkan di `moduleRegistry.js`
  - Sidebar: item Fulfillment ada di `PortalShell.jsx` pada section "OPERASIONAL GUDANG"

**Exit gate Phase 5:** ✅ **PASSED**
- Backend flow allocate → pick → pack → dispatch lulus.
- Frontend modul bisa diakses dari sidebar Gudang.

---

### Phase 6 — Phase 7 Reporting & Dashboard
**Goal:** Laporan Harian, Bulanan, Per PO, Actual vs Target + dashboard chart dan export.

**Status:** ✅ **COMPLETED**

**Implementation**
- Backend ✅
  - File: `/app/backend/routes/dewi_phase7_reports.py`
  - Endpoints:
    - `GET /api/dewi/reports/daily?date=YYYY-MM-DD`
    - `GET /api/dewi/reports/monthly?year=YYYY&month=MM`
    - `GET /api/dewi/reports/po/{po_id}`
    - `GET /api/dewi/reports/actual-vs-target?period=YYYY-MM`
    - `GET /api/dewi/reports/production-trend?days=N`
    - `GET /api/dewi/reports/export/daily.csv?date=YYYY-MM-DD`
    - `GET /api/dewi/reports/export/monthly.csv?year=YYYY&month=MM`
- Frontend ✅
  - File: `/app/frontend/src/components/erp/Phase7ReportingModule.jsx`
  - Tabs:
    - Harian, Bulanan, Per PO, Actual vs Target, Trend
  - Charts: Recharts (LineChart, BarChart, PieChart)
  - Export:
    - CSV via backend endpoints
    - Excel via `xlsx`
    - PDF via `jsPDF` + `html2canvas`
  - Registrasi modul:
    - `moduleRegistry.js`: module id `phase7-reports`
    - `PortalShell.jsx`: sidebar Manajemen → RINGKASAN

**Exit gate Phase 6:** ✅ **PASSED**
- Laporan bisa ditarik dan diexport.

---

## Next Actions
1. ✅ **Roadmap selesai 100%** sesuai `/app/memory/PRODUCTION_MAKLON_DEVELOPMENT_PLAN.md`.
2. (Opsional) Hardening:
   - Tambahkan guard permission untuk stock adjustment (sudah ada `_require_admin`, tinggal align dengan role/perms produksi gudang di organisasi).
   - Tambahkan pagination di Unified Inventory list jika data membesar.
   - Tambahkan UI progress history per job di Vendor Portal (read-only).
3. (Opsional) Improvement pelaporan:
   - Tambah export PDF multi-page (saat tabel panjang)
   - Tambah filter vendor/klien pada laporan bulanan.

---

## Success Criteria
- ✅ Vendor CMT operasional: login, lihat jobs, update progress, lihat DO dan confirm receipt.
- ✅ FG inventory **tidak lagi terpecah**: FG internal tercatat di `rahaza_material_stock` dengan kategori tepat.
- ✅ Internal flow minimal: cutting `cut_done` membentuk WIP dan packing approve membentuk FG pada source of truth yang sama.
- ✅ Unified Inventory Viewer: monitoring WIP/FG/material + movements + export + stock adjustment.
- ✅ Phase 6 Fulfillment: order fulfillment end-to-end berjalan, stock turun, movement tercatat, COGS integration tersedia, UI accessible.
- ✅ Phase 7 Reporting: laporan harian/bulanan/per PO/actual vs target/trend + export CSV/Excel/PDF.
- ✅ Tidak ada regresi pada Maklon PO/Dispatch/Finance posting yang sudah selesai di Phase 1–4.

---

## Test Status (Ringkas)
- ✅ Backend + integrasi inventory/finance: lulus.
- ✅ Report testing: `/app/test_reports/iteration_13.json` (22/23 PASS; issue minor kredensial vendor pada test awal, sudah diklarifikasi: password benar `Vendor@123`).
- ✅ Seed vendor demo tersedia: `POST /api/dewi/cmt/seed/vendor-demo`.
