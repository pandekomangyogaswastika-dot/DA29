# plan.md — P1.A Accessory Consolidation (SSOT: `rahaza_materials`) ✅ COMPLETED + P1.B Maklon Orders Consolidation (SSOT: `dewi_maklon_pos`) ✅ COMPLETED + P1.C P2P Flow Completion (Create GR from PO) ✅ COMPLETED + P1.D Legacy Toko Migration (SSOT: `marketing_*`) ✅ COMPLETED

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

**Status objective P1.B:** selesai, diverifikasi oleh POC + migration + testing_agent_v3 (iteration_16: 13/14 PASS; catatan: minor “issue” agen adalah mismatch URL OpenAPI; valid URL `/api/openapi.json`).

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
**Deprecate** 8 koleksi legacy toko dan konsolidasi ke SSOT marketing namespace dengan strategi **dual-write + migration + deprecation**.

**Outcome yang dicapai:**
- ✅ Adapter lengkap (12 conversion functions) untuk mapping data legacy ↔ marketing.
- ✅ Dual-write: semua write ke `dewi_toko_*` otomatis di-mirror ke `marketing_*` (upsert by id, idempotent).
- ✅ Semua endpoint legacy `/api/dewi/toko/*` ditandai `deprecated=True` di OpenAPI (40/40 verified).
- ✅ Migration script tersedia dan telah dieksekusi (idempotent; tidak drop legacy).

**Status objective P1.D:** selesai, diverifikasi oleh POC + migration + testing_agent_v3 (iteration_18: 16/17 PASS; 1 minor failure = test sequence issue, bukan bug).

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
2. ✅ Klarifikasi minor issue:
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

### Phase 9 — P1.C: P2P POC + Backend Core Flow (Create GR from PO) ✅ DONE
**Core workflow:** PO Approved → Create GR Draft dari PO → Receive → update stock + update PO status.

Steps:
1. ✅ Buat POC script: `/app/backend/migrations/poc_p2p_flow.py`
   - ✅ Seed material → create PO dengan 3 items → approve
   - ✅ Call endpoint `POST /api/rahaza/purchase-orders/{po_id}/create-gr` → GR draft berisi remaining qty
   - ✅ Update GR lines received_qty dan set `status='received'`
   - ✅ Verify:
     - PO qty_received per line terupdate
     - PO status → `partially_received`/`fully_received`
     - `rahaza_material_stock` bertambah
     - **Over-receive** ditolak
     - Create GR dari PO fully_received ditolak
     - Audit trail `/grs` mengembalikan 2 GR

Exit gate Phase 9:
- ✅ POC PASS 13/13 untuk skenario partially dan fully received

---

### Phase 10 — P1.C: Backend Endpoints (Create GR + PO→GR linkage) ✅ DONE
**Target:** endpoint yang dibutuhkan frontend agar tombol “Create GR dari PO” benar-benar bekerja.

Steps:
1. ✅ Tambah endpoint di `rahaza_po.py`:
   - ✅ `GET /api/rahaza/purchase-orders/{po_id}/remaining`
   - ✅ `POST /api/rahaza/purchase-orders/{po_id}/create-gr`
     - Validasi PO status ∈ {`approved`, `partially_received`}
     - Hitung remaining per item
     - Skip line fully received
     - Create GR draft di `warehouse_receiving` dengan:
       - `po_id`, `po_number`, `supplier_name` = vendor_name
       - `items[*].expected_qty = qty_remaining`
       - `enforce_po_qty = true` default jika ada po_id
       - Support `items_override` untuk partial GR
   - ✅ `GET /api/rahaza/purchase-orders/{po_id}/grs`
     - List GR audit trail linked ke PO
2. ✅ Bugfix: `update_po_received_qty()` sekarang bisa transisi `partially_received` → `fully_received`.

Exit gate Phase 10:
- ✅ Endpoint create-gr mengembalikan GR draft valid
- ✅ Endpoint list grs mengembalikan data audit trail

---

### Phase 11 — P1.C: Validations (Anti Over-Receive) ✅ DONE
**Target:** tidak bisa receive melebihi qty remaining dari PO.

Steps:
1. ✅ Update `warehouse.py` pada transisi `status: received`:
   - Jika GR punya `po_id` dan flag `enforce_po_qty=true`:
     - Ambil PO
     - Hitung remaining per material_id
     - Jika net_qty (received - rejected) > remaining → HTTP 400

Exit gate Phase 11:
- ✅ Over-receive selalu tertolak (400)
- ✅ Receive normal tetap sukses

---

### Phase 12 — P1.C: Frontend Integration ✅ DONE
**Target:** tombol di PO bisa membuat GR dan user bisa lanjutkan receiving tanpa input manual.

