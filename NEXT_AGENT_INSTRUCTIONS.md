# 🤖 INSTRUKSI UNTUK AGENT SELANJUTNYA
## CV. Dewi Aditya ERP — Continuation Guide

**Last Updated:** 22 Mei 2026  
**Previous Agent:** Neo (12-Lens Forensic Audit + P0 + P2 GAP)  
**Status Project:** ✅ P0 + P2 GAP SELESAI — Siap masuk P1 Data Consolidation

---

## 🇮🇩 BAHASA — RULE #1 ABSOLUTE

> **WAJIB respon ke user dalam Bahasa Indonesia (id-ID).**

Aplikasi ini target user-nya Indonesia, semua label UI Bahasa Indonesia, dan user prompt dalam Bahasa Indonesia. **Jangan pernah balas dalam Bahasa Inggris ke user.**

Boleh pakai istilah teknis bahasa Inggris (e.g., "endpoint", "schema", "migration") karena ini adalah konvensi developer, tapi penjelasan/narasi harus Indonesia.

---

## 📚 DOKUMEN WAJIB DIBACA SEBELUM MULAI

**WAJIB baca dengan urutan ini, sebelum melakukan apapun:**

1. **`/app/memory/PRD.md`** — Master document dengan history semua session, decisions, dan backlog
2. **`/app/FORENSIC_00_EXECUTIVE_SUMMARY.md`** — Ringkasan audit forensik 12 lensa
3. **`/app/FORENSIC_11_MIGRATION_ROADMAP.md`** — Roadmap eksekusi P0→P3
4. **`/app/FORENSIC_04_DATA_ARCHITECTURE.md`** — DB consolidation plan
5. **`/app/FORENSIC_09_CONSOLIDATION_PLAN.md`** — 14 workflow consolidations
6. **`/app/FORENSIC_07_INFORMATION_ARCHITECTURE.md`** — Sidebar restructure plan (before/after)
7. **`/app/test_credentials.md` atau `/app/memory/test_credentials.md`** — Login credentials

Jika ada FORENSIC report lain yang relevan dengan task user, baca juga.

---

## 🎯 CURRENT STATE & APA YANG SUDAH DILAKUKAN

### ✅ SELESAI di Session 22 Mei 2026

#### Audit Forensik 12-Lens
12 dokumen audit komprehensif tersimpan di `/app/FORENSIC_*.md`.  
Mencakup: Information Architecture, Business Process Engineering, UX Systems, DDD, Operational Efficiency, Design System, Data Architecture, Cross-Module Dependency, Workflow Consolidation, Human-Centered.

#### P0 Quick Wins (5 jam, zero data risk)
- ✅ Fix 4 broken menu (`prod-rework-board`, `prod-alert-settings`, `maklon-cmt`, `maklon-packing`)
- ✅ Relocate `cmt-progress` ke Production portal
- ✅ Hapus duplikat stock views (`wh-accessory-master`, `wh-accessory-stock`)
- ✅ Hapus legacy `toko-channels`, `toko-pricing` dari Marketing
- ✅ Cleanup 25+ badge "BARU" + technical badges
- ✅ Hapus 3 file backup/placeholder orphan

#### P2 GAP Items
- ✅ Communication Hub — file upload + edit/delete messages **ALREADY DONE** (di session sebelumnya)
- ✅ Asset Management — transfer + photo upload **ALREADY DONE**
- ✅ My Workspace — spreadsheet editor + share + auto-save **ALREADY DONE**
- ✅ Marketing seed data — **NEW di session ini**: 5 platforms, 150 sales, 10 catalog, 6 KOLs, 50 orders

---

## 🚧 PRIORITY UNTUK SESSION SELANJUTNYA

### Rekomendasi Urutan Eksekusi (dari Roadmap)

#### NEXT: P1 — Data Consolidation
**Pilih salah satu dari 4 (sesuai keputusan user):**

##### Option A: P1.A — Accessory Consolidation (~25 jam, Medium risk)
- Migrate `acc_items` → `rahaza_materials` (with `type='accessory'`)
- Migrate `acc_stock_movements` → `rahaza_material_movements`
- Migrate `acc_opname_*` → `wh_opname2_*`
- **Preserve specialized:** `acc_loans`, `acc_purchase_requests`, `acc_internal_requests`
- Update backend routes (`/api/acc/*`)
- Update frontend `AccessoryModule.jsx`
- **Pre-req:** Backup database, dry-run migration, then production

