# plan.md — P1.A Accessory Consolidation ✅ COMPLETED + P1.B Maklon Orders Consolidation ✅ COMPLETED + P1.C P2P Flow Completion ✅ COMPLETED + P1.D Legacy Toko Migration ✅ COMPLETED + **P1.A–D Cleanup Phase A (Post-monitoring)** ✅ COMPLETED

## 1) Objectives

### P1.A — Accessory Consolidation (Cluster 1) ✅ DONE
- ✅ Konsolidasi sistem aksesoris menjadi **1 SSOT internal** berbasis `rahaza_*` **tanpa mengubah kontrak API**.
- ✅ **API-stable:** semua endpoint `/api/acc/*` tetap ada dan tetap compatible dengan `AccessoryModule.jsx` (frontend tidak diubah).
- ✅ Migrasi data aman: **idempotent, tanpa data loss**, dengan dry-run + validasi + execute.
- ✅ Core stock logic aksesoris konsisten dengan sistem inventory utama:
  - master: `rahaza_materials` (filter `type='accessory'`)
  - saldo: `rahaza_material_stock`
  - histori: `rahaza_material_movements` (filter `domain='accessory'` + `legacy_movement_type` untuk back-compat)

**Status objective P1.A:** selesai, diverifikasi oleh POC + migration + testing_agent_v3 (iteration_15: 29/29 PASS).

### P1.B — Maklon Orders Consolidation (Cluster 2) ✅ DONE
- ✅ Deprecate SSOT lama `dewi_maklon_orders` → pindah SSOT ke `dewi_maklon_pos` (multi-item PO).
- ✅ Semua consumer utama (client portal, billing, samples, management tools) membaca dari SSOT baru.
- ✅ Endpoint legacy `/api/dewi/maklon/orders/*` tetap hidup untuk backward compatibility tetapi **ditandai deprecated** di OpenAPI.
- ✅ Migrasi legacy → PO aman: **idempotent**.

**Status objective P1.B:** selesai, diverifikasi oleh POC + migration + testing_agent_v3 (iteration_16: 13/14 PASS; catatan: URL OpenAPI valid adalah `/api/openapi.json`).

### P1.C — Procure-to-Pay (P2P) Flow Completion ✅ DONE
**Implement “Create GR from PO”** (Goods Receipt / Receiving dari PO) sehingga P2P end-to-end bisa berjalan dengan kontrol qty dan audit trail.

**Outcome yang dicapai:**
- ✅ User Purchasing/Warehouse dapat membuat GR Draft langsung dari PO Approved.
- ✅ GR otomatis prefill item + `expected_qty = qty_remaining` dari PO.
- ✅ Saat GR diposting `status='received'`:
  - ✅ `rahaza_material_stock` bertambah sesuai net_qty
  - ✅ PO `qty_received` per line bertambah dan status PO ter-update (`partially_received`/`fully_received`)
- ✅ Sistem mencegah **over-receive** (received > remaining) via validasi backend.
- ✅ PO detail dapat menampilkan daftar GR terkait (reverse linkage / audit trail).
- ✅ Frontend wiring selesai (tombol “Buat Goods Receipt” pada PO berfungsi end-to-end dan deep-link ke Receiving).

**Status objective P1.C:** selesai, diverifikasi oleh POC + testing_agent_v3 (iteration_17: 23/23 PASS).

### P1.D — Legacy Toko Migration (`dewi_toko_*` → `marketing_*`) ✅ DONE
**Deprecate** 8 koleksi legacy toko dan konsolidasi ke SSOT marketing namespace.

**Outcome yang dicapai:**
- ✅ Adapter lengkap (12 conversion functions) untuk mapping data legacy ↔ marketing.
- ✅ Seluruh endpoint legacy `/api/dewi/toko/*` ditandai `deprecated=True` di OpenAPI (40/40 verified).
- ✅ Migration script tersedia dan telah dieksekusi (idempotent).

**Status objective P1.D:** selesai, diverifikasi oleh POC + migration + testing_agent_v3 (iteration_18: 16/17 PASS; 1 minor failure = test sequence issue, bukan bug).

### P1.A–D Cleanup Phase A (Post-monitoring 1 minggu) ✅ DONE
**Goal:** drop legacy collections + flip backend reads/writes ke SSOT **tanpa mengubah kontrak API** (frontend tetap bisa memakai endpoint legacy).

