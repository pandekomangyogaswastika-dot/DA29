"""
CV. Dewi Aditya - Backend API Testing
Phase 8: Pagination & Vendor Portal Progress History

Tests:
1. Unified Inventory Pagination (GET /api/wms/stock/unified)
   - Basic pagination with page/limit
   - Pagination with filters (category, search)
   - Edge cases (out-of-range page, limit clamping)
2. Vendor Portal Progress History (GET /api/dewi/cmt/vendor/my-jobs/{job_id}/progress-history)
   - Vendor ownership validation
   - Admin access bypass
   - 403/404 error handling
3. Regression Tests:
   - Unified inventory summary
   - Stock adjustment
   - Phase 7 reports (daily, monthly)
"""
import requests
import sys
from datetime import datetime, date

# Configuration
BASE_URL = "https://workspace-hub-build.preview.emergentagent.com"
ADMIN_EMAIL = "admin@garment.com"
ADMIN_PASSWORD = "Admin@123"
VENDOR1_EMAIL = "vendor1@cmt.com"
VENDOR1_PASSWORD = "Vendor@123"
VENDOR2_EMAIL = "vendor2@cmt.com"
VENDOR2_PASSWORD = "Vendor@123"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'

class Phase8Tester:
    def __init__(self):
        self.admin_token = None
        self.vendor1_token = None
        self.vendor2_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        self.vendor1_job_id = None
        self.vendor2_job_id = None

    def log(self, msg, color=Colors.BLUE):
        print(f"{color}{msg}{Colors.END}")

    def test(self, name, method, endpoint, expected_status, data=None, token=None, params=None):
        """Run a single API test"""
        url = f"{BASE_URL}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n{Colors.BLUE}🔍 Test {self.tests_run}: {name}{Colors.END}")
        print(f"   {method} {endpoint}")
        if params:
            print(f"   Params: {params}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=15)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=15)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"{Colors.GREEN}✅ PASS - Status: {response.status_code}{Colors.END}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.tests_failed += 1
                self.failed_tests.append(name)
                print(f"{Colors.RED}❌ FAIL - Expected {expected_status}, got {response.status_code}{Colors.END}")
                try:
                    err_body = response.json()
                    print(f"{Colors.RED}   Error: {err_body.get('detail', err_body)}{Colors.END}")
                except:
                    print(f"{Colors.RED}   Response: {response.text[:200]}{Colors.END}")
                return False, {}

        except requests.exceptions.Timeout:
            self.tests_failed += 1
            self.failed_tests.append(name)
            print(f"{Colors.RED}❌ FAIL - Request timeout{Colors.END}")
            return False, {}
        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(name)
            print(f"{Colors.RED}❌ FAIL - Error: {str(e)}{Colors.END}")
            return False, {}

    def run_all_tests(self):
        """Execute all test suites"""
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("CV. DEWI ADITYA - BACKEND API TESTING", Colors.CYAN)
        self.log("Phase 8: Pagination & Vendor Portal Progress History", Colors.CYAN)
        self.log("="*80 + "\n", Colors.CYAN)

        # ─── AUTHENTICATION ───
        self.log("\n📋 PHASE 0: AUTHENTICATION", Colors.YELLOW)
        
        # Admin login
        success, data = self.test(
            "Admin Login",
            "POST",
            "/api/auth/login",
            200,
            data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if success and data.get('token'):
            self.admin_token = data['token']
            self.log(f"   ✓ Admin token obtained", Colors.GREEN)
        else:
            self.log("   ❌ Admin login failed - stopping tests", Colors.RED)
            return self.print_summary()

        # Vendor1 login
        success, data = self.test(
            "Vendor1 Login",
            "POST",
            "/api/auth/login",
            200,
            data={"email": VENDOR1_EMAIL, "password": VENDOR1_PASSWORD}
        )
        if success and data.get('token'):
            self.vendor1_token = data['token']
            self.log(f"   ✓ Vendor1 token obtained", Colors.GREEN)
        else:
            self.log("   ⚠ Vendor1 login failed - some tests will be skipped", Colors.YELLOW)

        # Vendor2 login
        success, data = self.test(
            "Vendor2 Login",
            "POST",
            "/api/auth/login",
            200,
            data={"email": VENDOR2_EMAIL, "password": VENDOR2_PASSWORD}
        )
        if success and data.get('token'):
            self.vendor2_token = data['token']
            self.log(f"   ✓ Vendor2 token obtained", Colors.GREEN)
        else:
            self.log("   ⚠ Vendor2 login failed - some tests will be skipped", Colors.YELLOW)

        # ─── PHASE 8.1: UNIFIED INVENTORY PAGINATION ───
        self.log("\n📋 PHASE 8.1: UNIFIED INVENTORY PAGINATION", Colors.YELLOW)
        
        # Test 1: Basic pagination page=1, limit=3
        self.log("\n   🔹 Test 8.1.1: Basic Pagination (page=1, limit=3)", Colors.CYAN)
        success, data = self.test(
            "GET /api/wms/stock/unified?page=1&limit=3",
            "GET",
            "/api/wms/stock/unified",
            200,
            token=self.admin_token,
            params={"page": 1, "limit": 3}
        )
        if success:
            # Verify response structure
            required_fields = ['items', 'total', 'page', 'limit', 'total_pages', 'has_next', 'has_prev', 'filters_applied']
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log(f"   ❌ Missing fields in response: {missing_fields}", Colors.RED)
                self.tests_failed += 1
                self.failed_tests.append("Pagination response structure validation")
            else:
                self.log(f"   ✓ Response structure valid", Colors.GREEN)
                self.log(f"   ✓ Total items: {data.get('total')}", Colors.GREEN)
                self.log(f"   ✓ Page: {data.get('page')}, Limit: {data.get('limit')}", Colors.GREEN)
                self.log(f"   ✓ Total pages: {data.get('total_pages')}", Colors.GREEN)
                self.log(f"   ✓ Has next: {data.get('has_next')}, Has prev: {data.get('has_prev')}", Colors.GREEN)
                
                # Verify total_pages calculation
                total = data.get('total', 0)
                limit = data.get('limit', 1)
                expected_total_pages = (total + limit - 1) // limit if total > 0 else 0
                actual_total_pages = data.get('total_pages', 0)
                if expected_total_pages == actual_total_pages:
                    self.log(f"   ✓ Total pages calculation correct: {actual_total_pages}", Colors.GREEN)
                else:
                    self.log(f"   ❌ Total pages calculation wrong: expected {expected_total_pages}, got {actual_total_pages}", Colors.RED)
                    self.tests_failed += 1
                    self.failed_tests.append("Total pages calculation")
                
                # Verify has_next for page 1 with data > 3
                if total > 3:
                    if data.get('has_next') == True:
                        self.log(f"   ✓ has_next=true for page 1 (total={total} > limit=3)", Colors.GREEN)
                    else:
                        self.log(f"   ❌ has_next should be true for page 1 when total > limit", Colors.RED)
                        self.tests_failed += 1
                        self.failed_tests.append("has_next validation")

        # Test 2: Page 2 with limit=3
        self.log("\n   🔹 Test 8.1.2: Page 2 Pagination (page=2, limit=3)", Colors.CYAN)
        success, data = self.test(
            "GET /api/wms/stock/unified?page=2&limit=3",
            "GET",
            "/api/wms/stock/unified",
            200,
            token=self.admin_token,
            params={"page": 2, "limit": 3}
        )
        if success:
            if data.get('page') == 2:
                self.log(f"   ✓ Page number correct: {data.get('page')}", Colors.GREEN)
            else:
                self.log(f"   ❌ Page number wrong: expected 2, got {data.get('page')}", Colors.RED)
            
            if data.get('has_prev') == True:
                self.log(f"   ✓ has_prev=true for page 2", Colors.GREEN)
            else:
                self.log(f"   ❌ has_prev should be true for page 2", Colors.RED)
                self.tests_failed += 1
                self.failed_tests.append("has_prev validation for page 2")

        # Test 3: Out-of-range page
        self.log("\n   🔹 Test 8.1.3: Out-of-range Page (page=999, limit=10)", Colors.CYAN)
        success, data = self.test(
            "GET /api/wms/stock/unified?page=999&limit=10",
            "GET",
            "/api/wms/stock/unified",
            200,
            token=self.admin_token,
            params={"page": 999, "limit": 10}
        )
        if success:
            items = data.get('items', None)
            if items is not None and len(items) == 0:
                self.log(f"   ✓ Out-of-range page returns empty items array", Colors.GREEN)
            else:
                self.log(f"   ❌ Out-of-range page should return items=[]", Colors.RED)
                self.tests_failed += 1
                self.failed_tests.append("Out-of-range page handling")

        # Test 4: Pagination + filter (inventory_category)
        self.log("\n   🔹 Test 8.1.4: Pagination + Filter (category=fg_internal)", Colors.CYAN)
        success, data = self.test(
            "GET /api/wms/stock/unified?inventory_category=fg_internal&page=1&limit=50",
            "GET",
            "/api/wms/stock/unified",
            200,
            token=self.admin_token,
            params={"inventory_category": "fg_internal", "page": 1, "limit": 50}
        )
        if success:
            filters = data.get('filters_applied', {})
            if filters.get('inventory_category') == 'fg_internal':
                self.log(f"   ✓ Filter applied correctly: {filters}", Colors.GREEN)
            else:
                self.log(f"   ❌ Filter not applied correctly", Colors.RED)
            
            # Verify all items match the filter
            items = data.get('items', [])
            if items:
                mismatched = [i for i in items if i.get('inventory_category') != 'fg_internal']
                if not mismatched:
                    self.log(f"   ✓ All {len(items)} items match filter", Colors.GREEN)
                else:
                    self.log(f"   ❌ {len(mismatched)} items don't match filter", Colors.RED)

        # Test 5: Pagination + search
        self.log("\n   🔹 Test 8.1.5: Pagination + Search (search=kemeja)", Colors.CYAN)
        success, data = self.test(
            "GET /api/wms/stock/unified?search=kemeja&page=1&limit=10",
            "GET",
            "/api/wms/stock/unified",
            200,
            token=self.admin_token,
            params={"search": "kemeja", "page": 1, "limit": 10}
        )
        if success:
            filters = data.get('filters_applied', {})
            if filters.get('search') == 'kemeja':
                self.log(f"   ✓ Search filter applied: {filters}", Colors.GREEN)
            items = data.get('items', [])
            self.log(f"   ✓ Found {len(items)} items matching 'kemeja'", Colors.GREEN)

        # Test 6: Limit clamping (limit=600 should clamp to 500)
        self.log("\n   🔹 Test 8.1.6: Limit Clamping (limit=600 → 500)", Colors.CYAN)
        success, data = self.test(
            "GET /api/wms/stock/unified?limit=600",
            "GET",
            "/api/wms/stock/unified",
            200,
            token=self.admin_token,
            params={"limit": 600}
        )
        if success:
            actual_limit = data.get('limit')
            if actual_limit == 500:
                self.log(f"   ✓ Limit clamped correctly: 600 → 500", Colors.GREEN)
            else:
                self.log(f"   ❌ Limit not clamped: expected 500, got {actual_limit}", Colors.RED)
                self.tests_failed += 1
                self.failed_tests.append("Limit clamping to 500")

        # ─── PHASE 8.2: VENDOR PORTAL PROGRESS HISTORY ───
        self.log("\n📋 PHASE 8.2: VENDOR PORTAL PROGRESS HISTORY", Colors.YELLOW)
        
        # First, get vendor jobs to find job IDs
        if self.vendor1_token:
            self.log("\n   🔹 Setup: Get Vendor1 Jobs", Colors.CYAN)
            success, data = self.test(
                "GET /api/dewi/cmt/vendor/my-jobs (Vendor1)",
                "GET",
                "/api/dewi/cmt/vendor/my-jobs",
                200,
                token=self.vendor1_token
            )
            if success and data:
                jobs = data if isinstance(data, list) else []
                if jobs:
                    self.vendor1_job_id = jobs[0].get('id')
                    self.log(f"   ✓ Vendor1 has {len(jobs)} jobs, using job_id: {self.vendor1_job_id}", Colors.GREEN)
                else:
                    self.log(f"   ⚠ Vendor1 has no jobs - will skip progress history tests", Colors.YELLOW)

        if self.vendor2_token:
            self.log("\n   🔹 Setup: Get Vendor2 Jobs", Colors.CYAN)
            success, data = self.test(
                "GET /api/dewi/cmt/vendor/my-jobs (Vendor2)",
                "GET",
                "/api/dewi/cmt/vendor/my-jobs",
                200,
                token=self.vendor2_token
            )
            if success and data:
                jobs = data if isinstance(data, list) else []
                if jobs:
                    self.vendor2_job_id = jobs[0].get('id')
                    self.log(f"   ✓ Vendor2 has {len(jobs)} jobs, using job_id: {self.vendor2_job_id}", Colors.GREEN)

        # Test 7: Vendor1 access their own job progress history
        if self.vendor1_token and self.vendor1_job_id:
            self.log("\n   🔹 Test 8.2.1: Vendor1 Access Own Job Progress History", Colors.CYAN)
            success, data = self.test(
                f"GET /api/dewi/cmt/vendor/my-jobs/{self.vendor1_job_id}/progress-history",
                "GET",
                f"/api/dewi/cmt/vendor/my-jobs/{self.vendor1_job_id}/progress-history",
                200,
                token=self.vendor1_token
            )
            if success:
                # Verify response structure
                required_fields = ['job', 'reports', 'summary', 'by_step']
                missing_fields = [f for f in required_fields if f not in data]
                if missing_fields:
                    self.log(f"   ❌ Missing fields: {missing_fields}", Colors.RED)
                    self.tests_failed += 1
                    self.failed_tests.append("Progress history response structure")
                else:
                    self.log(f"   ✓ Response structure valid", Colors.GREEN)
                    summary = data.get('summary', {})
                    self.log(f"   ✓ Total reports: {summary.get('total_reports')}", Colors.GREEN)
                    self.log(f"   ✓ Total processed: {summary.get('total_processed')}", Colors.GREEN)
                    self.log(f"   ✓ Pass rate: {summary.get('pass_rate_pct')}%", Colors.GREEN)
                    by_step = data.get('by_step', [])
                    self.log(f"   ✓ Steps tracked: {len(by_step)}", Colors.GREEN)

        # Test 8: Vendor2 try to access Vendor1's job (should get 403)
        if self.vendor2_token and self.vendor1_job_id:
            self.log("\n   🔹 Test 8.2.2: Vendor2 Access Vendor1's Job (403 Expected)", Colors.CYAN)
            success, data = self.test(
                f"GET /api/dewi/cmt/vendor/my-jobs/{self.vendor1_job_id}/progress-history (Vendor2)",
                "GET",
                f"/api/dewi/cmt/vendor/my-jobs/{self.vendor1_job_id}/progress-history",
                403,
                token=self.vendor2_token
            )
            if success:
                self.log(f"   ✓ Correctly blocked with 403", Colors.GREEN)

        # Test 9: Non-existent job_id (should get 404)
        if self.vendor1_token:
            self.log("\n   🔹 Test 8.2.3: Non-existent Job ID (404 Expected)", Colors.CYAN)
            fake_job_id = "nonexistent-job-id-12345"
            success, data = self.test(
                f"GET /api/dewi/cmt/vendor/my-jobs/{fake_job_id}/progress-history",
                "GET",
                f"/api/dewi/cmt/vendor/my-jobs/{fake_job_id}/progress-history",
                404,
                token=self.vendor1_token
            )
            if success:
                self.log(f"   ✓ Correctly returned 404 for non-existent job", Colors.GREEN)

        # Test 10: Admin access any job (should work - bypass vendor check)
        if self.admin_token and self.vendor1_job_id:
            self.log("\n   🔹 Test 8.2.4: Admin Access Any Job (Bypass Vendor Check)", Colors.CYAN)
            success, data = self.test(
                f"GET /api/dewi/cmt/vendor/my-jobs/{self.vendor1_job_id}/progress-history (Admin)",
                "GET",
                f"/api/dewi/cmt/vendor/my-jobs/{self.vendor1_job_id}/progress-history",
                200,
                token=self.admin_token
            )
            if success:
                self.log(f"   ✓ Admin can access vendor job (bypass check working)", Colors.GREEN)

        # ─── PHASE 8.3: REGRESSION TESTS ───
        self.log("\n📋 PHASE 8.3: REGRESSION TESTS", Colors.YELLOW)
        
        # Test 11: Unified inventory summary
        self.log("\n   🔹 Test 8.3.1: Unified Inventory Summary", Colors.CYAN)
        success, data = self.test(
            "GET /api/wms/stock/unified/summary",
            "GET",
            "/api/wms/stock/unified/summary",
            200,
            token=self.admin_token
        )
        if success:
            by_category = data.get('by_category', [])
            by_ownership = data.get('by_ownership', [])
            low_stock = data.get('low_stock_count', 0)
            self.log(f"   ✓ Categories: {len(by_category)}, Ownerships: {len(by_ownership)}, Low stock: {low_stock}", Colors.GREEN)

        # Test 12: Stock adjustment (+1 then -1 to restore)
        self.log("\n   🔹 Test 8.3.2: Stock Adjustment (Correction +1, then -1)", Colors.CYAN)
        
        # First, get a material to adjust
        success, data = self.test(
            "GET material for adjustment",
            "GET",
            "/api/wms/stock/unified",
            200,
            token=self.admin_token,
            params={"limit": 1}
        )
        
        if success and data.get('items'):
            material = data['items'][0]
            material_id = material.get('material_id')
            qty_before = material.get('quantity', 0)
            
            self.log(f"   ✓ Using material: {material_id} (qty: {qty_before})", Colors.GREEN)
            
            # Adjustment +1
            success, adj_data = self.test(
                "POST /api/wms/stock/unified/adjust (+1)",
                "POST",
                "/api/wms/stock/unified/adjust",
                200,
                data={
                    "material_id": material_id,
                    "adjustment_type": "correction",
                    "qty_delta": 1,
                    "reason": "Test adjustment +1 for regression test"
                },
                token=self.admin_token
            )
            
            if success:
                qty_after_plus = adj_data.get('qty_after', 0)
                self.log(f"   ✓ Adjustment +1: {qty_before} → {qty_after_plus}", Colors.GREEN)
                
                # Adjustment -1 to restore
                success, adj_data = self.test(
                    "POST /api/wms/stock/unified/adjust (-1)",
                    "POST",
                    "/api/wms/stock/unified/adjust",
                    200,
                    data={
                        "material_id": material_id,
                        "adjustment_type": "correction",
                        "qty_delta": -1,
                        "reason": "Test adjustment -1 to restore"
                    },
                    token=self.admin_token
                )
                
                if success:
                    qty_after_minus = adj_data.get('qty_after', 0)
                    self.log(f"   ✓ Adjustment -1: {qty_after_plus} → {qty_after_minus}", Colors.GREEN)
                    if qty_after_minus == qty_before:
                        self.log(f"   ✓ Quantity restored to original: {qty_before}", Colors.GREEN)
                    else:
                        self.log(f"   ⚠ Quantity not fully restored: expected {qty_before}, got {qty_after_minus}", Colors.YELLOW)
        else:
            self.log(f"   ⚠ No materials found for adjustment test", Colors.YELLOW)

        # Test 13: Phase 7 daily report
        self.log("\n   🔹 Test 8.3.3: Phase 7 Daily Report", Colors.CYAN)
        today = date.today().isoformat()
        success, data = self.test(
            "GET /api/dewi/reports/daily",
            "GET",
            "/api/dewi/reports/daily",
            200,
            token=self.admin_token,
            params={"date": today}
        )
        if success:
            self.log(f"   ✓ Daily report working for date: {today}", Colors.GREEN)

        # Test 14: Phase 7 monthly report
        self.log("\n   🔹 Test 8.3.4: Phase 7 Monthly Report", Colors.CYAN)
        now = datetime.now()
        success, data = self.test(
            "GET /api/dewi/reports/monthly",
            "GET",
            "/api/dewi/reports/monthly",
            200,
            token=self.admin_token,
            params={"year": now.year, "month": now.month}
        )
        if success:
            self.log(f"   ✓ Monthly report working for {now.year}-{now.month:02d}", Colors.GREEN)

        return self.print_summary()

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*80, Colors.CYAN)
        self.log("TEST SUMMARY", Colors.CYAN)
        self.log("="*80, Colors.CYAN)
        
        total = self.tests_run
        passed = self.tests_passed
        failed = self.tests_failed
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        self.log(f"\nTotal Tests: {total}", Colors.BLUE)
        self.log(f"Passed: {passed} ({pass_rate:.1f}%)", Colors.GREEN)
        self.log(f"Failed: {failed}", Colors.RED if failed > 0 else Colors.GREEN)
        
        if self.failed_tests:
            self.log("\n❌ Failed Tests:", Colors.RED)
            for test in self.failed_tests:
                self.log(f"   - {test}", Colors.RED)
        
        self.log("\n" + "="*80 + "\n", Colors.CYAN)
        
        return 0 if failed == 0 else 1

def main():
    tester = Phase8Tester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
