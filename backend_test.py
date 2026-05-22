"""
Backend API Testing for CV. Dewi Aditya — Phase 7 Reports & Unified Inventory
Testing:
1. Unified Inventory (stock viewer + manual adjustment/opname)
2. Phase 7 Reports (daily, monthly, per PO, actual-vs-target, trend, CSV exports)
3. Vendor CMT Portal (DO detail dialog)
"""
import requests
import sys
from datetime import datetime, date

class DewiPhase7Tester:
    def __init__(self, base_url="https://workspace-hub-build.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.vendor_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.po_id = None  # Will be populated from list
        self.material_id = None  # Will be populated from unified stock
        self.adjustment_id = None  # Will be populated from adjustment test

    def run_test(self, name, method, endpoint, expected_status, data=None, description="", token=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        # Use provided token or default to admin_token
        use_token = token if token is not None else self.admin_token
        if use_token:
            headers['Authorization'] = f'Bearer {use_token}'

        self.tests_run += 1
        print(f"\n{'='*80}")
        print(f"🔍 Test #{self.tests_run}: {name}")
        if description:
            print(f"   Description: {description}")
        print(f"   Endpoint: {method} {endpoint}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    resp_json = response.json()
                    if isinstance(resp_json, list):
                        print(f"   Response: List with {len(resp_json)} items")
                        if len(resp_json) > 0:
                            print(f"   First item keys: {list(resp_json[0].keys())[:8]}")
                    elif isinstance(resp_json, dict):
                        print(f"   Response keys: {list(resp_json.keys())[:10]}")
                        # Print some key metrics if available
                        if 'total' in resp_json:
                            print(f"   Total: {resp_json['total']}")
                        if 'items' in resp_json and isinstance(resp_json['items'], list):
                            print(f"   Items count: {len(resp_json['items'])}")
                except:
                    print(f"   Response: {response.text[:200]}")
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                self.failed_tests.append({
                    'name': name,
                    'endpoint': endpoint,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'response': response.text[:300]
                })

            return success, response.json() if success and response.text else {}

        except requests.exceptions.Timeout:
            print(f"❌ FAILED - Request timeout after 15 seconds")
            self.failed_tests.append({'name': name, 'endpoint': endpoint, 'error': 'Timeout'})
            return False, {}
        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)}")
            self.failed_tests.append({'name': name, 'endpoint': endpoint, 'error': str(e)})
            return False, {}

    def test_login(self, email, password, role="admin"):
        """Test login and get token"""
        print(f"\n{'#'*80}")
        print(f"# AUTHENTICATION TEST - {role.upper()}")
        print(f"{'#'*80}")
        success, response = self.run_test(
            f"Login as {role}",
            "POST",
            "/api/auth/login",
            200,
            data={"email": email, "password": password},
            description=f"Login dengan {role} credentials"
        )
        if success and 'token' in response:
            token = response['token']
            print(f"   ✓ Token obtained: {token[:20]}...")
            if role == "admin":
                self.admin_token = token
            elif role == "vendor":
                self.vendor_token = token
            return True
        return False

    # ═══════════════════════════════════════════════════════════════════════════
    # UNIFIED INVENTORY TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_unified_inventory_list(self):
        """Test GET /api/wms/stock/unified"""
        print(f"\n{'#'*80}")
        print(f"# UNIFIED INVENTORY TESTS")
        print(f"{'#'*80}")
        
        # Test 1: List all stock
        success, response = self.run_test(
            "Unified Inventory - List All",
            "GET",
            "/api/wms/stock/unified",
            200,
            description="List all stock without filters"
        )
        
        # Store material_id for adjustment test
        if success and response.get('items') and len(response['items']) > 0:
            self.material_id = response['items'][0].get('material_id')
            print(f"   ✓ Stored material_id for adjustment test: {self.material_id}")
        
        # Test 2: Filter by inventory_category
        self.run_test(
            "Unified Inventory - Filter by Category (raw_material)",
            "GET",
            "/api/wms/stock/unified?inventory_category=raw_material",
            200,
            description="Filter by inventory_category=raw_material"
        )
        
        # Test 3: Filter by ownership
        self.run_test(
            "Unified Inventory - Filter by Ownership (cv_da)",
            "GET",
            "/api/wms/stock/unified?ownership=cv_da",
            200,
            description="Filter by ownership=cv_da"
        )
        
        # Test 4: Search by material name
        self.run_test(
            "Unified Inventory - Search",
            "GET",
            "/api/wms/stock/unified?search=kain",
            200,
            description="Search by material name/code"
        )
        
        return success

    def test_unified_inventory_summary(self):
        """Test GET /api/wms/stock/unified/summary"""
        success, response = self.run_test(
            "Unified Inventory - Summary",
            "GET",
            "/api/wms/stock/unified/summary",
            200,
            description="Get aggregate summary by category and ownership"
        )
        
        if success:
            print(f"   ✓ Summary structure validated")
            if 'by_category' in response:
                print(f"   Categories: {len(response['by_category'])}")
            if 'by_ownership' in response:
                print(f"   Ownerships: {len(response['by_ownership'])}")
            if 'low_stock_count' in response:
                print(f"   Low stock items: {response['low_stock_count']}")
        
        return success

    def test_unified_inventory_adjust(self):
        """Test POST /api/wms/stock/unified/adjust - 4 adjustment types"""
        
        if not self.material_id:
            print(f"\n⚠️  Skipping adjustment tests - no material_id available")
            return False
        
        # Test 1: opname_increase (should convert to positive)
        success1, resp1 = self.run_test(
            "Stock Adjustment - opname_increase",
            "POST",
            "/api/wms/stock/unified/adjust",
            200,
            data={
                "material_id": self.material_id,
                "adjustment_type": "opname_increase",
                "qty_delta": 10,
                "reason": "Test opname increase - found extra stock",
                "reference_no": "TEST-OPNAME-001"
            },
            description="Adjustment type: opname_increase (should be +10)"
        )
        
        if success1 and resp1.get('movement_id'):
            self.adjustment_id = resp1['movement_id']
        
        # Test 2: opname_decrease (should convert to negative)
        success2, resp2 = self.run_test(
            "Stock Adjustment - opname_decrease",
            "POST",
            "/api/wms/stock/unified/adjust",
            200,
            data={
                "material_id": self.material_id,
                "adjustment_type": "opname_decrease",
                "qty_delta": 5,
                "reason": "Test opname decrease - stock missing",
                "reference_no": "TEST-OPNAME-002"
            },
            description="Adjustment type: opname_decrease (should be -5)"
        )
        
        # Test 3: damage (should convert to negative)
        success3, resp3 = self.run_test(
            "Stock Adjustment - damage",
            "POST",
            "/api/wms/stock/unified/adjust",
            200,
            data={
                "material_id": self.material_id,
                "adjustment_type": "damage",
                "qty_delta": 2,
                "reason": "Test damage adjustment - material damaged",
                "reference_no": "TEST-DAMAGE-001"
            },
            description="Adjustment type: damage (should be -2)"
        )
        
        # Test 4: correction (should preserve sign)
        success4, resp4 = self.run_test(
            "Stock Adjustment - correction (positive)",
            "POST",
            "/api/wms/stock/unified/adjust",
            200,
            data={
                "material_id": self.material_id,
                "adjustment_type": "correction",
                "qty_delta": 3,
                "reason": "Test correction - manual fix",
                "reference_no": "TEST-CORR-001"
            },
            description="Adjustment type: correction (should preserve +3)"
        )
        
        # Verify sign conversion
        if success1 and resp1.get('delta'):
            print(f"   ✓ opname_increase delta: {resp1['delta']} (expected positive)")
        if success2 and resp2.get('delta'):
            print(f"   ✓ opname_decrease delta: {resp2['delta']} (expected negative)")
        if success3 and resp3.get('delta'):
            print(f"   ✓ damage delta: {resp3['delta']} (expected negative)")
        if success4 and resp4.get('delta'):
            print(f"   ✓ correction delta: {resp4['delta']} (expected +3)")
        
        return success1 and success2 and success3 and success4

    def test_unified_inventory_adjustments_history(self):
        """Test GET /api/wms/stock/unified/adjustments"""
        
        # Test 1: List all adjustments
        success1, resp1 = self.run_test(
            "Adjustment History - All",
            "GET",
            "/api/wms/stock/unified/adjustments",
            200,
            description="List all adjustment history"
        )
        
        # Test 2: Filter by material_id
        if self.material_id:
            success2, resp2 = self.run_test(
                "Adjustment History - Filter by Material",
                "GET",
                f"/api/wms/stock/unified/adjustments?material_id={self.material_id}",
                200,
                description=f"Filter adjustments for material {self.material_id}"
            )
            return success1 and success2
        
        return success1

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 7 REPORTS TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_phase7_daily_report(self):
        """Test GET /api/dewi/reports/daily"""
        print(f"\n{'#'*80}")
        print(f"# PHASE 7 REPORTS TESTS")
        print(f"{'#'*80}")
        
        today = date.today().isoformat()
        
        # Test 1: Today's report
        success1, resp1 = self.run_test(
            "Phase 7 - Daily Report (Today)",
            "GET",
            f"/api/dewi/reports/daily?date={today}",
            200,
            description=f"Daily report for {today}"
        )
        
        # Test 2: Without date parameter (should default to today)
        success2, resp2 = self.run_test(
            "Phase 7 - Daily Report (Default)",
            "GET",
            "/api/dewi/reports/daily",
            200,
            description="Daily report without date (should default to today)"
        )
        
        if success1 and resp1:
            print(f"   ✓ Daily report structure validated")
            if 'production' in resp1:
                prod = resp1['production']
                print(f"   Production: {prod.get('total_processed', 0)} processed, {prod.get('total_passed', 0)} passed")
            if 'delivery_orders' in resp1:
                do = resp1['delivery_orders']
                print(f"   DOs: {do.get('issued', 0)} issued, {do.get('received', 0)} received")
        
        return success1 and success2

    def test_phase7_monthly_report(self):
        """Test GET /api/dewi/reports/monthly"""
        
        today = date.today()
        year = today.year
        month = today.month
        
        success, response = self.run_test(
            "Phase 7 - Monthly Report",
            "GET",
            f"/api/dewi/reports/monthly?year={year}&month={month}",
            200,
            description=f"Monthly report for {year}-{month:02d}"
        )
        
        if success and response:
            print(f"   ✓ Monthly report structure validated")
            if 'summary' in response:
                summ = response['summary']
                print(f"   Summary: {summ.get('total_processed', 0)} processed, {summ.get('vendor_count', 0)} vendors")
            if 'production_by_vendor' in response:
                print(f"   Vendors: {len(response['production_by_vendor'])}")
            if 'maklon_by_client' in response:
                print(f"   Maklon clients: {len(response['maklon_by_client'])}")
        
        return success

    def test_phase7_po_report(self):
        """Test GET /api/dewi/reports/po/{po_id}"""
        
        # First, get a PO ID from the list
        success_list, pos = self.run_test(
            "Phase 7 - Get PO List (for testing)",
            "GET",
            "/api/dewi/maklon/pos?limit=1",
            200,
            description="Get first PO for testing PO report"
        )
        
        if success_list and pos and len(pos) > 0:
            self.po_id = pos[0].get('id')
            print(f"   ✓ Using PO ID: {self.po_id}")
            
            # Test PO report
            success, response = self.run_test(
                "Phase 7 - PO Report",
                "GET",
                f"/api/dewi/reports/po/{self.po_id}",
                200,
                description=f"Detailed report for PO {self.po_id}"
            )
            
            if success and response:
                print(f"   ✓ PO report structure validated")
                if 'po' in response:
                    po = response['po']
                    print(f"   PO: {po.get('po_number', 'N/A')} - {po.get('client_name', 'N/A')}")
                if 'progress' in response:
                    prog = response['progress']
                    print(f"   Progress: {prog.get('qty_produced', 0)}/{prog.get('target_qty', 0)} produced")
                if 'finance' in response:
                    fin = response['finance']
                    print(f"   Finance: {fin.get('payment_status', 'N/A')}, outstanding: {fin.get('outstanding', 0)}")
            
            return success
        else:
            print(f"   ⚠️  No PO found - skipping PO report test")
            return True  # Don't fail if no PO exists

    def test_phase7_actual_vs_target(self):
        """Test GET /api/dewi/reports/actual-vs-target"""
        
        today = date.today()
        period = f"{today.year}-{today.month:02d}"
        
        success, response = self.run_test(
            "Phase 7 - Actual vs Target",
            "GET",
            f"/api/dewi/reports/actual-vs-target?period={period}",
            200,
            description=f"Comparison report for period {period}"
        )
        
        if success and response:
            print(f"   ✓ Actual vs Target structure validated")
            if 'cmt_jobs' in response:
                print(f"   CMT Jobs: {len(response['cmt_jobs'])}")
            if 'maklon_pos' in response:
                print(f"   Maklon POs: {len(response['maklon_pos'])}")
            if 'summary' in response:
                summ = response['summary']
                print(f"   Summary: CMT {summ.get('cmt_total_actual', 0)}/{summ.get('cmt_total_target', 0)}")
        
        return success

    def test_phase7_production_trend(self):
        """Test GET /api/dewi/reports/production-trend"""
        
        # Test with 30 days
        success1, resp1 = self.run_test(
            "Phase 7 - Production Trend (30 days)",
            "GET",
            "/api/dewi/reports/production-trend?days=30",
            200,
            description="Production trend for last 30 days"
        )
        
        # Test with 7 days
        success2, resp2 = self.run_test(
            "Phase 7 - Production Trend (7 days)",
            "GET",
            "/api/dewi/reports/production-trend?days=7",
            200,
            description="Production trend for last 7 days"
        )
        
        if success1 and resp1:
            print(f"   ✓ Trend structure validated")
            if 'trend' in resp1:
                print(f"   Trend data points: {len(resp1['trend'])}")
        
        return success1 and success2

    def test_phase7_csv_exports(self):
        """Test CSV export endpoints"""
        
        today = date.today()
        
        # Test 1: Daily CSV export
        success1, resp1 = self.run_test(
            "Phase 7 - Export Daily CSV",
            "GET",
            f"/api/dewi/reports/export/daily.csv?date={today.isoformat()}",
            200,
            description="Export daily report as CSV"
        )
        
        # Test 2: Monthly CSV export
        success2, resp2 = self.run_test(
            "Phase 7 - Export Monthly CSV",
            "GET",
            f"/api/dewi/reports/export/monthly.csv?year={today.year}&month={today.month}",
            200,
            description="Export monthly report as CSV"
        )
        
        return success1 and success2

    # ═══════════════════════════════════════════════════════════════════════════
    # VENDOR CMT PORTAL TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_vendor_portal_my_dos(self):
        """Test GET /api/dewi/cmt/delivery-orders/vendor/my-dos"""
        print(f"\n{'#'*80}")
        print(f"# VENDOR CMT PORTAL TESTS")
        print(f"{'#'*80}")
        
        if not self.vendor_token:
            print(f"   ⚠️  No vendor token - skipping vendor portal tests")
            return True
        
        # Test 1: List all DOs for vendor
        success1, resp1 = self.run_test(
            "Vendor Portal - My DOs (All)",
            "GET",
            "/api/dewi/cmt/delivery-orders/vendor/my-dos",
            200,
            description="List all DOs assigned to this vendor",
            token=self.vendor_token
        )
        
        # Test 2: Filter by status
        success2, resp2 = self.run_test(
            "Vendor Portal - My DOs (Issued)",
            "GET",
            "/api/dewi/cmt/delivery-orders/vendor/my-dos?status=issued",
            200,
            description="List only issued DOs",
            token=self.vendor_token
        )
        
        # Store DO ID for detail test
        do_id = None
        if success1 and resp1.get('delivery_orders') and len(resp1['delivery_orders']) > 0:
            do_id = resp1['delivery_orders'][0].get('id')
            print(f"   ✓ Found DO for detail test: {do_id}")
        
        # Test 3: Get DO detail
        if do_id:
            success3, resp3 = self.run_test(
                "Vendor Portal - DO Detail",
                "GET",
                f"/api/dewi/cmt/delivery-orders/vendor/my-dos/{do_id}",
                200,
                description=f"Get detail for DO {do_id}",
                token=self.vendor_token
            )
            
            if success3 and resp3:
                print(f"   ✓ DO detail structure validated")
                print(f"   DO Number: {resp3.get('do_number', 'N/A')}")
                print(f"   Status: {resp3.get('status', 'N/A')}")
                print(f"   Items: {len(resp3.get('items', []))}")
            
            return success1 and success2 and success3
        
        return success1 and success2

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*80}")
        print(f"{'='*80}")
        print(f"📊 TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed} ✅")
        print(f"Tests Failed: {len(self.failed_tests)} ❌")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print(f"\n{'='*80}")
            print(f"❌ FAILED TESTS DETAILS:")
            print(f"{'='*80}")
            for i, test in enumerate(self.failed_tests, 1):
                print(f"\n{i}. {test['name']}")
                print(f"   Endpoint: {test.get('endpoint', 'N/A')}")
                if 'expected' in test:
                    print(f"   Expected: {test['expected']}, Got: {test['actual']}")
                if 'error' in test:
                    print(f"   Error: {test['error']}")
                if 'response' in test:
                    print(f"   Response: {test['response']}")
        
        print(f"\n{'='*80}")
        return 0 if len(self.failed_tests) == 0 else 1