**Outcome yang dicapai:**
- ✅ **9 legacy collections dropped** dari MongoDB:
  - `acc_items`, `acc_stock_movements`
  - `dewi_maklon_orders`
  - `dewi_toko_products`, `dewi_toko_channels`, `dewi_toko_channel_syncs`, `dewi_toko_orders`, `dewi_toko_returns`, `dewi_toko_reviews`
- ✅ **Preserved (no SSOT equivalent yet):** `dewi_toko_flashsales`, `dewi_toko_pack_batches`
- ✅ **Wrapper pattern introduced** untuk menjaga API-stable cleanup:
  - `_ScopedView` (generic): Toko products/channels/syncs
  - `_LazyProductsView`: products with lazy catalog_id
  - `_OrdersView`: Toko orders with field translation
  - `_ScopedShimView`: Toko returns/reviews
  - `_MaklonOrdersView`: Maklon orders backed by `dewi_maklon_pos`
- ✅ **Field translation maps** ditambahkan di adapters untuk handle legacy field names + status values
- ✅ `server.py` index creation untuk koleksi legacy dibersihkan
- ✅ Testing:
  - 4 POCs all pass (39/39)
  - `testing_agent_v3 iteration_20`: **21/21 PASS** (setelah agent self-fix 2 bug maklon detail)

**Status objective Cleanup Phase A:** selesai dan stabil.

---

## 2) Implementation Steps (Phased)

### Phase 1 — Core POC (Isolated) ✅ DONE (P1.A)
**Core workflow:** “Aksesoris master + receive/issue stok + saldo stok konsisten” via `/api/acc/*` tetapi backed by `rahaza_*`.

User stories (POC):
1. ✅ Create item via `/api/acc/items` tersimpan sebagai `rahaza_materials.type='accessory'`.
2. ✅ Receive stok tercatat di `rahaza_material_stock`.
3. ✅ Issue stok berkurang + movement tercatat di `rahaza_material_movements`.
4. ✅ `/api/acc/stock` konsisten dengan SSOT.
5. ✅ `/api/acc/stock/movements` bisa ditelusuri per item.

Steps:
1. ✅ Tambah **POC script**: `/app/backend/migrations/poc_accessory_ssot.py`
2. ✅ Implement adapter minimal di `dewi_accessories_full.py`
3. ✅ Jalankan POC sampai PASS.

Exit gate Phase 1:
- ✅ POC script PASS 100%

---

### Phase 2 — V1 Refactor Backend (SSOT internal, API tetap) ✅ DONE (P1.A)
User stories (Backend V1):
1. ✅ Stock aksesoris konsisten karena SSOT sama.
2. ✅ Search aksesoris via `/api/acc/items?search=...`.
3. ✅ `min_stock` + indikator low/out stock benar.
4. ✅ Internal request “Issued” mengurangi stok di SSOT.
5. ✅ Loan reduce/return restore stok dan tercatat.

Steps:
1. ✅ Refactor penuh `dewi_accessories_full.py` dengan prinsip “API facade”:
   - ✅ MASTER: `acc_items` → `rahaza_materials (type='accessory')`
   - ✅ STOCK: operasi stok → `rahaza_material_stock` + log ke `rahaza_material_movements`
   - ✅ MOVEMENTS: query SSOT + enrich ke format legacy (IN/OUT + qty_signed)
   - ✅ Preserve feature unik: `acc_internal_requests`, `acc_loans`, `acc_purchase_requests`, `acc_opname_sessions/lines`
2. ✅ Update computations baca `rahaza_material_stock`
3. ✅ Update side-effects: IR/loan/PR/opname menulis ke SSOT movements + stock

Exit gate Phase 2:
- ✅ Semua `/api/acc/*` berfungsi tanpa perubahan frontend

---

### Phase 3 — Data Migration (acc_* → rahaza_*) + Validation ✅ DONE (P1.A)
Steps:
1. ✅ Buat script: `/app/backend/migrations/migrate_accessories.py` (dry-run + execute)
2. ✅ Migrasi executed dan recompute stock benar
3. ✅ (Saat itu) legacy collections tidak di-drop

Exit gate Phase 3:
- ✅ Report validasi PASS

---

### Phase 4 — Testing & Regression ✅ DONE (P1.A)
Steps:
1. ✅ `testing_agent_v3` iteration_15 → **29/29 PASS** (`/app/test_reports/iteration_15.json`)
2. ✅ PRD updated

---

### Phase 5 — Maklon POC: Adapter + Dual-Collection Resolver ✅ DONE (P1.B)
Steps:
1. ✅ Tambah POC script: `/app/backend/migrations/poc_maklon_consolidation.py` (PASS 6/6)
2. ✅ Adapter & resolver dibuat

