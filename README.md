# DA14 ERP - CV. Dewi Aditya

> 🆕 **STATUS UPDATE — 2026-05-08 (Session 5 closing)**: Real-time Executive KPIs ✅, AI Cash-Flow Prediction (Emergent LLM) ✅, Portal Saya Cuti & Lembur ✅, LMS Certificate PDF 🟡 (implemented, **awaiting testing_agent_v3 verification**), MongoDB-backed Rate Limiter 🔴 (P1, not started). Full breakdown in `/app/memory/PRD.md → Session 5`.

> ⚠️ **User-imposed constraints (DO NOT VIOLATE)**:
> - **Lanjutkan SELAIN integrasi** — jangan tambah 3rd-party API integration baru tanpa instruksi eksplisit (Shopee/TikTok/Twilio WA/Google Cal di-block).
> - **Lanjutkan SELAIN split** — jangan split file monster (`dewi_kpi.py`, `HRKPIModule.jsx`, dll). User akan minta sendiri kalau perlu.
> - **Bahasa**: Selalu balas user dalam **Bahasa Indonesia**.

## 🎯 INSTRUKSI PENTING UNTUK AI AGENT BERIKUTNYA

### 📚 WAJIB DIBACA SEBELUM MULAI DEVELOPMENT:

Sebelum Anda mengerjakan **APAPUN**, Anda **HARUS** membaca dokumen-dokumen berikut secara BERURUTAN:

1. **`/app/memory/PRD.md`** — Product Requirements Document
   - Berisi: Fitur yang sudah diimplementasi (Sprint 1-40 + Session 1-5)
   - Berisi: Prioritized backlog (P0/P1/P2) dengan status terbaru
   - Berisi: Reference ke `test_credentials.md` dan key endpoints (termasuk Session 5: AI Cashflow, LMS Certificate, Cuti/Lembur)
   - **STATUS**: ✅ Updated (2026-05-08) — P0 completed, P1 partially done, Session 5 added with LMS pending test

2. **`/app/plan.md`** — Current Session Execution Plan
   - Berisi: Objectives sesi saat ini dan progress detail
   - Berisi: Implementation steps dengan exit gates
   - Berisi: Success criteria untuk setiap phase
   - **STATUS**: ✅ Current working document — selalu update ini setelah selesai task

3. **`/app/memory/AUDIT_COMPREHENSIVE_2026-05-05.md`** — Comprehensive System Audit
   - Berisi: Review mendalam per portal (score, bugs, rekomendasi)
   - Berisi: Cross-cutting issues (pagination, testing, security)
   - Berisi: Priority recommendations (Top 10 tasks)
   - **PENTING**: Cek section "RENCANA AKSI PRIORITY" untuk tahu task apa yang harus dikerjakan

4. **`/app/memory/MASTER_ANALYSIS_AND_PLAN.md`** — Master Architecture & Roadmap
   - Berisi: Transformasi PT Rahaza → CV. Dewi Aditya
   - Berisi: 7 Fase pengembangan (Fondasi → Analytics & AI)
   - Berisi: Gap analysis modul existing vs kebutuhan
   - **GUNAKAN INI** untuk memahami big picture dan future roadmap

5. **`/app/test_reports/iteration_12.json`** — Latest Test Report
   - Berisi: Testing results terakhir (backend + frontend)
   - Berisi: Bug list yang ditemukan dan sudah/belum difix
   - **CEK INI** sebelum claim "sudah selesai" — pastikan tidak ada bug

6. **`/app/memory/test_credentials.md`** — 🆕 Test Credentials (single source of truth)
   - Berisi: Email + password untuk SuperAdmin, Maklon Client, KOL Creator
   - **WAJIB UPDATE** kalau Anda buat / ubah credential auth (admin baru, demo user, seed script)
   - Testing agent baca file ini sebelum auth flow — kalau kosong/missing, tests gagal

7. **`/app/memory/MEMORY_SYNC_INSTRUCTIONS.md`** — 🆕 Workflow guide untuk AI agent
   - Berisi: Step-by-step onboarding → planning → coding → testing → docs update → handover
   - Berisi: Common mistakes & escalation protocol
   - **BACA SEKALI** di awal session, lalu rujuk saat ragu

### 🔄 WORKFLOW YANG HARUS DIIKUTI:

**STEP 1: SYNC MEMORY (SETIAP KALI AGENT BARU MULAI)**
```
1. Read `/app/memory/PRD.md` → Pahami apa yang sudah ada
2. Read `/app/plan.md` → Pahami task yang sedang dikerjakan
3. Read latest test report → Pahami status testing
4. JANGAN LANGSUNG CODING — Ask user dulu untuk klarifikasi prioritas
```

**STEP 2: SEBELUM IMPLEMENT FITUR BARU**
```
1. Update `/app/plan.md` → Tambahkan task baru ke dalam plan
2. Breakdown task menjadi sub-tasks yang spesifik
3. Set success criteria yang jelas dan terukur
4. Confirm dengan user sebelum mulai coding
```

**STEP 3: SETELAH SELESAI IMPLEMENT**
```
1. Testing menggunakan testing_agent_v3 (MANDATORY untuk fitur baru)
2. Fix semua bugs yang ditemukan (prioritas: High → Medium → Low)
3. Update `/app/plan.md` → Mark task as completed
4. Update `/app/memory/PRD.md` → Tambahkan fitur ke section "What's Been Implemented"
5. JANGAN SKIP testing — ini yang paling sering dilupakan!
```

**STEP 4: SEBELUM FINISH SESSION**
```
1. Pastikan semua test PASS (backend + frontend)
2. Pastikan tidak ada critical bugs yang belum difix
3. Update dokumentasi memory dengan status terbaru
4. Buat summary untuk user tentang apa yang sudah dikerjakan
```

### ⚠️ YANG TIDAK BOLEH DILAKUKAN:

❌ **JANGAN** mulai coding tanpa membaca memory documents
❌ **JANGAN** mengubah kode tanpa memahami konteks dari plan.md
❌ **JANGAN** claim task "completed" tanpa testing
❌ **JANGAN** ignore bug reports dari testing agent
❌ **JANGAN** skip update dokumentasi setelah selesai implement
❌ **JANGAN** refactor "monster files" tanpa comprehensive test suite
❌ **JANGAN** break backward compatibility tanpa approval user

### ✅ BEST PRACTICES:

✅ **SELALU** baca memory documents sebelum mulai (workflow step 1)
✅ **SELALU** update plan.md sebelum dan sesudah implement
✅ **SELALU** run testing_agent_v3 untuk fitur baru/bug fix
✅ **SELALU** fix ALL bugs (even low priority) sebelum finish
✅ **SELALU** maintain backward compatibility kecuali ada breaking change yang disetujui
✅ **SELALU** tanya user jika ada ambiguitas atau keputusan penting

### 📊 CURRENT STATUS (Last Updated: 2026-05-08)

**Session 4 — COMPLETED ✅**
- P0.1: Brute-force protection Maklon Client Portal ✅
- P0.2: Portal Saya verification ✅  
- P0.3: Pagination rollout (global safety + proper pagination) ✅
- P1/P2: Portal Saya photo upload ✅
- P1/P2: Bank Reconciliation CSV import ✅
- P1/P2: Bank Reconciliation auto-match ✅

**Session 5 — MOSTLY DONE 🟡**
- ✅ Rebranding PT Rahaza → CV. Dewi Aditya
- ✅ Executive Dashboard real-time KPIs (Manajemen)
- ✅ AI Cash-Flow Prediction (Finance, Emergent LLM)
- ✅ Portal Saya: Cuti & Lembur self-service
- 🟡 LMS Certificate PDF download — **needs testing_agent_v3 verification** (endpoint `GET /api/portal/training/{enrollment_id}/certificate`)
- ✅ Memory documentation refresh (PRD + this README + MEMORY_SYNC_INSTRUCTIONS.md created)

**Testing Status:**
- Backend pytest: 13/13 PASS ✅ (iteration_12.json)
- No critical regressions ✅
- LMS Certificate flow: ⚠️ NOT YET RUN through testing agent

**Next Priority Tasks (Recommended for incoming agent):**
1. 🔴 **Run testing_agent_v3_fork** untuk LMS Certificate PDF (backend + frontend) — top priority
2. 🟠 **Migrate rate limiter** dari `defaultdict` (in-memory) ke MongoDB collection + TTL index — `server.py:677`
3. 🟡 Continue pagination rollout to high-traffic endpoints (operations, production, dashboard)
4. 🟡 Expand automated test coverage (KPI calc, payroll, journal posting)
5. 🟢 Performance optimization (add indexes for common filter fields)
