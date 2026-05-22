# plan.md — P1.A Accessory Consolidation (SSOT: `rahaza_materials`) ✅ COMPLETED

## 1) Objectives
- ✅ Konsolidasi sistem aksesoris menjadi **1 SSOT internal** berbasis `rahaza_*` **tanpa mengubah kontrak API**.
- ✅ **API-stable:** semua endpoint `/api/acc/*` tetap ada dan tetap compatible dengan `AccessoryModule.jsx` (frontend tidak diubah).
- ✅ Migrasi data aman: **idempotent, tanpa data loss**, dengan dry-run + validasi + execute.
- ✅ Core stock logic aksesoris konsisten dengan sistem inventory utama:
  - master: `rahaza_materials` (filter `type='accessory'`)
  - saldo: `rahaza_material_stock`
  - histori: `rahaza_material_movements` (filter `domain='accessory'` + `legacy_movement_type` untuk back-compat)

**Status objective:** selesai, diverifikasi oleh POC + migration + testing_agent_v3 (iteration_15: 29/29 PASS).

## 2) Implementation Steps (Phased)

### Phase 1 — Core POC (Isolated) ✅ DONE
**Core workflow:** “Aksesoris master + receive/issue stok + saldo stok konsisten” via `/api/acc/*` tetapi backed by `rahaza_*`.

User stories (POC):
1. ✅ Sebagai admin, saya bisa membuat item aksesoris via `/api/acc/items` dan item tersebut tersimpan sebagai `rahaza_materials.type='accessory'`.
2. ✅ Sebagai admin, saya bisa menerima stok aksesoris dan stok tersebut tercatat di `rahaza_material_stock`.
3. ✅ Sebagai admin, saya bisa mengeluarkan stok aksesoris dan stok berkurang serta tercatat di `rahaza_material_movements`.
4. ✅ Sebagai admin, saya bisa melihat daftar stok `/api/acc/stock` yang sesuai dengan SSOT.
5. ✅ Sebagai admin, saya bisa melihat histori movements `/api/acc/stock/movements` untuk satu aksesoris.

Steps:
1. ✅ Tambah **POC script**: `/app/backend/migrations/poc_accessory_ssot.py`
   - Create 1 accessory (via endpoint)
   - Receive 10 pcs ke lokasi `ZNA-AKSESORIS`
   - Issue 3 pcs
   - Assert saldo akhir = 7 dan movement count sesuai.
2. ✅ Implement minimal adapter di `dewi_accessories_full.py` untuk 7 endpoint core.
3. ✅ Jalankan POC script sampai PASS.

Exit gate Phase 1:
- ✅ POC script PASS 100% (semua user story lulus).

---

### Phase 2 — V1 Refactor Backend (SSOT internal, API tetap) ✅ DONE
User stories (Backend V1):
1. ✅ Sebagai user gudang, saya melihat stok aksesoris yang sama antara modul Gudang dan modul Aksesoris (SSOT sama).
2. ✅ Sebagai admin, saya dapat mencari aksesoris (code/name/category) via `/api/acc/items?search=...`.
3. ✅ Sebagai admin, saya dapat mengatur `min_stock` dan indikator low/out stock tetap benar.
4. ✅ Sebagai admin, saya dapat membuat internal request dan saat status “Issued”, stok berkurang di SSOT.
5. ✅ Sebagai admin, saya dapat membuat peminjaman (loan) yang mengurangi stok dan return yang mengembalikan stok.

Steps:
1. ✅ Refactor penuh `dewi_accessories_full.py` dengan prinsip “API facade”:
   - ✅ **MASTER**: `acc_items` → `rahaza_materials (type='accessory')`
   - ✅ **STOCK**: operasi stok → `rahaza_material_stock` + log ke `rahaza_material_movements`
   - ✅ **MOVEMENTS LIST**: `/api/acc/stock/movements` query dari `rahaza_material_movements` + enrich ke format legacy (IN/OUT + qty_signed)
   - ✅ Preserve koleksi feature-unik tetap: `acc_internal_requests`, `acc_loans`, `acc_purchase_requests`, `acc_opname_sessions/lines`
2. ✅ Pastikan field mapping minimal:
   - `acc_items.{id,code,name,category,unit,description,min_stock,supplier,notes,deleted}` →
     `rahaza_materials.{id,code,name,type='accessory',unit,notes,min_stock,active}`
3. ✅ Update stock computations:
   - `_stock_qty` / `_all_accessory_stock` sekarang baca `rahaza_material_stock` (bukan agregasi `acc_stock_movements`).
4. ✅ Update side-effects writer:
   - `internal-requests -> Issued` → stock -qty + movement `issue` (legacy_type OUT)
   - `loans` → stock -qty + movement `issue` (legacy_type LOAN_OUT)
   - `loan return` → stock +qty + movement `receive` (legacy_type LOAN_RETURN)
   - `purchase-requests -> Received` → stock +qty + movement `receive` (legacy_type IN)
   - `opname -> complete` → adjust stock + movement `adjust` (legacy_type ADJUST)