##### Option B: P1.B — Maklon Orders Consolidation (~12 jam, Medium risk)
- Deprecate `dewi_maklon_orders` (lama)
- Migrate orphan data ke `dewi_maklon_pos`
- Update routes yang masih baca dari old collection
- Monitor 1 minggu, then delete

##### Option C: P1.C — Procure-to-Pay Completion (~14 jam, Medium risk)
- Implement "Create GR from PO" endpoint + UI button
- Auto pre-fill GR form dari PO data
- Status cascade: PO → Partial Receive → Full Receive → Invoice

##### Option D: P1.D — Legacy Toko Migration (~18 jam, Medium risk)
- 8 collections `dewi_toko_*` → migrate to `marketing_*` cluster
- Per-collection migration script (8 scripts)
- Update routes, then delete legacy

### Setelah P1: P2 Workflow Consolidation
14 konsolidasi konkret di `FORENSIC_09_CONSOLIDATION_PLAN.md`. **High-impact yang direkomendasikan first:**
- Maklon PO 360° View (6 modul → 1 tab-based) — big UX win
- HR Approval Inbox (5 → 1) — unified approvals
- Production Control Tower (4 → 1) — daily ops dashboard

### Setelah P2: P3 Architecture Long-Term
Lihat `FORENSIC_10_FUTURE_STATE_ARCHITECTURE.md` untuk visi DDD 8 bounded contexts.

---

## 📋 RULES OF ENGAGEMENT

### Rule #1: KOMUNIKASI USER WAJIB INDONESIA
Sudah dijelaskan di atas. **No exception.**

### Rule #2: BACA DOKUMEN AUDIT SEBELUM EKSEKUSI
Semua keputusan strategis sudah dianalisis di FORENSIC_*.md. **Jangan re-invent** atau ambil keputusan baru tanpa konsultasi dokumen.

### Rule #3: USER APPROVAL UNTUK MAJOR CHANGES
Sebelum:
- Migrasi DB
- Hapus collection/route/component
- Refactor besar (>3 file)
- Schema change

**WAJIB minta approval user dengan ringkasan dampak.**

### Rule #4: DECISION AUTHORITY SAYA (Agent)
User sudah delegate decision authority untuk:
- Konsolidasi menu/submenu yang memiliki same business goal
- Naming consistency improvements
- Dead code removal (after verification)
- Sidebar restructure (sesuai FORENSIC_07)

**Boleh eksekusi tanpa tanya, tapi report dampak.**

### Rule #5: TESTING WAJIB SETELAH PERUBAHAN
- Lint check (Python: ruff, JS: ESLint)
- Restart service yang relevan
- Screenshot/curl test untuk verify
- Untuk feature besar: panggil `testing_agent_v3`

### Rule #6: COMMIT TO SOURCE OF TRUTH (FORENSIC reports)
- Setiap perubahan strategis → update `/app/memory/PRD.md`
- Setiap completion phase → update relevan FORENSIC_*.md atau buat baru
- Setiap deviation dari roadmap → document alasannya

### Rule #7: ZERO TOLERANCE UNTUK BREAKING CHANGES
- **JANGAN** ubah `REACT_APP_BACKEND_URL` di `frontend/.env`
- **JANGAN** ubah `MONGO_URL` di `backend/.env`
- **JANGAN** ubah port binding (backend 0.0.0.0:8001)
- **JANGAN** ubah supervisor configs
- **PRESERVE** semua collection yang masih ditulis aktif

### Rule #8: USE BACKWARD-COMPAT REDIRECTS
Saat hapus/rename menu ID, **selalu** tambahkan redirect di `moduleRegistry.js`:
```javascript
'old-menu-id': makeRedirect('new-menu-id'),
```

### Rule #9: PRESERVE WHAT WORKS
- **JANGAN** rewrite module yang berfungsi tanpa alasan kuat
- Refactor incremental, bukan big-bang
- Test feature lama setelah refactor

### Rule #10: USE EXISTING TOOLS
- DB collection seeding: tambah ke `/app/backend/scripts/`
- UI patterns: gunakan Shadcn/UI dari `/app/frontend/src/components/ui/`
- Icons: Lucide-react ONLY
- HTTP calls: Pakai `process.env.REACT_APP_BACKEND_URL`