Steps:
1. ✅ Update `/app/frontend/src/components/erp/PurchaseOrderModule.jsx`:
   - Implement `createGRFromPO(po)`:
     - call `POST /api/rahaza/purchase-orders/{po_id}/create-gr`
     - navigate ke receiving module dengan `receipt_id` (deep-link)
   - Fetch dan tampilkan list GR di PO detail (pakai endpoint `/grs`)
2. ✅ Update `/app/frontend/src/components/erp/ReceivingModule.jsx`:
   - Badge “Dari PO {po_number}” + indikator `enforce_po_qty`
   - Auto-open GR detail ketika dinavigasi dari PO (deepLinkParams.receipt_id)
3. ✅ Update `/app/frontend/src/App.js`:
   - `handleNavigate(moduleId, params)` menyimpan navParams dan pass `deepLinkParams` ke module

Exit gate Phase 12:
- ✅ Dari PO Approved → 1 klik jadi GR Draft
- ✅ Receiving flow tidak perlu prefill manual

---

### Phase 13 — P1.C: Testing & Regression ✅ DONE
Steps:
1. ✅ `testing_agent_v3` iteration_17 → **23/23 PASS (100%)** (`/app/test_reports/iteration_17.json`)
2. ✅ POC script re-run passes (13/13 PASS)

Exit gate Phase 13:
- ✅ Semua test P2P flow PASS

---

### Phase 14 — P1.D: Adapter (Legacy Toko ↔ Marketing) ✅ DONE
**Target:** menyediakan konversi schema konsisten dan reusable untuk dual-write + migration.

Steps:
1. ✅ Buat adapter: `/app/backend/routes/_toko_adapter.py`
   - 12 fungsi konversi utama:
     - products ↔ catalog_items
     - channels ↔ platform_accounts
     - orders ↔ marketing_orders
     - returns ↔ marketing_returns
     - reviews ↔ marketing_reviews
     - sync logs → marketing_stock_syncs
   - Helper idempotent: `get_or_create_toko_legacy_catalog(db)` (auto-create parent `marketing_catalogs`)

Exit gate Phase 14:
- ✅ Adapter usable oleh route + migration

---

### Phase 15 — P1.D: POC Dual-Write ✅ DONE
**Core workflow:** setiap write legacy toko memunculkan mirror di marketing_*.

Steps:
1. ✅ POC script: `/app/backend/migrations/poc_toko_consolidation.py`
2. ✅ Validasi 10 user stories (products/channels/sync/orders/returns/reviews + OpenAPI deprecated)

Exit gate Phase 15:
- ✅ POC PASS 10/10

---

### Phase 16 — P1.D: Refactor Routes (Dual-Write + Deprecation) ✅ DONE
**Target:** semua write endpoint legacy otomatis mirror ke SSOT marketing_*, tanpa mengubah frontend.

Steps:
1. ✅ Update `/app/backend/routes/dewi_toko.py`:
   - Tambah mirror helpers: `_mirror_product`, `_mirror_channel`, `_mirror_sync_log`
   - Inject mirror setelah create/update/delete
   - Auto-seed channel juga mirror
   - Mark 18 endpoints deprecated
2. ✅ Update `/app/backend/routes/dewi_online_orders.py`:
   - Tambah `_mirror_order`
   - Mirror setelah create/update/status/cancel + batch packing flow
   - Mark 10 endpoints deprecated
3. ✅ Update `/app/backend/routes/dewi_returns.py`:
   - Tambah `_mirror_return`, `_mirror_review`
   - Mirror setelah create/update/decision/respond/flag
   - Mark 12 endpoints deprecated

Exit gate Phase 16:
- ✅ Dual-write berjalan untuk 6 koleksi mapped
- ✅ Tidak ada breaking change ke frontend legacy

---

### Phase 17 — P1.D: OpenAPI Deprecation Verification ✅ DONE
Steps:
1. ✅ Mark semua decorator endpoint pada 3 file route dengan `deprecated=True`
2. ✅ Verifikasi via `/api/openapi.json`: 40/40 endpoint `/api/dewi/toko/*` deprecated

Exit gate Phase 17:
- ✅ OpenAPI menunjukkan deprecation untuk seluruh toko endpoints

---

### Phase 18 — P1.D: Data Migration Script + Execute ✅ DONE
Steps:
1. ✅ Buat script: `/app/backend/migrations/migrate_toko_data.py` (dry-run + execute)
2. ✅ Execute migration (idempotent). Legacy collections **tidak di-drop**.
3. ✅ Preserve (no marketing equivalent): `dewi_toko_flashsales`, `dewi_toko_pack_batches`

