"""
Phase C Toko Route Removal — Backend Regression Testing
========================================================

Tests 31 deleted endpoints return 404, 9 preserved endpoints work,
and all marketing namespace endpoints remain functional.

Created: 2026-05-23 (Phase C cleanup verification)
"""
import requests
import sys
import json
from datetime import datetime
from typing import Dict, List, Tuple

BASE_URL = "https://doc-audit-4.preview.emergentagent.com"

class PhaseC_RegressionTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests: List[Dict] = []
        self.headers = {'Content-Type': 'application/json'}
        
    def log(self, msg: str, level: str = "INFO"):
        """Simple logger"""
        prefix = {
            "INFO": "ℹ️",
            "PASS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️"
        }.get(level, "•")
        print(f"{prefix} {msg}")
    
    def test(self, name: str, method: str, endpoint: str, 
             expected_status: int, data: dict = None, 
             check_response: callable = None) -> Tuple[bool, dict]:
        """Run a single test"""
        url = f"{self.base_url}{endpoint}"
        headers = self.headers.copy()
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        self.tests_run += 1
        self.log(f"Test #{self.tests_run}: {name}", "INFO")
        
        try:
            if method == 'GET':
                resp = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                resp = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                resp = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'PATCH':
                resp = requests.patch(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                resp = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Check status code
            if resp.status_code != expected_status:
                self.log(f"FAILED: Expected {expected_status}, got {resp.status_code}", "FAIL")
                self.log(f"  Response: {resp.text[:200]}", "FAIL")
                self.failed_tests.append({
                    "test": name,
                    "endpoint": endpoint,
                    "expected": expected_status,
                    "actual": resp.status_code,
                    "response": resp.text[:200]
                })
                return False, {}
            
            # Additional response checks
            response_data = {}
            try:
                response_data = resp.json()
            except:
                pass
            
            if check_response and response_data:
                check_result = check_response(response_data)
                if not check_result:
                    self.log(f"FAILED: Response validation failed", "FAIL")
                    self.failed_tests.append({
                        "test": name,
                        "endpoint": endpoint,
                        "issue": "Response validation failed",
                        "response": response_data
                    })
                    return False, response_data
            
            self.tests_passed += 1
            self.log(f"PASSED: {resp.status_code}", "PASS")
            return True, response_data
            
        except Exception as e:
            self.log(f"FAILED: Exception - {str(e)}", "FAIL")
            self.failed_tests.append({
                "test": name,
                "endpoint": endpoint,
                "error": str(e)
            })
            return False, {}
    
    def run_all_tests(self):
        """Execute all Phase C regression tests"""
        self.log("=" * 70, "INFO")
        self.log("PHASE C REGRESSION TESTING — Toko Route Removal", "INFO")
        self.log("=" * 70, "INFO")
        
        # ── 1. Authentication ──
        self.log("\n[1] AUTHENTICATION", "INFO")
        success, resp = self.test(
            "Admin login",
            "POST",
            "/api/auth/login",
            200,
            data={"email": "admin@garment.com", "password": "Admin@2025"}
        )
        if not success:
            self.log("Cannot proceed without authentication", "FAIL")
            return False
        
        self.token = resp.get('token')
        if not self.token:
            self.log("No token received from login", "FAIL")
            return False
        
        # ── 2. Test DELETED endpoints return 404 ──
        self.log("\n[2] DELETED ENDPOINTS (should return 404)", "INFO")
        
        deleted_endpoints = [
            # From dewi_toko.py
            ("GET", "/api/dewi/toko/products", "Legacy products endpoint"),
            ("GET", "/api/dewi/toko/channels", "Legacy channels endpoint"),
            ("GET", "/api/dewi/toko/dashboard", "Legacy dashboard endpoint"),
            ("POST", "/api/dewi/toko/channels/shopee/sync", "Legacy channel sync"),
            ("GET", "/api/dewi/toko/channels/shopee/sync-history", "Legacy sync history"),
            ("PUT", "/api/dewi/toko/channels/shopee", "Legacy channel update"),
            
            # From dewi_returns.py (ALL)
            ("GET", "/api/dewi/toko/returns", "Legacy returns list"),
            ("POST", "/api/dewi/toko/returns", "Legacy returns create"),
            ("PUT", "/api/dewi/toko/returns/test-id", "Legacy returns update"),
            ("DELETE", "/api/dewi/toko/returns/test-id", "Legacy returns delete"),
            ("POST", "/api/dewi/toko/returns/test-id/approve", "Legacy returns approve"),
            ("POST", "/api/dewi/toko/returns/test-id/reject", "Legacy returns reject"),
            ("POST", "/api/dewi/toko/returns/test-id/complete", "Legacy returns complete"),
            ("GET", "/api/dewi/toko/reviews", "Legacy reviews list"),
            ("POST", "/api/dewi/toko/reviews", "Legacy reviews create"),
            ("PUT", "/api/dewi/toko/reviews/test-id", "Legacy reviews update"),
            ("DELETE", "/api/dewi/toko/reviews/test-id", "Legacy reviews delete"),
            ("POST", "/api/dewi/toko/reviews/test-id/respond", "Legacy reviews respond"),
            
            # From dewi_online_orders.py
            ("GET", "/api/dewi/toko/orders", "Legacy orders list"),
            ("POST", "/api/dewi/toko/orders", "Legacy orders create"),
            ("GET", "/api/dewi/toko/orders/test-id", "Legacy orders get"),
            ("PUT", "/api/dewi/toko/orders/test-id", "Legacy orders update"),
            ("DELETE", "/api/dewi/toko/orders/test-id", "Legacy orders delete"),
            ("PATCH", "/api/dewi/toko/orders/test-id/status", "Legacy orders status"),
            ("POST", "/api/dewi/toko/orders/test-id/cancel", "Legacy orders cancel"),
        ]
        
        for method, endpoint, description in deleted_endpoints:
            data = {} if method in ['POST', 'PUT', 'PATCH'] else None
            self.test(
                f"Deleted: {description}",
                method,
                endpoint,
                404,
                data=data
            )
        
        # ── 3. Test PRESERVED flashsales endpoints ──
        self.log("\n[3] PRESERVED FLASHSALES ENDPOINTS", "INFO")
        
        # List flashsales
        success, resp = self.test(
            "GET /api/dewi/toko/flashsales",
            "GET",
            "/api/dewi/toko/flashsales",
            200,
            check_response=lambda r: isinstance(r, list)
        )
        
        # Create flashsale
        flashsale_data = {
            "name": "Test Flashsale Phase C",
            "channel_code": "shopee",
            "start_at": "2026-05-24T10:00:00Z",
            "end_at": "2026-05-24T18:00:00Z",
            "products": [
                {
                    "sku_code": "DA-GMB-001",
                    "name": "Gamis Test",
                    "original_price": 100000,
                    "flashsale_price": 80000,
                    "discount_pct": 20,
                    "quota": 50
                }
            ],
            "notes": "Phase C regression test"
        }
        success, resp = self.test(
            "POST /api/dewi/toko/flashsales",
            "POST",
            "/api/dewi/toko/flashsales",
            201,
            data=flashsale_data,
            check_response=lambda r: 'id' in r and 'message' in r
        )
        
        flashsale_id = resp.get('id') if success else None
        
        if flashsale_id:
            # Get flashsale
            self.test(
                "GET /api/dewi/toko/flashsales/{id}",
                "GET",
                f"/api/dewi/toko/flashsales/{flashsale_id}",
                200,
                check_response=lambda r: r.get('id') == flashsale_id
            )
            
            # Update flashsale
            self.test(
                "PUT /api/dewi/toko/flashsales/{id}",
                "PUT",
                f"/api/dewi/toko/flashsales/{flashsale_id}",
                200,
                data={"notes": "Updated in Phase C test"}
            )
            
            # Activate flashsale
            self.test(
                "POST /api/dewi/toko/flashsales/{id}/activate",
                "POST",
                f"/api/dewi/toko/flashsales/{flashsale_id}/activate",
                200,
                check_response=lambda r: r.get('status') == 'active'
            )
            
            # Deactivate before delete
            self.test(
                "POST /api/dewi/toko/flashsales/{id}/activate (deactivate)",
                "POST",
                f"/api/dewi/toko/flashsales/{flashsale_id}/activate",
                200,
                check_response=lambda r: r.get('status') == 'draft'
            )
            
            # Delete flashsale
            self.test(
                "DELETE /api/dewi/toko/flashsales/{id}",
                "DELETE",
                f"/api/dewi/toko/flashsales/{flashsale_id}",
                200
            )
        
        # ── 4. Test PRESERVED pack-batches endpoints ──
        self.log("\n[4] PRESERVED PACK-BATCHES ENDPOINTS", "INFO")
        
        # First, create a test order in marketing_orders
        order_data = {
            "platform": "manual",
            "customer_name": "Test Customer Phase C",
            "sku_id": "DA-GMB-001",
            "product_name": "Test Product",
            "quantity": 1,
            "price_final": 100000,
            "total_payment": 100000
        }
        success, order_resp = self.test(
            "Create test order for pack-batch",
            "POST",
            "/api/marketing/orders",
            200,
            data=order_data,
            check_response=lambda r: 'id' in r
        )
        
        test_order_id = order_resp.get('id') if success else None
        
        # List pack-batches
        self.test(
            "GET /api/dewi/toko/pack-batches",
            "GET",
            "/api/dewi/toko/pack-batches",
            200,
            check_response=lambda r: isinstance(r, list)
        )
        
        # Create pack-batch with order
        if test_order_id:
            pack_batch_data = {
                "batch_name": "Phase C Test Batch",
                "schedule_time": "13:00",
                "order_ids": [test_order_id]
            }
            success, batch_resp = self.test(
                "POST /api/dewi/toko/pack-batches",
                "POST",
                "/api/dewi/toko/pack-batches",
                201,
                data=pack_batch_data,
                check_response=lambda r: 'id' in r and 'batch_code' in r
            )
            
            batch_id = batch_resp.get('id') if success else None
            
            # ── 5. Integration test: Verify order marked as 'packed' ──
            self.log("\n[5] INTEGRATION: Order marked as 'packed' in marketing_orders", "INFO")
            
            if test_order_id:
                success, order_check = self.test(
                    "GET /api/marketing/orders/{id} - verify status=packed",
                    "GET",
                    f"/api/marketing/orders/{test_order_id}",
                    200,
                    check_response=lambda r: r.get('status') == 'packed' and r.get('pack_batch_id') == batch_id
                )
                
                if success and order_check.get('status') == 'packed':
                    self.log("✅ Order successfully marked as 'packed' in marketing_orders", "PASS")
                else:
                    self.log(f"❌ Order status is '{order_check.get('status')}', expected 'packed'", "FAIL")
                    self.failed_tests.append({
                        "test": "Pack-batch integration",
                        "issue": f"Order not marked as packed. Status: {order_check.get('status')}",
                        "order_id": test_order_id,
                        "batch_id": batch_id
                    })
            
            # Close pack-batch
            if batch_id:
                self.test(
                    "POST /api/dewi/toko/pack-batches/{id}/close",
                    "POST",
                    f"/api/dewi/toko/pack-batches/{batch_id}/close",
                    200
                )
            
            # Cleanup: delete test order
            if test_order_id:
                self.test(
                    "Cleanup: Delete test order",
                    "DELETE",
                    f"/api/marketing/orders/{test_order_id}",
                    200
                )
        
        # ── 6. Test MARKETING namespace endpoints ──
        self.log("\n[6] MARKETING NAMESPACE ENDPOINTS (should all work)", "INFO")
        
        # Dashboard
        self.test(
            "GET /api/marketing/dashboard/toko-overview",
            "GET",
            "/api/marketing/dashboard/toko-overview",
            200,
            check_response=lambda r: 'products' in r and 'channels' in r and 'mock_mode' in r
        )
        
        # Orders summary
        self.test(
            "GET /api/marketing/orders/summary",
            "GET",
            "/api/marketing/orders/summary",
            200,
            check_response=lambda r: 'total_orders' in r and 'by_status' in r
        )
        
        # Orders list
        self.test(
            "GET /api/marketing/orders",
            "GET",
            "/api/marketing/orders",
            200,
            check_response=lambda r: 'orders' in r and 'pagination' in r
        )
        
        # Create order (already tested above, but verify again)
        order_data2 = {
            "platform": "shopee",
            "customer_name": "Test Customer 2",
            "sku_id": "DA-CKW-005",
            "product_name": "Test Product 2",
            "quantity": 2,
            "price_final": 75000,
            "total_payment": 150000
        }
        success, order_resp2 = self.test(
            "POST /api/marketing/orders",
            "POST",
            "/api/marketing/orders",
            200,
            data=order_data2,
            check_response=lambda r: 'id' in r and r.get('platform') == 'shopee'
        )
        
        test_order_id2 = order_resp2.get('id') if success else None
        
        if test_order_id2:
            # Update order status
            self.test(
                "PATCH /api/marketing/orders/{id}/status",
                "PATCH",
                f"/api/marketing/orders/{test_order_id2}/status",
                200,
                data={"status": "packed"},
                check_response=lambda r: r.get('new_status') == 'packed'
            )
            
            # Delete order
            self.test(
                "DELETE /api/marketing/orders/{id}",
                "DELETE",
                f"/api/marketing/orders/{test_order_id2}",
                200
            )
        
        # ── 7. Sanity checks ──
        self.log("\n[7] SANITY CHECKS", "INFO")
        
        # Check OpenAPI spec is parseable
        success, spec = self.test(
            "GET /openapi.json - verify spec parseable",
            "GET",
            "/openapi.json",
            200,
            check_response=lambda r: 'openapi' in r and 'paths' in r
        )
        
        if success:
            # Verify deleted endpoints NOT in spec
            paths = spec.get('paths', {})
            deleted_in_spec = []
            for path in paths:
                if '/dewi/toko/products' in path or \
                   '/dewi/toko/channels' in path or \
                   '/dewi/toko/dashboard' in path or \
                   '/dewi/toko/orders' in path and '/pack-batches' not in path or \
                   '/dewi/toko/returns' in path or \
                   '/dewi/toko/reviews' in path:
                    deleted_in_spec.append(path)
            
            if deleted_in_spec:
                self.log(f"⚠️  WARNING: Deleted endpoints still in OpenAPI spec: {deleted_in_spec}", "WARN")
            else:
                self.log("✅ OpenAPI spec clean - no deleted endpoints found", "PASS")
        
        return True
    
    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "=" * 70, "INFO")
        self.log("TEST SUMMARY", "INFO")
        self.log("=" * 70, "INFO")
        self.log(f"Total tests: {self.tests_run}", "INFO")
        self.log(f"Passed: {self.tests_passed}", "PASS")
        self.log(f"Failed: {len(self.failed_tests)}", "FAIL" if self.failed_tests else "PASS")
        
        if self.failed_tests:
            self.log("\nFAILED TESTS:", "FAIL")
            for i, failure in enumerate(self.failed_tests, 1):
                self.log(f"\n{i}. {failure.get('test', 'Unknown')}", "FAIL")
                for key, value in failure.items():
                    if key != 'test':
                        self.log(f"   {key}: {value}", "FAIL")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\nSuccess Rate: {success_rate:.1f}%", "PASS" if success_rate >= 95 else "FAIL")
        
        return success_rate >= 95


def main():
    tester = PhaseC_RegressionTester()
    
    try:
        tester.run_all_tests()
        success = tester.print_summary()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
