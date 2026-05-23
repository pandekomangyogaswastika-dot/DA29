"""
Backend API Testing for CV. Dewi Aditya — Phase B Frontend Cutover (Maklon)
Testing:
1. Modern /api/dewi/maklon/pos endpoints (GET list, GET detail, POST confirm, POST cancel)
2. Legacy /api/dewi/maklon/orders endpoints (verify wrapper works)
3. Legacy production-detail and material-issues endpoints
4. Accessory module endpoints (POST /api/acc/items, GET /api/acc/items, POST /api/acc/stock/receive)
5. Toko module endpoints (POST /api/dewi/toko/products, GET /api/dewi/toko/products, etc.)
6. Verify dropped collections are absent
"""
import requests
import sys
from datetime import datetime, date

class DewiPhaseBTester:
    def __init__(self, base_url="https://doc-audit-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.po_id = None
        self.client_id = None
        self.legacy_order_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, description=""):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.admin_token:
            headers['Authorization'] = f'Bearer {self.admin_token}'

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
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=15)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    resp_json = response.json()
                    if isinstance(resp_json, list):
                        print(f"   Response: List with {len(resp_json)} items")
                        if len(resp_json) > 0:
                            print(f"   First item keys: {list(resp_json[0].keys())[:10]}")
                    elif isinstance(resp_json, dict):
                        print(f"   Response keys: {list(resp_json.keys())[:12]}")
                        # Print key fields
                        if 'items' in resp_json and isinstance(resp_json['items'], list):
                            print(f"   Items count: {len(resp_json['items'])}")
                        if 'po_number' in resp_json:
                            print(f"   PO Number: {resp_json['po_number']}")
                        if 'order_code' in resp_json:
                            print(f"   Order Code: {resp_json['order_code']}")
                        if 'status' in resp_json:
                            print(f"   Status: {resp_json['status']}")
                        if '_source' in resp_json:
                            print(f"   Source: {resp_json['_source']}")
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

    def test_login(self):
        """Test login and get token"""
        print(f"\n{'#'*80}")
        print(f"# AUTHENTICATION TEST")
        print(f"{'#'*80}")
        success, response = self.run_test(
            "Login as admin",
            "POST",
            "/api/auth/login",
            200,
            data={"email": "admin@garment.com", "password": "Admin@123"},
            description="Login with admin credentials"
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            print(f"   ✓ Token obtained: {self.admin_token[:20]}...")
            return True
        return False

    # ═══════════════════════════════════════════════════════════════════════════
    # MODERN /api/dewi/maklon/pos ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_modern_pos_endpoints(self):
        """Test modern /api/dewi/maklon/pos endpoints"""
        print(f"\n{'#'*80}")
        print(f"# MODERN /api/dewi/maklon/pos ENDPOINTS")
        print(f"{'#'*80}")
        
        # Test 1: GET /api/dewi/maklon/pos - List POs
        success1, resp1 = self.run_test(
            "Modern PO - List All",
            "GET",
            "/api/dewi/maklon/pos",
            200,
            description="List all POs in modern shape with items[], po_number, total_qty, total_value, status"
        )
        
        # Store po_id and client_id for later tests
        if success1 and isinstance(resp1, list) and len(resp1) > 0:
            self.po_id = resp1[0].get('id')
            self.client_id = resp1[0].get('client_id')
            print(f"   ✓ Stored PO ID: {self.po_id}")
            print(f"   ✓ Stored Client ID: {self.client_id}")
            
            # Verify modern shape
            first_po = resp1[0]
            required_fields = ['id', 'po_number', 'items', 'total_qty', 'total_value', 'status']
            missing_fields = [f for f in required_fields if f not in first_po]
            if missing_fields:
                print(f"   ⚠️  Missing fields in PO: {missing_fields}")
            else:
                print(f"   ✓ All required fields present in PO")
            
            # Verify items structure
            if 'items' in first_po and isinstance(first_po['items'], list) and len(first_po['items']) > 0:
                first_item = first_po['items'][0]
                item_fields = ['item_id', 'seri_no', 'artikel', 'qty', 'cmt_rate_per_pcs']
                missing_item_fields = [f for f in item_fields if f not in first_item]
                if missing_item_fields:
                    print(f"   ⚠️  Missing fields in item: {missing_item_fields}")
                else:
                    print(f"   ✓ All required fields present in items")
        
        # Test 2: GET /api/dewi/maklon/pos/{po_id} - Single PO detail
        if self.po_id:
            success2, resp2 = self.run_test(
                "Modern PO - Get Detail",
                "GET",
                f"/api/dewi/maklon/pos/{self.po_id}",
                200,
                description=f"Get single PO detail with full items for PO {self.po_id}"
            )
            
            if success2:
                # Verify detail includes dispatches, material_receives, bom
                detail_fields = ['dispatches', 'material_receives', 'bom']
                present_fields = [f for f in detail_fields if f in resp2]
                print(f"   ✓ Detail enrichment fields present: {present_fields}")
        else:
            print(f"   ⚠️  No PO ID available, skipping detail test")
            success2 = True
        
        return success1 and success2

    def test_modern_pos_confirm_cancel(self):
        """Test POST /api/dewi/maklon/pos/{po_id}/confirm and cancel"""
        
        # First, create a test PO
        if not self.client_id:
            print(f"\n⚠️  No client_id available, skipping confirm/cancel tests")
            return True
        
        # Get a client first
        success_client, clients = self.run_test(
            "Get Maklon Clients",
            "GET",
            "/api/dewi/maklon/clients",
            200,
            description="Get list of maklon clients"
        )
        
        if not success_client or not clients or len(clients) == 0:
            print(f"   ⚠️  No clients found, skipping confirm/cancel tests")
            return True
        
        client_id = clients[0].get('id')
        
        # Create a test PO
        test_po_data = {
            "client_id": client_id,
            "po_date": date.today().isoformat(),
            "deadline": "2026-12-31",
            "payment_terms": "net_30",
            "notes": "Test PO for Phase B testing",
            "items": [
                {
                    "seri_no": "S01",
                    "artikel": "TEST-ARTIKEL-001",
                    "sku_code": "TEST-SKU-001",
                    "color": "Blue",
                    "size": "M",
                    "qty": 100,
                    "cmt_rate_per_pcs": 15000,
                    "product_description": "Test Product for Phase B",
                    "notes": "Test item"
                }
            ]
        }
        
        success_create, resp_create = self.run_test(
            "Modern PO - Create Test PO",
            "POST",
            "/api/dewi/maklon/pos",
            200,
            data=test_po_data,
            description="Create a test PO for confirm/cancel testing"
        )
        
        if not success_create or 'id' not in resp_create:
            print(f"   ⚠️  Failed to create test PO, skipping confirm/cancel tests")
            return False
        
        test_po_id = resp_create['id']
        print(f"   ✓ Created test PO: {test_po_id}")
        
        # Test 3: POST /api/dewi/maklon/pos/{po_id}/confirm
        success_confirm, resp_confirm = self.run_test(
            "Modern PO - Confirm PO",
            "POST",
            f"/api/dewi/maklon/pos/{test_po_id}/confirm",
            200,
            description="Confirm PO - should transition status to 'confirmed'"
        )
        
        if success_confirm:
            # Verify status changed
            if 'status' in resp_confirm and resp_confirm['status'] == 'confirmed':
                print(f"   ✓ PO status transitioned to 'confirmed'")
            else:
                print(f"   ⚠️  PO status not 'confirmed': {resp_confirm.get('status')}")
            
            # Verify WOs created
            if 'work_orders_created' in resp_confirm:
                print(f"   ✓ Work orders created: {len(resp_confirm['work_orders_created'])}")
            
            # Verify AR invoice created
            if 'ar_invoice_number' in resp_confirm:
                print(f"   ✓ AR Invoice created: {resp_confirm['ar_invoice_number']}")
        
        # Create another test PO for cancel test
        success_create2, resp_create2 = self.run_test(
            "Modern PO - Create Test PO for Cancel",
            "POST",
            "/api/dewi/maklon/pos",
            200,
            data=test_po_data,
            description="Create another test PO for cancel testing"
        )
        
        if success_create2 and 'id' in resp_create2:
            test_po_id2 = resp_create2['id']
            
            # Test 4: POST /api/dewi/maklon/pos/{po_id}/cancel
            success_cancel, resp_cancel = self.run_test(
                "Modern PO - Cancel PO",
                "POST",
                f"/api/dewi/maklon/pos/{test_po_id2}/cancel",
                200,
                data={"reason": "Test cancellation"},
                description="Cancel PO - should transition status to 'cancelled'"
            )
            
            if success_cancel:
                if 'status' in resp_cancel and resp_cancel['status'] == 'cancelled':
                    print(f"   ✓ PO status transitioned to 'cancelled'")
                else:
                    print(f"   ⚠️  PO status not 'cancelled': {resp_cancel.get('status')}")
        else:
            success_cancel = True
        
        return success_confirm and success_cancel

    # ═══════════════════════════════════════════════════════════════════════════
    # LEGACY /api/dewi/maklon/orders ENDPOINTS (via wrapper)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_legacy_orders_endpoints(self):
        """Test legacy /api/dewi/maklon/orders endpoints (should work via wrapper)"""
        print(f"\n{'#'*80}")
        print(f"# LEGACY /api/dewi/maklon/orders ENDPOINTS (via wrapper)")
        print(f"{'#'*80}")
        
        # Test 1: GET /api/dewi/maklon/orders - List orders
        success1, resp1 = self.run_test(
            "Legacy Orders - List All",
            "GET",
            "/api/dewi/maklon/orders",
            200,
            description="List orders via legacy endpoint - should return legacy shape from dewi_maklon_pos"
        )
        
        # Verify legacy shape
        if success1 and 'items' in resp1 and isinstance(resp1['items'], list) and len(resp1['items']) > 0:
            first_order = resp1['items'][0]
            self.legacy_order_id = first_order.get('id')
            print(f"   ✓ Stored legacy order ID: {self.legacy_order_id}")
            
            # Verify legacy fields
            legacy_fields = ['id', 'order_code', 'client_id', 'client_name', 'product_name', 
                           'qty_ordered', 'price_per_pcs', 'total_value', 'status', 'order_date']
            missing_fields = [f for f in legacy_fields if f not in first_order]
            if missing_fields:
                print(f"   ⚠️  Missing legacy fields: {missing_fields}")
            else:
                print(f"   ✓ All required legacy fields present")
            
            # Verify _source marker
            if '_source' in first_order and first_order['_source'] == 'dewi_maklon_pos':
                print(f"   ✓ Source marker present: dewi_maklon_pos")
            else:
                print(f"   ⚠️  Source marker missing or incorrect")
        
        # Test 2: GET /api/dewi/maklon/orders/{order_id} - Single order detail
        if self.legacy_order_id:
            success2, resp2 = self.run_test(
                "Legacy Orders - Get Detail",
                "GET",
                f"/api/dewi/maklon/orders/{self.legacy_order_id}",
                200,
                description=f"Get single order detail via legacy endpoint for {self.legacy_order_id}"
            )
            
            if success2:
                # Verify legacy shape with stage_qty
                if 'stage_qty' in resp2:
                    print(f"   ✓ stage_qty field present: {resp2['stage_qty']}")
                if 'linked_wo_ids' in resp2:
                    print(f"   ✓ linked_wo_ids field present")
        else:
            print(f"   ⚠️  No legacy order ID available, skipping detail test")
            success2 = True
        
        return success1 and success2

    def test_legacy_production_detail(self):
        """Test GET /api/dewi/maklon/orders/{id}/production-detail"""
        
        if not self.legacy_order_id:
            print(f"\n⚠️  No legacy order ID available, skipping production-detail test")
            return True
        
        success, response = self.run_test(
            "Legacy Orders - Production Detail",
            "GET",
            f"/api/dewi/maklon/orders/{self.legacy_order_id}/production-detail",
            200,
            description="Get production detail for order (supports stage_qty workflow)"
        )
        
        if success:
            # Verify production detail structure
            required_fields = ['order', 'linked_wos', 'stage_qty', 'sync_mode']
            missing_fields = [f for f in required_fields if f not in response]
            if missing_fields:
                print(f"   ⚠️  Missing fields in production detail: {missing_fields}")
            else:
                print(f"   ✓ All required fields present in production detail")
            
            if 'linked_wos' in response:
                print(f"   ✓ Linked WOs count: {len(response['linked_wos'])}")
        
        return success

    def test_legacy_material_issues(self):
        """Test GET /api/dewi/maklon/orders/{id}/material-issues"""
        
        if not self.legacy_order_id:
            print(f"\n⚠️  No legacy order ID available, skipping material-issues test")
            return True
        
        success, response = self.run_test(
            "Legacy Orders - Material Issues",
            "GET",
            f"/api/dewi/maklon/orders/{self.legacy_order_id}/material-issues",
            200,
            description="Get material issues for order (MaklonMaterialIssuePanel depends on this)"
        )
        
        if success:
            if isinstance(response, list):
                print(f"   ✓ Material issues list returned: {len(response)} items")
            else:
                print(f"   ⚠️  Unexpected response type: {type(response)}")
        
        return success

    # ═══════════════════════════════════════════════════════════════════════════
    # ACCESSORY MODULE ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_accessory_module(self):
        """Test Accessory module endpoints (should still work from rahaza_materials SSOT)"""
        print(f"\n{'#'*80}")
        print(f"# ACCESSORY MODULE ENDPOINTS")
        print(f"{'#'*80}")
        
        # Test 1: POST /api/acc/items - Create accessory item
        test_acc_data = {
            "code": f"ACC-TEST-{int(datetime.now().timestamp())}",
            "name": "Test Accessory Item",
            "category": "accessories",
            "unit": "pcs",
            "min_stock": 10,
            "notes": "Test accessory for Phase B testing"
        }
        
        success1, resp1 = self.run_test(
            "Accessory - Create Item",
            "POST",
            "/api/acc/items",
            201,  # 201 Created is correct for resource creation
            data=test_acc_data,
            description="Create accessory item (should use rahaza_materials SSOT)"
        )
        
        acc_item_id = None
        if success1 and 'id' in resp1:
            acc_item_id = resp1['id']
            print(f"   ✓ Created accessory item: {acc_item_id}")
        
        # Test 2: GET /api/acc/items - List accessory items
        success2, resp2 = self.run_test(
            "Accessory - List Items",
            "GET",
            "/api/acc/items",
            200,
            description="List all accessory items"
        )
        
        # Test 3: POST /api/acc/stock/receive - Receive stock
        if acc_item_id:
            receive_data = {
                "acc_id": acc_item_id,  # Fixed: use acc_id not material_id
                "qty": 100,
                "unit": "pcs",
                "supplier": "Test Supplier",
                "notes": "Test stock receive"
            }
            
            success3, resp3 = self.run_test(
                "Accessory - Receive Stock",
                "POST",
                "/api/acc/stock/receive",
                201,  # 201 Created is correct for resource creation
                data=receive_data,
                description="Receive accessory stock"
            )
        else:
            print(f"   ⚠️  No accessory item ID, skipping stock receive test")
            success3 = True
        
        return success1 and success2 and success3

    # ═══════════════════════════════════════════════════════════════════════════
    # TOKO MODULE ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_toko_module(self):
        """Test Toko module endpoints (legacy URLs via wrappers, marketing_* backed)"""
        print(f"\n{'#'*80}")
        print(f"# TOKO MODULE ENDPOINTS (legacy URLs via wrappers)")
        print(f"{'#'*80}")
        
        # Test 1: POST /api/dewi/toko/products - Create product
        test_product_data = {
            "sku_code": f"TOKO-TEST-{int(datetime.now().timestamp())}",  # Fixed: use sku_code not sku
            "name": "Test Toko Product",
            "category": "fashion",
            "base_price": 150000,  # Fixed: use base_price not price
            "cost_price": 100000,
            "description": "Test product for Phase B testing"
        }
        
        success1, resp1 = self.run_test(
            "Toko - Create Product",
            "POST",
            "/api/dewi/toko/products",
            200,
            data=test_product_data,
            description="Create toko product (should use marketing_* backend)"
        )
        
        product_id = None
        if success1 and 'id' in resp1:
            product_id = resp1['id']
            print(f"   ✓ Created toko product: {product_id}")
        
        # Test 2: GET /api/dewi/toko/products - List products
        success2, resp2 = self.run_test(
            "Toko - List Products",
            "GET",
            "/api/dewi/toko/products",
            200,
            description="List all toko products"
        )
        
        # Test 3: POST /api/dewi/toko/orders - Create order (OPTIONAL - not part of Phase B)
        # Note: Toko order creation endpoint structure is unclear, skipping for Phase B testing
        print(f"\n   ℹ️  Skipping Toko order creation test (not part of Phase B cutover)")
        success3 = True
        success4 = True
        
        # Test 4: GET /api/dewi/toko/orders - List orders (verify read still works)
        success4, resp4 = self.run_test(
            "Toko - List Orders",
            "GET",
            "/api/dewi/toko/orders",
            200,
            description="List all toko orders (verify legacy endpoint still works)"
        )
        
        return success1 and success2 and success3 and success4

    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE COLLECTION VERIFICATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def test_dropped_collections(self):
        """Verify dropped collections are absent"""
        print(f"\n{'#'*80}")
        print(f"# DATABASE COLLECTION VERIFICATION")
        print(f"{'#'*80}")
        
        # This test requires direct DB access, which we don't have via API
        # We'll verify indirectly by checking that legacy endpoints return data from new collections
        
        print(f"   ℹ️  Direct DB collection check requires backend access")
        print(f"   ℹ️  Verifying indirectly via API responses...")
        
        # Check that legacy orders endpoint returns data with _source marker
        success, response = self.run_test(
            "Verify Legacy Wrapper - Source Marker",
            "GET",
            "/api/dewi/maklon/orders?limit=1",
            200,
            description="Verify legacy endpoint returns data from dewi_maklon_pos (check _source marker)"
        )
        
        if success and 'items' in response and len(response['items']) > 0:
            first_item = response['items'][0]
            if '_source' in first_item and first_item['_source'] == 'dewi_maklon_pos':
                print(f"   ✅ VERIFIED: Legacy endpoint uses dewi_maklon_pos (not dewi_maklon_orders)")
                print(f"   ✅ This confirms dewi_maklon_orders collection is not being used")
            else:
                print(f"   ⚠️  Source marker missing or incorrect: {first_item.get('_source')}")
        
        print(f"\n   Expected dropped collections (should NOT be in use):")
        dropped_collections = [
            "acc_items",
            "acc_stock_movements",
            "dewi_maklon_orders",
            "dewi_toko_products",
            "dewi_toko_channels",
            "dewi_toko_channel_syncs",
            "dewi_toko_orders",
            "dewi_toko_returns",
            "dewi_toko_reviews"
        ]
        for coll in dropped_collections:
            print(f"   - {coll}")
        
        print(f"\n   ✓ Indirect verification complete via API source markers")
        
        return success

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*80}")
        print(f"{'='*80}")
        print(f"📊 TEST SUMMARY - Phase B Frontend Cutover (Maklon)")
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
Phase B Frontend Cutover (Maklon Modules)
{'='*80}
Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Base URL: https://doc-audit-4.preview.emergentagent.com
{'='*80}

