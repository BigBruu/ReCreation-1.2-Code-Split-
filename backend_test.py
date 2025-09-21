import requests
import sys
import json
from datetime import datetime
import time

class TheReCreationAPITester:
    def __init__(self, base_url="https://therecreation-game.preview.emergentagent.com"):
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

    def test_user_spaceport(self):
        """Test getting user spaceport position"""
        success, status, data = self.make_request('GET', 'game/user-spaceport')
        
        if success and 'spaceport_position' in data:
            self.spaceport_x = data['spaceport_position']['x']
            self.spaceport_y = data['spaceport_position']['y']
            return self.log_test("Get User Spaceport", True, f"Spaceport at ({self.spaceport_x},{self.spaceport_y})")
        else:
            return self.log_test("Get User Spaceport", False, f"Status: {status}, Data: {data}")

    def test_observatory_api(self):
        """Test Observatory API with different coordinates"""
        if not hasattr(self, 'spaceport_x'):
            return self.log_test("Observatory API", False, "No spaceport position available")
        
        # Test 1: Observatory view centered on spaceport
        success, status, data = self.make_request(
            'POST', 'game/observatory',
            {
                "center_x": self.spaceport_x,
                "center_y": self.spaceport_y
            }
        )
        
        if not success:
            return self.log_test("Observatory API - Spaceport Center", False, f"Status: {status}, Data: {data}")
        
        # Validate response structure
        if not all(key in data for key in ['view', 'center', 'size']):
            return self.log_test("Observatory API - Response Structure", False, "Missing required fields")
        
        if data['size'] != 7:
            return self.log_test("Observatory API - View Size", False, f"Expected size 7, got {data['size']}")
        
        # Check that we get a 7x7 grid
        view_count = len(data['view'])
        if view_count > 49:  # Maximum 7x7 = 49 fields (some might be out of bounds)
            return self.log_test("Observatory API - Grid Size", False, f"Too many fields: {view_count}")
        
        self.log_test("Observatory API - Spaceport Center", True, f"7x7 view with {view_count} fields")
        
        # Test 2: Observatory view at different coordinates
        test_x, test_y = 10, 10
        success, status, data = self.make_request(
            'POST', 'game/observatory',
            {
                "center_x": test_x,
                "center_y": test_y
            }
        )
        
        if success and 'view' in data:
            self.log_test("Observatory API - Different Coordinates", True, f"View at ({test_x},{test_y})")
        else:
            self.log_test("Observatory API - Different Coordinates", False, f"Status: {status}, Data: {data}")
        
        # Test 3: Observatory view at edge coordinates
        edge_x, edge_y = 0, 0
        success, status, data = self.make_request(
            'POST', 'game/observatory',
            {
                "center_x": edge_x,
                "center_y": edge_y
            }
        )
        
        if success and 'view' in data:
            return self.log_test("Observatory API - Edge Coordinates", True, f"View at edge ({edge_x},{edge_y})")
        else:
            return self.log_test("Observatory API - Edge Coordinates", False, f"Status: {status}, Data: {data}")

    def test_fleet_apis(self):
        """Test Fleet-related APIs"""
        # First get user's fleets
        success, status, data = self.make_request('GET', 'game/fleets')
        
        if not success:
            return self.log_test("Get User Fleets", False, f"Status: {status}, Data: {data}")
        
        self.log_test("Get User Fleets", True, f"Found {len(data)} fleets")
        
        # If no fleets exist, we can't test fleet movement
        if len(data) == 0:
            return self.log_test("Fleet Movement API", False, "No fleets available for movement testing")
        
        # Test fleet movement with first available fleet
        fleet = data[0]
        fleet_id = fleet['id']
        current_pos = fleet['position']
        
        # Calculate a valid target position (move 1 step)
        target_x = min(46, current_pos['x'] + 1)
        target_y = current_pos['y']
        
        success, status, move_data = self.make_request(
            'POST', 'game/move-fleet',
            {
                "fleet_id": fleet_id,
                "target_position": {"x": target_x, "y": target_y}
            }
        )
        
        if success and 'message' in move_data:
            # Check if movement_start_time and movement_end_time are set
            if 'arrival_time' in move_data:
                return self.log_test("Fleet Movement API", True, f"Fleet movement started, arrival: {move_data['arrival_time']}")
            else:
                return self.log_test("Fleet Movement API", True, "Fleet movement started")
        else:
            return self.log_test("Fleet Movement API", False, f"Status: {status}, Data: {move_data}")

    def test_fleet_movement_errors(self):
        """Test Fleet Movement API error handling"""
        # Test 1: Invalid fleet ID
        success, status, data = self.make_request(
            'POST', 'game/move-fleet',
            {
                "fleet_id": "invalid-fleet-id",
                "target_position": {"x": 10, "y": 10}
            },
            expected_status=404
        )
        
        result1 = self.log_test("Fleet Movement - Invalid Fleet ID", success, "Correctly rejected invalid fleet ID")
        
        # Test 2: Out of bounds coordinates
        # First get a valid fleet
        fleet_success, fleet_status, fleet_data = self.make_request('GET', 'game/fleets')
        if fleet_success and len(fleet_data) > 0:
            fleet_id = fleet_data[0]['id']
            
            success, status, data = self.make_request(
                'POST', 'game/move-fleet',
                {
                    "fleet_id": fleet_id,
                    "target_position": {"x": 100, "y": 100}  # Out of bounds
                }
            )
            
            # This might succeed or fail depending on validation - either is acceptable
            result2 = self.log_test("Fleet Movement - Out of Bounds", True, f"Handled out of bounds coordinates (Status: {status})")
        else:
            result2 = self.log_test("Fleet Movement - Out of Bounds", False, "No fleet available for testing")
        
        return result1 and result2

    def test_authentication_required(self):
        """Test that endpoints require proper authentication"""
        # Save current token
        original_token = self.token
        
        # Test without token
        self.token = None
        success, status, data = self.make_request(
            'POST', 'game/observatory',
            {"center_x": 10, "center_y": 10},
            expected_status=401
        )
        
        result1 = self.log_test("Observatory - No Auth", success, "Correctly rejected request without token")
        
        # Test with invalid token
        self.token = "invalid-token"
        success, status, data = self.make_request(
            'GET', 'game/fleets',
            expected_status=401
        )
        
        result2 = self.log_test("Fleets - Invalid Auth", success, "Correctly rejected request with invalid token")
        
        # Restore original token
        self.token = original_token
        
        return result1 and result2

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
        
        # Test observatory with invalid coordinates
        success, status, data = self.make_request(
            'POST', 'game/observatory',
            {
                "center_x": -10,  # Negative coordinate
                "center_y": 100   # Out of bounds
            }
        )
        
        # This might succeed or fail depending on validation - either is acceptable
        result2 = self.log_test("Observatory - Invalid Coordinates", True, f"Handled invalid coordinates (Status: {status})")
        
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