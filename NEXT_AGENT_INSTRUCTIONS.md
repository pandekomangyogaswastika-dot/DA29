# 🤖 NEXT AGENT INSTRUCTIONS
## CV. Dewi Aditya ERP — Quick Start untuk Agent Berikutnya

**Last Updated:** 22 Mei 2026  
**Previous Session:** Audit Forensik 12-Lens + P0 Quick Wins + P2 GAP  
**System Health:** 5.5/10 (improving from 4.0)  
**Bahasa:** 🇮🇩 **WAJIB respon ke user dalam Bahasa Indonesia**

---

## 🔴 STEP 0 — BACA INI DULU (TIDAK BOLEH DI-SKIP)

```
1. /app/AGENT_DEVELOPMENT_RULES.md    ← MANDATORY RULES (anti-tech-debt)
2. /app/memory/PRD.md                  ← Product context + session history
3. /app/FORENSIC_00_EXECUTIVE_SUMMARY.md  ← Audit ringkasan
4. /app/FORENSIC_11_MIGRATION_ROADMAP.md  ← Roadmap eksekusi
```

**Tanpa baca ke-4 dokumen ini, Anda akan mengulangi technical debt yang sama.**

---

## 📋 CURRENT STATE SISTEM

### ✅ Sudah Selesai
| Phase | Status | Details |
|-------|--------|---------|
| **Forensic Audit** | ✅ DONE | 12 deliverables di `/app/FORENSIC_*.md` |
| **P0 Quick Wins** | ✅ DONE | 4 broken menus fixed, sidebar cleaned, 3 backup files deleted |
| **P2 GAP Items** | ✅ DONE | Comm Hub, Asset Mgmt, Workspace (sudah implemented sebelumnya), Marketing seeded |

### 🚧 Pending (di Roadmap, perlu eksekusi)

#### **P1 — Data Consolidation** (Total ~69 jam, MEDIUM risk)
Pilih satu dengan user untuk eksekusi:

**P1.A — Accessory Consolidation** (~25 jam)
- Migrate `acc_items` → `rahaza_materials` (with type='accessory')
- Migrate `acc_stock_movements` → `rahaza_material_movements`
- Preserve: `acc_loans`, `acc_purchase_requests`, `acc_internal_requests`
- 📖 Detail: `FORENSIC_04_DATA_ARCHITECTURE.md` Section "Cluster 1"

**P1.B — Maklon Orders Consolidation** (~12 jam)
- Deprecate `dewi_maklon_orders` → use `dewi_maklon_pos` saja
- 📖 Detail: `FORENSIC_04_DATA_ARCHITECTURE.md` Section "Cluster 2"

**P1.C — Procure-to-Pay Completion** (~14 jam)
- Implement "Create GR from PO" backend + frontend
- 📖 Detail: `FORENSIC_03_BUSINESS_PROCESS_MAP.md` Section "BP1"

**P1.D — Legacy Toko Migration** (~18 jam)
- 8 collections `dewi_toko_*` → migrate ke `marketing_*`
- 📖 Detail: `FORENSIC_04_DATA_ARCHITECTURE.md` Section "Cluster 7"

#### **P2 — Workflow Consolidation** (Total ~180 jam)
14 konsolidasi konkret di `FORENSIC_09_CONSOLIDATION_PLAN.md`.

High-impact picks:
- 🌟 **Maklon PO 360° View** (6 modul → 1 tab-based) — big UX win
- 🌟 **HR Approval Inbox** (5 → 1) — unified approvals
- 🌟 **Production Control Tower** (4 → 1) — daily ops dashboard

#### **P3 — Architecture Long-Term** (Total ~120 jam)
- Notification unification, Counter unification, Performance/KPI cleanup
- Warehouse Gen 1 cleanup, Design system standardization
- Global Workspace Dashboard, Naming convention phase-out
- 📖 Detail: `FORENSIC_10_FUTURE_STATE_ARCHITECTURE.md`

### 🐛 Tech Debt Backlog (track baru)