Exit gate Phase 18:
- ✅ Script idempotent (re-run skip existing)
- ✅ Validasi counts sesuai

---

### Phase 19 — P1.D: Testing & Regression ✅ DONE
Steps:
1. ✅ `testing_agent_v3` iteration_18 → **16/17 PASS (94.1%)** (`/app/test_reports/iteration_18.json`)
2. ✅ Catatan minor:
   - “Cancel order” gagal karena order sudah shipped (aturan bisnis benar; test sequence issue, bukan bug)

Exit gate Phase 19:
- ✅ Tidak ada critical bugs
- ✅ Dual-write + migration validated

---

## 3) Next Actions (Immediate)
Karena **P1.A + P1.B + P1.C + P1.D sudah selesai**, fokus berikutnya adalah post-consolidation stabilization dan roadmap FORENSIC_11.

1. **Cleanup (post-monitoring 1 minggu) — P1.A s/d P1.D**
   - Jika tidak ada rollback need:
     - Drop legacy `acc_items` + `acc_stock_movements`
     - Drop legacy `dewi_maklon_orders`
     - Drop legacy `dewi_toko_products`, `dewi_toko_channels`, `dewi_toko_channel_syncs`, `dewi_toko_orders`, `dewi_toko_returns`, `dewi_toko_reviews`
   - Hapus route deprecated:
     - `dewi_maklon.py` (orders endpoints)
     - `dewi_toko.py`, `dewi_online_orders.py`, `dewi_returns.py` (toko endpoints)
   - Output: pengurangan file monster (terutama `dewi_maklon.py`) dan mengurangi kompleksitas DB.

2. **Frontend cutover (recommended next)**
   - Update 6 UI modules Toko (`Toko*Module.jsx`) untuk membaca langsung dari `/api/marketing/*` (bukan legacy `/api/dewi/toko/*`).
   - Update UI Maklon (bila masih ada calls legacy) untuk memakai `/api/dewi/maklon/pos/*`.

3. **acc_opname migration (related to P1.A, separate scope)**
   - Migrasi `acc_opname_sessions/lines` → `wh_opname2_cycles/variances` (FORENSIC_04 Cluster B)

4. **Phase 4 Finance (Future) — AP Invoice generation from GR**
   - Auto-generate AP invoice dari GR + 3-way match (PO ↔ GR ↔ AP)

5. **3-way match dashboard (Future)**
   - Visualisasi PO ↔ GR ↔ AP + exception handling (qty mismatch, price mismatch, late delivery)

6. **P2 Workflow Consolidations (FORENSIC_11)**
   - Maklon PO 360° View, HR Approval Inbox, Production Control Tower, dsb (~180 jam)

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

### P1.C (completed)
- ✅ `POST /api/rahaza/purchase-orders/{po_id}/create-gr` menghasilkan GR draft yang benar dan hanya untuk qty remaining.
- ✅ `GET /api/rahaza/purchase-orders/{po_id}/remaining` mengembalikan remaining qty per item untuk prefill.
- ✅ `GET /api/rahaza/purchase-orders/{po_id}/grs` menampilkan audit trail GR per PO.
- ✅ Over-receive ditolak (400) pada saat GR diposting `received`.
- ✅ PO otomatis update qty_received dan status (partially/fully received) saat GR diterima.
- ✅ Frontend PO module: tombol “Create GR dari PO” berfungsi end-to-end + deep-link ke Receiving.
- ✅ Test: iteration_17 **23/23 PASS**.

### P1.D (completed)
- ✅ Semua write legacy `/api/dewi/toko/*` mirrored ke SSOT `marketing_*`:
  - products → `marketing_catalog_items` (dengan auto parent catalog `marketing_catalogs`)
  - channels → `marketing_platform_accounts`
  - channel_syncs → `marketing_stock_syncs`
  - orders → `marketing_orders`
  - returns → `marketing_returns`
  - reviews → `marketing_reviews`
- ✅ Endpoint legacy tetap berjalan (back-compat) namun seluruhnya deprecated (40/40 flagged di OpenAPI).
- ✅ Migration script `migrate_toko_data.py` tersedia dan idempotent.
- ✅ Test: iteration_18 **16/17 PASS** (minor failure = test sequencing; no critical bugs).

### Session-level completion gate
- ✅ PRD.md sudah diupdate dengan log P1.A + P1.B + P1.C + P1.D
- ✅ Test reports tersimpan:
  - `/app/test_reports/iteration_15.json`
  - `/app/test_reports/iteration_16.json`
  - `/app/test_reports/iteration_17.json`
  - `/app/test_reports/iteration_18.json`
