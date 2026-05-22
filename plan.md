# plan.md — P1.A Accessory Consolidation (SSOT: `rahaza_materials`)

## 1) Objectives
- Konsolidasi 4 sistem aksesoris paralel menjadi **1 SSOT internal** berbasis `rahaza_*` tanpa mengubah kontrak API.
- **API-stable:** semua endpoint `/api/acc/*` tetap ada dan tetap compatible dengan `AccessoryModule.jsx` (tidak diubah).
- Migrasi data aman: **tanpa data loss**, dengan dry-run + validasi count + sampling.
- Core stock logic aksesoris konsisten dengan sistem inventory utama (`rahaza_material_stock` + `rahaza_material_movements`).

## 2) Implementation Steps (Phased)

### Phase 1 — Core POC (Isolated) ✅ Wajib sebelum refactor besar
**Core workflow:** “Aksesoris master + receive/issue stok + saldo stok konsisten” via `/api/acc/*` tetapi backed by `rahaza_*`.

User stories (POC):
1. Sebagai admin, saya bisa membuat item aksesoris via `/api/acc/items` dan item tersebut tersimpan sebagai `rahaza_materials.type='accessory'`.
2. Sebagai admin, saya bisa menerima stok aksesoris dan stok tersebut tercatat di `rahaza_material_stock`.
3. Sebagai admin, saya bisa mengeluarkan stok aksesoris dan stok berkurang serta tercatat di `rahaza_material_movements`.
4. Sebagai admin, saya bisa melihat daftar stok `/api/acc/stock` yang sesuai dengan SSOT (bukan agregasi `acc_stock_movements`).
5. Sebagai admin, saya bisa melihat histori movements `/api/acc/stock/movements` untuk satu aksesoris.

Steps:
1. Tambah **POC script**: `/app/backend/migrations/poc_accessory_ssot.py`
   - Create 1 accessory (via direct DB insert atau call endpoint)
   - Receive 10 pcs ke lokasi `ZNA-AKSESORIS`
   - Issue 3 pcs
   - Assert saldo akhir = 7 dan movement count sesuai.
2. Implement minimal adapter di `dewi_accessories_full.py` (tanpa hapus endpoint):
   - `list_items`, `create_item`, `update_item`, `get_stock_overview`, `receive_stock`, `issue_stock`, `get_movements`
   - Semua baca/tulis ke `rahaza_materials`, `rahaza_material_stock`, `rahaza_material_movements`
3. Jalankan POC script sampai PASS.

Exit gate Phase 1:
- POC script PASS (saldo & movements konsisten) dan endpoint terkait `/api/acc/*` merespon 200/201 sesuai.

---

### Phase 2 — V1 Refactor Backend (SSOT internal, API tetap)
User stories (Backend V1):
1. Sebagai user gudang, saya melihat stok aksesoris yang sama antara modul Gudang dan modul Aksesoris.
2. Sebagai admin, saya dapat mencari aksesoris (code/name/category) via `/api/acc/items?search=...`.
3. Sebagai admin, saya dapat mengatur `min_stock` dan indikator low/out stock tetap benar.
4. Sebagai admin, saya dapat membuat internal request dan saat status “Issued”, stok berkurang di SSOT.
5. Sebagai admin, saya dapat membuat peminjaman (loan) yang mengurangi stok dan return yang mengembalikan stok.

Steps:
1. Refactor penuh `dewi_accessories_full.py` dengan prinsip “API facade”:
   - **MASTER**: map `acc_items` → `rahaza_materials (type='accessory')`
   - **STOCK**: map operasi stok → `rahaza_material_stock` + `_log_movement()` (schema `rahaza_material_movements`)
   - **MOVEMENTS LIST**: `/api/acc/stock/movements` query dari `rahaza_material_movements` (filter by material_id)
   - Preserve koleksi feature-unik tetap: `acc_internal_requests`, `acc_loans`, `acc_purchase_requests`
2. Pastikan field mapping minimal:
   - `acc_items.{id,code,name,category,unit,description,min_stock,supplier,notes,deleted}` → `rahaza_materials.{id,code,name,type='accessory',unit,notes,min_stock,active}`
   - Simpan `category/supplier/description` ke `notes` atau field tambahan bila sudah ada (tanpa membuat collection baru).
3. Update stock computations:
   - `_stock_qty` dan `_all_stock` jangan lagi agregasi `acc_stock_movements`.
   - Hitung stok dari `rahaza_material_stock` (sum semua lokasi untuk material_id) agar konsisten.