```markdown
# TECH DEBT IDENTIFIED IN AUDIT (must be addressed eventually)

## File Size Violations (MUST refactor per AGENT_DEVELOPMENT_RULES Protocol #2.1)
- [TD-001] AssetManagementPortal.jsx (3124 lines) — split into 5+ sub-modules
- [TD-002] LiveHostModule.jsx (~2300 lines) — split per feature
- [TD-003] dewi_asset_management.py (2392 lines) — split per aggregate
- [TD-004] CommunicationHubPortal.jsx (1751 lines) — extract sub-components
- [TD-005] dewi_communication.py (1141 lines) — split channels/messages/threads
- [TD-006] WorkspacePortal.jsx (1364 lines) — extract editor + dialogs
- [TD-007] PortalShell.jsx (1439 lines) — extract sidebar tree to JSON config

## Data Architecture Tech Debt
- [TD-008] 3 opname systems parallel (see FORENSIC_04 Cluster B)
- [TD-009] 4 accessory systems (see FORENSIC_04 Cluster 1)
- [TD-010] 3 namespace prefixes mixed (rahaza_/dewi_/wms_)
- [TD-011] 280+ collections (target: <230)
- [TD-012] 30+ orphan registry IDs in moduleRegistry.js

## UI/UX Tech Debt
- [TD-013] DataTable v1 still used in ~30 modules (migrate to V2)
- [TD-014] Custom Modal.jsx coexists with Shadcn Dialog
- [TD-015] Tables not responsive on mobile
- [TD-016] Form patterns inconsistent across modules

## Performance Tech Debt
- [TD-017] No bundle size monitoring
- [TD-018] Some routes lack proper indexing
- [TD-019] N+1 queries in some report endpoints
```

---

## 🚀 RECOMMENDED FIRST ACTIONS

### Step 1: Read Mandatory Docs (15 menit)
Baca 4 dokumen di atas.

### Step 2: Verify System Health
```bash
supervisorctl status
# Expected: backend RUNNING, frontend RUNNING, mongodb RUNNING

# Login test
# URL: from REACT_APP_BACKEND_URL in /app/frontend/.env
# Credentials: admin@garment.com / Admin@123
```

### Step 3: Sapa User dalam Bahasa Indonesia

Template sapaan:
```
Halo! Saya melanjutkan dari session sebelumnya yang telah menyelesaikan:
- ✅ Audit Forensik 12-Lens (12 dokumen di /app/FORENSIC_*.md)
- ✅ P0 Quick Wins (4 broken menus fixed, sidebar dibersihkan)
- ✅ P2 GAP Items (Marketing seeded, Comm Hub/Asset Mgmt/Workspace sudah lengkap)

Saya sudah baca:
- /app/AGENT_DEVELOPMENT_RULES.md (rules anti-tech-debt)
- /app/memory/PRD.md
- /app/FORENSIC_00_EXECUTIVE_SUMMARY.md
- /app/FORENSIC_11_MIGRATION_ROADMAP.md

Berdasarkan request Anda "[user message]", saya rekomendasi:

[Specific recommendation dari roadmap]

Mau lanjut dengan ini, atau ada prioritas lain? 🙏
```

---

## 🗺️ FILE MAP — Dokumen Penting

```
📂 /app/
├── 📄 README.md                            ← Project overview
├── 📄 AGENT_DEVELOPMENT_RULES.md          ← 🔴 MANDATORY RULES
├── 📄 NEXT_AGENT_INSTRUCTIONS.md          ← (file ini)
├── 📄 design_guidelines.md                 ← UI/UX bible
├── 📄 WORKSPACE_DESIGN.md                  ← Workspace feature spec
├── 📄 MARKETING_KOL_LIVEHOST_DOCUMENTATION.md  ← KOL feature spec
│
├── 📊 FORENSIC_00_EXECUTIVE_SUMMARY.md    ← Audit ringkasan + Top 10 findings
├── 📊 FORENSIC_01_INVENTORY_BASELINE.md   ← Inventarisasi sistem
├── 📊 FORENSIC_02_DEPENDENCY_GRAPH.md     ← Menu→Route→Component→API→DB
├── 📊 FORENSIC_03_BUSINESS_PROCESS_MAP.md ← 10 E2E business flows
├── 📊 FORENSIC_04_DATA_ARCHITECTURE.md    ← 12 cluster DB consolidation
├── 📊 FORENSIC_05_UX_EFFICIENCY_REPORT.md ← Cognitive load + friction
├── 📊 FORENSIC_06_DESIGN_SYSTEM_AUDIT.md  ← UI consistency
├── 📊 FORENSIC_07_INFORMATION_ARCHITECTURE.md ← Sidebar restructure
├── 📊 FORENSIC_08_DEAD_CODE_INVENTORY.md  ← Cleanup list
├── 📊 FORENSIC_09_CONSOLIDATION_PLAN.md   ← 14 workflow merges
├── 📊 FORENSIC_10_FUTURE_STATE_ARCHITECTURE.md ← DDD target
├── 📊 FORENSIC_11_MIGRATION_ROADMAP.md    ← P0→P3 sequence
│
└── 📂 memory/
    ├── 📄 PRD.md                           ← Product requirements + history
    └── 📄 test_credentials.md              ← Login credentials
```

