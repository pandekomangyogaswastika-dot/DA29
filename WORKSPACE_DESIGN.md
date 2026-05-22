# 📁 WORKSPACE PORTAL - Design Document

## 🎯 Konsep: Personal Workspace dengan Grid Editor

### **Vision:**
Setiap user punya **personal workspace** untuk:
- Create & edit spreadsheets (simplified Excel)
- Simpan file pribadi (spreadsheets, dokumen)
- Share file ke user/team lain dengan permissions
- Import/Export dari Excel
- Import data dari system modules (Asset, Procurement, dll)
- Export data balik ke system modules

---

## 🏗️ ARSITEKTUR

### **1. Portal Structure**

```
CV. Dewi Aditya ERP
├── Dashboard
├── HR Management
├── WMS
├── Marketing
├── Finance
├── Communication Hub
├── Asset Management
└── 🆕 MY WORKSPACE ← NEW!
    ├── My Documents (Private files)
    ├── Shared with Me (Files dari user lain)
    ├── Spreadsheets (Grid editor)
    ├── Recent Files
    └── Trash
```

---

### **2. Database Schema**

#### **Collection: `workspace_documents`**
```json
{
  "id": "uuid",
  "type": "spreadsheet" | "text" | "uploaded_file",
  "name": "Asset Planning 2026",
  "description": "Draft asset procurement planning",
  "owner_id": "user_uuid",
  "owner_name": "Admin User",
  
  "content": {
    // For spreadsheet type
    "columns": [
      {"key": "name", "name": "Asset Name", "type": "text", "editable": true},
      {"key": "category", "name": "Category", "type": "select", "options": ["IT", "Furniture"], "editable": true},
      {"key": "cost", "name": "Cost", "type": "number", "editable": true}
    ],
    "rows": [
      {"id": "row1", "name": "Laptop Dell", "category": "IT", "cost": 15000000},
      {"id": "row2", "name": "Meja Kantor", "category": "Furniture", "cost": 2000000}
    ]
  },
  
  "permissions": {
    "public": false,
    "shared_with": [
      {"user_id": "user2_uuid", "access": "view"},
      {"user_id": "user3_uuid", "access": "edit"}
    ]
  },
  
  "metadata": {
    "source_module": "assets",  // Optional: jika import dari module
    "export_target": null,       // Optional: target module untuk export
    "file_size": 12345,
    "row_count": 2,
    "column_count": 3
  },
  
  "created_at": "2026-05-19T12:00:00Z",
  "updated_at": "2026-05-19T14:30:00Z",
  "last_accessed_at": "2026-05-19T15:00:00Z",
  "is_deleted": false
}
```

#### **Collection: `workspace_shares`**
```json
{
  "id": "uuid",
  "document_id": "doc_uuid",
  "shared_by": "user1_uuid",
  "shared_with": "user2_uuid",
  "access_level": "view" | "edit" | "admin",
  "shared_at": "2026-05-19T12:00:00Z",
  "expires_at": null  // Optional expiry
}
```

---

## 🎨 UI/UX DESIGN

### **A. Workspace Portal Homepage**

```
┌─────────────────────────────────────────────────────────────┐
│ MY WORKSPACE                                    [+ New Doc] │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │ 📊 New      │ │ 📄 New      │ │ 📤 Import   │           │
│ │ Spreadsheet │ │ Document    │ │ from Excel  │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────┤
│ Recent Files                                                │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 📊 Asset Planning 2026         Last edited 2 hours ago  ││
│ │    25 rows · 8 columns         [Open] [Share] [...]     ││
│ ├─────────────────────────────────────────────────────────┤│
│ │ 📊 Procurement Items Draft     Last edited yesterday    ││
│ │    15 rows · 6 columns         [Open] [Share] [...]     ││
│ └─────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│ Shared with Me                                              │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 📊 Monthly Budget (by Finance Manager)                  ││
│ │    View only · 50 rows         [Open]                   ││
│ └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

### **B. Spreadsheet Editor View**

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Asset Planning 2026                        [Share] [•••] │
│ Owner: You · Last saved: 2 minutes ago                      │
├─────────────────────────────────────────────────────────────┤
│ [💾 Save] [↩️ Undo] [↪️ Redo] [+ Add Row] [🗑️ Delete]      │
│ [📥 Import from Excel] [📤 Export to Excel]                 │
│ [📦 Import from Assets] [📦 Export to Assets]               │
├─────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Name          │ Category  │ Location   │ Cost         │   │
│ ├───────────────────────────────────────────────────────┤   │
│ │ Laptop Dell   │ IT        │ Ruang IT   │ 15,000,000   │   │
│ │ Printer Canon │ IT        │ Admin      │ 3,000,000    │   │
│ │ [empty]       │ [empty]   │ [empty]    │ [empty]      │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                             │
│ 25 rows · 8 columns                                         │
└─────────────────────────────────────────────────────────────┘
```