### Rule #11: INTEGRATION SERVICE PROTOCOL
Untuk integrasi LLM (OpenAI, Anthropic, Google):
1. Panggil `integration_playbook_expert_v2` dulu
2. Implementasi sesuai playbook
3. Pakai `EMERGENT_LLM_KEY` (universal key) via `emergentintegrations` library
4. Untuk service lain (Stripe, FAL, dll), juga via integration agent

### Rule #12: ALWAYS PROVIDE CONTEXT SAAT CALL SUB-AGENT
Saat panggil `testing_agent_v3` atau `design_agent`, **always include**:
- Original problem statement dari user
- Tech stack (FARM: FastAPI + React + MongoDB)
- Reference ke FORENSIC documents
- Test credentials (`admin@garment.com` / `Admin@123`)

---

## 🛠️ PRACTICAL COMMANDS

### Status Check
```bash
supervisorctl status                  # Check all services
tail -50 /var/log/supervisor/backend.err.log
tail -50 /var/log/supervisor/frontend.err.log
```

### Restart Services
```bash
supervisorctl restart backend         # After .env or requirements changes
supervisorctl restart frontend        # After package.json changes
```
**Catatan:** Hot reload otomatis untuk code changes. Restart hanya jika config/dep berubah.

### Database Access
```python
# Test DB connection in Python
cd /app/backend && python3 -c "
import asyncio
from database import get_db
async def check():
    db = get_db()
    cnt = await db.your_collection.count_documents({})
    print(f'Count: {cnt}')
asyncio.run(check())
"
```

### Run Seed Script
```bash
cd /app/backend && python3 scripts/seed_marketing_demo.py
```

