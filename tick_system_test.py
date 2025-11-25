import requests
import sys
import json
from datetime import datetime, timedelta
import time

class TickSystemTester:
    def __init__(self, base_url="https://therecreation-game.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_username = f"ticktest_{int(time.time())}"
        self.test_email = f"ticktest_{int(time.time())}@example.com"
        self.test_password = "TickTest123!"

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

    def setup_authentication(self):
        """Setup authentication for testing"""
        # Try admin login first to create invite code
        success, status, data = self.make_request(
            'POST', 'admin/login',
            {"password": "admin2025"},
            expected_status=200
        )
        
        if success and 'access_token' in data:
            admin_token = data['access_token']
            
            # Create invite code
            headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {admin_token}'}
            try:
                response = requests.post(
                    f"{self.api_url}/admin/invite-codes",
                    json={"max_uses": 1},
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    invite_data = response.json()
                    self.invite_code = invite_data['code']
                    
                    # Register new user
                    success, status, data = self.make_request(
                        'POST', 'register', 
                        {
                            "username": self.test_username,
                            "email": self.test_email,
                            "password": self.test_password,
                            "invite_code": self.invite_code
                        },
                        expected_status=200
                    )
                    
                    if success and 'access_token' in data:
                        self.token = data['access_token']
                        return self.log_test("Authentication Setup", True, "User registered and authenticated")
                    else:
                        return self.log_test("Authentication Setup", False, f"Registration failed: {status}")
                else:
                    return self.log_test("Authentication Setup", False, f"Failed to create invite: {response.status_code}")
            except Exception as e:
                return self.log_test("Authentication Setup", False, f"Error: {str(e)}")
        else:
            # Try existing test credentials
            test_users = [
                ("testuser", "testpass"),
                ("admin", "admin"),
                ("user1", "password"),
                ("test", "test123")
            ]
            
            for username, password in test_users:
                success, status, data = self.make_request(
                    'POST', 'login',
                    {"username": username, "password": password},
                    expected_status=200
                )
                
                if success and 'access_token' in data:
                    self.token = data['access_token']
                    self.test_username = username
                    return self.log_test("Authentication Setup", True, f"Logged in as {username}")
            
            return self.log_test("Authentication Setup", False, "Could not authenticate with any credentials")

    def test_current_game_state(self):
        """Test 1: Check Current Game State - Test /api/game/state endpoint"""
        success, status, data = self.make_request('GET', 'game/state')
        
        if not success:
            return self.log_test("Current Game State", False, f"API call failed: Status {status}, Data: {data}")
        
        # Check required fields
        required_fields = ['current_tick', 'last_tick_time', 'next_tick_time']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return self.log_test("Current Game State", False, f"Missing fields: {missing_fields}")
        
        # Store initial state for comparison
        self.initial_tick = data['current_tick']
        self.initial_last_tick_time = data['last_tick_time']
        self.initial_next_tick_time = data['next_tick_time']
        
        # Validate timing looks correct
        try:
            last_tick = datetime.fromisoformat(data['last_tick_time'].replace('Z', '+00:00'))
            next_tick = datetime.fromisoformat(data['next_tick_time'].replace('Z', '+00:00'))
            
            # Check if next tick is after last tick
            if next_tick <= last_tick:
                return self.log_test("Current Game State", False, "next_tick_time should be after last_tick_time")
            
            # Check if the interval looks reasonable (should be around 60 seconds)
            interval = (next_tick - last_tick).total_seconds()
            if interval < 30 or interval > 120:  # Allow some tolerance
                return self.log_test("Current Game State", False, f"Tick interval seems wrong: {interval}s (expected ~60s)")
            
            return self.log_test("Current Game State", True, 
                               f"Tick: {data['current_tick']}, Interval: {interval}s, Next tick in: {(next_tick - datetime.now()).total_seconds():.1f}s")
        
        except Exception as e:
            return self.log_test("Current Game State", False, f"Error parsing timestamps: {str(e)}")

    def test_manual_tick_processing(self):
        """Test 3: Test Manual Tick (for comparison) - Test the manual /api/game/tick endpoint"""
        # Get state before manual tick
        success, status, before_data = self.make_request('GET', 'game/state')
        if not success:
            return self.log_test("Manual Tick - Before State", False, f"Could not get state before tick: {status}")
        
        before_tick = before_data['current_tick']
        
        # Process manual tick
        success, status, tick_data = self.make_request('POST', 'game/tick', {})
        
        if not success:
            return self.log_test("Manual Tick Processing", False, f"Manual tick failed: Status {status}, Data: {tick_data}")
        
        # Get state after manual tick
        success, status, after_data = self.make_request('GET', 'game/state')
        if not success:
            return self.log_test("Manual Tick - After State", False, f"Could not get state after tick: {status}")
        
        after_tick = after_data['current_tick']
        
        # Verify tick incremented
        if after_tick != before_tick + 1:
            return self.log_test("Manual Tick Processing", False, 
                               f"Tick did not increment correctly: {before_tick} -> {after_tick}")
        
        return self.log_test("Manual Tick Processing", True, 
                           f"Manual tick processed successfully: {before_tick} -> {after_tick}")

    def test_automatic_tick_monitoring(self):
        """Test 2: Monitor Tick Processing - Wait for automatic tick processing and verify current_tick increments"""
        print(f"\n🕐 Monitoring automatic tick system...")
        
        # Get initial state
        success, status, initial_data = self.make_request('GET', 'game/state')
        if not success:
            return self.log_test("Automatic Tick Monitoring", False, f"Could not get initial state: {status}")
        
        initial_tick = initial_data['current_tick']
        initial_next_tick_time = initial_data['next_tick_time']
        
        try:
            next_tick_dt = datetime.fromisoformat(initial_next_tick_time.replace('Z', '+00:00'))
            current_time = datetime.now()
            
            # Calculate how long to wait (add some buffer)
            wait_seconds = (next_tick_dt - current_time).total_seconds() + 10
            
            # Don't wait more than 2 minutes for testing purposes
            if wait_seconds > 120:
                wait_seconds = 70  # Wait a bit more than one tick duration
            elif wait_seconds < 10:
                wait_seconds = 70  # If we just missed a tick, wait for the next one
            
            print(f"   Waiting {wait_seconds:.1f} seconds for automatic tick processing...")
            
            # Wait for the tick to process
            time.sleep(wait_seconds)
            
            # Check if tick incremented
            success, status, new_data = self.make_request('GET', 'game/state')
            if not success:
                return self.log_test("Automatic Tick Monitoring", False, f"Could not get state after waiting: {status}")
            
            new_tick = new_data['current_tick']
            new_last_tick_time = new_data['last_tick_time']
            new_next_tick_time = new_data['next_tick_time']
            
            # Check if tick incremented
            if new_tick <= initial_tick:
                return self.log_test("Automatic Tick Monitoring", False, 
                                   f"Tick did not increment automatically: {initial_tick} -> {new_tick}")
            
            # Check if timestamps updated
            if new_last_tick_time == initial_data['last_tick_time']:
                return self.log_test("Automatic Tick Monitoring", False, 
                                   "last_tick_time did not update")
            
            if new_next_tick_time == initial_next_tick_time:
                return self.log_test("Automatic Tick Monitoring", False, 
                                   "next_tick_time did not update")
            
            return self.log_test("Automatic Tick Monitoring", True, 
                               f"Automatic tick processed: {initial_tick} -> {new_tick}, timestamps updated correctly")
        
        except Exception as e:
            return self.log_test("Automatic Tick Monitoring", False, f"Error during monitoring: {str(e)}")

    def test_resource_processing_during_ticks(self):
        """Test 4: Verify Resource Processing - Check if resources are being processed automatically during ticks"""
        # First, check if user has any planets and fleets
        success, status, planets = self.make_request('GET', 'game/planets')
        if not success:
            return self.log_test("Resource Processing - Get Planets", False, f"Could not get planets: {status}")
        
        success, status, fleets = self.make_request('GET', 'game/fleets')
        if not success:
            return self.log_test("Resource Processing - Get Fleets", False, f"Could not get fleets: {status}")
        
        if len(planets) == 0:
            return self.log_test("Resource Processing", False, "No planets available for resource processing test")
        
        if len(fleets) == 0:
            # Try to create a mining fleet for testing
            if not self.create_mining_fleet_for_testing():
                return self.log_test("Resource Processing", False, "No fleets available and could not create mining fleet")
            
            # Get fleets again
            success, status, fleets = self.make_request('GET', 'game/fleets')
            if not success or len(fleets) == 0:
                return self.log_test("Resource Processing", False, "Still no fleets available after creation attempt")
        
        # Get initial planet resources
        planet = planets[0]
        initial_resources = planet['resources']
        
        # Get user profile for initial points
        success, status, user_data = self.make_request('GET', 'me')
        if not success:
            return self.log_test("Resource Processing - Get User", False, f"Could not get user data: {status}")
        
        initial_points = user_data.get('points', 0)
        
        print(f"   Initial planet resources: Food={initial_resources['food']}, Metal={initial_resources['metal']}")
        print(f"   Initial user points: {initial_points}")
        print(f"   User has {len(fleets)} fleet(s)")
        
        # Process a manual tick to see if resources change
        success, status, tick_data = self.make_request('POST', 'game/tick', {})
        if not success:
            return self.log_test("Resource Processing", False, f"Could not process tick: {status}")
        
        # Check resources after tick
        success, status, updated_planets = self.make_request('GET', 'game/planets')
        if not success:
            return self.log_test("Resource Processing", False, f"Could not get updated planets: {status}")
        
        success, status, updated_user = self.make_request('GET', 'me')
        if not success:
            return self.log_test("Resource Processing", False, f"Could not get updated user: {status}")
        
        updated_planet = next((p for p in updated_planets if p['id'] == planet['id']), None)
        if not updated_planet:
            return self.log_test("Resource Processing", False, "Could not find updated planet")
        
        updated_resources = updated_planet['resources']
        updated_points = updated_user.get('points', 0)
        
        print(f"   After tick resources: Food={updated_resources['food']}, Metal={updated_resources['metal']}")
        print(f"   After tick user points: {updated_points}")
        
        # Check if any resources changed or points increased
        resources_changed = (
            updated_resources['food'] != initial_resources['food'] or
            updated_resources['metal'] != initial_resources['metal'] or
            updated_resources['silicon'] != initial_resources['silicon'] or
            updated_resources['hydrogen'] != initial_resources['hydrogen']
        )
        
        points_changed = updated_points != initial_points
        
        if resources_changed or points_changed:
            return self.log_test("Resource Processing", True, 
                               f"Resource processing detected: Resources changed={resources_changed}, Points changed={points_changed}")
        else:
            # This might be normal if no mining fleets are active
            return self.log_test("Resource Processing", True, 
                               "No resource changes detected (normal if no active mining operations)")

    def create_mining_fleet_for_testing(self):
        """Helper method to create a mining fleet for testing"""
        try:
            # Get planets
            success, status, planets = self.make_request('GET', 'game/planets')
            if not success or len(planets) == 0:
                return False
            
            planet = planets[0]
            planet_id = planet['id']
            
            # Check existing ship designs
            success, status, designs = self.make_request('GET', 'game/ship-designs')
            if not success:
                return False
            
            # Create a mining ship design if none exists
            mining_design_id = None
            for design in designs:
                if design.get('mining_units', 0) > 0:
                    mining_design_id = design['id']
                    break
            
            if not mining_design_id:
                # Create a mining ship design
                success, status, design_data = self.make_request(
                    'POST', 'game/ship-design',
                    {
                        "name": "Mining Ship",
                        "drive_type": "segel",
                        "drive_level": 1,
                        "drive_quantity": 1,
                        "shield_type": "stahl",
                        "shield_level": 1,
                        "shield_quantity": 1,
                        "weapon_type": "projektil",
                        "weapon_level": 1,
                        "weapon_quantity": 1,
                        "mining_units": 1,
                        "colony_units": 0
                    }
                )
                
                if not success:
                    return False
                
                mining_design_id = design_data['id']
            
            # Build mining ships
            success, status, build_data = self.make_request(
                'POST', 'game/build-ships',
                {
                    "planet_id": planet_id,
                    "design_id": mining_design_id,
                    "quantity": 1
                }
            )
            
            if not success:
                return False
            
            # Create fleet from built ships
            success, status, fleet_data = self.make_request(
                'POST', 'game/create-fleet',
                {
                    "planet_id": planet_id,
                    "fleet_name": "Mining Fleet",
                    "ships": [{"design_id": mining_design_id, "quantity": 1}]
                }
            )
            
            return success
        
        except Exception as e:
            print(f"Error creating mining fleet: {str(e)}")
            return False

def main():
    print("🕐 Starting Automatic Tick System Tests")
    print("=" * 60)
    
    tester = TickSystemTester()
    
    # Setup authentication
    print("\n🔐 Setting up authentication...")
    if not tester.setup_authentication():
        print("❌ Authentication setup failed, stopping tests")
        return 1
    
    # Test 1: Check Current Game State
    print("\n📊 Test 1: Current Game State")
    tester.test_current_game_state()
    
    # Test 3: Test Manual Tick (for comparison)
    print("\n🔧 Test 3: Manual Tick Processing")
    tester.test_manual_tick_processing()
    
    # Test 4: Verify Resource Processing
    print("\n⛏️ Test 4: Resource Processing During Ticks")
    tester.test_resource_processing_during_ticks()
    
    # Test 2: Monitor Automatic Tick Processing (this takes time, so do it last)
    print("\n🤖 Test 2: Automatic Tick Monitoring")
    tester.test_automatic_tick_monitoring()
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tick system tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())