---

### **C. Share Dialog**

```
┌──────────────────────────────────────────┐
│ Share "Asset Planning 2026"              │
├──────────────────────────────────────────┤
│ Share with:                              │
│ [Search users...]                        │
│                                          │
│ Current sharing:                         │
│ ┌──────────────────────────────────────┐ │
│ │ 👤 Finance Manager                   │ │
│ │    Can Edit    [Change] [Remove]     │ │
│ ├──────────────────────────────────────┤ │
│ │ 👤 HR Staff                          │ │
│ │    Can View    [Change] [Remove]     │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ Link sharing:                            │
│ [ ] Anyone with link can view            │
│                                          │
│         [Cancel]  [Save]                 │
└──────────────────────────────────────────┘
```

---

### **D. Import/Export Flow**

#### **Import from Excel:**
```
1. Click "Import from Excel"
2. Upload .xlsx file
3. Preview: "Found 3 sheets. Select one:"
   - Sheet1: Asset List (50 rows, 8 columns) [Select]
   - Sheet2: Summary
4. Map columns:
   Excel Column A → Name
   Excel Column B → Category
   Excel Column C → Cost
5. [Import] → Create new spreadsheet
```

#### **Import from System Module (Assets):**
```
1. Click "Import from Assets"
2. Filter dialog:
   - Category: [All / IT / Furniture / ...]
   - Status: [All / Active / Disposed / ...]
   - Date range: [Last 30 days]
3. Preview: "50 assets match your filter"
4. Select columns to import:
   [x] Asset Number
   [x] Name
   [x] Category
   [x] Location
   [x] Purchase Cost
   [ ] Serial Number
5. [Import] → Load data ke grid
6. User bisa edit data
7. [Export back to Assets] → Update database
```

#### **Export to System Module:**
```
1. Click "Export to Assets"
2. Review changes:
   - 3 new assets to create
   - 2 existing assets to update
   - 1 validation error (invalid category)
3. Fix errors
4. [Confirm Export]
5. Bulk create/update di Asset Management module
6. Toast: "Successfully exported 5 assets"
```

---

## 🔐 PERMISSION SYSTEM

### **Access Levels:**

| Level | View | Edit | Share | Delete | Export to Module |
|-------|------|------|-------|--------|------------------|
| **Owner** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Admin** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Edit** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **View** | ✅ | ❌ | ❌ | ❌ | ❌ |

### **Sharing Rules:**
- Owner dapat share ke any user dengan any permission
- User dengan "Admin" access bisa share ke user lain
- User dengan "Edit" access bisa edit content tapi tidak bisa share
- User dengan "View" access hanya bisa lihat (read-only grid)

---

## 🚀 IMPLEMENTATION ROADMAP

### **Phase 1: Basic Workspace (3-4 hari)**

**Backend:**
- [ ] `workspace_documents` collection schema
- [ ] `POST /api/workspace/documents` - Create spreadsheet
- [ ] `GET /api/workspace/documents` - List user's docs
- [ ] `GET /api/workspace/documents/{id}` - Get single doc
- [ ] `PUT /api/workspace/documents/{id}` - Update content
- [ ] `DELETE /api/workspace/documents/{id}` - Soft delete

**Frontend:**
- [ ] Workspace Portal component (sidebar + homepage)
- [ ] Document list view (card grid)
- [ ] "New Spreadsheet" dialog
- [ ] Basic grid editor dengan react-data-grid
- [ ] Save/auto-save functionality

---

### **Phase 2: Sharing & Permissions (2-3 hari)**

**Backend:**
- [ ] `workspace_shares` collection
- [ ] `POST /api/workspace/documents/{id}/share` - Share doc
- [ ] `GET /api/workspace/documents/shared-with-me` - List shared docs
- [ ] Permission middleware (check access before edit)

**Frontend:**
- [ ] "Share" dialog dengan user search
- [ ] "Shared with Me" section
- [ ] Permission badges (Owner, Edit, View)
- [ ] Read-only mode untuk "View" access

---

### **Phase 3: Import/Export Excel (2 hari)**

**Backend:**
- [ ] `POST /api/workspace/documents/import-excel` - Upload & parse Excel
- [ ] `GET /api/workspace/documents/{id}/export-excel` - Download as Excel

**Frontend:**
- [ ] "Import from Excel" file upload
- [ ] Excel preview & sheet selection
- [ ] Column mapping UI
- [ ] "Export to Excel" download button

---

### **Phase 4: System Integration (3-4 hari)**

**Backend:**
- [ ] `POST /api/workspace/documents/import-from-module` - Import from Asset/Procurement/etc
  - Support filters (category, status, date range)
- [ ] `POST /api/workspace/documents/{id}/export-to-module` - Export back to module
  - Validation logic
  - Bulk create/update