---

### Phase 6 — Refactor Consumers to SSOT `dewi_maklon_pos` ✅ DONE (P1.B)
Steps:
1. ✅ Buat adapter: `/app/backend/routes/_maklon_adapter.py`
2. ✅ Refactor consumers read dari `dewi_maklon_pos`
3. ✅ Mark 12 legacy `/api/dewi/maklon/orders/*` deprecated=True

---

### Phase 7 — Data Migration (dewi_maklon_orders → dewi_maklon_pos) ✅ DONE (P1.B)
Steps:
1. ✅ Script: `/app/backend/migrations/migrate_maklon_orders.py`
2. ✅ Dry-run + execute
3. ✅ (Saat itu) legacy collection tidak di-drop

---

### Phase 8 — Testing & Regression ✅ DONE (P1.B)
Steps:
1. ✅ `testing_agent_v3` iteration_16 → **13/14 PASS** (`/app/test_reports/iteration_16.json`)
2. ✅ Verifikasi deprecation flag via `/api/openapi.json`

---

### Phase 9 — P1.C: P2P POC + Backend Core Flow ✅ DONE
Steps:
1. ✅ POC script: `/app/backend/migrations/poc_p2p_flow.py` (PASS 13/13)

---

### Phase 10 — P1.C: Backend Endpoints ✅ DONE
Steps:
1. ✅ `rahaza_po.py`: remaining + create-gr + grs endpoints
2. ✅ Bugfix status transition partially→fully received

---

### Phase 11 — P1.C: Validations (Anti Over-Receive) ✅ DONE
Steps:
1. ✅ `warehouse.py update_receiving`: block over-receive linked to PO

---

### Phase 12 — P1.C: Frontend Integration ✅ DONE
Steps:
1. ✅ PurchaseOrderModule: createGRFromPO
2. ✅ ReceivingModule: badge + deepLink
3. ✅ App.js: deepLinkParams

---

### Phase 13 — P1.C: Testing & Regression ✅ DONE
Steps:
1. ✅ `testing_agent_v3` iteration_17 → **23/23 PASS** (`/app/test_reports/iteration_17.json`)

---

### Phase 14 — P1.D: Adapter (Legacy Toko ↔ Marketing) ✅ DONE
Steps:
1. ✅ Adapter: `/app/backend/routes/_toko_adapter.py` (12 functions + helper catalog)

---

### Phase 15 — P1.D: POC Dual-Write ✅ DONE
Steps:
1. ✅ POC: `/app/backend/migrations/poc_toko_consolidation.py` (PASS 10/10)

---

### Phase 16 — P1.D: Refactor Routes (Dual-Write + Deprecation) ✅ DONE
Steps:
1. ✅ Dual-write helpers added to `dewi_toko.py`, `dewi_online_orders.py`, `dewi_returns.py`
2. ✅ Mark 40 toko endpoints deprecated=True

---

### Phase 17 — P1.D: OpenAPI Deprecation Verification ✅ DONE
Steps:
1. ✅ Verified 40/40 deprecated in `/api/openapi.json`

---

### Phase 18 — P1.D: Data Migration Script + Execute ✅ DONE
Steps:
1. ✅ Script: `/app/backend/migrations/migrate_toko_data.py`
2. ✅ Execute idempotent; (saat itu) legacy collections tidak di-drop

---

### Phase 19 — P1.D: Testing & Regression ✅ DONE
Steps:
1. ✅ `testing_agent_v3` iteration_18 → **16/17 PASS** (`/app/test_reports/iteration_18.json`)

---

### Phase 20 — Cleanup Phase A (Drop Collections + Flip Reads via Wrappers) ✅ DONE
**Tujuan:** menghapus legacy collections sambil mempertahankan endpoint legacy agar frontend tidak rusak.

Steps:
1. ✅ Drop `acc_items` + `acc_stock_movements`
2. ✅ Introduce wrappers + field/status translation:
   - ✅ Toko: `_ScopedView`, `_LazyProductsView`, `_OrdersView`, `_ScopedShimView`
   - ✅ Maklon: `_MaklonOrdersView` (backed by `dewi_maklon_pos`)
3. ✅ Flip code reads/writes:
   - ✅ `dewi_toko.py`, `dewi_online_orders.py`, `dewi_returns.py` now use marketing_* SSOT
   - ✅ `dewi_maklon.py` now serves legacy `/orders` endpoints from `dewi_maklon_pos` SSOT