4. Update side-effects writer:
   - `internal-requests -> Issued` membuat movement `type='issue'` + update stock.
   - `loans` membuat movement `type='issue'` (atau `loan_out` dengan type khusus) + update stock.
   - `loan return` membuat movement `type='receive'`/`loan_return` + update stock.
   - `purchase-requests -> Received` membuat movement `type='receive'` + update stock.

Exit gate Phase 2:
- Semua endpoint `/api/acc/*` berfungsi tanpa perubahan frontend.
- Tidak ada query lagi ke `acc_items` / `acc_stock_movements` untuk master & stok.

---

### Phase 3 — Data Migration (acc_* → rahaza_*) + Validation
User stories (Migration):
1. Sebagai admin, setelah migrasi saya tetap melihat item aksesoris lama muncul di modul Aksesoris.
2. Sebagai admin, histori pergerakan stok aksesoris lama tetap bisa ditelusuri.
3. Sebagai admin, saldo stok akhir tidak berubah sebelum vs sesudah migrasi.
4. Sebagai auditor, saya bisa melihat laporan validasi count dan sampling hasil migrasi.
5. Sebagai operator, tidak ada downtime panjang (migrasi idempotent dan bisa diulang).

Steps:
1. Buat migration script: `/app/backend/migrations/migrate_accessories.py`
   - Mode `--dry-run` (default): hitung source/target, sample transform
   - Mode `--execute`: upsert ke `rahaza_materials` & append/transform ke `rahaza_material_movements`
   - Idempotent: gunakan `id` yang sama, dan dedup movement dengan `id`.
2. Migrasi:
   - `acc_items` → `rahaza_materials` (set `type='accessory'`, `active=True`, mapping unit/min_stock)
   - `acc_stock_movements` → `rahaza_material_movements`
     - map `acc_id` → `material_id`
     - map `qty_signed` + `movement_type` → `type` + `qty` (gunakan sign pada qty atau field type+qty)
     - set `ref_type/ref_id/ref_number/notes/created_at/created_by_name` bila tersedia.
3. Validasi:
   - count match (items)
   - saldo per-item match (sample 20 item) sebelum/after
   - movement count match (atau documented transform) + sampling 20 rows.
4. Setelah migrasi, **jangan drop** legacy collections (monitoring 1 minggu) — hanya stop writing.

Exit gate Phase 3:
- Dry-run + execute menghasilkan report validasi PASS.
- Semua akses master/stock sudah memakai `rahaza_*`.

---

### Phase 4 — Testing & Regression
User stories (QA):
1. Sebagai admin, saya bisa end-to-end: create item → receive → issue → lihat stock & movements.
2. Sebagai admin, saya bisa end-to-end: internal request → approve → issued → stok berkurang.
3. Sebagai admin, saya bisa end-to-end: loan → return → stok kembali.
4. Sebagai admin, saya bisa end-to-end: purchase request → received → stok bertambah.
5. Sebagai admin, dashboard aksesoris menampilkan metrik yang benar.

Steps:
1. Jalankan `testing_agent_v3` fokus modul aksesoris.
2. Jalankan pytest subset terkait bila ada (atau minimal smoke via curl untuk endpoint utama).
3. Fix bug sampai PASS.
4. Update docs: `PRD.md` + catat hasil migrasi & langkah rollback.

Exit gate Phase 4:
- testing_agent_v3 PASS untuk flow aksesoris.
- Tidak ada regresi kritikal di inventory/material endpoints.

## 3) Next Actions (Immediate)
1. Implement POC script `poc_accessory_ssot.py` dan minimal adapter di `dewi_accessories_full.py` untuk 7 endpoint core.
2. Jalankan POC sampai PASS.
3. Lanjut refactor penuh writers (issued/loans/purchase received) ke SSOT.
4. Buat migration script `migrate_accessories.py` + dry-run report.

## 4) Success Criteria
- `/api/acc/items` mengelola aksesoris yang tersimpan di `rahaza_materials (type='accessory')`.
- `/api/acc/stock` & `/api/acc/stock/*` menggunakan `rahaza_material_stock` + `rahaza_material_movements` sebagai SSOT.
- Endpoint existing tetap compatible dengan frontend (tanpa perubahan `AccessoryModule.jsx`).
- Migrasi dapat dijalankan idempotent, ada dry-run, dan validasi saldo per-item terbukti.
- testing_agent_v3 menyatakan flow aksesoris end-to-end berjalan.
