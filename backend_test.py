"""
Phase B Toko Frontend Cutover — Backend Testing
================================================
Tests all Phase B.1 and B.2 endpoints + regression checks.

Run: python3 /app/backend_test.py
"""
import requests
import sys
import json
import io
from datetime import datetime

BASE_URL = "https://doc-audit-4.preview.emergentagent.com"
ADMIN_EMAIL = "admin@garment.com"
ADMIN_PASSWORD = "Admin@2025"


class TokoBackendTester:
    def __init__(self):
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.catalog_id = None
        self.account_id = None
        self.item_id = None
        self.order_id = None

    def log(self, msg, level="INFO"):
        """Log with timestamp"""
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {level}: {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, headers=None):
        """Run a single API test"""
        url = f"{BASE_URL}{endpoint}"
        req_headers = {'Content-Type': 'application/json'}
        if self.token:
            req_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            req_headers.update(headers)
        
        # Remove Content-Type for multipart uploads
        if files:
            req_headers.pop('Content-Type', None)

        self.tests_run += 1
        self.log(f"Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=req_headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, headers=req_headers, timeout=30)
                else:
                    response = requests.post(url, json=data, headers=req_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=req_headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=req_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=req_headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASS - Status: {response.status_code}", "PASS")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.tests_failed += 1
                self.log(f"❌ FAIL - Expected {expected_status}, got {response.status_code}", "FAIL")
                try:
                    err_body = response.json()
                    self.log(f"   Response: {json.dumps(err_body, indent=2)}", "FAIL")
                except:
                    self.log(f"   Response: {response.text[:200]}", "FAIL")
                self.failures.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "endpoint": endpoint
                })
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.log(f"❌ FAIL - Error: {str(e)}", "FAIL")
            self.failures.append({
                "test": name,
                "error": str(e),
                "endpoint": endpoint
            })
            return False, {}

    def test_login(self):
        """Test login and get token"""
        self.log("=" * 60)
        self.log("PHASE 0: Authentication")
        self.log("=" * 60)
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "/api/auth/login",
            200,
            data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.log(f"Token obtained: {self.token[:20]}...", "INFO")
            return True
        return False

    def test_phase_b1_dashboard(self):
        """Phase B.1 - Test toko dashboard overview"""
        self.log("\n" + "=" * 60)
        self.log("PHASE B.1: Dashboard & Sync Endpoints")
        self.log("=" * 60)
        
        success, response = self.run_test(
            "GET /api/marketing/dashboard/toko-overview",
            "GET",
            "/api/marketing/dashboard/toko-overview",
            200
        )
        if success:
            # Verify response structure
            required_keys = ['products', 'channels', 'top_products', 'recent_syncs', 'mock_mode']
            missing = [k for k in required_keys if k not in response]
            if missing:
                self.log(f"⚠️  Missing keys in response: {missing}", "WARN")
            else:
                self.log(f"   Products: {response['products']}", "INFO")
                self.log(f"   Channels: {response['channels']['total']} total, {response['channels']['enabled']} enabled", "INFO")
                self.log(f"   Mock mode: {response['mock_mode']}", "INFO")
        return success

    def test_phase_b1_sync(self):
        """Phase B.1 - Test account sync"""
        # First, get an account to sync
        success, response = self.run_test(
            "GET /api/marketing/catalogs (to find account)",
            "GET",
            "/api/marketing/catalogs",
            200
        )
        
        if not success or not response.get('catalogs'):
            self.log("⚠️  No catalogs found, cannot test sync", "WARN")
            return False
        
        # Find a toko legacy account
        catalog = None
        for cat in response.get('catalogs', []):
            if cat.get('_toko_legacy'):
                catalog = cat
                self.catalog_id = cat.get('id')
                self.account_id = cat.get('account_id')
                break
        
        if not self.account_id:
            self.log("⚠️  No toko legacy account found, cannot test sync", "WARN")
            return False
        
        self.log(f"   Using account_id: {self.account_id}", "INFO")
        
        # Test sync
        success, response = self.run_test(
            f"POST /api/marketing/accounts/{self.account_id}/sync",
            "POST",
            f"/api/marketing/accounts/{self.account_id}/sync",
            200
        )
        
        if success:
            self.log(f"   Sync result: {response.get('message')}", "INFO")
            self.log(f"   Counts: {response.get('counts')}", "INFO")
            self.log(f"   Duration: {response.get('duration_ms')}ms", "INFO")
        
        return success

    def test_phase_b1_sync_history(self):
        """Phase B.1 - Test sync history"""
        if not self.account_id:
            self.log("⚠️  No account_id available, skipping sync history test", "WARN")
            return False
        
        success, response = self.run_test(
            f"GET /api/marketing/accounts/{self.account_id}/sync-history",
            "GET",
            f"/api/marketing/accounts/{self.account_id}/sync-history?limit=5",
            200
        )
        
        if success:
            history = response if isinstance(response, list) else []
            self.log(f"   Sync history entries: {len(history)}", "INFO")
            if history:
                latest = history[0]
                self.log(f"   Latest sync: {latest.get('status')} at {latest.get('started_at')}", "INFO")
        
        return success

    def test_phase_b1_legacy_config(self):
        """Phase B.1 - Test legacy channel config update"""
        if not self.account_id:
            self.log("⚠️  No account_id available, skipping legacy config test", "WARN")
            return False
        
        success, response = self.run_test(
            f"PUT /api/marketing/accounts/{self.account_id}/legacy-config",
            "PUT",
            f"/api/marketing/accounts/{self.account_id}/legacy-config",
            200,
            data={
                "enabled": True,
                "credentials": {
                    "api_key": "test_key_12345",
                    "api_secret": "test_secret_67890"
                },
                "fee_pct": 2.5,
                "commission_pct": 5.0,
                "notes": "Test config update from Phase B testing"
            }
        )
        
        if success:
            channel = response.get('channel', {})
            creds = channel.get('credentials', {})
            # Verify credentials are masked
            if 'api_key' in creds:
                masked = creds['api_key'].startswith('***')
                if masked:
                    self.log(f"   ✅ Credentials properly masked: {creds['api_key']}", "INFO")
                else:
                    self.log(f"   ⚠️  Credentials NOT masked: {creds['api_key']}", "WARN")
        
        return success

    def test_phase_b2_orders(self):
        """Phase B.2 - Test order creation, update, delete"""
        self.log("\n" + "=" * 60)
        self.log("PHASE B.2: Orders Management")
        self.log("=" * 60)
        
        # Create manual order
        success, response = self.run_test(
            "POST /api/marketing/orders (manual order)",
            "POST",
            "/api/marketing/orders",
            200,
            data={
                "platform": "manual",
                "customer_name": "Test Customer Phase B",
                "sku_id": "TEST-SKU-001",
                "product_name": "Test Product",
                "variation": "Size M / Color Blue",
                "quantity": 2,
                "price_original": 100000,
                "price_final": 90000,
                "total_payment": 180000,
                "shipping_cost": 15000,
                "courier": "JNE",
                "payment_method": "Transfer Bank",
                "customer_phone": "081234567890",
                "city": "Jakarta",
                "note": "Test order from Phase B backend testing"
            }
        )
        
        if success:
            self.order_id = response.get('id')
            order_ref = response.get('order_id')
            self.log(f"   Order created: {order_ref} (id: {self.order_id})", "INFO")
            
            # Verify auto-gen order_id format (MAN-YYYYMMDD-XXXXXX)
            if order_ref and order_ref.startswith('MAN-'):
                self.log(f"   ✅ Order ID auto-generated correctly: {order_ref}", "INFO")
            else:
                self.log(f"   ⚠️  Order ID format unexpected: {order_ref}", "WARN")
        
        if not self.order_id:
            return False
        
        # Update order status
        success2, _ = self.run_test(
            f"PATCH /api/marketing/orders/{self.order_id}/status",
            "PATCH",
            f"/api/marketing/orders/{self.order_id}/status",
            200,
            data={
                "status": "packed",
                "note": "Order packed and ready to ship"
            }
        )
        
        # Delete order
        success3, _ = self.run_test(
            f"DELETE /api/marketing/orders/{self.order_id}",
            "DELETE",
            f"/api/marketing/orders/{self.order_id}",
            200
        )
        
        return success and success2 and success3

    def test_phase_b2_catalog_items(self):
        """Phase B.2 - Test catalog item CRUD"""
        self.log("\n" + "=" * 60)
        self.log("PHASE B.2: Catalog Items Management")
        self.log("=" * 60)
        
        if not self.catalog_id:
            self.log("⚠️  No catalog_id available, skipping catalog items test", "WARN")
            return False
        
        # Create catalog item
        success, response = self.run_test(
            f"POST /api/marketing/catalogs/{self.catalog_id}/items",
            "POST",
            f"/api/marketing/catalogs/{self.catalog_id}/items",
            200,
            data={
                "sku": "TEST-PHASE-B-001",
                "name": "Test Product Phase B",
                "description": "Test product for Phase B backend testing",
                "price": 150000,
                "original_price": 120000,
                "platform_price": 150000,
                "stock_quantity": 50,
                "stock_alert_threshold": 10,
                "category": "Test Category",
                "variant_info": "Color: Blue, Size: M",
                "weight_gram": 250,
                "is_active": True
            }
        )
        
        if success:
            self.item_id = response.get('item', {}).get('id')
            self.log(f"   Item created: {self.item_id}", "INFO")
        
        if not self.item_id:
            return False
        
        # Update catalog item
        success2, _ = self.run_test(
            f"PUT /api/marketing/catalogs/{self.catalog_id}/items/{self.item_id}",
            "PUT",
            f"/api/marketing/catalogs/{self.catalog_id}/items/{self.item_id}",
            200,
            data={
                "price": 160000,
                "stock_quantity": 45,
                "description": "Updated description for Phase B testing"
            }
        )
        
        return success and success2

    def test_phase_b2_photo_upload(self):
        """Phase B.2 - Test photo upload and removal"""
        if not self.catalog_id or not self.item_id:
            self.log("⚠️  No catalog/item available, skipping photo test", "WARN")
            return False
        
        # Create a dummy image file
        dummy_image = io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
        dummy_image.name = 'test_photo.png'
        
        # Upload photo
        success, response = self.run_test(
            f"POST /api/marketing/catalogs/{self.catalog_id}/items/{self.item_id}/photos",
            "POST",
            f"/api/marketing/catalogs/{self.catalog_id}/items/{self.item_id}/photos",
            200,
            files={'file': ('test_photo.png', dummy_image, 'image/png')}
        )
        
        photo_url = None
        if success:
            photo_url = response.get('url')
            self.log(f"   Photo uploaded: {photo_url}", "INFO")
        
        if not photo_url:
            return False
        
        # Remove photo
        success2, _ = self.run_test(
            f"POST /api/marketing/catalogs/{self.catalog_id}/items/{self.item_id}/photos/remove",
            "POST",
            f"/api/marketing/catalogs/{self.catalog_id}/items/{self.item_id}/photos/remove",
            200,
            data={"url": photo_url}
        )
        
        return success and success2

    def test_phase_b2_catalog_item_delete(self):
        """Phase B.2 - Delete catalog item (cleanup)"""
        if not self.catalog_id or not self.item_id:
            return True  # Already cleaned up or not created
        
        success, _ = self.run_test(
            f"DELETE /api/marketing/catalogs/{self.catalog_id}/items/{self.item_id}",
            "DELETE",
            f"/api/marketing/catalogs/{self.catalog_id}/items/{self.item_id}",
            200
        )
        
        return success

    def test_backfill_verification(self):
        """Phase B.2 - Verify backfill dual-shape docs"""
        self.log("\n" + "=" * 60)
        self.log("PHASE B.2: Backfill Verification")
        self.log("=" * 60)
        
        # Check returns for dual-shape
        success1, response1 = self.run_test(
            "GET /api/marketing/returns (check dual-shape)",
            "GET",
            "/api/marketing/returns?page_size=5",
            200
        )
        
        if success1:
            returns = response1.get('data', [])
            if returns:
                sample = returns[0]
                # Check for both legacy and marketing fields
                has_legacy = 'channel_code' in sample or 'decision' in sample
                has_marketing = 'platform' in sample and 'refund_type' in sample
                self.log(f"   Returns dual-shape: legacy={has_legacy}, marketing={has_marketing}", "INFO")
                if has_legacy and has_marketing:
                    self.log(f"   ✅ Returns have dual-shape fields", "INFO")
                else:
                    self.log(f"   ⚠️  Returns missing dual-shape fields", "WARN")
        
        # Check reviews for dual-shape
        success2, response2 = self.run_test(
            "GET /api/marketing/reviews (check dual-shape)",
            "GET",
            "/api/marketing/reviews?page_size=5",
            200
        )
        
        if success2:
            reviews = response2.get('data', [])
            if reviews:
                sample = reviews[0]
                has_legacy = 'channel_code' in sample
                has_marketing = 'platform' in sample and 'category' in sample
                self.log(f"   Reviews dual-shape: legacy={has_legacy}, marketing={has_marketing}", "INFO")
                if has_legacy and has_marketing:
                    self.log(f"   ✅ Reviews have dual-shape fields", "INFO")
                else:
                    self.log(f"   ⚠️  Reviews missing dual-shape fields", "WARN")
        
        # Check catalog items for dual-shape
        success3, response3 = self.run_test(
            "GET /api/marketing/catalogs (check items dual-shape)",
            "GET",
            "/api/marketing/catalogs",
            200
        )
        
        if success3:
            catalogs = response3.get('catalogs', [])
            for cat in catalogs:
                if cat.get('_toko_legacy'):
                    cat_id = cat.get('id')
                    success4, response4 = self.run_test(
                        f"GET /api/marketing/catalogs/{cat_id}/items",
                        "GET",
                        f"/api/marketing/catalogs/{cat_id}/items?limit=5",
                        200
                    )
                    if success4:
                        items = response4.get('items', [])
                        if items:
                            sample = items[0]
                            has_legacy = 'sku_code' in sample or 'base_price' in sample
                            has_marketing = 'sku' in sample and 'price' in sample
                            self.log(f"   Catalog items dual-shape: legacy={has_legacy}, marketing={has_marketing}", "INFO")
                            if has_legacy and has_marketing:
                                self.log(f"   ✅ Catalog items have dual-shape fields", "INFO")
                            else:
                                self.log(f"   ⚠️  Catalog items missing dual-shape fields", "WARN")
                    break
        
        return success1 and success2 and success3

    def test_regression_legacy_endpoints(self):
        """Regression - Test legacy /api/dewi/toko/* endpoints still work"""
        self.log("\n" + "=" * 60)
        self.log("REGRESSION: Legacy Toko Endpoints")
        self.log("=" * 60)
        
        # Test legacy dashboard
        success1, _ = self.run_test(
            "GET /api/dewi/toko/dashboard (legacy)",
            "GET",
            "/api/dewi/toko/dashboard",
            200
        )
        
        # Test legacy channels
        success2, _ = self.run_test(
            "GET /api/dewi/toko/channels (legacy)",
            "GET",
            "/api/dewi/toko/channels",
            200
        )
        
        # Test legacy products
        success3, _ = self.run_test(
            "GET /api/dewi/toko/products (legacy)",
            "GET",
            "/api/dewi/toko/products?page=1&page_size=5",
            200
        )
        
        # Test legacy orders
        success4, _ = self.run_test(
            "GET /api/dewi/toko/orders (legacy)",
            "GET",
            "/api/dewi/toko/orders?page=1&page_size=5",
            200
        )
        
        return success1 and success2 and success3 and success4

    def test_regression_preserved_endpoints(self):
        """Regression - Test preserved pack-batches and flashsales endpoints"""
        # Test pack-batches (preserved)
        success1, _ = self.run_test(
            "GET /api/dewi/toko/pack-batches (preserved)",
            "GET",
            "/api/dewi/toko/pack-batches",
            200
        )
        
        # Test flashsales (preserved)
        success2, _ = self.run_test(
            "GET /api/dewi/toko/flashsales (preserved)",
            "GET",
            "/api/dewi/toko/flashsales",
            200
        )
        
        return success1 and success2

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"Total tests: {self.tests_run}")
        self.log(f"Passed: {self.tests_passed} ✅")
        self.log(f"Failed: {self.tests_failed} ❌")
        
        if self.failures:
            self.log("\n" + "=" * 60)
            self.log("FAILED TESTS:")
            self.log("=" * 60)
            for i, failure in enumerate(self.failures, 1):
                self.log(f"{i}. {failure.get('test')}")
                self.log(f"   Endpoint: {failure.get('endpoint')}")
                if 'expected' in failure:
                    self.log(f"   Expected: {failure['expected']}, Got: {failure['actual']}")
                if 'error' in failure:
                    self.log(f"   Error: {failure['error']}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\nSuccess Rate: {success_rate:.1f}%")
        
        return self.tests_failed == 0


def main():
    tester = TokoBackendTester()
    
    # Phase 0: Authentication
    if not tester.test_login():
        tester.log("❌ Login failed, stopping tests", "ERROR")
        return 1
    
    # Phase B.1: Dashboard & Sync
    tester.test_phase_b1_dashboard()
    tester.test_phase_b1_sync()
    tester.test_phase_b1_sync_history()
    tester.test_phase_b1_legacy_config()
    
    # Phase B.2: Orders
    tester.test_phase_b2_orders()
    
    # Phase B.2: Catalog Items
    tester.test_phase_b2_catalog_items()
    tester.test_phase_b2_photo_upload()
    tester.test_phase_b2_catalog_item_delete()
    
    # Phase B.2: Backfill Verification
    tester.test_backfill_verification()
    
    # Regression: Legacy endpoints
    tester.test_regression_legacy_endpoints()
    tester.test_regression_preserved_endpoints()
    
    # Print summary
    all_passed = tester.print_summary()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