---

## ⚠️ TOP 10 PITFALLS TO AVOID

(Anti-pattern yang sudah pernah terjadi — JANGAN ulangi)

1. **JANGAN buat collection baru** sebelum cek apakah existing collection bisa di-extend
2. **JANGAN buat component baru** sebelum cek `find /app/frontend/src -iname "*Keyword*"`
3. **JANGAN rewrite file** kalau >500 lines — split dulu
4. **JANGAN ubah `server.py` besar-besaran** — gunakan pattern `include_router`
5. **JANGAN biarkan badge "BARU"** stale — set expiry atau hapus
6. **JANGAN buat naming pakai prefix `rahaza_` atau `dewi_`** — pakai domain prefix
7. **JANGAN delete collection tanpa monitor 1 minggu** dulu (cek tidak ada writes)
8. **JANGAN skip update PRD.md** setelah session
9. **JANGAN balas user dengan Bahasa Inggris**
10. **JANGAN lewat Step 0** (baca docs dulu)

---

## 🎯 SUCCESS METRICS (untuk track progress)

### Per Session
- Lines code added vs deleted (favor deletion)
- File size compliance (per AGENT_DEVELOPMENT_RULES #2.1)
- Lint warnings (zero target)
- Tasks from roadmap completed
- PRD.md updated

### Cumulative System Health (target post P3)
| Metric | Sekarang | Target P3 |
|--------|----------|-----------|
| Sidebar items | ~170 | ~140 |
| Backend routes | 194 | ~150 |
| Components | 270 | ~220 |
| Collections | 280 | ~230 |
| Avg time-to-task | 3.6x | 1.5x optimal |
| System Health | 5.5/10 | 8.5/10 |
| File size violations | 7+ | 0 |

---

## 📞 ESCALATION

Jika stuck setelah 2 percobaan:
1. **Read FORENSIC docs** lagi — kemungkinan ada konteks yang missed
2. **Call `troubleshoot_agent`** untuk RCA
3. **Ask user** dalam Bahasa Indonesia dengan context lengkap

---

## 🤝 KONTRAK ANTAR-AGENT

### Agent Sebelumnya (Neo - 22 Mei 2026) Sudah:
- ✅ Audit Forensik 12-Lens lengkap (12 deliverables)
- ✅ Execute P0 Quick Wins (zero risk)
- ✅ Marketing data seeded
- ✅ Update PRD.md
- ✅ Create AGENT_DEVELOPMENT_RULES.md (rules anti-tech-debt)
- ✅ Cleanup 12 outdated docs

### Agent Selanjutnya (Anda) HARUS:
- 🎯 Baca AGENT_DEVELOPMENT_RULES.md SEBELUM mulai
- 🎯 Lanjut dari P1 Data Consolidation (per roadmap)
- 🎯 Patuhi semua 12 protocols di RULES
- 🎯 Update PRD.md setiap major change
- 🎯 Jangan re-invent atau re-decide tanpa baca docs
- 🎯 Bahasa Indonesia ke user, ALWAYS

---

## 📅 SESSION LOG

Tambahkan log Anda di sini setelah selesai session:

### Session 22 Mei 2026 (Agent: Neo)
**Tasks:** Forensic Audit + P0 + P2 GAP + Docs cleanup + Anti-tech-debt rules
**Files:** PortalShell.jsx, moduleRegistry.js, seed_marketing_demo.py, PRD.md, AGENT_DEVELOPMENT_RULES.md
**DB:** marketing_* seeded (5 platforms, 150 sales, 6 KOL, 50 orders)
**Decisions:** Confirmed user approval for all 4 strategic decisions (Accessory SSOT, Maklon DB, Toko migration, Broken menus fix)
**Next:** P1 Data Consolidation (4 options) atau P2 Workflow Consolidation

### Session [Date] (Agent: [Name])
- [Add your session entry here following format above]

---

**🚀 Selamat melanjutkan! Patuhi RULES untuk hindari technical debt recurring.**
