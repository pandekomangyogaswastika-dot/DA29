"""
Phase C Extended Marketing Endpoints Testing
=============================================

Additional tests for marketing namespace endpoints:
- Platform accounts sync & config
- Returns management
- Reviews management
- Catalog items management

Created: 2026-05-23
"""
import requests
import sys
from typing import Dict, List, Tuple

BASE_URL = "https://doc-audit-4.preview.emergentagent.com"

class MarketingExtendedTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests: List[Dict] = []
        self.headers = {'Content-Type': 'application/json'}
        
    def log(self, msg: str, level: str = "INFO"):
        prefix = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}.get(level, "•")
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
        """Execute extended marketing endpoint tests"""
        self.log("=" * 70, "INFO")
        self.log("PHASE C EXTENDED MARKETING ENDPOINTS TESTING", "INFO")
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
        
        # ── 2. Platform Accounts Sync & Config ──
        self.log("\n[2] PLATFORM ACCOUNTS SYNC & CONFIG", "INFO")
        
        # Get list of accounts first
        success, accounts_resp = self.test(
            "GET /api/marketing/accounts",
            "GET",
            "/api/marketing/accounts",
            200,
            check_response=lambda r: isinstance(r, list) or 'accounts' in r
        )
        
        # Extract account code for testing
        test_account_code = None
        if success:
            accounts = accounts_resp if isinstance(accounts_resp, list) else accounts_resp.get('accounts', [])
            if accounts:
                test_account_code = accounts[0].get('code') or accounts[0].get('channel_code')
        
        if not test_account_code:
            # Use default test code
            test_account_code = 'shopee'
            self.log(f"⚠️  No accounts found, using default code: {test_account_code}", "WARN")
        
        # Test sync endpoint (MOCK)
        self.test(
            f"POST /api/marketing/accounts/{test_account_code}/sync (MOCK)",
            "POST",
            f"/api/marketing/accounts/{test_account_code}/sync",
            200,
            check_response=lambda r: 'duration_ms' in r or 'message' in r
        )
        
        # Test sync history
        self.test(
            f"GET /api/marketing/accounts/{test_account_code}/sync-history",
            "GET",
            f"/api/marketing/accounts/{test_account_code}/sync-history",
            200,
            check_response=lambda r: isinstance(r, list)
        )
        
        # Test legacy config update
        config_data = {
            "enabled": True,
            "fee_pct": 2.5,
            "commission_pct": 1.0,
            "credentials": {
                "api_key": "test_key_phase_c"
            }
        }
        self.test(
            f"PUT /api/marketing/accounts/{test_account_code}/legacy-config",
            "PUT",
            f"/api/marketing/accounts/{test_account_code}/legacy-config",
            200,
            data=config_data,
            check_response=lambda r: 'message' in r or 'ok' in r
        )
        
        # ── 3. Returns Management ──
        self.log("\n[3] RETURNS MANAGEMENT", "INFO")
        
        # List returns
        self.test(
            "GET /api/marketing/returns",
            "GET",
            "/api/marketing/returns",
            200,
            check_response=lambda r: isinstance(r, list) or 'returns' in r
        )
        
        # Create return
        return_data = {
            "order_id": "TEST-ORDER-001",
            "platform": "shopee",
            "customer_name": "Test Customer",
            "product_name": "Test Product",
            "sku_id": "DA-GMB-001",
            "quantity": 1,
            "refund_amount": 100000,
            "refund_type": "full",
            "reason": "Produk cacat",
            "notes": "Phase C test return"
        }
        success, return_resp = self.test(
            "POST /api/marketing/returns",
            "POST",
            "/api/marketing/returns",
            201,
            data=return_data,
            check_response=lambda r: 'id' in r or 'return_id' in r
        )
        
        return_id = None
        if success:
            return_id = return_resp.get('id') or return_resp.get('return_id')
        
        if return_id:
            # Get return
            self.test(
                f"GET /api/marketing/returns/{return_id}",
                "GET",
                f"/api/marketing/returns/{return_id}",
                200,
                check_response=lambda r: r.get('id') == return_id or r.get('return_id') == return_id
            )
            
            # Update return
            self.test(
                f"PUT /api/marketing/returns/{return_id}",
                "PUT",
                f"/api/marketing/returns/{return_id}",
                200,
                data={"notes": "Updated in Phase C test"}
            )
            
            # Approve return
            self.test(
                f"POST /api/marketing/returns/{return_id}/approve",
                "POST",
                f"/api/marketing/returns/{return_id}/approve",
                200,
                data={"notes": "Approved"}
            )
            
            # Complete return
            self.test(
                f"POST /api/marketing/returns/{return_id}/complete",
                "POST",
                f"/api/marketing/returns/{return_id}/complete",
                200,
                data={"notes": "Completed"}
            )
            
            # Delete return
            self.test(
                f"DELETE /api/marketing/returns/{return_id}",
                "DELETE",
                f"/api/marketing/returns/{return_id}",
                200
            )
        
        # ── 4. Reviews Management ──
        self.log("\n[4] REVIEWS MANAGEMENT", "INFO")
        
        # List reviews
        self.test(
            "GET /api/marketing/reviews",
            "GET",
            "/api/marketing/reviews",
            200,
            check_response=lambda r: isinstance(r, list) or 'reviews' in r
        )
        
        # Create review
        review_data = {
            "order_id": "TEST-ORDER-002",
            "platform": "tokopedia",
            "customer_name": "Test Reviewer",
            "product_name": "Test Product",
            "sku_id": "DA-CKW-005",
            "rating": 5,
            "category": "positive",
            "review_text": "Produk bagus sekali!",
            "notes": "Phase C test review"
        }
        success, review_resp = self.test(
            "POST /api/marketing/reviews",
            "POST",
            "/api/marketing/reviews",
            201,
            data=review_data,
            check_response=lambda r: 'id' in r or 'review_id' in r
        )
        
        review_id = None
        if success:
            review_id = review_resp.get('id') or review_resp.get('review_id')
        
        if review_id:
            # Get review
            self.test(
                f"GET /api/marketing/reviews/{review_id}",
                "GET",
                f"/api/marketing/reviews/{review_id}",
                200,
                check_response=lambda r: r.get('id') == review_id or r.get('review_id') == review_id
            )
            
            # Update review
            self.test(
                f"PUT /api/marketing/reviews/{review_id}",
                "PUT",
                f"/api/marketing/reviews/{review_id}",
                200,
                data={"notes": "Updated in Phase C test"}
            )
            
            # Respond to review
            self.test(
                f"POST /api/marketing/reviews/{review_id}/respond",
                "POST",
                f"/api/marketing/reviews/{review_id}/respond",
                200,
                data={"response_text": "Terima kasih atas reviewnya!"}
            )
            
            # Delete review
            self.test(
                f"DELETE /api/marketing/reviews/{review_id}",
                "DELETE",
                f"/api/marketing/reviews/{review_id}",
                200
            )
        
        # ── 5. Catalog Items Management ──
        self.log("\n[5] CATALOG ITEMS MANAGEMENT", "INFO")
        
        # Get catalogs first
        success, catalogs_resp = self.test(
            "GET /api/marketing/catalogs",
            "GET",
            "/api/marketing/catalogs",
            200,
            check_response=lambda r: isinstance(r, list) or 'catalogs' in r
        )
        
        test_catalog_id = None
        if success:
            catalogs = catalogs_resp if isinstance(catalogs_resp, list) else catalogs_resp.get('catalogs', [])
            if catalogs:
                test_catalog_id = catalogs[0].get('id') or catalogs[0].get('catalog_id')
        
        if test_catalog_id:
            # List catalog items
            self.test(
                f"GET /api/marketing/catalogs/{test_catalog_id}/items",
                "GET",
                f"/api/marketing/catalogs/{test_catalog_id}/items",
                200,
                check_response=lambda r: isinstance(r, list) or 'items' in r
            )
            
            # Create catalog item
            item_data = {
                "sku": "TEST-SKU-PHASE-C",
                "name": "Test Product Phase C",
                "price": 150000,
                "stock_total": 100,
                "status": "active",
                "description": "Test product for Phase C regression"
            }
            success, item_resp = self.test(
                f"POST /api/marketing/catalogs/{test_catalog_id}/items",
                "POST",
                f"/api/marketing/catalogs/{test_catalog_id}/items",
                201,
                data=item_data,
                check_response=lambda r: 'id' in r or 'item_id' in r
            )
            
            item_id = None
            if success:
                item_id = item_resp.get('id') or item_resp.get('item_id')
            
            if item_id:
                # Get catalog item
                self.test(
                    f"GET /api/marketing/catalogs/{test_catalog_id}/items/{item_id}",
                    "GET",
                    f"/api/marketing/catalogs/{test_catalog_id}/items/{item_id}",
                    200,
                    check_response=lambda r: r.get('id') == item_id or r.get('item_id') == item_id
                )
                
                # Update catalog item
                self.test(
                    f"PUT /api/marketing/catalogs/{test_catalog_id}/items/{item_id}",
                    "PUT",
                    f"/api/marketing/catalogs/{test_catalog_id}/items/{item_id}",
                    200,
                    data={"price": 175000, "stock_total": 150}
                )
                
                # Delete catalog item
                self.test(
                    f"DELETE /api/marketing/catalogs/{test_catalog_id}/items/{item_id}",
                    "DELETE",
                    f"/api/marketing/catalogs/{test_catalog_id}/items/{item_id}",
                    200
                )
        else:
            self.log("⚠️  No catalogs found, skipping catalog items tests", "WARN")
        
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
        self.log(f"\nSuccess Rate: {success_rate:.1f}%", "PASS" if success_rate >= 90 else "FAIL")
        
        return success_rate >= 90


def main():
    tester = MarketingExtendedTester()
    
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