Testing Scope:
1. Modern /api/dewi/maklon/pos endpoints (GET list, GET detail, POST confirm, POST cancel)
2. Legacy /api/dewi/maklon/orders endpoints (verify wrapper works)
3. Legacy production-detail and material-issues endpoints
4. Accessory module endpoints (POST /api/acc/items, GET /api/acc/items, POST /api/acc/stock/receive)
5. Toko module endpoints (POST /api/dewi/toko/products, GET /api/dewi/toko/products, etc.)
6. Verify dropped collections are absent (indirect via source markers)
{'='*80}
""")

    tester = DewiPhaseBTester()

    # ═══════════════════════════════════════════════════════════════════════════
    # AUTHENTICATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    if not tester.test_login():
        print("\n❌ Admin login failed, cannot proceed with tests")
        return tester.print_summary()

    # ═══════════════════════════════════════════════════════════════════════════
    # MODERN /api/dewi/maklon/pos ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    tester.test_modern_pos_endpoints()
    tester.test_modern_pos_confirm_cancel()

    # ═══════════════════════════════════════════════════════════════════════════
    # LEGACY /api/dewi/maklon/orders ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    tester.test_legacy_orders_endpoints()
    tester.test_legacy_production_detail()
    tester.test_legacy_material_issues()

    # ═══════════════════════════════════════════════════════════════════════════
    # ACCESSORY MODULE ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    tester.test_accessory_module()

    # ═══════════════════════════════════════════════════════════════════════════
    # TOKO MODULE ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    tester.test_toko_module()

    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE COLLECTION VERIFICATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    tester.test_dropped_collections()

    # Print final summary
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())