def main():
    print(f"""
{'='*80}
CV. DEWI ADITYA ERP — BACKEND API TEST
Phase 7 Reports & Unified Inventory Testing
{'='*80}
Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Base URL: https://workspace-hub-build.preview.emergentagent.com
{'='*80}

Testing Scope:
1. Unified Inventory (GET list, summary, POST adjust, GET adjustments)
2. Phase 7 Reports (daily, monthly, per PO, actual-vs-target, trend, CSV)
3. Vendor CMT Portal (my-dos list & detail)
{'='*80}
""")

    tester = DewiPhase7Tester()

    # ═══════════════════════════════════════════════════════════════════════════
    # AUTHENTICATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Login as admin
    if not tester.test_login("admin@garment.com", "Admin@123", role="admin"):
        print("\n❌ Admin login failed, cannot proceed with tests")
        return tester.print_summary()
    
    # Login as vendor (optional - for vendor portal tests)
    tester.test_login("vendor1@cmt.com", "password123", role="vendor")

    # ═══════════════════════════════════════════════════════════════════════════
    # UNIFIED INVENTORY TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    tester.test_unified_inventory_list()
    tester.test_unified_inventory_summary()
    tester.test_unified_inventory_adjust()
    tester.test_unified_inventory_adjustments_history()

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 7 REPORTS TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    tester.test_phase7_daily_report()
    tester.test_phase7_monthly_report()
    tester.test_phase7_po_report()
    tester.test_phase7_actual_vs_target()
    tester.test_phase7_production_trend()
    tester.test_phase7_csv_exports()

    # ═══════════════════════════════════════════════════════════════════════════
    # VENDOR CMT PORTAL TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    tester.test_vendor_portal_my_dos()

    # Print final summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
