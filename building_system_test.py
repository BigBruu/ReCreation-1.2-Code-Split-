import requests
import sys
import json
from datetime import datetime
import time

class BuildingSystemTester:
    def __init__(self, base_url="https://spacewars.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        # Use the credentials from the review request
        self.test_username = "TestUser1"
        self.test_password = "password123"

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

    def test_user_login(self):
        """Test user login with provided credentials"""
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
            return self.log_test("User Login", True, f"Login successful for {self.test_username}")
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

    def test_get_buildings_list(self):
        """Test GET /api/game/buildings - List all buildings with levels"""
        success, status, data = self.make_request('GET', 'game/buildings')
        
        if not success:
            return self.log_test("GET Buildings List", False, f"Status: {status}, Data: {data}")
        
        if not isinstance(data, list):
            return self.log_test("GET Buildings List", False, "Response is not a list")
        
        # Check expected buildings exist
        expected_buildings = {
            'plantage': {'category': 'resource', 'base_cost': 500},
            'erzmine': {'category': 'resource', 'base_cost': 500},
            'elektrolysator': {'category': 'resource', 'base_cost': 500},
            'werft': {'category': 'special', 'base_cost': 5000},
            'raumhafen': {'category': 'special', 'base_cost': 10000},
            'forschungslabor': {'category': 'special', 'base_cost': 15000}
        }
        
        found_buildings = {}
        for building in data:
            building_type = building.get('building_type')
            if building_type in expected_buildings:
                found_buildings[building_type] = building
        
        # Verify all expected buildings are present
        missing_buildings = set(expected_buildings.keys()) - set(found_buildings.keys())
        if missing_buildings:
            return self.log_test("GET Buildings List", False, f"Missing buildings: {missing_buildings}")
        
        # Verify building structure and costs
        for building_type, expected in expected_buildings.items():
            building = found_buildings[building_type]
            
            # Check required fields
            required_fields = ['building_type', 'name', 'level', 'category', 'upgrade_cost_metal']
            missing_fields = [field for field in required_fields if field not in building]
            if missing_fields:
                return self.log_test("GET Buildings List", False, f"Building {building_type} missing fields: {missing_fields}")
            
            # Check category
            if building['category'] != expected['category']:
                return self.log_test("GET Buildings List", False, f"Building {building_type} wrong category: {building['category']} != {expected['category']}")
            
            # Check base cost (for level 0 buildings)
            if building['level'] == 0 and building['upgrade_cost_metal'] != expected['base_cost']:
                return self.log_test("GET Buildings List", False, f"Building {building_type} wrong base cost: {building['upgrade_cost_metal']} != {expected['base_cost']}")
        
        self.buildings_data = found_buildings
        return self.log_test("GET Buildings List", True, f"Found all {len(expected_buildings)} expected buildings")

    def test_cost_calculation(self):
        """Test cost calculation: Base cost + 5% per level for resource buildings"""
        if not hasattr(self, 'buildings_data'):
            return self.log_test("Cost Calculation", False, "No buildings data available")
        
        resource_buildings = ['plantage', 'erzmine', 'elektrolysator']
        
        for building_type in resource_buildings:
            building = self.buildings_data[building_type]
            current_level = building['level']
            current_cost = building['upgrade_cost_metal']
            
            # Calculate expected cost: base_cost * (1.05)^level
            base_cost = 500
            expected_cost = int(base_cost * (1.05 ** current_level))
            
            if current_cost != expected_cost:
                return self.log_test("Cost Calculation", False, 
                    f"Building {building_type} level {current_level}: expected cost {expected_cost}, got {current_cost}")
        
        return self.log_test("Cost Calculation", True, "Resource building costs calculated correctly")

    def test_upgrade_building_werft(self):
        """Test POST /api/game/buildings/upgrade - Test upgrade function for werft"""
        if not hasattr(self, 'buildings_data'):
            return self.log_test("Upgrade Werft", False, "No buildings data available")
        
        # Get current werft level
        werft = self.buildings_data['werft']
        initial_level = werft['level']
        upgrade_cost = werft['upgrade_cost_metal']
        
        # First, check if user has enough metal resources
        success, status, planets = self.make_request('GET', 'game/planets')
        if not success:
            return self.log_test("Upgrade Werft - Get Planets", False, f"Could not get planets: {status}")
        
        total_metal = sum(planet['resources']['metal'] for planet in planets)
        
        if total_metal < upgrade_cost:
            return self.log_test("Upgrade Werft", False, 
                f"Insufficient metal for upgrade. Need {upgrade_cost}, have {total_metal}")
        
        # Attempt to upgrade werft
        success, status, data = self.make_request(
            'POST', 'game/buildings/upgrade',
            {"building_type": "werft"}
        )
        
        if not success:
            return self.log_test("Upgrade Werft", False, f"Upgrade failed: Status {status}, Data: {data}")
        
        # Verify the upgrade started
        success, status, updated_buildings = self.make_request('GET', 'game/buildings')
        if not success:
            return self.log_test("Upgrade Werft - Verify", False, "Could not get updated buildings")
        
        updated_werft = None
        for building in updated_buildings:
            if building['building_type'] == 'werft':
                updated_werft = building
                break
        
        if not updated_werft:
            return self.log_test("Upgrade Werft - Verify", False, "Werft not found in updated buildings")
        
        # Check if upgrade is in progress
        if not updated_werft.get('upgrading', False):
            return self.log_test("Upgrade Werft - Verify", False, "Werft not marked as upgrading")
        
        return self.log_test("Upgrade Werft", True, f"Werft upgrade started from level {initial_level}")

    def test_single_building_upgrade_limit(self):
        """Test that only one building can be upgraded at a time"""
        # Try to upgrade another building while werft is upgrading
        success, status, data = self.make_request(
            'POST', 'game/buildings/upgrade',
            {"building_type": "plantage"},
            expected_status=400
        )
        
        if success:
            return self.log_test("Single Building Upgrade Limit", True, "Correctly rejected second upgrade")
        else:
            return self.log_test("Single Building Upgrade Limit", False, 
                f"Should have rejected second upgrade but got status {status}")

    def test_prototype_limit_without_werft(self):
        """Test prototype limit: Try to create ship design without werft level (should fail)"""
        # First check current werft level
        success, status, buildings = self.make_request('GET', 'game/buildings')
        if not success:
            return self.log_test("Prototype Limit Test", False, "Could not get buildings")
        
        werft_level = 0
        for building in buildings:
            if building['building_type'] == 'werft':
                werft_level = building['level']
                break
        
        # Count current ship designs
        success, status, designs = self.make_request('GET', 'game/ship-designs')
        if not success:
            return self.log_test("Prototype Limit Test", False, "Could not get ship designs")
        
        current_designs = len(designs)
        max_allowed = werft_level
        
        if current_designs >= max_allowed:
            # Try to create another design (should fail)
            success, status, data = self.make_request(
                'POST', 'game/ship-design',
                {
                    "name": "Test Prototype Limit",
                    "drive_type": "segel",
                    "drive_level": 1,
                    "drive_quantity": 1,
                    "shield_type": "stahl",
                    "shield_level": 1,
                    "shield_quantity": 1,
                    "weapon_type": "projektil",
                    "weapon_level": 1,
                    "weapon_quantity": 1
                },
                expected_status=400
            )
            
            if success:
                return self.log_test("Prototype Limit Test", True, 
                    f"Correctly rejected prototype creation (werft level {werft_level}, designs {current_designs})")
            else:
                return self.log_test("Prototype Limit Test", False, 
                    f"Should have rejected prototype creation but got status {status}")
        else:
            return self.log_test("Prototype Limit Test", True, 
                f"Prototype limit not reached (werft level {werft_level}, designs {current_designs})")

    def test_fleet_limit_without_raumhafen(self):
        """Test fleet limit: Try to create fleet without raumhafen level (should fail)"""
        # First check current raumhafen level
        success, status, buildings = self.make_request('GET', 'game/buildings')
        if not success:
            return self.log_test("Fleet Limit Test", False, "Could not get buildings")
        
        raumhafen_level = 0
        for building in buildings:
            if building['building_type'] == 'raumhafen':
                raumhafen_level = building['level']
                break
        
        # Count current fleets
        success, status, fleets = self.make_request('GET', 'game/fleets')
        if not success:
            return self.log_test("Fleet Limit Test", False, "Could not get fleets")
        
        current_fleets = len(fleets)
        max_allowed = raumhafen_level
        
        if current_fleets >= max_allowed:
            # Try to create another fleet (should fail)
            # First need to get planets and ships
            success, status, planets = self.make_request('GET', 'game/planets')
            if not success or len(planets) == 0:
                return self.log_test("Fleet Limit Test", False, "No planets available")
            
            planet_id = planets[0]['id']
            
            # Check spaceport ships
            success, status, spaceport_ships = self.make_request('GET', 'game/spaceport-ships')
            if not success:
                return self.log_test("Fleet Limit Test", False, "Could not get spaceport ships")
            
            # If no ships available, this test is not applicable
            if not spaceport_ships:
                return self.log_test("Fleet Limit Test", True, 
                    f"No ships available for fleet creation test (raumhafen level {raumhafen_level})")
            
            # Try to create fleet
            success, status, data = self.make_request(
                'POST', 'game/create-fleet',
                {
                    "planet_id": planet_id,
                    "fleet_name": "Test Fleet Limit",
                    "ships": [{"design_id": "dummy", "quantity": 1}]
                },
                expected_status=400
            )
            
            if success:
                return self.log_test("Fleet Limit Test", True, 
                    f"Correctly rejected fleet creation (raumhafen level {raumhafen_level}, fleets {current_fleets})")
            else:
                return self.log_test("Fleet Limit Test", False, 
                    f"Should have rejected fleet creation but got status {status}")
        else:
            return self.log_test("Fleet Limit Test", True, 
                f"Fleet limit not reached (raumhafen level {raumhafen_level}, fleets {current_fleets})")

    def test_resources_no_silicon(self):
        """Test that Silicon was removed - only Food, Metal, Hydrogen"""
        success, status, planets = self.make_request('GET', 'game/planets')
        if not success:
            return self.log_test("Resources Check", False, "Could not get planets")
        
        for planet in planets:
            resources = planet.get('resources', {})
            
            # Check that only expected resources exist
            expected_resources = {'food', 'metal', 'hydrogen'}
            actual_resources = set(resources.keys())
            
            # Check for silicon (should not exist)
            if 'silicon' in actual_resources or 'silizium' in actual_resources:
                return self.log_test("Resources Check", False, 
                    f"Found silicon/silizium in planet resources: {actual_resources}")
            
            # Check that all expected resources exist
            missing_resources = expected_resources - actual_resources
            if missing_resources:
                return self.log_test("Resources Check", False, 
                    f"Missing expected resources: {missing_resources}")
            
            # Check for unexpected resources
            unexpected_resources = actual_resources - expected_resources
            if unexpected_resources:
                return self.log_test("Resources Check", False, 
                    f"Found unexpected resources: {unexpected_resources}")
        
        return self.log_test("Resources Check", True, "Only Food, Metal, Hydrogen found (no Silicon)")

    def test_metal_cost_deduction(self):
        """Test that costs are deducted from Metal resources"""
        # Get initial metal amount
        success, status, planets = self.make_request('GET', 'game/planets')
        if not success:
            return self.log_test("Metal Cost Deduction", False, "Could not get planets")
        
        initial_metal = sum(planet['resources']['metal'] for planet in planets)
        
        # Try a small upgrade if possible (plantage)
        success, status, buildings = self.make_request('GET', 'game/buildings')
        if not success:
            return self.log_test("Metal Cost Deduction", False, "Could not get buildings")
        
        plantage = None
        for building in buildings:
            if building['building_type'] == 'plantage' and not building.get('upgrading', False):
                plantage = building
                break
        
        if not plantage:
            return self.log_test("Metal Cost Deduction", True, "No plantage available for upgrade test")
        
        upgrade_cost = plantage['upgrade_cost_metal']
        
        if initial_metal < upgrade_cost:
            return self.log_test("Metal Cost Deduction", True, 
                f"Insufficient metal for test ({initial_metal} < {upgrade_cost})")
        
        # Attempt upgrade
        success, status, data = self.make_request(
            'POST', 'game/buildings/upgrade',
            {"building_type": "plantage"}
        )
        
        if not success:
            return self.log_test("Metal Cost Deduction", False, f"Upgrade failed: {status}")
        
        # Check metal after upgrade
        success, status, updated_planets = self.make_request('GET', 'game/planets')
        if not success:
            return self.log_test("Metal Cost Deduction", False, "Could not get updated planets")
        
        final_metal = sum(planet['resources']['metal'] for planet in updated_planets)
        expected_metal = initial_metal - upgrade_cost
        
        if final_metal == expected_metal:
            return self.log_test("Metal Cost Deduction", True, 
                f"Metal correctly deducted: {initial_metal} - {upgrade_cost} = {final_metal}")
        else:
            return self.log_test("Metal Cost Deduction", False, 
                f"Metal deduction incorrect: expected {expected_metal}, got {final_metal}")

def main():
    print("🏗️  Starting TheReCreation Building System Tests")
    print("=" * 60)
    
    tester = BuildingSystemTester()
    
    # Authentication
    print("\n📝 Authentication:")
    if not tester.test_user_login():
        print("❌ Login failed, stopping tests")
        return 1
    
    if not tester.test_get_user_profile():
        print("❌ Profile fetch failed, stopping tests")
        return 1
    
    # Building System Tests
    print("\n🏗️  Building System Tests:")
    
    # Test 1: GET /api/game/buildings
    tester.test_get_buildings_list()
    
    # Test 2: Cost calculation
    tester.test_cost_calculation()
    
    # Test 3: Resources check (no silicon)
    tester.test_resources_no_silicon()
    
    # Test 4: Upgrade building
    tester.test_upgrade_building_werft()
    
    # Test 5: Single building upgrade limit
    tester.test_single_building_upgrade_limit()
    
    # Test 6: Metal cost deduction
    tester.test_metal_cost_deduction()
    
    # Test 7: Prototype limit
    tester.test_prototype_limit_without_werft()
    
    # Test 8: Fleet limit
    tester.test_fleet_limit_without_raumhafen()
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Building System Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All building system tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} building system tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())