### Backend API Test
```bash
# Get backend URL from frontend env
BACKEND_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2)
curl -X GET $BACKEND_URL/api/dashboard/overview \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Linting Before Test
```bash
# Use the lint tools
mcp_lint_python "/app/backend/routes/your_file.py"
mcp_lint_javascript "/app/frontend/src/components/erp/YourModule.jsx"
```

---

## 🔑 KEY FILES & CONVENTIONS

### Sidebar Configuration
- `/app/frontend/src/components/erp/PortalShell.jsx` — sidebar tree
- `/app/frontend/src/components/erp/moduleRegistry.js` — ID → React component mapping

**Format menu item:**
```javascript
{ id: 'unique-id', label: 'Display Label', icon: IconFromLucide, badge: 'AI' }
// indent: 1 — for sub-items under isHeader
// isHeader: true — for visual section headers (no click)
```

### Database Schema
- **UUIDs only** — `id` field is `str(uuid.uuid4())`, not MongoDB ObjectId
- **Timezone aware** — `datetime.now(timezone.utc)` saved as ISO string
- **Collection naming** — see FORENSIC_04 for target naming convention

### API Routes
- Prefix MUST be `/api/*` (Kubernetes ingress routing)
- Pattern: `/api/<domain>/<resource>/<action>` (e.g., `/api/rahaza/orders`)
- Specific routes BEFORE generic routes (e.g., `/users/me` before `/users/{id}`)

### Frontend State Management
- Local state: `useState`
- Cross-component: prop drilling OR context (existing: `ProductionUIContext`)
- Server state: Direct fetch with manual cache
- No Redux/Zustand currently (keep simple)

---

## 🎨 DESIGN SYSTEM (MANDATORY)

Baca `/app/design_guidelines.md` untuk detail. Highlights:

- **Components:** Shadcn/UI ONLY dari `@/components/ui/`
- **Icons:** Lucide-react ONLY (no emoji icons)
- **Colors:** CSS variables dari `index.css`, no hardcoded
- **Forms:** Shadcn `Form` pattern
- **Tables:** `DataTableV2.jsx` (deprecate v1)
- **Modals:** Shadcn `Dialog` (deprecate custom `Modal.jsx`)
- **Toast:** Sonner from `@/components/ui/sonner`
- **Test IDs:** `data-testid="kebab-case-descriptive"` on all interactive

---

## 💬 SAMPLE FIRST INTERACTION

When you receive a task, follow this template:

```
Halo! Saya [Agent Name], melanjutkan dari session sebelumnya.

📋 Status terakhir: P0 Quick Wins + P2 GAP Items SELESAI ✅
🚧 Next priorities: P1 Data Consolidation (4 options) atau P2 Workflow Consolidation (14 options)

Saya sudah baca:
- /app/memory/PRD.md
- /app/FORENSIC_00_EXECUTIVE_SUMMARY.md
- /app/FORENSIC_11_MIGRATION_ROADMAP.md

Berdasarkan request Anda "[user's message]", saya rekomendasi:
1. [Specific task from roadmap]
2. [Estimated effort]
3. [Risk level]

Apakah lanjut dengan opsi ini atau ada pilihan lain dari roadmap?
```

---

## ⚠️ COMMON PITFALLS TO AVOID

1. **Jangan rewrite `server.py`** — file sudah besar (1542 lines) dengan banyak include_router. Tambah route baru via include_router pattern.

2. **Jangan ubah PortalShell.jsx besar-besaran sekaligus** — Edit per section dengan `search_replace`. File ini 1439 lines.

3. **Jangan delete collection tanpa verify writes** — Cek apakah ada endpoint yang masih `INSERT` ke sana via grep.

4. **Jangan create new "rahaza_*" atau "dewi_*" collections** — Target naming sudah ditentukan (domain-based: `production_*`, `inventory_*`, dll). Lihat FORENSIC_04.

5. **Jangan skip backup files cleanup verification** — Ada file seperti `RahazaHPPModule.jsx.backup` yang harus dihapus. Cari dengan `find /app -iname "*.backup" -o -iname "*Placeholder*"`.

6. **Jangan ignore badge clutter** — User secara eksplisit tidak suka badge "BARU" yang stale. Default: tidak ada badge kecuali truly new (with auto-expire).

7. **Jangan lewat audit phase** — Selalu konsultasi dokumen FORENSIC dulu sebelum eksekusi.

---

## 📊 SCORECARD TARGET

Setelah seluruh roadmap selesai (P0+P1+P2+P3):

| Metric | Sebelum | Target |
|--------|---------|--------|
| Sidebar items | 205 | ~140 (-32%) |
| Backend routes | 194 | ~150 (-23%) |
| Frontend components | 270 | ~220 (-19%) |
| MongoDB collections | 280 | ~230 (-18%) |
| Avg time-to-task | 3.6x optimal | 1.5x optimal |
| Cognitive load score | 4/10 | 8/10 |
| Code maintainability | 5/10 | 8/10 |
| System Health Score | 4.0/10 | 8.5/10 |

---

## 🏁 FINAL CHECKLIST SEBELUM MULAI

- [ ] Baca `/app/memory/PRD.md` end-to-end
- [ ] Baca minimal `FORENSIC_00` + `FORENSIC_11`
- [ ] Cek `supervisorctl status` (semua RUNNING)
- [ ] Test login di preview URL dengan `admin@garment.com` / `Admin@123`
- [ ] Tanya user **dalam Bahasa Indonesia** mau lanjut P1 mana / atau prioritas lain
- [ ] Setelah approval, baru eksekusi

---

## 🤝 KONTRAK ANTAR-AGENT

Saya (agent sebelumnya) sudah:
- ✅ Melakukan audit komprehensif 12-lens
- ✅ Eksekusi P0 Quick Wins (zero risk)
- ✅ Seed marketing data
- ✅ Update PRD.md
- ✅ Tinggalkan instruksi ini

Anda (agent selanjutnya) sebaiknya:
- 🎯 Lanjutkan dari P1 Data Consolidation
- 🎯 Setiap perubahan strategis: update PRD.md
- 🎯 Setiap selesai phase: report ke user + update FORENSIC roadmap
- 🎯 Pertahankan kontinuitas: jangan re-audit, jangan re-decide

**Selamat melanjutkan! 🚀**

---

_Document ini wajib di-update saat ada agent baru. Add session log di bawah._

## SESSION LOG

### Session 22 Mei 2026 (Agent: Neo)
- Audit Forensik 12-Lens (12 deliverables di /app/FORENSIC_*.md)
- P0 Quick Wins (5 jam)
- P2 GAP Items: Marketing seed (5 platforms, 150 sales records, 6 KOL, 50 orders)
- Update PRD.md
- Create NEXT_AGENT_INSTRUCTIONS.md (file ini)

### Session [DD MMM YYYY] (Agent: [Name])
- [Add your session summary here]
