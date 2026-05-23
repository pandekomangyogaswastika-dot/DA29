# plan.md — P1.A Accessory Consolidation (SSOT: `rahaza_materials`) ✅ COMPLETED + P1.B Maklon Orders Consolidation (SSOT: `dewi_maklon_pos`) ✅ COMPLETED

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
- ✅ Migrasi legacy → PO aman: **idempotent** dan tidak drop legacy collection.

**Status objective P1.B:** selesai, diverifikasi oleh POC + migration + testing_agent_v3 (iteration_16: 13/14 PASS; 1 “issue” non-blocking ternyata mismatch URL OpenAPI).

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
1. ✅ Stock aksesoris konsisten (Gudang ↔ Aksesoris) karena SSOT sama.
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
2. ✅ Update computations baca `rahaza_material_stock` (bukan agregasi legacy movements)
3. ✅ Update side-effects: IR/loan/PR/opname menulis ke SSOT movements + stock

Exit gate Phase 2:
- ✅ Semua `/api/acc/*` berfungsi tanpa perubahan frontend
- ✅ Legacy `acc_items`/`acc_stock_movements` tidak lagi dipakai sebagai SSOT

---

### Phase 3 — Data Migration (acc_* → rahaza_*) + Validation ✅ DONE (P1.A)
User stories (Migration):
1. ✅ Item lama muncul di modul Aksesoris.
2. ✅ Histori movements lama tetap bisa ditelusuri.
3. ✅ Saldo akhir tidak berubah.
4. ✅ Ada laporan validasi count + sampling.
5. ✅ Idempotent safe re-run.

Steps:
1. ✅ Buat script: `/app/backend/migrations/migrate_accessories.py` (dry-run + execute)
2. ✅ Migrasi executed dan recompute stock benar
3. ✅ Legacy collections tidak di-drop

Exit gate Phase 3:
- ✅ Report validasi PASS
- ✅ Master/stock memakai `rahaza_*`

---

### Phase 4 — Testing & Regression ✅ DONE (P1.A)
Steps:
1. ✅ `testing_agent_v3` iteration_15 → **29/29 PASS** (`/app/test_reports/iteration_15.json`)
2. ✅ Smoke verification via curl/manual sampling
3. ✅ PRD updated dengan log P1.A

Exit gate Phase 4:
- ✅ No regression critical

---

### Phase 5 — Maklon POC: Adapter + Dual-Collection Resolver ✅ DONE (P1.B)
**Core workflow:** pastikan konversi legacy ↔ PO benar dan resolver bisa menemukan record dari kedua koleksi.

User stories (POC):
1. ✅ Seed 2 legacy orders (simulasi)
2. ✅ `order_to_po_create_payload()` split `qty_per_size` menjadi multi-item PO
3. ✅ `po_to_legacy_order()` menghasilkan legacy shape back-compat
4. ✅ `find_maklon_record()` resolve by id dan by code/number

Steps:
1. ✅ Tambah POC script: `/app/backend/migrations/poc_maklon_consolidation.py`
2. ✅ Jalankan POC sampai PASS 6/6

Exit gate Phase 5:
- ✅ POC PASS 100%

---

### Phase 6 — Refactor Consumers to SSOT `dewi_maklon_pos` ✅ DONE (P1.B)
**Target:** hentikan pembacaan `dewi_maklon_orders` oleh consumer utama.

Steps:
1. ✅ Buat adapter: `/app/backend/routes/_maklon_adapter.py`
   - `po_to_legacy_order(po_doc)`
   - `order_to_po_create_payload(order_doc)`
   - `find_maklon_record(db, id_or_code)`
2. ✅ Refactor consumers untuk read dari `dewi_maklon_pos`:
   - ✅ `dewi_client_portal.py`: dashboard + 4 orders endpoints (list/detail/qc/samples) → read PO + project legacy
   - ✅ `dewi_management_tools.py`: weekly-digest maklon counts → read PO
   - ✅ `dewi_maklon_billing.py`: generate-invoice, cancel-invoice, hpp → lookup PO-first (fallback legacy)
   - ✅ `dewi_maklon_samples.py`: create_sample → lookup PO-first, simpan `po_id` untuk traceability
3. ✅ Deprecate legacy endpoints:
   - ✅ 12 endpoint `/api/dewi/maklon/orders/*` ditandai `deprecated=True` di `dewi_maklon.py`
   - ✅ Verified di OpenAPI: `GET /api/openapi.json` menunjukkan 12/12 deprecated

