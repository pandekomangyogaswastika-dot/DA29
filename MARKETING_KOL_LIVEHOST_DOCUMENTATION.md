# 📱 DOKUMENTASI KOL & CREATOR MANAGEMENT + PROPOSAL LIVEHOST
**CV. Dewi Aditya ERP - Marketing Portal**  
**Tanggal:** 20 Mei 2026  
**Author:** Neo AI Agent

---

## 🎯 EXECUTIVE SUMMARY

Portal Marketing memiliki sistem **KOL & Creator Management** yang sangat comprehensive (1,285 baris backend code), termasuk **Creator Portal yang sudah fully functional**. User request: **Tambahkan fitur LiveHost Management** sebagai enhancement.

---

## 📚 TABLE OF CONTENTS

1. [KOL & Creator Management - Cara Kerja](#cara-kerja)
2. [Fitur-Fitur yang Ada](#fitur-fitur)
3. [Creator Portal - Status & Review](#creator-portal)
4. [Proposal: LiveHost Management](#livehost-proposal)
5. [Implementation Plan](#implementation-plan)

---

<a name="cara-kerja"></a>
## 🔄 KOL & CREATOR MANAGEMENT - CARA KERJA

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     MARKETING PORTAL                             │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ADMIN SIDE (Internal Staff)                               │ │
│  │  - Create Creator Account                                   │ │
│  │  - Assign Platform Accounts (Shopee, TikTok, Tokopedia)   │ │
│  │  - Set KPI Targets                                         │ │
│  │  - Manage Product Catalog                                  │ │
│  │  - Approve/Reject Item Requests                            │ │
│  │  - View Leaderboard & Analytics                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓↑                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  CREATOR PORTAL (Separate JWT Auth)                        │ │
│  │  - Login via email/password                                │ │
│  │  - View assigned accounts                                  │ │
│  │  - Browse product catalog (with real-time stock)          │ │
│  │  - Request items for live promo                            │ │
│  │  - Record live session performance                         │ │
│  │  - View KPI dashboard & performance                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓↑                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  DATA LAYER                                                 │ │
│  │  • marketing_kol_creators         (Creator profiles)       │ │
│  │  • marketing_creator_catalog      (Product catalog)        │ │
│  │  • marketing_creator_item_requests (Item requests)         │ │
│  │  • marketing_creator_sessions     (Live performance data)  │ │
│  │  • rahaza_material_stock          (Real-time FG inventory) │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Workflow End-to-End

#### 1️⃣ **Setup Phase (Admin)**
```
Step 1: Admin creates Creator account
  POST /api/marketing/creators
  {
    "name": "Bella Saphira",
    "creator_code": "KOL-001",
    "login_email": "bella@creator.com",
    "login_password": "SecurePass123",
    "phone": "08123456789",
    "platforms": {
      "tiktok": "@bellasaphira_id",
      "shopee": "bellasaphira_official",
      "instagram": "@bellasaphira"
    },
    "assigned_account_ids": [
      "shopee-official-store-id",
      "tiktok-reseller-id"
    ],
    "kpi_targets": {
      "monthly_revenue": 50000000,
      "monthly_sessions": 12,
      "monthly_viewers": 100000
    }
  }

Step 2: System generates secure credentials
  - Password di-hash menggunakan bcrypt
  - Creator dapat login ke Creator Portal
  - Status default: "active"

Step 3: Admin menambahkan produk ke Creator Catalog
  POST /api/marketing/kol/catalog
  {
    "account_id": "shopee-official-store-id",
    "fg_product_id": "FG-001",  // Link ke Production System
    "product_name": "Mukena Batik Premium",
    "sku": "MKN-BTK-001",
    "unit_price": 350000,
    "category": "Fashion Muslim",
    "is_active": true
  }
  
  Note: Real-time stock di-fetch dari WMS (rahaza_material_stock)
```

#### 2️⃣ **Creator Request Phase**
```
Step 1: Creator login ke Creator Portal
  POST /api/marketing/creator-portal/auth/login
  {
    "email": "bella@creator.com",
    "password": "SecurePass123"
  }
  
  Response:
  {
    "token": "eyJ...",  // JWT with audience='creator-portal'
    "creator_id": "xxx",
    "creator_name": "Bella Saphira",
    "creator_code": "KOL-001",
    "assigned_account_ids": ["shopee-official-store-id", ...]
  }
  
  Security:
  - Brute-force protection: 5 failed attempts → 15 min lockout
  - Token expiry: 24 hours

Step 2: Creator browse catalog (with real-time stock)
  GET /api/marketing/creator-portal/catalog?account_id=xxx
  
  Response:
  [
    {
      "id": "catalog-item-001",
      "product_name": "Mukena Batik Premium",
      "sku": "MKN-BTK-001",
      "unit_price": 350000,
      "category": "Fashion Muslim",
      "stock_qty": 45.0,  // Real-time from WMS
      "fg_product_id": "FG-001"
    }
  ]

Step 3: Creator request item untuk live promo
  POST /api/marketing/creator-portal/requests
  {
    "account_id": "shopee-official-store-id",
    "catalog_item_id": "catalog-item-001",
    "quantity_requested": 10,
    "purpose": "Flash Sale Live 21:00",
    "notes": "Butuh 10 pcs untuk give away + demo live"
  }
  
  System:
  - Validates stock availability
  - Records current stock at request time
  - Sets status: "pending"
  - Notifies admin
```

#### 3️⃣ **Admin Approval Phase**
```
Step 1: Admin view pending requests
  GET /api/marketing/kol/requests?status=pending
  
  Response shows:
  - Creator name & code
  - Product name & SKU
  - Quantity requested
  - Current stock (real-time)
  - Stock at request time
  - Purpose & notes

Step 2: Admin approve/reject
  
  APPROVE:
  POST /api/marketing/kol/requests/{request_id}/approve
  → Status: "approved"
  → Creator notified (future: WA/Email)
  
  REJECT:
  POST /api/marketing/kol/requests/{request_id}/reject?reason=Stock%20habis
  → Status: "rejected"
  → Rejection reason stored
  → Creator notified
```

#### 4️⃣ **Live Session Phase**
```
Step 1: Creator goes live (TikTok, Shopee Live, etc.)
  - Promote approved items
  - Engage with viewers
  - Drive sales

Step 2: Creator records session performance
  POST /api/marketing/sessions (Admin) or
  POST /api/marketing/creator-portal/sessions (Creator)
  
  {
    "creator_id": "xxx",
    "account_id": "shopee-official-store-id",
    "date": "2026-05-20",
    "platform": "tiktokshop",
    "session_name": "Flash Sale Malam",
    "duration_minutes": 90,
    "viewers": 8500,
    "peak_viewers": 12000,
    "revenue": 18500000,
    "orders": 52,
    "items_promoted": ["Mukena Batik Premium", "Gamis Syari"],
    "notes": "Respon sangat bagus, banyak yang tanya warna lain"
  }
  
  System calculates:
  - Average Order Value (AOV) = revenue / orders
  - Conversion Rate = orders / viewers
  - Revenue per viewer
```

#### 5️⃣ **Analytics & Leaderboard Phase**
```
Step 1: Creator views personal KPI dashboard
  GET /api/marketing/creator-portal/my-kpi
  
  Response:
  {
    "month": "2026-05",
    "creator_name": "Bella Saphira",
    "kpi_targets": {
      "monthly_revenue": 50000000,
      "monthly_sessions": 12,
      "monthly_viewers": 100000
    },
    "actuals": {
      "monthly_revenue": 42500000,
      "monthly_sessions": 9,
      "monthly_viewers": 78000
    },
    "progress": {
      "revenue_pct": 85.0,
      "sessions_pct": 75.0,
      "viewers_pct": 78.0
    }
  }

Step 2: Admin views leaderboard
  GET /api/marketing/kol/leaderboard?month=2026-05
  
  Response (ranked by revenue):
  [
    {
      "rank": 1,
      "creator_name": "Bella Saphira",
      "creator_code": "KOL-001",
      "total_revenue": 42500000,
      "total_viewers": 78000,
      "total_orders": 320,
      "total_sessions": 9,
      "avg_revenue_per_session": 4722222,
      "kpi_achievement": {
        "revenue_pct": 85.0,
        "sessions_pct": 75.0,
        "viewers_pct": 78.0,
        "overall_pct": 79.3
      }
    },
    {
      "rank": 2,
      "creator_name": "Rina Susanti",
      ...
    }
  ]
```

---

<a name="fitur-fitur"></a>
## ✨ FITUR-FITUR YANG ADA

### 🔐 A. AUTHENTICATION & SECURITY

#### A1. Separate JWT for Creator Portal
```python
# Token with special audience
payload = {
    'sub': creator_id,
    'email': creator_email,
    'creator_id': creator_id,
    'aud': 'creator-portal',  # Isolate from main app
    'exp': now + 24h
}
```

**Why separate auth?**
- Creator tidak boleh akses internal ERP
- Creator hanya lihat data mereka sendiri
- Simplified permission model

#### A2. Brute-Force Protection
```
Rule:
- Track failed attempts per IP + email
- 5 failed attempts → 15 minute lockout
- Success → clear attempts
- Lockout auto-expire setelah 15 menit
```

**Collection:** `marketing_kol_login_attempts`
```json
{
  "identifier": "192.168.1.100:bella@creator.com",
  "attempts": 3,
  "first_attempt_at": "2026-05-20T10:00:00Z",
  "last_attempt_at": "2026-05-20T10:05:00Z",
  "locked_until": null  // or timestamp
}
```

---

### 👥 B. CREATOR MANAGEMENT (ADMIN)

#### B1. Creator CRUD
```
✅ POST   /api/marketing/creators          - Create creator
✅ GET    /api/marketing/creators          - List all creators
✅ GET    /api/marketing/creators/{id}     - Get creator detail
✅ PATCH  /api/marketing/creators/{id}     - Update creator
✅ DELETE /api/marketing/creators/{id}     - Delete creator
```

**Creator Profile Schema:**
```json
{
  "id": "uuid",
  "name": "Bella Saphira",
  "creator_code": "KOL-001",
  "login_email": "bella@creator.com",
  "login_password_hash": "bcrypt...",
  "phone": "08123456789",
  "platforms": {
    "tiktok": "@bellasaphira_id",
    "shopee": "bellasaphira_official",
    "tokopedia": "bellasaphira",
    "instagram": "@bellasaphira"
  },
  "assigned_account_ids": ["acc-1", "acc-2"],
  "kpi_targets": {
    "monthly_revenue": 50000000,
    "monthly_sessions": 12,
    "monthly_viewers": 100000,
    "monthly_orders": 400
  },
  "status": "active",  // active | inactive
  "notes": "Top performer, specializes in fashion muslim",
  "created_at": "2026-05-01T10:00:00Z",
  "last_login_at": "2026-05-20T09:30:00Z"
}
```

#### B2. Platform Account Assignment
```
Admin dapat assign multiple platform accounts ke creator:

Example:
Creator "Bella Saphira" assigned to:
- Shopee Official Store
- TikTok Reseller Account
- Tokopedia Distributor

→ Creator hanya bisa request items & record sessions untuk account yang assigned
```

#### B3. KPI Target Setting
```
Admin sets monthly targets:
- Revenue target (Rp)
- Session count target
- Viewer target
- Order target (optional)

→ System auto-calculates achievement %
→ Leaderboard shows overall KPI achievement
```

---

### 📦 C. PRODUCT CATALOG MANAGEMENT

#### C1. Creator Catalog
**Collection:** `marketing_creator_catalog`

**Purpose:** Product catalog khusus untuk creators (approved items only)

**Features:**
✅ Link to FG Product (Production System)
✅ Real-time stock integration from WMS
✅ Per-account catalog (different products per platform)
✅ Active/inactive toggle
✅ Price & description

**Endpoints:**
```
✅ POST   /api/marketing/kol/catalog         - Add product to catalog
✅ GET    /api/marketing/kol/catalog         - List all catalog items
✅ PUT    /api/marketing/kol/catalog/{id}    - Update catalog item
✅ DELETE /api/marketing/kol/catalog/{id}    - Remove from catalog (soft delete)
✅ GET    /api/marketing/kol/fg-products     - List FG products for linking
```

**Schema:**
```json
{
  "id": "uuid",
  "account_id": "shopee-official-store-id",
  "account_name": "Shopee Official Store DEMO",
  "fg_product_id": "FG-001",  // Link to rahaza_materials
  "product_name": "Mukena Batik Premium",
  "sku": "MKN-BTK-001",
  "category": "Fashion Muslim",
  "unit_price": 350000,
  "description": "Mukena batik cap premium, bahan katun",
  "is_active": true,
  "stock_qty": 45.0,  // Real-time dari WMS (computed)
  "created_at": "2026-05-01T10:00:00Z",
  "created_by": "admin@garment.com"
}
```

**Real-time Stock Logic:**
```python
# Setiap fetch catalog, system auto-enrich dengan stock
for item in catalog:
    fg_id = item.get('fg_product_id')
    if fg_id:
        # Get default warehouse location
        location = db.rahaza_locations.find_one({'active': True})
        
        # Get stock for this material at this location
        stock_doc = db.rahaza_material_stock.find_one({
            'material_id': fg_id,
            'location_id': location['id']
        })
        
        item['stock_qty'] = stock_doc.get('qty', 0)
```

**Benefit:**
- Creator selalu lihat stock terkini
- Avoid request item yang out of stock
- Admin dapat quick decision approve/reject

---

### 🎁 D. ITEM REQUEST SYSTEM

#### D1. Request Flow
```
Creator → Request item → Pending → Admin review → Approve/Reject
```

**Collection:** `marketing_creator_item_requests`

**Schema:**
```json
{
  "id": "uuid",
  "creator_id": "xxx",
  "creator_name": "Bella Saphira",
  "creator_code": "KOL-001",
  "account_id": "shopee-official-store-id",
  "catalog_item_id": "catalog-item-001",
  "product_name": "Mukena Batik Premium",
  "sku": "MKN-BTK-001",
  "fg_product_id": "FG-001",
  "quantity_requested": 10,
  "stock_at_request": 45.0,  // Snapshot stock saat request
  "purpose": "Flash Sale Live 21:00",
  "notes": "Butuh 10 pcs untuk give away + demo live",
  "status": "pending",  // pending | approved | rejected
  "reviewed_at": null,
  "reviewed_by": null,
  "rejection_reason": null,
  "created_at": "2026-05-20T15:00:00Z"
}
```

**Endpoints:**
```
Creator Side:
✅ POST /api/marketing/creator-portal/requests       - Submit request
✅ GET  /api/marketing/creator-portal/my-requests    - View own requests

Admin Side:
✅ GET  /api/marketing/kol/requests                  - List all requests (with pagination)
✅ POST /api/marketing/kol/requests/{id}/approve     - Approve request
✅ POST /api/marketing/kol/requests/{id}/reject      - Reject request (with reason)
```

**Features:**
✅ Real-time stock check saat request
✅ Purpose & notes untuk context
✅ Pagination untuk admin (bisa banyak requests)
✅ Filter by status, creator, account
✅ Rejection reason tracking
✅ Activity log integration

---

### 📹 E. LIVE SESSION TRACKING

**Collection:** `marketing_creator_sessions`

**Purpose:** Track live streaming performance (TikTok Live, Shopee Live, etc.)

**Schema:**
```json
{
  "id": "uuid",
  "creator_id": "xxx",
  "creator_name": "Bella Saphira",
  "creator_code": "KOL-001",
  "account_id": "shopee-official-store-id",
  "account_name": "Shopee Official Store DEMO",
  "date": "2026-05-20",
  "platform": "tiktokshop",  // shopee | tiktokshop | tokopedia
  "session_name": "Flash Sale Malam",
  "duration_minutes": 90,
  
  // Viewership metrics
  "viewers": 8500,
  "peak_viewers": 12000,
  
  // Sales metrics
  "revenue": 18500000,
  "orders": 52,
  "aov": 355769,  // Auto-calculated: revenue / orders
  
  // Engagement (optional)
  "likes": 15000,
  "comments": 3200,
  "shares": 450,
  
  // Content
  "items_promoted": ["Mukena Batik Premium", "Gamis Syari"],
  "notes": "Respon sangat bagus, banyak yang tanya warna lain",
  
  "created_at": "2026-05-20T22:30:00Z",
  "created_by": "bella@creator.com"
}
```

**Endpoints:**
```
Admin:
✅ POST /api/marketing/sessions       - Record session (admin entry)
✅ GET  /api/marketing/sessions       - List all sessions (with filters)

Creator:
✅ POST /api/marketing/creator-portal/sessions       - Record own session
✅ GET  /api/marketing/creator-portal/my-performance - View own performance
✅ GET  /api/marketing/creator-portal/my-kpi         - View KPI dashboard
```

**Calculated Metrics:**
```
Per Session:
- AOV (Average Order Value) = revenue / orders
- Conversion Rate = orders / viewers
- Revenue per Viewer = revenue / viewers
- Engagement Rate = (likes + comments + shares) / viewers

Aggregated (monthly):
- Total Revenue
- Total Sessions
- Total Viewers
- Average Revenue per Session
- Average Viewers per Session
- KPI Achievement %
```

---

### 🏆 F. LEADERBOARD & ANALYTICS

#### F1. Creator Leaderboard
**Endpoint:** `GET /api/marketing/kol/leaderboard?month=YYYY-MM`

**Ranking Logic:**
```
Primary: Total Revenue (desc)
Secondary: Overall KPI Achievement %
```

**Response:**
```json
[
  {
    "rank": 1,
    "creator_id": "xxx",
    "creator_name": "Bella Saphira",
    "creator_code": "KOL-001",
    "profile_picture": null,
    
    // Performance metrics
    "total_revenue": 42500000,
    "total_viewers": 78000,
    "total_orders": 320,
    "total_sessions": 9,
    
    // Calculated averages
    "avg_revenue_per_session": 4722222,
    "avg_viewers_per_session": 8667,
    "avg_orders_per_session": 36,
    "overall_conversion_rate": 0.0041,  // 0.41%
    
    // KPI achievement
    "kpi_targets": {
      "monthly_revenue": 50000000,
      "monthly_sessions": 12,
      "monthly_viewers": 100000
    },
    "kpi_achievement": {
      "revenue_pct": 85.0,
      "sessions_pct": 75.0,
      "viewers_pct": 78.0,
      "overall_pct": 79.3  // Average
    }
  },
  ...
]
```

**UI Features:**
✅ Badge untuk top 3 (🥇🥈🥉)
✅ Color-coded achievement (green ≥80%, yellow 50-79%, red <50%)
✅ Drill-down ke creator detail
✅ Month selector

---

<a name="creator-portal"></a>
## 🎨 CREATOR PORTAL - STATUS & REVIEW

### ✅ Status: **FULLY FUNCTIONAL**

**Route:** `/creator`  
**File:** `/app/frontend/src/components/creator/CreatorPortalApp.jsx` (653 lines)

### Features Implemented

#### 1️⃣ **Login Page**
```
✅ Email/password authentication
✅ Separate JWT (audience='creator-portal')
✅ Brute-force protection (5 attempts → 15 min lockout)
✅ Error messages (clear & actionable)
✅ Auto-redirect on success
✅ Session persistence (localStorage)
✅ Responsive design (mobile-friendly)
✅ Dark theme with gradient background
✅ data-testid attributes untuk testing
```

**UI Screenshot Description:**
- Dark theme (`bg-[#0a0a0f]` with violet/pink gradient)
- Centered login card (glass-morphism effect)
- Video icon logo (violet-to-pink gradient)
- Clear form labels
- Error toast notifications

#### 2️⃣ **Creator Dashboard**
```
✅ Welcome header dengan creator name & code
✅ KPI Progress Cards (3 metrics: Revenue, Sessions, Viewers)
  - Progress bar (green ≥80%, yellow 50-79%, red <50%)
  - Actual vs Target display
  - Percentage achievement
✅ Quick Stats Grid
  - Total Sessions
  - Total Revenue (formatted Rupiah)
  - Total Viewers
  - Total Orders
✅ Recent Sessions Table
  - Date, Platform, Session Name
  - Viewers, Revenue, Orders
  - Drill-down to detail (future)
✅ Refresh button
✅ Logout button
```

**API Integration:**
```javascript
// Dashboard fetches:
GET /api/marketing/creator-portal/my-kpi          // KPI summary
GET /api/marketing/creator-portal/my-performance  // Session list
```

#### 3️⃣ **Product Catalog Page**
```
✅ Filter by assigned account (dropdown)
✅ Product grid/list view
✅ Real-time stock display
✅ Product details:
  - Product name
  - SKU
  - Price (formatted Rupiah)
  - Category
  - Stock quantity (color-coded: green >10, yellow 5-10, red <5)
✅ Request Item button (opens modal)
✅ Empty state (no products)
✅ Loading skeleton
```

**Request Item Modal:**
```
✅ Product info (name, sku, current stock)
✅ Quantity input (validation: min 1, max stock)
✅ Purpose dropdown (Flash Sale, Review, Giveaway, Demo, Other)
✅ Notes textarea
✅ Submit button
✅ Cancel button
✅ Success toast
✅ Error handling
```

#### 4️⃣ **My Requests Page**
```
✅ List all creator's item requests
✅ Filter by status (All, Pending, Approved, Rejected)
✅ Request cards:
  - Product name & SKU
  - Quantity requested
  - Purpose
  - Status badge (color-coded)
  - Request date
  - Stock at request time vs current stock
  - Rejection reason (if rejected)
✅ Empty state per filter
✅ Refresh button
```

#### 5️⃣ **Performance Page** (Detail)
```
✅ Month selector (prev/next month navigation)
✅ Summary cards (total revenue, sessions, viewers, orders)
✅ KPI progress bars (3 metrics)
✅ Session list table:
  - Date, Platform, Session Name
  - Duration, Viewers, Peak Viewers
  - Revenue, Orders, AOV
  - Items promoted (tags)
  - Notes
✅ Export to Excel (future)
```

### UI/UX Analysis

#### Strengths ✅
1. **Consistent Dark Theme**
   - Professional gaming/creator vibe
   - Violet-to-pink gradient accent (matches platform identity)
   - Glass-morphism effects (modern)

2. **Responsive Design**
   - Mobile-first approach
   - Adaptive grid (1 col mobile → 2-3 cols desktop)
   - Touch-friendly buttons

3. **Clear Information Hierarchy**
   - Large numbers for key metrics
   - Color-coded status (green/yellow/red)
   - Progress bars untuk visual feedback

4. **Accessibility**
   - data-testid attributes
   - Clear labels
   - Keyboard navigation support
   - Screen reader friendly

5. **Error Handling**
   - Toast notifications (sonner)
   - Inline validation
   - Clear error messages

#### Areas for Enhancement 💡
1. **Profile Picture**
   - Current: No profile picture support
   - Recommendation: Add avatar upload (link to file storage)

2. **Notification System**
   - Current: No real-time notifications
   - Recommendation: WebSocket for:
     * Request approved/rejected
     * New product added to catalog
     * KPI milestone achieved

3. **Session Recording**
   - Current: Manual entry via admin side only
   - Recommendation: Add "Record Session" form di Creator Portal

4. **Product Images**
   - Current: No product images in catalog
   - Recommendation: Add image URL field to catalog schema

5. **Charts & Visualization**
   - Current: Basic tables & progress bars
   - Recommendation: Add:
     * Revenue trend chart (7/30 days)
     * Viewer growth chart
     * Platform distribution (pie chart)

---

<a name="livehost-proposal"></a>
## 🎤 PROPOSAL: LIVEHOST MANAGEMENT

### 🎯 Problem Statement

**Current System:**
- KOL/Creator = Individu influencer (Bella Saphira, Rina Susanti, dll)
- Creator mencatat **own performance** di Creator Portal
- Admin mencatat session yang creator lakukan

**Gap:**
- **LiveHost** = Host yang di-hire perusahaan untuk live streaming (bukan influencer dengan followers sendiri)
- LiveHost sering part-time atau freelance
- LiveHost perlu shift scheduling (pagi, siang, malam)
- LiveHost perlu script/talking points dari admin
- LiveHost performance di-track berbeda (per shift, bukan per month)
- LiveHost bisa handle multiple accounts dalam 1 hari

**Use Case:**
```
Scenario: Perusahaan punya Shopee Official Store yang live 12 jam/hari

Shift Schedule:
- Shift Pagi (09:00-13:00)   → LiveHost: Ani
- Shift Siang (13:00-17:00)  → LiveHost: Budi
- Shift Malam (17:00-21:00)  → LiveHost: Citra

Each host records:
- Shift duration
- Viewers, Orders, Revenue
- Products promoted
- Challenges faced
- Script adherence

Admin needs:
- Shift roster management
- Host performance comparison
- Best shift time analysis
- Host training tracking
```

---

### 🏗️ Solution: LiveHost Module

#### Feature Set

##### 1️⃣ **LiveHost Management (Admin)**
```
✅ LiveHost CRUD
  - Name, Email, Phone
  - Employment type: Full-time, Part-time, Freelance, Contract
  - Hourly rate (for payment calculation)
  - Shift preferences (morning, afternoon, evening, night)
  - Language skills (Indonesia, English, Mandarin, etc.)
  - Product expertise (Fashion, Electronics, Food, Beauty)
  - Status: Active, Inactive, On Leave

✅ LiveHost Assignment
  - Assign to platform accounts
  - Set shift schedule (weekly recurring)
  - Holiday/leave management
  
✅ LiveHost Performance Tracking
  - Per shift metrics (revenue, orders, viewers)
  - Shift attendance (on-time, late, no-show)
  - Average performance per shift type
  - Top performers per shift
  - Training completion tracking
```

##### 2️⃣ **Shift Management**
```
✅ Shift Templates
  - Define shift types (Morning, Afternoon, Evening, Night, Custom)
  - Set time ranges (e.g., Morning = 09:00-13:00)
  - Set break times
  - Set max consecutive shifts per host

✅ Shift Scheduling
  - Weekly calendar view
  - Drag-drop shift assignment
  - Auto-conflict detection
  - Swap shift request (host-initiated)
  - Coverage gap alerts

✅ Shift Recording
  - Clock in/out (mobile-friendly)
  - Record performance metrics per shift
  - Upload proof of live session (screenshot)
  - Notes & challenges faced
```

##### 3️⃣ **Script & Training Management**
```
✅ Script Library
  - Product scripts (opening, demo, closing)
  - Promo scripts (flash sale, discount announcement)
  - FAQ responses
  - Objection handling scripts
  - Per-account customization

✅ Training Modules
  - Product knowledge
  - Platform rules (TikTok, Shopee, Tokopedia)
  - Engagement techniques
  - Sales techniques
  - Video tutorials

✅ Certification Tracking
  - Required training per host
  - Completion status
  - Quiz scores
  - Expiry dates (for platform-specific certifications)
```

##### 4️⃣ **Performance Analytics**
```
✅ Host Performance Dashboard
  - Revenue per shift
  - Average viewers per shift
  - Conversion rate per shift
  - Best shift time analysis
  - Host comparison (ranking)

✅ Shift Performance Analysis
  - Best performing shift (Morning vs Evening vs Night)
  - Day-of-week analysis (Mon vs Sat vs Sun)
  - Holiday performance
  - Platform performance (TikTok vs Shopee)

✅ Payment Calculation
  - Auto-calculate payment based on:
    * Shift hours × hourly rate (base pay)
    * Bonus: Revenue achieved ÷ Revenue target × bonus_rate
    * Penalty: Late clock-in, no-show
  - Export to Finance module for payroll
```

##### 5️⃣ **LiveHost Portal (Optional)**
```
✅ View assigned shifts (weekly calendar)
✅ Clock in/out (with GPS check if required)
✅ View script library
✅ Record shift performance
✅ Request shift swap
✅ View own performance history
✅ View training materials
```

---

### 📊 Data Model

#### Collection: `marketing_livehosts`
```json
{
  "id": "uuid",
  "name": "Ani Wijaya",
  "email": "ani@livehost.com",
  "phone": "08123456789",
  "employment_type": "part_time",  // full_time | part_time | freelance | contract
  "hourly_rate": 50000,
  "shift_preferences": ["morning", "afternoon"],  // morning | afternoon | evening | night
  "language_skills": ["indonesia", "english"],
  "product_expertise": ["fashion", "beauty"],
  "status": "active",  // active | inactive | on_leave
  "assigned_account_ids": ["shopee-official-store-id"],
  "training_completed": ["product-101", "platform-tiktok"],
  "certification_expiry": {
    "tiktok_seller": "2027-01-01"
  },
  "created_at": "2026-05-01T10:00:00Z"
}
```

#### Collection: `marketing_livehost_shifts`
```json
{
  "id": "uuid",
  "host_id": "xxx",
  "host_name": "Ani Wijaya",
  "account_id": "shopee-official-store-id",
  "account_name": "Shopee Official Store DEMO",
  "date": "2026-05-20",
  "shift_type": "morning",  // morning | afternoon | evening | night | custom
  "shift_start_time": "09:00",
  "shift_end_time": "13:00",
  "scheduled_duration_minutes": 240,
  
  // Attendance
  "clock_in_time": "2026-05-20T09:05:00Z",
  "clock_out_time": "2026-05-20T13:02:00Z",
  "actual_duration_minutes": 237,
  "attendance_status": "on_time",  // on_time | late | no_show
  
  // Performance
  "platform": "shopee",
  "viewers": 3500,
  "peak_viewers": 5000,
  "revenue": 8500000,
  "orders": 42,
  "items_promoted": ["Mukena Batik", "Gamis Syari"],
  
  // Script & Training
  "script_ids_used": ["script-opening-001", "script-promo-flash-sale"],
  "script_adherence_score": 85,  // 0-100, rated by admin
  
  // Notes
  "notes": "Peak viewers saat promo jam 11:00",
  "challenges_faced": "Koneksi sempat lag 10 menit",
  "screenshot_url": "/uploads/shifts/shift-xxx-screenshot.jpg",
  
  // Payment
  "base_pay": 200000,  // 4 hours × 50000
  "bonus": 50000,
  "penalty": 0,
  "total_pay": 250000,
  
  "created_at": "2026-05-20T13:05:00Z",
  "reviewed_by": "admin@garment.com",
  "reviewed_at": "2026-05-20T14:00:00Z"
}
```

#### Collection: `marketing_livehost_scripts`
```json
{
  "id": "uuid",
  "title": "Opening Script - Fashion Products",
  "category": "opening",  // opening | demo | promo | closing | faq | objection_handling
  "account_id": "shopee-official-store-id",  // or null for global
  "script_text": "Halo semuanya! Selamat datang di live kita hari ini...",
  "language": "indonesia",
  "products_applicable": ["fashion", "muslim_wear"],
  "is_active": true,
  "created_at": "2026-05-01T10:00:00Z",
  "created_by": "admin@garment.com"
}
```

#### Collection: `marketing_livehost_training`
```json
{
  "id": "uuid",
  "title": "Product Knowledge 101",
  "category": "product_knowledge",  // product_knowledge | platform_rules | engagement | sales_techniques
  "description": "Pelajari semua produk fashion muslim kita",
  "content_type": "video",  // video | pdf | quiz | external_link
  "content_url": "/uploads/training/product-101.mp4",
  "duration_minutes": 30,
  "is_required": true,
  "expiry_months": 12,  // re-certification required every 12 months
  "passing_score": 80,  // for quiz type
  "created_at": "2026-05-01T10:00:00Z"
}
```

#### Collection: `marketing_livehost_training_progress`
```json
{
  "id": "uuid",
  "host_id": "xxx",
  "training_id": "yyy",
  "status": "completed",  // not_started | in_progress | completed
  "score": 85,  // for quiz type
  "completed_at": "2026-05-10T15:00:00Z",
  "expiry_date": "2027-05-10",  // if training has expiry
  "certificate_url": "/uploads/certificates/host-xxx-training-yyy.pdf"
}
```

---

<a name="implementation-plan"></a>
## 🚀 IMPLEMENTATION PLAN

### Phase 1: Core LiveHost Management (2-3 hari)

#### Backend:
```
File: /app/backend/routes/marketing_livehost.py (new file, estimate ~800 lines)

Endpoints:
✅ POST   /api/marketing/livehosts              - Create livehost
✅ GET    /api/marketing/livehosts              - List livehosts
✅ GET    /api/marketing/livehosts/{id}         - Get livehost detail
✅ PATCH  /api/marketing/livehosts/{id}         - Update livehost
✅ DELETE /api/marketing/livehosts/{id}         - Delete livehost
✅ POST   /api/marketing/livehost-shifts        - Create shift
✅ GET    /api/marketing/livehost-shifts        - List shifts (with filters)
✅ PATCH  /api/marketing/livehost-shifts/{id}   - Update shift (record performance)
✅ GET    /api/marketing/livehost-shifts/calendar - Get calendar view
```

#### Frontend:
```
File: /app/frontend/src/components/erp/marketing/LiveHostModule.jsx (new, ~600 lines)

Features:
- LiveHost list table
- Add/Edit LiveHost modal
- Shift calendar (weekly view)
- Shift assignment modal
- Shift recording form
```

#### Database:
```
Collections:
- marketing_livehosts
- marketing_livehost_shifts

Indexes:
- marketing_livehost_shifts: (date, -1), (host_id, 1)
```

#### Testing:
```
Backend tests: test_livehost_crud.py
Playwright E2E: test_livehost_module.spec.js
```

---

### Phase 2: Script & Training Management (2 hari)

#### Backend:
```
Add to /app/backend/routes/marketing_livehost.py (~400 lines additional)

Endpoints:
✅ POST   /api/marketing/livehost-scripts           - Create script
✅ GET    /api/marketing/livehost-scripts           - List scripts
✅ PUT    /api/marketing/livehost-scripts/{id}      - Update script
✅ DELETE /api/marketing/livehost-scripts/{id}      - Delete script
✅ POST   /api/marketing/livehost-training          - Create training
✅ GET    /api/marketing/livehost-training          - List training
✅ POST   /api/marketing/livehost-training/assign   - Assign training to host
✅ POST   /api/marketing/livehost-training/{id}/complete - Mark training complete
```

#### Frontend:
```
Add to LiveHostModule.jsx (~300 lines additional)

Features:
- Script library tab
- Training library tab
- Training assignment modal
- Training progress tracking
```

---

### Phase 3: Analytics & Payment (1-2 hari)

#### Backend:
```
Add to marketing_livehost.py (~300 lines)

Endpoints:
✅ GET /api/marketing/livehost-analytics/performance - Host performance dashboard
✅ GET /api/marketing/livehost-analytics/shifts      - Shift analysis
✅ POST /api/marketing/livehost-payment/calculate    - Calculate payment
✅ GET /api/marketing/livehost-payment/export        - Export for payroll
```

#### Frontend:
```
Add to LiveHostModule.jsx (~200 lines)

Features:
- Performance dashboard
- Payment calculation table
- Export to Excel
```

---

### Phase 4: LiveHost Portal (Optional, 2 hari)

#### Backend:
```
File: Add to marketing_livehost.py (~200 lines)

Endpoints:
✅ POST /api/marketing/livehost-portal/auth/login    - LiveHost login
✅ GET  /api/marketing/livehost-portal/my-shifts     - View assigned shifts
✅ POST /api/marketing/livehost-portal/clock-in      - Clock in
✅ POST /api/marketing/livehost-portal/clock-out     - Clock out
✅ GET  /api/marketing/livehost-portal/scripts       - View scripts
```

#### Frontend:
```
File: /app/frontend/src/components/livehost/LiveHostPortalApp.jsx (new, ~400 lines)

Features:
- Login page (similar to Creator Portal)
- My Shifts calendar
- Clock in/out button (with geolocation)
- Script viewer
- Performance history
```

---

### Total Effort Estimate

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 1: Core LiveHost Management | 2-3 hari | **HIGH** (Must Have) |
| Phase 2: Script & Training | 2 hari | **MEDIUM** (Should Have) |
| Phase 3: Analytics & Payment | 1-2 hari | **MEDIUM** (Should Have) |
| Phase 4: LiveHost Portal | 2 hari | **LOW** (Nice to Have) |
| **Total** | **7-9 hari** | |

---

## 🎯 REKOMENDASI PRIORITAS

### Implementasi Sekarang (Must Have):
1. ✅ **Phase 1: Core LiveHost Management**
   - LiveHost CRUD
   - Shift scheduling & assignment
   - Shift recording & performance tracking
   - Basic calendar view

**Rationale:** Ini adalah blocker utama untuk mulai manage live hosts

---

### Implementasi Sprint Berikutnya (Should Have):
2. ✅ **Phase 2: Script & Training Management**
   - Script library
   - Training modules
   - Training assignment & tracking

**Rationale:** Improve quality & consistency of live sessions

3. ✅ **Phase 3: Analytics & Payment**
   - Performance analytics
   - Payment calculation
   - Export for Finance

**Rationale:** Enable data-driven decisions & automate payroll

---

### Implementasi Future (Nice to Have):
4. ✅ **Phase 4: LiveHost Portal**
   - Self-service portal untuk live hosts
   - Mobile-friendly clock in/out
   - Script access on mobile

**Rationale:** Improve host experience, reduce admin workload

---

## 📝 NEXT STEPS

**Apakah Anda ingin saya:**
1. ✅ **Implementasi Phase 1: Core LiveHost Management** (2-3 hari)?
2. ✅ **Buat seed data dulu untuk KOL/Creator** yang existing (1 hari)?
3. ✅ **Review & improve Creator Portal** (UI polish, add features)?
4. ✅ **Atau prioritas lain**?

---

**Prepared by:** Neo AI Agent  
**Date:** 20 Mei 2026  
**Status:** READY FOR IMPLEMENTATION