Exit gate Phase 2:
- ✅ Semua endpoint `/api/acc/*` berfungsi tanpa perubahan frontend.
- ✅ Tidak ada penggunaan `acc_items` / `acc_stock_movements` untuk master & stok (legacy read/write dihentikan).

---

### Phase 3 — Data Migration (acc_* → rahaza_*) + Validation ✅ DONE
User stories (Migration):
1. ✅ Setelah migrasi, item aksesoris lama muncul di modul Aksesoris.
2. ✅ Histori pergerakan stok lama tetap bisa ditelusuri.
3. ✅ Saldo stok akhir tidak berubah sebelum vs sesudah migrasi.
4. ✅ Ada laporan validasi count + sampling.
5. ✅ Migrasi idempotent dan bisa diulang (safe re-run).

Steps:
1. ✅ Buat migration script: `/app/backend/migrations/migrate_accessories.py`
   - ✅ Mode `--dry-run` (default)
   - ✅ Mode `--execute`
   - ✅ Idempotent (upsert by id; skip existing movement rows)
2. ✅ Migrasi executed sukses:
   - ✅ `acc_items` → `rahaza_materials` (type='accessory')
   - ✅ `acc_stock_movements` → `rahaza_material_movements` (domain='accessory')
   - ✅ Recompute `rahaza_material_stock` dari movements (net receive/issue/adjust)
3. ✅ Validasi hasil:
   - ✅ LEGACY-ACC-001 saldo 450 pcs (500 - 50)
   - ✅ LEGACY-ACC-002 saldo 27 rol (25 + 2 adjust)
   - ✅ POC item saldo 7 pcs (10 - 3)
4. ✅ Legacy collections TIDAK di-drop (monitoring 1 minggu).

Exit gate Phase 3:
- ✅ Dry-run + execute menghasilkan report validasi PASS.
- ✅ Akses master/stock sudah memakai `rahaza_*`.

---

### Phase 4 — Testing & Regression ✅ DONE
User stories (QA):
1. ✅ End-to-end: create item → receive → issue → lihat stock & movements.
2. ✅ End-to-end: internal request → approve → issued → stok berkurang.
3. ✅ End-to-end: loan → return → stok kembali.
4. ✅ End-to-end: purchase request → received → stok bertambah.
5. ✅ Dashboard aksesoris menampilkan metrik yang benar.

Steps:
1. ✅ Jalankan `testing_agent_v3` fokus modul aksesoris.
   - Report: `/app/test_reports/iteration_15.json`
   - Result: **29/29 backend tests PASS (100%)**
2. ✅ Smoke verification via curl/manual sampling (items, stock, dashboard).
3. ✅ Fixes: tidak ada bug blocking yang tersisa.
4. ✅ Docs update: PRD sudah diupdate dengan session log P1.A.

Exit gate Phase 4:
- ✅ testing_agent_v3 PASS untuk flow aksesoris.
- ✅ Tidak ada regresi kritikal di inventory/material endpoints.

## 3) Next Actions (Immediate)
Karena P1.A sudah selesai, next actions bergeser ke backlog berikutnya:

1. **Pilih next P1 dari Roadmap (butuh keputusan user):**
   - **P1.B — Maklon Orders Consolidation** (~12 jam)
   - **P1.C — Procure-to-Pay Completion (Create GR from PO)** (~14 jam)
   - **P1.D — Legacy Toko Migration** (~18 jam)

2. **Cleanup P1.A (post-monitoring 1 minggu):**
   - Pastikan tidak ada writes baru ke `acc_items` dan `acc_stock_movements`
   - Jika aman: drop collections legacy tersebut (sesuai protocol migration)

3. **Task related (separate scope, recommended next after P1.B/C/D):**
   - Migrasi `acc_opname_sessions/lines` → `wh_opname2_cycles/variances` (FORENSIC_04 Cluster B)

## 4) Success Criteria
**P1.A (completed):**
- ✅ `/api/acc/items` mengelola aksesoris yang tersimpan di `rahaza_materials (type='accessory')`.
- ✅ `/api/acc/stock` & `/api/acc/stock/*` menggunakan `rahaza_material_stock` + `rahaza_material_movements` sebagai SSOT.
- ✅ Endpoint existing tetap compatible dengan frontend (tanpa perubahan `AccessoryModule.jsx`).
- ✅ Migrasi idempotent, ada dry-run, dan validasi saldo per-item terbukti.
- ✅ testing_agent_v3 menyatakan flow aksesoris end-to-end berjalan (iteration_15: 29/29 PASS).

**Session-level completion gate:**
- ✅ PRD.md sudah diupdate dengan log P1.A
- ✅ Test report tersimpan: `/app/test_reports/iteration_15.json`

**Butuh keputusan user untuk melanjutkan:** pilih P1.B / P1.C / P1.D sebagai fokus berikutnya.