**Frontend:**
- [ ] "Import from Assets" dialog dengan filters
- [ ] "Export to Assets" review dialog
- [ ] Validation UI (show errors inline)
- [ ] Success/error notifications

---

### **Phase 5: Advanced Features (Optional, 2-3 hari)**

- [ ] Document templates (pre-defined columns untuk asset, procurement, etc)
- [ ] Version history (track changes)
- [ ] Comments on cells (collaboration)
- [ ] Cell formatting (bold, color, alignment)
- [ ] Formula support (basic: SUM, AVG, COUNT)

---

## 💾 STORAGE STRATEGY

### **Option A: MongoDB (Recommended)**
Store spreadsheet data as JSON document.

**Pros:**
- ✅ Simple - reuse existing database
- ✅ Fast development
- ✅ No file system complexity
- ✅ Easy to query & filter

**Cons:**
- ⚠️ Size limit 16MB per document (cukup untuk ~10k rows)

---

### **Option B: File System + MongoDB Metadata**
Store spreadsheet as JSON file, metadata di MongoDB.

**Pros:**
- ✅ No size limit
- ✅ Can store very large spreadsheets

**Cons:**
- ⚠️ File system management complexity
- ⚠️ Backup strategy lebih kompleks

**Verdict:** Use **Option A** (MongoDB) untuk MVP. Migrate ke Option B jika hit size limit.

---

## 📊 PERFORMANCE CONSIDERATIONS

### **Grid Performance:**
- Render max 100 rows at a time (virtual scrolling)
- Lazy load more rows on scroll
- Debounce auto-save (save after 2 seconds idle)
- Optimistic UI updates (instant feedback, async save)

### **Large Datasets:**
- Warning jika import > 1000 rows
- Pagination untuk list documents
- Search indexing untuk quick find

---

## 🎯 SUCCESS METRICS

**User Adoption:**
- 80% users create at least 1 spreadsheet dalam 1 bulan
- 50% users share documents dengan team

**Productivity:**
- Bulk entry 50+ assets 10x lebih cepat vs form 1-by-1
- Reduce data entry errors by 30%

**Integration:**
- 60% spreadsheets di-export balik ke system modules
- Import/Export digunakan minimal 5x per minggu

---

## 📝 EXAMPLE USE CASES

### **Use Case 1: Asset Planning**
1. Finance Manager buat spreadsheet "Asset Plan Q3 2026"
2. List 30 asset yang mau dibeli (nama, kategori, estimasi harga)
3. Share "Can Edit" ke Department Heads untuk review
4. Dept Heads edit/tambah items
5. Finance Manager review final list
6. Export ke Procurement module → Create 30 PR sekaligus

### **Use Case 2: Inventory Adjustment**
1. WMS Staff import 500 items dari Inventory module
2. Edit quantity setelah physical count (stock opname)
3. Save as "Stock Opname May 2026"
4. Export back to Inventory → Update stock quantities

### **Use Case 3: Salary Calculation**
1. HR import employee list dari HR module
2. Add columns: Bonus, Deduction, Total Salary
3. Calculate using formulas (if implemented)
4. Share "View Only" dengan Finance for approval
5. Export to Payroll module → Generate payslips

---

## 🛡️ SECURITY CONSIDERATIONS

**Data Protection:**
- [ ] Permission check pada setiap API call
- [ ] Owner cannot be changed after creation
- [ ] Soft delete (data tidak hilang permanently)
- [ ] Audit log (who changed what when)

**Validation:**
- [ ] Max document size: 10MB
- [ ] Max rows per spreadsheet: 10,000
- [ ] Rate limiting untuk save operations (max 10 saves/minute)

**Sharing:**
- [ ] Cannot share dengan external users (only internal system users)
- [ ] Owner dapat revoke access kapan saja
- [ ] Share link expires after 30 days (if link sharing enabled)

---

## 📦 DELIVERABLES

### **Phase 1-2 (MVP): 5-7 hari**
- ✅ Workspace Portal homepage
- ✅ Create/edit/delete spreadsheets
- ✅ Grid editor (react-data-grid)
- ✅ Share dengan users (permission system)
- ✅ Auto-save

### **Phase 3-4 (Full Features): +5 hari**
- ✅ Import/Export Excel
- ✅ Import from system modules (Assets, Procurement)
- ✅ Export to system modules (bulk create/update)

### **Total Effort: 10-12 hari (~2 minggu)**

---

## ✅ DECISION POINT

**Ready to proceed dengan design ini?**

**Recommended Implementation Order:**
1. **Week 1:** Phase 1-2 (Basic Workspace + Sharing)
2. **Week 2:** Phase 3-4 (Import/Export + System Integration)

**Atau ada perubahan/tambahan yang Anda inginkan?**
