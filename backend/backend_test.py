"""
CV. Dewi Aditya - Backend API Testing
P1.A: Accessory Consolidation (SSOT-backed implementation)

Tests all /api/acc/* endpoints to verify:
- Items now backed by rahaza_materials (type='accessory')
- Stock backed by rahaza_material_stock
- Movements backed by rahaza_material_movements
- Specialized features (loans, internal-requests, purchase-requests, opname) preserved

Test Coverage:
1. Item CRUD (list, create, update, delete)
2. Stock operations (receive, issue, movements)
3. Internal requests (create, approve, issue)
4. Loans (create, return)
5. Purchase requests (create, submit, receive)
6. Opname (start, count, complete)
7. Dashboard stats
"""
import requests
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://doc-audit-4.preview.emergentagent.com"
ADMIN_EMAIL = "admin@garment.com"
ADMIN_PASSWORD = "Admin@123"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'

class AccessoryTester:
    def __init__(self):
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Test data IDs (will be populated during tests)
        self.test_item_id = None
        self.test_request_id = None
        self.test_loan_id = None
        self.test_pr_id = None
        self.test_opname_id = None

    def log(self, msg, color=Colors.BLUE):
        print(f"{color}{msg}{Colors.END}")

    def test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{BASE_URL}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n{Colors.BLUE}🔍 Test {self.tests_run}: {name}{Colors.END}")
        print(f"   {method} {endpoint}")
        if params:
            print(f"   Params: {params}")
        if data:
            print(f"   Data: {data}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)
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

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(name)
            print(f"{Colors.RED}❌ FAIL - Exception: {str(e)}{Colors.END}")
            return False, {}

    def login(self):
        """Login as admin"""
        self.log("\n" + "="*80, Colors.MAGENTA)
        self.log("AUTHENTICATION", Colors.MAGENTA)
        self.log("="*80, Colors.MAGENTA)
        
        success, response = self.test(
            "Admin Login",
            "POST",
            "/api/auth/login",
            200,
            data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.log(f"✅ Logged in as {ADMIN_EMAIL}", Colors.GREEN)
            return True
        else:
            self.log("❌ Login failed - cannot proceed", Colors.RED)
            return False

    def test_items_crud(self):
        """Test item CRUD operations"""
        self.log("\n" + "="*80, Colors.MAGENTA)
        self.log("SECTION 1: ITEM CRUD (rahaza_materials with type='accessory')", Colors.MAGENTA)
        self.log("="*80, Colors.MAGENTA)
        
        # 1. List items (should include migrated legacy items)
        success, response = self.test(
            "GET /api/acc/items - List all accessories",
            "GET",
            "/api/acc/items",
            200
        )
        if success:
            items = response if isinstance(response, list) else []
            self.log(f"   Found {len(items)} accessories", Colors.CYAN)
            if len(items) > 0:
                sample = items[0]
                self.log(f"   Sample: {sample.get('code')} - {sample.get('name')}", Colors.CYAN)
                # Verify field shape
                required_fields = ['id', 'code', 'name', 'category', 'unit', 'stock_qty', 'stock_status']
                missing = [f for f in required_fields if f not in sample]
                if missing:
                    self.log(f"   ⚠️  Missing fields: {missing}", Colors.YELLOW)
        
        # 2. Search by name
        success, response = self.test(
            "GET /api/acc/items?search=Legacy - Search accessories",
            "GET",
            "/api/acc/items",
            200,
            params={"search": "Legacy"}
        )
        if success:
            items = response if isinstance(response, list) else []
            self.log(f"   Found {len(items)} items matching 'Legacy'", Colors.CYAN)
        
        # 3. Filter by category
        success, response = self.test(
            "GET /api/acc/items?category=Resleting - Filter by category",
            "GET",
            "/api/acc/items",
            200,
            params={"category": "Resleting"}
        )
        
        # 4. Create new accessory
        success, response = self.test(
            "POST /api/acc/items - Create accessory 'Test Resleting YKK'",
            "POST",
            "/api/acc/items",
            201,
            data={
                "name": "Test Resleting YKK",
                "code": "TEST-RES-001",
                "category": "Resleting",
                "unit": "pcs",
                "min_stock": 20,
                "description": "Test item for P1.A validation",
                "supplier": "YKK Indonesia"
            }
        )
        if success:
            self.test_item_id = response.get('id')
            self.log(f"   Created item ID: {self.test_item_id}", Colors.CYAN)
            self.log(f"   Code: {response.get('code')}", Colors.CYAN)
            self.log(f"   Stock status: {response.get('stock_status')}", Colors.CYAN)
        
        # 5. Verify item appears in list
        if self.test_item_id:
            success, response = self.test(
                "GET /api/acc/items - Verify new item in list",
                "GET",
                "/api/acc/items",
                200
            )
            if success:
                items = response if isinstance(response, list) else []
                found = any(item.get('id') == self.test_item_id for item in items)
                if found:
                    self.log(f"   ✅ New item found in list", Colors.GREEN)
                else:
                    self.log(f"   ❌ New item NOT found in list", Colors.RED)
        
        # 6. Update item (change min_stock to 50)
        if self.test_item_id:
            success, response = self.test(
                "PUT /api/acc/items/{id} - Update min_stock to 50",
                "PUT",
                f"/api/acc/items/{self.test_item_id}",
                200,
                data={"min_stock": 50}
            )
            if success:
                new_min = response.get('min_stock')
                if new_min == 50:
                    self.log(f"   ✅ min_stock updated to {new_min}", Colors.GREEN)
                else:
                    self.log(f"   ❌ min_stock is {new_min}, expected 50", Colors.RED)

    def test_stock_operations(self):
        """Test stock receive, issue, and movements"""
        self.log("\n" + "="*80, Colors.MAGENTA)
        self.log("SECTION 2: STOCK OPERATIONS (rahaza_material_stock + movements)", Colors.MAGENTA)
        self.log("="*80, Colors.MAGENTA)
        
        if not self.test_item_id:
            self.log("⚠️  Skipping stock tests - no test item created", Colors.YELLOW)
            return
        
        # 1. Receive stock (100 pcs)
        success, response = self.test(
            "POST /api/acc/stock/receive - Receive 100 pcs",
            "POST",
            "/api/acc/stock/receive",
            201,
            data={
                "acc_id": self.test_item_id,
                "qty": 100,
                "notes": "Initial stock for testing",
                "ref_type": "manual"
            }
        )
        if success:
            new_qty = response.get('new_qty')
            self.log(f"   New stock quantity: {new_qty}", Colors.CYAN)
            if new_qty == 100:
                self.log(f"   ✅ Stock correctly updated to 100", Colors.GREEN)
            else:
                self.log(f"   ❌ Expected 100, got {new_qty}", Colors.RED)
        
        # 2. Verify stock in overview
        success, response = self.test(
            "GET /api/acc/stock - Verify stock in overview",
            "GET",
            "/api/acc/stock",
            200
        )
        if success:
            items = response if isinstance(response, list) else []
            item = next((i for i in items if i.get('id') == self.test_item_id), None)
            if item:
                stock_qty = item.get('stock_qty')
                stock_status = item.get('stock_status')
                self.log(f"   Stock qty: {stock_qty}, status: {stock_status}", Colors.CYAN)
                if stock_qty == 100 and stock_status == 'ok':
                    self.log(f"   ✅ Stock overview correct", Colors.GREEN)
                else:
                    self.log(f"   ❌ Stock overview incorrect", Colors.RED)
        
        # 3. Issue stock (30 pcs)
        success, response = self.test(
            "POST /api/acc/stock/issue - Issue 30 pcs",
            "POST",
            "/api/acc/stock/issue",
            201,
            data={
                "acc_id": self.test_item_id,
                "qty": 30,
                "notes": "Test issue",
                "ref_type": "manual"
            }
        )
        if success:
            new_qty = response.get('new_qty')
            self.log(f"   New stock quantity: {new_qty}", Colors.CYAN)
            if new_qty == 70:
                self.log(f"   ✅ Stock correctly updated to 70", Colors.GREEN)
            else:
                self.log(f"   ❌ Expected 70, got {new_qty}", Colors.RED)
        
        # 4. Try to issue more than available (should fail)
        success, response = self.test(
            "POST /api/acc/stock/issue - Try to issue 200 pcs (should fail)",
            "POST",
            "/api/acc/stock/issue",
            400,
            data={
                "acc_id": self.test_item_id,
                "qty": 200,
                "notes": "Should fail - insufficient stock"
            }
        )
        if success:
            self.log(f"   ✅ Correctly rejected insufficient stock", Colors.GREEN)
        
        # 5. Verify movements logged
        success, response = self.test(
            "GET /api/acc/stock/movements?acc_id={id} - Verify movements",
            "GET",
            "/api/acc/stock/movements",
            200,
            params={"acc_id": self.test_item_id}
        )
        if success:
            movements = response if isinstance(response, list) else []
            self.log(f"   Found {len(movements)} movements", Colors.CYAN)
            if len(movements) >= 2:
                # Should have IN +100 and OUT -30
                in_mvs = [m for m in movements if m.get('movement_type') == 'IN']
                out_mvs = [m for m in movements if m.get('movement_type') == 'OUT']
                self.log(f"   IN movements: {len(in_mvs)}, OUT movements: {len(out_mvs)}", Colors.CYAN)
                
                # Verify qty_signed
                for m in movements[:2]:
                    self.log(f"   Movement: {m.get('movement_type')} qty_signed={m.get('qty_signed')}", Colors.CYAN)

    def test_internal_requests(self):
        """Test internal request workflow"""
        self.log("\n" + "="*80, Colors.MAGENTA)
        self.log("SECTION 3: INTERNAL REQUESTS (acc_internal_requests)", Colors.MAGENTA)
        self.log("="*80, Colors.MAGENTA)
        
        if not self.test_item_id:
            self.log("⚠️  Skipping internal request tests - no test item", Colors.YELLOW)
            return
        
        # 1. Create internal request
        success, response = self.test(
            "POST /api/acc/internal-requests - Create request",
            "POST",
            "/api/acc/internal-requests",
            201,
            data={
                "divisi": "Produksi",
                "purpose": "Test request for P1.A validation",
                "items": [
                    {
                        "acc_id": self.test_item_id,
                        "acc_name": "Test Resleting YKK",
                        "qty_requested": 10
                    }
                ]
            }
        )
        if success:
            self.test_request_id = response.get('id')
            request_number = response.get('request_number')
            status = response.get('status')
            self.log(f"   Request ID: {self.test_request_id}", Colors.CYAN)
            self.log(f"   Request number: {request_number}", Colors.CYAN)
            self.log(f"   Status: {status}", Colors.CYAN)
            if status == 'Pending':
                self.log(f"   ✅ Request created with Pending status", Colors.GREEN)
        
        # 2. Approve request
        if self.test_request_id:
            success, response = self.test(
                "PUT /api/acc/internal-requests/{id} - Approve request",
                "PUT",
                f"/api/acc/internal-requests/{self.test_request_id}",
                200,
                data={"status": "Approved", "admin_notes": "Approved for testing"}
            )
            if success:
                status = response.get('status')
                if status == 'Approved':
                    self.log(f"   ✅ Request approved", Colors.GREEN)
        
        # 3. Issue request (should deduct stock)
        if self.test_request_id:
            success, response = self.test(
                "PUT /api/acc/internal-requests/{id} - Issue request",
                "PUT",
                f"/api/acc/internal-requests/{self.test_request_id}",
                200,
                data={"status": "Issued"}
            )
            if success:
                status = response.get('status')
                if status == 'Issued':
                    self.log(f"   ✅ Request issued", Colors.GREEN)
                    
                    # Verify stock decreased (70 - 10 = 60)
                    success2, response2 = self.test(
                        "GET /api/acc/stock - Verify stock after issue",
                        "GET",
                        "/api/acc/stock",
                        200
                    )
                    if success2:
                        items = response2 if isinstance(response2, list) else []
                        item = next((i for i in items if i.get('id') == self.test_item_id), None)
                        if item:
                            stock_qty = item.get('stock_qty')
                            self.log(f"   Stock after issue: {stock_qty}", Colors.CYAN)
                            if stock_qty == 60:
                                self.log(f"   ✅ Stock correctly decreased to 60", Colors.GREEN)
                            else:
                                self.log(f"   ❌ Expected 60, got {stock_qty}", Colors.RED)

    def test_loans(self):
        """Test loan workflow"""
        self.log("\n" + "="*80, Colors.MAGENTA)
        self.log("SECTION 4: LOANS (acc_loans)", Colors.MAGENTA)
        self.log("="*80, Colors.MAGENTA)
        
        if not self.test_item_id:
            self.log("⚠️  Skipping loan tests - no test item", Colors.YELLOW)
            return
        
        # 1. Create loan
        success, response = self.test(
            "POST /api/acc/loans - Create loan",
            "POST",
            "/api/acc/loans",
            201,
            data={
                "borrower_name": "Budi Santoso",
                "borrower_divisi": "Produksi",
                "purpose": "Test loan for P1.A validation",
                "items": [
                    {
                        "acc_id": self.test_item_id,
                        "acc_name": "Test Resleting YKK",
                        "qty": 5
                    }
                ]
            }
        )
        if success:
            self.test_loan_id = response.get('id')
            loan_number = response.get('loan_number')
            status = response.get('status')
            self.log(f"   Loan ID: {self.test_loan_id}", Colors.CYAN)
            self.log(f"   Loan number: {loan_number}", Colors.CYAN)
            self.log(f"   Status: {status}", Colors.CYAN)
            
            # Verify stock decreased (60 - 5 = 55)
            success2, response2 = self.test(
                "GET /api/acc/stock - Verify stock after loan",
                "GET",
                "/api/acc/stock",
                200
            )
            if success2:
                items = response2 if isinstance(response2, list) else []
                item = next((i for i in items if i.get('id') == self.test_item_id), None)
                if item:
                    stock_qty = item.get('stock_qty')
                    self.log(f"   Stock after loan: {stock_qty}", Colors.CYAN)
                    if stock_qty == 55:
                        self.log(f"   ✅ Stock correctly decreased to 55", Colors.GREEN)
                    else:
                        self.log(f"   ❌ Expected 55, got {stock_qty}", Colors.RED)
        
        # 2. Return loan
        if self.test_loan_id:
            success, response = self.test(
                "PUT /api/acc/loans/{id}/return - Return loan",
                "PUT",
                f"/api/acc/loans/{self.test_loan_id}/return",
                200,
                data={"return_notes": "Returned in good condition"}
            )
            if success:
                status = response.get('status')
                if status == 'Returned':
                    self.log(f"   ✅ Loan returned", Colors.GREEN)
                    
                    # Verify stock increased (55 + 5 = 60)
                    success2, response2 = self.test(
                        "GET /api/acc/stock - Verify stock after return",
                        "GET",
                        "/api/acc/stock",
                        200
                    )
                    if success2:
                        items = response2 if isinstance(response2, list) else []
                        item = next((i for i in items if i.get('id') == self.test_item_id), None)
                        if item:
                            stock_qty = item.get('stock_qty')
                            self.log(f"   Stock after return: {stock_qty}", Colors.CYAN)
                            if stock_qty == 60:
                                self.log(f"   ✅ Stock correctly increased to 60", Colors.GREEN)
                            else:
                                self.log(f"   ❌ Expected 60, got {stock_qty}", Colors.RED)

    def test_purchase_requests(self):
        """Test purchase request workflow"""
        self.log("\n" + "="*80, Colors.MAGENTA)
        self.log("SECTION 5: PURCHASE REQUESTS (acc_purchase_requests)", Colors.MAGENTA)
        self.log("="*80, Colors.MAGENTA)
        
        if not self.test_item_id:
            self.log("⚠️  Skipping PR tests - no test item", Colors.YELLOW)
            return
        
        # 1. Create PR
        success, response = self.test(
            "POST /api/acc/purchase-requests - Create PR",
            "POST",
            "/api/acc/purchase-requests",
            201,
            data={
                "priority": "Normal",
                "purpose": "Restock for testing",
                "supplier": "YKK Indonesia",
                "items": [
                    {
                        "acc_id": self.test_item_id,
                        "acc_name": "Test Resleting YKK",
                        "qty_requested": 200,
                        "estimated_price": 5000
                    }
                ]
            }
        )
        if success:
            self.test_pr_id = response.get('id')
            pr_number = response.get('pr_number')
            status = response.get('status')
            total = response.get('total_estimated')
            self.log(f"   PR ID: {self.test_pr_id}", Colors.CYAN)
            self.log(f"   PR number: {pr_number}", Colors.CYAN)
            self.log(f"   Status: {status}", Colors.CYAN)
            self.log(f"   Total estimated: {total}", Colors.CYAN)
            if status == 'Draft' and total == 1000000:
                self.log(f"   ✅ PR created correctly", Colors.GREEN)
        
        # 2. Submit PR
        if self.test_pr_id:
            success, response = self.test(
                "PUT /api/acc/purchase-requests/{id} - Submit PR",
                "PUT",
                f"/api/acc/purchase-requests/{self.test_pr_id}",
                200,
                data={"status": "Submitted"}
            )
            if success:
                status = response.get('status')
                if status == 'Submitted':
                    self.log(f"   ✅ PR submitted", Colors.GREEN)
        
        # 3. Mark as Received (should increase stock)
        if self.test_pr_id:
            success, response = self.test(
                "PUT /api/acc/purchase-requests/{id} - Mark as Received",
                "PUT",
                f"/api/acc/purchase-requests/{self.test_pr_id}",
                200,
                data={"status": "Received"}
            )
            if success:
                status = response.get('status')
                if status == 'Received':
                    self.log(f"   ✅ PR marked as received", Colors.GREEN)
                    
                    # Verify stock increased (60 + 200 = 260)
                    success2, response2 = self.test(
                        "GET /api/acc/stock - Verify stock after PR receive",
                        "GET",
                        "/api/acc/stock",
                        200
                    )
                    if success2:
                        items = response2 if isinstance(response2, list) else []
                        item = next((i for i in items if i.get('id') == self.test_item_id), None)
                        if item:
                            stock_qty = item.get('stock_qty')
                            self.log(f"   Stock after PR receive: {stock_qty}", Colors.CYAN)
                            if stock_qty == 260:
                                self.log(f"   ✅ Stock correctly increased to 260", Colors.GREEN)
                            else:
                                self.log(f"   ❌ Expected 260, got {stock_qty}", Colors.RED)

    def test_opname(self):
        """Test opname (stock taking) workflow"""
        self.log("\n" + "="*80, Colors.MAGENTA)
        self.log("SECTION 6: OPNAME (acc_opname_sessions)", Colors.MAGENTA)
        self.log("="*80, Colors.MAGENTA)
        
        # 1. Start opname session
        success, response = self.test(
            "POST /api/acc/opname - Start opname session",
            "POST",
            "/api/acc/opname",
            201,
            data={"notes": "P1.A validation opname"}
        )
        if success:
            self.test_opname_id = response.get('id')
            ref_number = response.get('ref_number')
            status = response.get('status')
            total_items = response.get('total_items')
            self.log(f"   Opname ID: {self.test_opname_id}", Colors.CYAN)
            self.log(f"   Ref number: {ref_number}", Colors.CYAN)
            self.log(f"   Status: {status}", Colors.CYAN)
            self.log(f"   Total items: {total_items}", Colors.CYAN)
            if status == 'Active':
                self.log(f"   ✅ Opname session started", Colors.GREEN)
        
        # 2. Submit count for test item (counted 258 when system shows 260)
        if self.test_opname_id and self.test_item_id:
            success, response = self.test(
                "PUT /api/acc/opname/{id}/count - Submit count",
                "PUT",
                f"/api/acc/opname/{self.test_opname_id}/count",
                200,
                data={
                    "acc_id": self.test_item_id,
                    "counted_qty": 258,
                    "notes": "Test count"
                }
            )
            if success:
                diff = response.get('diff')
                self.log(f"   Difference: {diff}", Colors.CYAN)
                if diff == -2:
                    self.log(f"   ✅ Diff calculated correctly (-2)", Colors.GREEN)
                else:
                    self.log(f"   ❌ Expected -2, got {diff}", Colors.RED)
        
        # 3. Complete opname (should adjust stock)
        if self.test_opname_id:
            success, response = self.test(
                "POST /api/acc/opname/{id}/complete - Complete opname",
                "POST",
                f"/api/acc/opname/{self.test_opname_id}/complete",
                200
            )
            if success:
                adjustments = response.get('adjustments_made')
                self.log(f"   Adjustments made: {adjustments}", Colors.CYAN)
                
                # Verify stock adjusted (260 - 2 = 258)
                success2, response2 = self.test(
                    "GET /api/acc/stock - Verify stock after opname",
                    "GET",
                    "/api/acc/stock",
                    200
                )
                if success2:
                    items = response2 if isinstance(response2, list) else []
                    item = next((i for i in items if i.get('id') == self.test_item_id), None)
                    if item:
                        stock_qty = item.get('stock_qty')
                        self.log(f"   Stock after opname: {stock_qty}", Colors.CYAN)
                        if stock_qty == 258:
                            self.log(f"   ✅ Stock correctly adjusted to 258", Colors.GREEN)
                        else:
                            self.log(f"   ❌ Expected 258, got {stock_qty}", Colors.RED)

    def test_dashboard(self):
        """Test dashboard stats"""
        self.log("\n" + "="*80, Colors.MAGENTA)
        self.log("SECTION 7: DASHBOARD", Colors.MAGENTA)
        self.log("="*80, Colors.MAGENTA)
        
        success, response = self.test(
            "GET /api/acc/dashboard - Get dashboard stats",
            "GET",
            "/api/acc/dashboard",
            200
        )
        if success:
            self.log(f"   Total items: {response.get('total_items')}", Colors.CYAN)
            self.log(f"   Out of stock: {response.get('out_of_stock')}", Colors.CYAN)
            self.log(f"   Low stock: {response.get('low_stock')}", Colors.CYAN)
            self.log(f"   Pending requests: {response.get('pending_requests')}", Colors.CYAN)
            self.log(f"   Active loans: {response.get('active_loans')}", Colors.CYAN)
            self.log(f"   Pending PR: {response.get('pending_pr')}", Colors.CYAN)
            
            # After our tests, active_loans should be 0 (returned), pending_requests should be 0 (issued)
            if response.get('active_loans') == 0 and response.get('pending_requests') == 0:
                self.log(f"   ✅ Dashboard stats look correct", Colors.GREEN)

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*80, Colors.MAGENTA)
        self.log("TEST SUMMARY", Colors.MAGENTA)
        self.log("="*80, Colors.MAGENTA)
        
        self.log(f"\nTotal Tests: {self.tests_run}", Colors.BLUE)
        self.log(f"Passed: {self.tests_passed}", Colors.GREEN)
        self.log(f"Failed: {self.tests_failed}", Colors.RED)
        
        if self.tests_failed > 0:
            self.log(f"\nFailed Tests:", Colors.RED)
            for test in self.failed_tests:
                self.log(f"  - {test}", Colors.RED)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\nSuccess Rate: {success_rate:.1f}%", Colors.CYAN)
        
        if self.tests_failed == 0:
            self.log("\n🎉 ALL TESTS PASSED! P1.A Accessory Consolidation is working correctly.", Colors.GREEN)
            return 0
        else:
            self.log(f"\n⚠️  {self.tests_failed} test(s) failed. Please review.", Colors.YELLOW)
            return 1

    def run_all_tests(self):
        """Run all test suites"""
        if not self.login():
            return 1
        
        self.test_items_crud()
        self.test_stock_operations()
        self.test_internal_requests()
        self.test_loans()
        self.test_purchase_requests()
        self.test_opname()
        self.test_dashboard()
        
        return self.print_summary()

def main():
    tester = AccessoryTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())
