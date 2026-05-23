"""
Backend API Testing for P1.A-D Cleanup Phase A
Testing SSOT migration and legacy endpoint compatibility.

P1.A-D Cleanup Phase A completed:
- 9 MongoDB collections dropped (acc_items, acc_stock_movements, dewi_maklon_orders, 
  dewi_toko_products, dewi_toko_channels, dewi_toko_channel_syncs, dewi_toko_orders, 
  dewi_toko_returns, dewi_toko_reviews)
- Legacy routes now use Python wrappers routing to SSOT collections
- API contracts preserved

Test Coverage:
1. Maklon legacy endpoints (GET/POST/PUT /api/dewi/maklon/orders) - route to dewi_maklon_pos
2. Maklon POs endpoint (GET /api/dewi/maklon/pos) - verify migrated data
3. Toko legacy endpoints (products, channels, orders, returns, reviews) - route to marketing_*
4. Accessory endpoints - use rahaza_materials
5. Verify dropped collections no longer exist
6. Verify preserved collections still exist (dewi_toko_flashsales, dewi_toko_pack_batches)
"""
import requests
import sys
from datetime import datetime
import pymongo

class P1CleanupTester:
    def __init__(self, base_url="https://doc-audit-4.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.test_data = {}  # Store created test data IDs

    def run_test(self, name, method, endpoint, expected_status, data=None, description=""):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

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
                        if len(resp_json) > 0 and isinstance(resp_json[0], dict):
                            print(f"   First item keys: {list(resp_json[0].keys())[:8]}")
                    elif isinstance(resp_json, dict):
                        print(f"   Response keys: {list(resp_json.keys())[:10]}")
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
            self.token = response['token']
            print(f"   ✓ Token obtained: {self.token[:20]}...")
            return True
        print(f"   ✗ Login failed - cannot proceed with tests")
        return False

    # ═══════════════════════════════════════════════════════════════
    # MAKLON LEGACY ENDPOINTS TESTS
    # ═══════════════════════════════════════════════════════════════

    def test_maklon_orders_list(self):
        """Test GET /api/dewi/maklon/orders - should return list from dewi_maklon_pos"""
        print(f"\n{'#'*80}")
        print(f"# MAKLON LEGACY ENDPOINTS - LIST ORDERS")
        print(f"{'#'*80}")
        success, response = self.run_test(
            "List Maklon Orders (legacy endpoint)",
            "GET",
            "/api/dewi/maklon/orders",
            200,
            description="Should return orders from dewi_maklon_pos via legacy wrapper"
        )
        if success and 'items' in response:
            items = response.get('items', [])
            print(f"   ✓ Found {len(items)} orders")
            if len(items) > 0:
                first = items[0]
                # Check for legacy fields
                legacy_fields = ['order_code', 'qty_ordered', 'status', 'client_name']
                found_fields = [f for f in legacy_fields if f in first]
                print(f"   ✓ Legacy fields present: {found_fields}")
                # Store first order ID for detail test
                if 'id' in first:
                    self.test_data['maklon_order_id'] = first['id']
                    self.test_data['maklon_order_code'] = first.get('order_code', '')
        return success

    def test_maklon_order_detail(self):
        """Test GET /api/dewi/maklon/orders/{order_id} - single order detail"""
        print(f"\n{'#'*80}")
        print(f"# MAKLON LEGACY ENDPOINTS - ORDER DETAIL")
        print(f"{'#'*80}")
        
        # Try with known legacy PO IDs first
        test_ids = ['MKLO-LEG-001', 'MKLO-LEG-002']
        if 'maklon_order_id' in self.test_data:
            test_ids.insert(0, self.test_data['maklon_order_id'])
        
        for order_id in test_ids:
            success, response = self.run_test(
                f"Get Maklon Order Detail: {order_id}",
                "GET",
                f"/api/dewi/maklon/orders/{order_id}",
                200,
                description=f"Should return order {order_id} from dewi_maklon_pos"
            )
            if success:
                # Verify legacy shape
                legacy_fields = ['order_code', 'qty_ordered', 'status', 'client_name', 'product_name']
                found = [f for f in legacy_fields if f in response]
                print(f"   ✓ Legacy fields in response: {found}")
                if '_source' in response:
                    print(f"   ✓ Source collection: {response['_source']}")
                return True
        
        print(f"   ⚠ No valid order found for detail test")
        return False

    def test_maklon_create_order(self):
        """Test POST /api/dewi/maklon/orders - create new order via legacy endpoint"""
        print(f"\n{'#'*80}")
        print(f"# MAKLON LEGACY ENDPOINTS - CREATE ORDER")
        print(f"{'#'*80}")
        
        timestamp = datetime.now().strftime("%H%M%S")
        order_data = {
            "order_code": f"TEST-MKLO-{timestamp}",
            "client_id": "test-client-001",
            "client_name": "Test Client",
            "product_name": "Test Product",
            "product_category": "Baju Wanita",
            "qty_ordered": 100,
            "price_per_pcs": 50000,
            "total_value": 5000000,
            "order_date": datetime.now().isoformat()[:10],
            "deadline_date": "2026-12-31",
            "status": "draft",
            "fabric_provided_by": "client",
            "notes": "Test order for P1.B cleanup verification"
        }
        
        success, response = self.run_test(
            "Create Maklon Order (legacy endpoint)",
            "POST",
            "/api/dewi/maklon/orders",
            200,
            data=order_data,
            description="Should create order in dewi_maklon_pos (not dewi_maklon_orders)"
        )
        
        if success and 'id' in response:
            self.test_data['created_maklon_order_id'] = response['id']
            print(f"   ✓ Created order ID: {response['id']}")
        
        return success

    def test_maklon_update_order_status(self):
        """Test PUT /api/dewi/maklon/orders/{order_id} - update order status"""
        print(f"\n{'#'*80}")
        print(f"# MAKLON LEGACY ENDPOINTS - UPDATE ORDER STATUS")
        print(f"{'#'*80}")
        
        order_id = self.test_data.get('created_maklon_order_id')
        if not order_id:
            print(f"   ⚠ No created order ID available, skipping update test")
            return False
        
        update_data = {
            "status": "cutting"
        }
        
        success, response = self.run_test(
            "Update Maklon Order Status",
            "PUT",
            f"/api/dewi/maklon/orders/{order_id}/status",
            200,
            data=update_data,
            description="Should translate 'cutting' → 'in_production' in dewi_maklon_pos"
        )
        
        if success:
            print(f"   ✓ Status updated successfully")
        
        return success

    def test_maklon_pos_endpoint(self):
        """Test GET /api/dewi/maklon/pos - should return all POs including migrated ones"""
        print(f"\n{'#'*80}")
        print(f"# MAKLON POS ENDPOINT - VERIFY MIGRATED DATA")
        print(f"{'#'*80}")
        
        success, response = self.run_test(
            "List Maklon POs",
            "GET",
            "/api/dewi/maklon/pos",
            200,
            description="Should return all POs including MKLO-LEG-* migrated ones"
        )
        
        if success and 'items' in response:
            items = response.get('items', [])
            print(f"   ✓ Found {len(items)} POs")
            
            # Check for migrated legacy orders
            legacy_pos = [po for po in items if po.get('po_number', '').startswith('MKLO-LEG-')]
            if legacy_pos:
                print(f"   ✓ Found {len(legacy_pos)} migrated legacy POs")
                for po in legacy_pos[:3]:
                    print(f"     - {po.get('po_number')}: status={po.get('status')}, total_qty={po.get('total_qty')}, total_value={po.get('total_value')}")
            else:
                print(f"   ⚠ No migrated legacy POs found (MKLO-LEG-*)")
        
        return success

    def test_maklon_clients(self):
        """Test GET /api/dewi/maklon/clients - should still work (not affected by cleanup)"""
        print(f"\n{'#'*80}")
        print(f"# MAKLON CLIENTS ENDPOINT")
        print(f"{'#'*80}")
        
        success, response = self.run_test(
            "List Maklon Clients",
            "GET",
            "/api/dewi/maklon/clients",
            200,
            description="Should still work (not affected by P1.B cleanup)"
        )
        
        if success and isinstance(response, list):
            print(f"   ✓ Found {len(response)} clients")
        
        return success

    # ═══════════════════════════════════════════════════════════════
    # TOKO LEGACY ENDPOINTS TESTS
    # ═══════════════════════════════════════════════════════════════

    def test_toko_products_list(self):
        """Test GET /api/dewi/toko/products - should route to marketing_catalog_items"""
        print(f"\n{'#'*80}")
        print(f"# TOKO LEGACY ENDPOINTS - PRODUCTS")
        print(f"{'#'*80}")
        
        success, response = self.run_test(
            "List Toko Products (legacy endpoint)",
            "GET",
            "/api/dewi/toko/products",
            200,
            description="Should return products from marketing_catalog_items with _legacy_toko=true"
        )
        
        if success and isinstance(response, list):
            print(f"   ✓ Found {len(response)} products")
            if len(response) > 0:
                first = response[0]
                if '_source' in first:
                    print(f"   ✓ Source: {first['_source']}")
        
        return success

    def test_toko_create_product(self):
        """Test POST /api/dewi/toko/products - create product via legacy endpoint"""
        print(f"\n{'#'*80}")
        print(f"# TOKO LEGACY ENDPOINTS - CREATE PRODUCT")
        print(f"{'#'*80}")
        
        timestamp = datetime.now().strftime("%H%M%S")
        product_data = {
            "sku_code": f"TEST-SKU-{timestamp}",
            "name": f"Test Product {timestamp}",
            "description": "Test product for P1.D cleanup verification",
            "category": "Test Category",
            "base_price": 100000,
            "cost_price": 50000,
            "stock_total": 10,
            "status": "draft"
        }
        
        success, response = self.run_test(
            "Create Toko Product (legacy endpoint)",
            "POST",
            "/api/dewi/toko/products",
            200,
            data=product_data,
            description="Should create in marketing_catalog_items with _legacy_toko=true"
        )
        
        if success and 'id' in response:
            self.test_data['created_product_id'] = response['id']
            print(f"   ✓ Created product ID: {response['id']}")
        
        return success

    def test_toko_channels(self):
        """Test GET /api/dewi/toko/channels - should route to marketing_platform_accounts"""
        print(f"\n{'#'*80}")
        print(f"# TOKO LEGACY ENDPOINTS - CHANNELS")
        print(f"{'#'*80}")
        
        success, response = self.run_test(
            "List Toko Channels (legacy endpoint)",
            "GET",
            "/api/dewi/toko/channels",
            200,
            description="Should return channels from marketing_platform_accounts with _legacy_toko=true"
        )
        
        if success and isinstance(response, list):
            print(f"   ✓ Found {len(response)} channels")
        
        return success

    def test_toko_orders_list(self):
        """Test GET /api/dewi/toko/orders - should route to marketing_orders"""
        print(f"\n{'#'*80}")
        print(f"# TOKO LEGACY ENDPOINTS - ORDERS")
        print(f"{'#'*80}")
        
        success, response = self.run_test(
            "List Toko Orders (legacy endpoint)",
            "GET",
            "/api/dewi/toko/orders",
            200,
            description="Should return orders from marketing_orders with _legacy_toko=true"
        )
        
        if success and isinstance(response, list):
            print(f"   ✓ Found {len(response)} orders")
        
        return success

    def test_toko_create_order(self):
        """Test POST /api/dewi/toko/orders - create order via legacy endpoint"""
        print(f"\n{'#'*80}")
        print(f"# TOKO LEGACY ENDPOINTS - CREATE ORDER")
        print(f"{'#'*80}")
        
        order_data = {
            "channel_code": "manual",
            "customer_name": "Test Customer",
            "customer_address": "Test Address",
            "customer_city": "Sragen",
            "customer_phone": "08123456789",
            "items": [
                {
                    "sku_code": "TEST-SKU",
                    "product_name": "Test Product",
                    "qty": 2,
                    "price": 100000
                }
            ],
            "total_amount": 200000,
            "fee_amount": 10000,
            "notes": "Test order for P1.D cleanup verification"
        }
        
        success, response = self.run_test(
            "Create Toko Order (legacy endpoint)",
            "POST",
            "/api/dewi/toko/orders",
            201,
            data=order_data,
            description="Should create in marketing_orders with _legacy_toko=true"
        )
        
        if success and 'id' in response:
            self.test_data['created_order_id'] = response['id']
            print(f"   ✓ Created order ID: {response['id']}")
        
        return success

    def test_toko_returns(self):
        """Test GET /api/dewi/toko/returns - should route to marketing_returns"""
        print(f"\n{'#'*80}")
        print(f"# TOKO LEGACY ENDPOINTS - RETURNS")
        print(f"{'#'*80}")
        
        success, response = self.run_test(
            "List Toko Returns (legacy endpoint)",
            "GET",
            "/api/dewi/toko/returns",
            200,
            description="Should return returns from marketing_returns with _legacy_toko=true"
        )
        
        if success and isinstance(response, list):
            print(f"   ✓ Found {len(response)} returns")
        
        return success

    def test_toko_reviews(self):
        """Test GET /api/dewi/toko/reviews - should route to marketing_reviews"""
        print(f"\n{'#'*80}")
        print(f"# TOKO LEGACY ENDPOINTS - REVIEWS")
        print(f"{'#'*80}")
        
        success, response = self.run_test(
            "List Toko Reviews (legacy endpoint)",
            "GET",
            "/api/dewi/toko/reviews",
            200,
            description="Should return reviews from marketing_reviews with _legacy_toko=true"
        )
        
        if success and isinstance(response, list):
            print(f"   ✓ Found {len(response)} reviews")
        
        return success

    # ═══════════════════════════════════════════════════════════════
    # ACCESSORY ENDPOINTS TESTS
    # ═══════════════════════════════════════════════════════════════

    def test_accessory_items_list(self):
        """Test GET /api/acc/items - should use rahaza_materials"""
        print(f"\n{'#'*80}")
        print(f"# ACCESSORY ENDPOINTS - LIST ITEMS")
        print(f"{'#'*80}")
        
        success, response = self.run_test(
            "List Accessory Items",
            "GET",
            "/api/acc/items",
            200,
            description="Should return items from rahaza_materials (type='accessory')"
        )
        
        if success and isinstance(response, list):
            print(f"   ✓ Found {len(response)} accessory items")
            if len(response) > 0:
                self.test_data['accessory_id'] = response[0].get('id')
        
        return success

    def test_accessory_create_item(self):
        """Test POST /api/acc/items - create accessory item"""
        print(f"\n{'#'*80}")
        print(f"# ACCESSORY ENDPOINTS - CREATE ITEM")
        print(f"{'#'*80}")
        
        timestamp = datetime.now().strftime("%H%M%S")
        item_data = {
            "name": f"Test Accessory {timestamp}",
            "category": "Test Category",
            "unit": "pcs",
            "description": "Test accessory for P1.A cleanup verification",
            "min_stock": 10,
            "supplier": "Test Supplier"
        }
        
        success, response = self.run_test(
            "Create Accessory Item",
            "POST",
            "/api/acc/items",
            201,
            data=item_data,
            description="Should create in rahaza_materials with type='accessory'"
        )
        
        if success and 'id' in response:
            self.test_data['created_accessory_id'] = response['id']
            print(f"   ✓ Created accessory ID: {response['id']}")
        
        return success

    def test_accessory_stock(self):
        """Test GET /api/acc/stock - should use rahaza_material_stock"""
        print(f"\n{'#'*80}")
        print(f"# ACCESSORY ENDPOINTS - STOCK")
        print(f"{'#'*80}")
        
        success, response = self.run_test(
            "Get Accessory Stock",
            "GET",
            "/api/acc/stock",
            200,
            description="Should return stock from rahaza_material_stock"
        )
        
        if success and isinstance(response, list):
            print(f"   ✓ Found stock for {len(response)} items")
        
        return success

    def test_accessory_receive_stock(self):
        """Test POST /api/acc/stock/receive - receive stock"""
        print(f"\n{'#'*80}")
        print(f"# ACCESSORY ENDPOINTS - RECEIVE STOCK")
        print(f"{'#'*80}")
        
        acc_id = self.test_data.get('created_accessory_id') or self.test_data.get('accessory_id')
        if not acc_id:
            print(f"   ⚠ No accessory ID available, skipping receive test")
            return False
        
        receive_data = {
            "acc_id": acc_id,
            "qty": 50,
            "notes": "Test receive for P1.A cleanup verification"
        }
        
        success, response = self.run_test(
            "Receive Accessory Stock",
            "POST",
            "/api/acc/stock/receive",
            201,
            data=receive_data,
            description="Should update rahaza_material_stock and log to rahaza_material_movements"
        )
        
        if success:
            print(f"   ✓ Stock received successfully")
        
        return success

    # ═══════════════════════════════════════════════════════════════
    # DATABASE VERIFICATION TESTS
    # ═══════════════════════════════════════════════════════════════

    def test_verify_dropped_collections(self):
        """Verify that dropped collections no longer exist in MongoDB"""
        print(f"\n{'#'*80}")
        print(f"# DATABASE VERIFICATION - DROPPED COLLECTIONS")
        print(f"{'#'*80}")
        
        try:
            # Connect to MongoDB
            mongo_url = "mongodb://localhost:27017/"
            client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            db = client['dewi_aditya_erp']
            
            # Get all collection names
            all_collections = db.list_collection_names()
            
            # Collections that should be dropped
            dropped_collections = [
                'acc_items',
                'acc_stock_movements',
                'dewi_maklon_orders',
                'dewi_toko_products',
                'dewi_toko_channels',
                'dewi_toko_channel_syncs',
                'dewi_toko_orders',
                'dewi_toko_returns',
                'dewi_toko_reviews'
            ]
            
            print(f"   Checking for dropped collections...")
            found_dropped = []
            for coll in dropped_collections:
                if coll in all_collections:
                    found_dropped.append(coll)
                    print(f"   ❌ FOUND (should be dropped): {coll}")
                else:
                    print(f"   ✓ Correctly dropped: {coll}")
            
            if found_dropped:
                print(f"\n   ❌ FAILED: Found {len(found_dropped)} collections that should be dropped")
                self.failed_tests.append({
                    'name': 'Verify Dropped Collections',
                    'error': f'Found collections that should be dropped: {found_dropped}'
                })
                return False
            else:
                print(f"\n   ✅ PASSED: All collections correctly dropped")
                self.tests_passed += 1
                return True
                
        except Exception as e:
            print(f"   ❌ FAILED - Error connecting to MongoDB: {str(e)}")
            self.failed_tests.append({
                'name': 'Verify Dropped Collections',
                'error': f'MongoDB connection error: {str(e)}'
            })
            return False
        finally:
            self.tests_run += 1

    def test_verify_preserved_collections(self):
        """Verify that preserved collections still exist"""
        print(f"\n{'#'*80}")
        print(f"# DATABASE VERIFICATION - PRESERVED COLLECTIONS")
        print(f"{'#'*80}")
        
        try:
            # Connect to MongoDB
            mongo_url = "mongodb://localhost:27017/"
            client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            db = client['dewi_aditya_erp']
            
            # Get all collection names
            all_collections = db.list_collection_names()
            
            # Collections that should be preserved
            preserved_collections = [
                'dewi_toko_flashsales',
                'dewi_toko_pack_batches'
            ]
            
            print(f"   Checking for preserved collections...")
            missing_preserved = []
            for coll in preserved_collections:
                if coll in all_collections:
                    print(f"   ✓ Correctly preserved: {coll}")
                else:
                    missing_preserved.append(coll)
                    print(f"   ❌ MISSING (should be preserved): {coll}")
            
            if missing_preserved:
                print(f"\n   ❌ FAILED: Missing {len(missing_preserved)} collections that should be preserved")
                self.failed_tests.append({
                    'name': 'Verify Preserved Collections',
                    'error': f'Missing collections that should be preserved: {missing_preserved}'
                })
                return False
            else:
                print(f"\n   ✅ PASSED: All collections correctly preserved")
                self.tests_passed += 1
                return True
                
        except Exception as e:
            print(f"   ❌ FAILED - Error connecting to MongoDB: {str(e)}")
            self.failed_tests.append({
                'name': 'Verify Preserved Collections',
                'error': f'MongoDB connection error: {str(e)}'
            })
            return False
        finally:
            self.tests_run += 1

    # ═══════════════════════════════════════════════════════════════
    # MAIN TEST RUNNER
    # ═══════════════════════════════════════════════════════════════

    def run_all_tests(self):
        """Run all P1.A-D cleanup tests"""
        print(f"\n{'█'*80}")
        print(f"█ P1.A-D CLEANUP PHASE A - BACKEND API TESTING")
        print(f"█ Base URL: {self.base_url}")
        print(f"█ Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'█'*80}\n")

        # Authentication
        if not self.test_login():
            print("\n❌ Authentication failed. Cannot proceed with tests.")
            return 1

        # Maklon Tests
        self.test_maklon_orders_list()
        self.test_maklon_order_detail()
        self.test_maklon_create_order()
        self.test_maklon_update_order_status()
        self.test_maklon_pos_endpoint()
        self.test_maklon_clients()

        # Toko Tests
        self.test_toko_products_list()
        self.test_toko_create_product()
        self.test_toko_channels()
        self.test_toko_orders_list()
        self.test_toko_create_order()
        self.test_toko_returns()
        self.test_toko_reviews()

        # Accessory Tests
        self.test_accessory_items_list()
        self.test_accessory_create_item()
        self.test_accessory_stock()
        self.test_accessory_receive_stock()

        # Database Verification
        self.test_verify_dropped_collections()
        self.test_verify_preserved_collections()

        # Print Summary
        self.print_summary()

        return 0 if self.tests_passed == self.tests_run else 1

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'█'*80}")
        print(f"█ TEST SUMMARY")
        print(f"{'█'*80}")
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "N/A")
        
        if self.failed_tests:
            print(f"\n{'='*80}")
            print(f"FAILED TESTS DETAILS:")
            print(f"{'='*80}")
            for i, test in enumerate(self.failed_tests, 1):
                print(f"\n{i}. {test.get('name', 'Unknown')}")
                print(f"   Endpoint: {test.get('endpoint', 'N/A')}")
                if 'expected' in test:
                    print(f"   Expected: {test['expected']}, Got: {test.get('actual', 'N/A')}")
                if 'error' in test:
                    print(f"   Error: {test['error']}")
                if 'response' in test:
                    print(f"   Response: {test['response'][:200]}")
        
        print(f"\n{'█'*80}\n")


def main():
    tester = P1CleanupTester("https://doc-audit-4.preview.emergentagent.com")
    return tester.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