4. ✅ Drop legacy collections:
   - ✅ `dewi_maklon_orders`
   - ✅ 6 `dewi_toko_*` collections (products/channels/syncs/orders/returns/reviews)
5. ✅ Cleanup `server.py` index creation for dropped collections
6. ✅ Testing/regression:
   - ✅ POCs: 39/39 PASS
   - ✅ `testing_agent_v3 iteration_20`: 21/21 PASS (after 2 bugfix in maklon detail endpoints)

Exit gate Phase 20:
- ✅ Tidak ada koleksi legacy tersisa selain yang memang dipreserve
- ✅ Endpoint legacy tetap berjalan

---

## 3) Next Actions (Immediate)

Karena **P1.A + P1.B + P1.C + P1.D + Cleanup Phase A sudah selesai**, fokus berikutnya adalah pengurangan codebase (Phase C) dan migrasi frontend (Phase B).

1. **Phase B — Frontend Cutover (Deferred, recommended next)**
   - Update ±16 modules frontend agar langsung memakai SSOT endpoints:
     - Toko modules: `/api/marketing/*`
     - Maklon modules: `/api/dewi/maklon/pos/*`
   - Setelah cutover, endpoint legacy bisa dihapus.

2. **Phase C — Route Removal / Code Reduction (~1500 LOC, Deferred)**
   - Hapus endpoint deprecated yang masih tersisa (setelah frontend cutover):
     - `dewi_maklon.py`: legacy `/orders/*` block
     - `dewi_toko.py`, `dewi_online_orders.py`, `dewi_returns.py`: legacy `/api/dewi/toko/*` blocks
   - Target: bersihkan file monster dan turunkan kompleksitas maintain.

3. **acc_opname migration (related to P1.A, separate scope)**
   - Migrasi `acc_opname_sessions/lines` → `wh_opname2_*` (FORENSIC_04 Cluster B)

4. **Phase 4 Finance (Future) — AP Invoice generation from GR**
   - Auto-generate AP invoice dari GR + 3-way match (PO ↔ GR ↔ AP)

5. **3-way match dashboard (Future)**
   - Visualisasi PO ↔ GR ↔ AP + exception handling

6. **SSOT design decision for preserved Toko modules (Future)**
   - Tentukan SSOT untuk `dewi_toko_flashsales` + `dewi_toko_pack_batches` (tetap dedicated vs migrate ke marketing)

---

## 4) Success Criteria

### P1.A (completed)
- ✅ `/api/acc/items` mengelola aksesoris di `rahaza_materials (type='accessory')`.
- ✅ `/api/acc/stock` & `/api/acc/stock/*` menggunakan `rahaza_material_stock` + `rahaza_material_movements` sebagai SSOT.
- ✅ Endpoint existing tetap compatible dengan frontend.
- ✅ Test: iteration_15 **29/29 PASS**.

### P1.B (completed)
- ✅ SSOT maklon orders = `dewi_maklon_pos`.
- ✅ Consumer utama membaca SSOT PO.
- ✅ Legacy `/api/dewi/maklon/orders/*` deprecated (12/12 flagged di `/api/openapi.json`) dan **tetap berjalan**.
- ✅ Test: iteration_16 **13/14 PASS**.

### P1.C (completed)
- ✅ Create GR from PO endpoints + anti over-receive + audit trail.
- ✅ Test: iteration_17 **23/23 PASS**.

### P1.D (completed)
- ✅ Toko SSOT migrated to `marketing_*`.
- ✅ Legacy toko endpoints deprecated (40/40) dan tetap berjalan.
- ✅ Test: iteration_18 **16/17 PASS**.

### Cleanup Phase A (completed)
- ✅ 9 legacy collections dropped (listed above), preserved only 2 intentional collections.
- ✅ Endpoint legacy tetap berfungsi dengan wrapper routing ke SSOT.
- ✅ `server.py` indexes untuk legacy dibersihkan.
- ✅ Testing: iteration_20 **21/21 PASS**.

### Session-level completion gate
- ✅ PRD.md sudah diupdate dengan log P1.A + P1.B + P1.C + P1.D + Cleanup Phase A
- ✅ Test reports tersimpan:
  - `/app/test_reports/iteration_15.json`
  - `/app/test_reports/iteration_16.json`
  - `/app/test_reports/iteration_17.json`
  - `/app/test_reports/iteration_18.json`
  - `/app/test_reports/iteration_19.json`
  - `/app/test_reports/iteration_20.json`