Exit gate Phase 6:
- ✅ Consumer utama sudah menggunakan SSOT PO
- ✅ Legacy endpoints masih berjalan (back-compat) tapi jelas deprecated

---

### Phase 7 — Data Migration (dewi_maklon_orders → dewi_maklon_pos) ✅ DONE (P1.B)
User stories (Migration):
1. ✅ Semua legacy order dapat dimigrasi menjadi PO.
2. ✅ `qty_per_size` menjadi beberapa item.
3. ✅ Status mapping benar dan linked WO terjaga.
4. ✅ Idempotent (re-run skip existing).
5. ✅ Legacy collection tidak di-drop.

Steps:
1. ✅ Buat script: `/app/backend/migrations/migrate_maklon_orders.py`
2. ✅ Dry-run + execute
3. ✅ Migrasi executed contoh 3 legacy orders → 3 POs:
   - MKLO-LEG-001: sewing → in_production, 3 items (S/M/L), qty=200
   - MKLO-LEG-002: completed, 1 item, qty=100
   - MKLO-LEG-003: draft, 1 item, qty=50

Exit gate Phase 7:
- ✅ Target pos_migrated_from_legacy bertambah sesuai src
- ✅ No duplicate on re-run

---

### Phase 8 — Testing & Regression ✅ DONE (P1.B)
Steps:
1. ✅ `testing_agent_v3` iteration_16 → **13/14 PASS** (`/app/test_reports/iteration_16.json`)
2. ✅ Klarifikasi 1 minor issue:
   - Agent mengecek `/openapi.json` (404) padahal FastAPI `openapi_url=/api/openapi.json`
   - Verifikasi manual: 12/12 legacy endpoints deprecated=true
3. ✅ Smoke test via curl:
   - `GET /api/dewi/maklon/pos` OK
   - `GET /api/management/weekly-digest` OK
   - `GET /api/dewi/maklon/orders` legacy OK

Exit gate Phase 8:
- ✅ Semua critical flow maklon berjalan
- ✅ Tidak ada regresi blocking

---

## 3) Next Actions (Immediate)
Karena **P1.A dan P1.B sudah selesai**, next actions bergeser ke backlog berikutnya:

1. **P1.C — Procure-to-Pay Completion (Create GR from PO)** (~14 jam)
   - Implement “Create GR from PO” (Goods Receipt) + stock & accounting side-effects
   - Pastikan audit trail + role permissions

2. **P1.D — Legacy Toko Migration** (~18 jam)
   - Migrasi 8 koleksi `dewi_toko_*` → `marketing_*` (seed + mapping + idempotent migration)

3. **Cleanup (post-monitoring 1 minggu) — P1.A + P1.B**
   - Jika tidak ada rollback need:
     - Drop legacy `acc_items` + `acc_stock_movements`
     - Drop legacy `dewi_maklon_orders`
   - Hapus route deprecated di `dewi_maklon.py` (mengurangi file monster)

4. **Task related (separate scope, recommended next)**
   - Migrasi `acc_opname_sessions/lines` → `wh_opname2_cycles/variances` (FORENSIC_04 Cluster B)

---

## 4) Success Criteria

### P1.A (completed)
- ✅ `/api/acc/items` mengelola aksesoris di `rahaza_materials (type='accessory')`.
- ✅ `/api/acc/stock` & `/api/acc/stock/*` menggunakan `rahaza_material_stock` + `rahaza_material_movements` sebagai SSOT.
- ✅ Endpoint existing tetap compatible dengan frontend.
- ✅ Migrasi idempotent + validasi saldo terbukti.
- ✅ Test: iteration_15 **29/29 PASS**.

### P1.B (completed)
- ✅ SSOT maklon orders = `dewi_maklon_pos`.
- ✅ Consumer utama membaca SSOT PO (client portal, billing, samples, management tools).
- ✅ Legacy `/api/dewi/maklon/orders/*` tetap hidup tapi **deprecated** (12/12 flagged di `/api/openapi.json`).
- ✅ Migrasi idempotent legacy → PO berjalan dan tidak drop legacy.
- ✅ Test: iteration_16 **13/14 PASS**, seluruh critical flow verified.

### Session-level completion gate
- ✅ PRD.md sudah diupdate dengan log P1.A + P1.B
- ✅ Test reports tersimpan:
  - `/app/test_reports/iteration_15.json`
  - `/app/test_reports/iteration_16.json`

**Butuh keputusan user untuk melanjutkan:** pilih P1.C / P1.D sebagai fokus berikutnya.