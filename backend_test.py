import requests
import sys
import json
from datetime import datetime
import time

class TheReCreationAPITester:
    def __init__(self, base_url="https://recreation.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_username = f"testuser_{int(time.time())}"
        self.test_email = f"test_{int(time.time())}@example.com"
        self.test_password = "TestPass123!"

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def make_request(self, method, endpoint, data=None, expected_status=200):
        """Make API request with proper headers"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            result_data = {}
            
            try:
                result_data = response.json()
            except:
                result_data = {"text": response.text}

            return success, response.status_code, result_data

        except Exception as e:
            return False, 0, {"error": str(e)}

    def test_user_registration(self):
        """Test user registration"""
        success, status, data = self.make_request(
            'POST', 'register', 
            {
                "username": self.test_username,
                "email": self.test_email,
                "password": self.test_password
            },
            expected_status=200
        )
        
        if success and 'access_token' in data:
            self.token = data['access_token']
            return self.log_test("User Registration", True, f"Token received")
        else:
            return self.log_test("User Registration", False, f"Status: {status}, Data: {data}")

    def test_user_login(self):
        """Test user login with existing credentials"""
        success, status, data = self.make_request(
            'POST', 'login',
            {
                "username": self.test_username,
                "password": self.test_password
            },
            expected_status=200
        )
        
        if success and 'access_token' in data:
            self.token = data['access_token']
            return self.log_test("User Login", True, f"Login successful")
        else:
            return self.log_test("User Login", False, f"Status: {status}, Data: {data}")

    def test_get_user_profile(self):
        """Test getting current user profile"""
        success, status, data = self.make_request('GET', 'me')
        
        if success and 'username' in data:
            self.user_id = data.get('id')
            return self.log_test("Get User Profile", True, f"User: {data['username']}")
        else:
            return self.log_test("Get User Profile", False, f"Status: {status}, Data: {data}")

    def test_game_state(self):
        """Test getting game state"""
        success, status, data = self.make_request('GET', 'game/state')
        
        if success and 'current_tick' in data:
            return self.log_test("Game State", True, f"Tick: {data['current_tick']}")
        else:
            return self.log_test("Game State", False, f"Status: {status}, Data: {data}")

    def test_game_field(self):
        """Test getting game field"""
        success, status, data = self.make_request('GET', 'game/field')
        
        if success and 'field' in data and 'size' in data:
            field_size = data['size']
            field_count = len(data['field'])
            expected_count = field_size * field_size
            if field_count == expected_count:
                return self.log_test("Game Field", True, f"47x47 field with {field_count} positions")
            else:
                return self.log_test("Game Field", False, f"Expected {expected_count} positions, got {field_count}")
        else:
            return self.log_test("Game Field", False, f"Status: {status}, Data: {data}")

    def test_create_colony(self):
        """Test creating a colony"""
        import random
        # Use random position to avoid conflicts
        x, y = random.randint(0, 46), random.randint(0, 46)
        success, status, data = self.make_request(
            'POST', 'game/colony',
            {
                "position": {"x": x, "y": y},
                "name": "Test Colony"
            },
            expected_status=200
        )
        
        if success and 'id' in data:
            self.colony_id = data['id']
            return self.log_test("Create Colony", True, f"Colony created at ({x},{y})")
        else:
            return self.log_test("Create Colony", False, f"Status: {status}, Data: {data}")

    def test_get_colonies(self):
        """Test getting user's colonies"""
        success, status, data = self.make_request('GET', 'game/colonies')
        
        if success and isinstance(data, list):
            return self.log_test("Get Colonies", True, f"Found {len(data)} colonies")
        else:
            return self.log_test("Get Colonies", False, f"Status: {status}, Data: {data}")

    def test_create_ship(self):
        """Test creating a ship"""
        if not hasattr(self, 'colony_id'):
            return self.log_test("Create Ship", False, "No colony available for ship creation")
        
        # Process enough ticks to generate resources (scout needs 100 metal, 50 silicon)
        print("   Processing ticks to generate resources...")
        for i in range(25):  # 25 ticks * 5 resources = 125 of each resource
            self.make_request('POST', 'game/tick', {})
            if i % 5 == 0:
                print(f"   Processed {i+1} ticks...")
        
        success, status, data = self.make_request(
            'POST', 'game/ship',
            {
                "colony_id": self.colony_id,
                "ship_type": "scout",
                "name": "Test Scout"
            },
            expected_status=200
        )
        
        if success and 'id' in data:
            self.ship_id = data['id']
            return self.log_test("Create Ship", True, f"Scout ship created")
        else:
            return self.log_test("Create Ship", False, f"Status: {status}, Data: {data}")

    def test_get_ships(self):
        """Test getting user's ships"""
        success, status, data = self.make_request('GET', 'game/ships')
        
        if success and isinstance(data, list):
            return self.log_test("Get Ships", True, f"Found {len(data)} ships")
        else:
            return self.log_test("Get Ships", False, f"Status: {status}, Data: {data}")

    def test_move_ship(self):
        """Test moving a ship"""
        if not hasattr(self, 'ship_id'):
            return self.log_test("Move Ship", False, "No ship available for movement")
        
        success, status, data = self.make_request(
            'POST', 'game/move',
            {
                "ship_id": self.ship_id,
                "target_position": {"x": 11, "y": 10}
            },
            expected_status=200
        )
        
        if success:
            return self.log_test("Move Ship", True, f"Ship moved to (11,10)")
        else:
            return self.log_test("Move Ship", False, f"Status: {status}, Data: {data}")

    def test_process_tick(self):
        """Test processing game tick"""
        success, status, data = self.make_request('POST', 'game/tick', {})
        
        if success:
            return self.log_test("Process Tick", True, "Tick processed successfully")
        else:
            return self.log_test("Process Tick", False, f"Status: {status}, Data: {data}")

    def test_rankings(self):
        """Test getting rankings"""
        success, status, data = self.make_request('GET', 'game/rankings')
        
        if success and isinstance(data, list):
            return self.log_test("Get Rankings", True, f"Found {len(data)} players in rankings")
        else:
            return self.log_test("Get Rankings", False, f"Status: {status}, Data: {data}")

    def test_invalid_endpoints(self):
        """Test some invalid scenarios"""
        # Test invalid login
        success, status, data = self.make_request(
            'POST', 'login',
            {"username": "invalid", "password": "invalid"},
            expected_status=401
        )
        
        result1 = self.log_test("Invalid Login", success, "Correctly rejected invalid credentials")
        
        # Test creating colony at occupied position
        success, status, data = self.make_request(
            'POST', 'game/colony',
            {
                "position": {"x": 10, "y": 10},  # Same position as before
                "name": "Duplicate Colony"
            },
            expected_status=400
        )
        
        result2 = self.log_test("Duplicate Colony", success, "Correctly rejected duplicate position")
        
        return result1 and result2

def main():
    print("🚀 Starting TheReCreation API Tests")
    print("=" * 50)
    
    tester = TheReCreationAPITester()
    
    # Run authentication tests
    print("\n📝 Authentication Tests:")
    if not tester.test_user_registration():
        print("❌ Registration failed, stopping tests")
        return 1
    
    if not tester.test_user_login():
        print("❌ Login failed, stopping tests")
        return 1
    
    if not tester.test_get_user_profile():
        print("❌ Profile fetch failed, stopping tests")
        return 1
    
    # Run game state tests
    print("\n🎮 Game State Tests:")
    tester.test_game_state()
    tester.test_game_field()
    tester.test_rankings()
    
    # Run game mechanics tests
    print("\n🏗️ Game Mechanics Tests:")
    if tester.test_create_colony():
        tester.test_get_colonies()
        
        if tester.test_create_ship():
            tester.test_get_ships()
            tester.test_move_ship()
    
    tester.test_process_tick()
    
    # Run error handling tests
    print("\n🔍 Error Handling Tests:")
    tester.test_invalid_endpoints()
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())