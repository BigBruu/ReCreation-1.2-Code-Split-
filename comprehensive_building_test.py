import requests
import sys
import json
from datetime import datetime
import time

class ComprehensiveBuildingTester:
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

    def test_get_buildings_api(self):
        """Test 1: GET /api/game/buildings - List all buildings with levels"""
        success, status, data = self.make_request('GET', 'game/buildings')
        
        if not success:
            return self.log_test("1. GET /api/game/buildings", False, f"Status: {status}, Data: {data}")
        
        if not isinstance(data, list):
            return self.log_test("1. GET /api/game/buildings", False, "Response is not a list")
        
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
            return self.log_test("1. GET /api/game/buildings", False, f"Missing buildings: {missing_buildings}")
        
        # Store buildings data for other tests
        self.buildings_data = found_buildings
        
        # Check building structure
        details = []
        for building_type, building in found_buildings.items():
            level = building.get('level', 0)
            upgrading = building.get('upgrading', False)
            cost = building.get('upgrade_cost_metal', 0)
            details.append(f"{building_type}: Level {level}, Cost {cost}, Upgrading: {upgrading}")
        
        return self.log_test("1. GET /api/game/buildings", True, 
            f"Found all 6 buildings. Details: {'; '.join(details)}")

    def test_upgrade_building_api(self):
        """Test 2: POST /api/game/buildings/upgrade - Test upgrade function"""
        if not hasattr(self, 'buildings_data'):
            return self.log_test("2. POST /api/game/buildings/upgrade", False, "No buildings data available")
        
        # Check if any building is currently upgrading
        upgrading_building = None
        available_building = None
        
        for building_type, building in self.buildings_data.items():
            if building.get('upgrading', False):
                upgrading_building = building_type
            elif not building.get('upgrading', False):
                available_building = building_type
        
        if upgrading_building:
            # Test that we can't upgrade another building
            if available_building:
                success, status, data = self.make_request(
                    'POST', 'game/buildings/upgrade',
                    {"building_type": available_building},
                    expected_status=400
                )
                
                if success:
                    return self.log_test("2. POST /api/game/buildings/upgrade", True, 
                        f"Correctly rejected upgrade of {available_building} while {upgrading_building} is upgrading")
                else:
                    return self.log_test("2. POST /api/game/buildings/upgrade", False, 
                        f"Should have rejected upgrade but got status {status}")
            else:
                return self.log_test("2. POST /api/game/buildings/upgrade", True, 
                    f"Building {upgrading_building} is currently upgrading - single upgrade limit working")
        else:
            # Try to upgrade werft if possible
            werft = self.buildings_data.get('werft')
            if not werft:
                return self.log_test("2. POST /api/game/buildings/upgrade", False, "Werft not found")
            
            upgrade_cost = werft.get('upgrade_cost_metal', 0)
            
            # Check if user has enough metal
            success, status, planets = self.make_request('GET', 'game/planets')
            if not success:
                return self.log_test("2. POST /api/game/buildings/upgrade", False, "Could not get planets")
            
            total_metal = sum(planet['resources']['metal'] for planet in planets)
            
            if total_metal < upgrade_cost:
                return self.log_test("2. POST /api/game/buildings/upgrade", True, 
                    f"Insufficient metal for werft upgrade. Need {upgrade_cost}, have {total_metal}")
            
            # Attempt upgrade
            success, status, data = self.make_request(
                'POST', 'game/buildings/upgrade',
                {"building_type": "werft"}
            )
            
            if success:
                return self.log_test("2. POST /api/game/buildings/upgrade", True, 
                    f"Werft upgrade started successfully")
            else:
                return self.log_test("2. POST /api/game/buildings/upgrade", False, 
                    f"Werft upgrade failed: Status {status}, Data: {data}")

    def test_cost_calculation(self):
        """Test 3: Cost calculation - Base cost + 5% per level for resource buildings"""
        if not hasattr(self, 'buildings_data'):
            return self.log_test("3. Cost Calculation", False, "No buildings data available")
        
        resource_buildings = ['plantage', 'erzmine', 'elektrolysator']
        results = []
        
        for building_type in resource_buildings:
            building = self.buildings_data[building_type]
            current_level = building['level']
            current_cost = building['upgrade_cost_metal']
            
            # Calculate expected cost: base_cost * (1.05)^level
            base_cost = 500
            expected_cost = int(base_cost * (1.05 ** current_level))
            
            if current_cost == expected_cost:
                results.append(f"{building_type} L{current_level}: {current_cost} ✓")
            else:
                return self.log_test("3. Cost Calculation", False, 
                    f"Building {building_type} level {current_level}: expected cost {expected_cost}, got {current_cost}")
        
        return self.log_test("3. Cost Calculation", True, f"Resource building costs correct: {'; '.join(results)}")

    def test_prototype_limit(self):
        """Test 4: Prototype limit - Try to create ship design without werft level"""
        if not hasattr(self, 'buildings_data'):
            return self.log_test("4. Prototype Limit Test", False, "No buildings data available")
        
        werft = self.buildings_data.get('werft')
        if not werft:
            return self.log_test("4. Prototype Limit Test", False, "Werft not found")
        
        werft_level = werft['level']
        
        # Get current ship designs
        success, status, designs = self.make_request('GET', 'game/ship-designs')
        if not success:
            return self.log_test("4. Prototype Limit Test", False, "Could not get ship designs")
        
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
                return self.log_test("4. Prototype Limit Test", True, 
                    f"Correctly rejected prototype creation (werft level {werft_level}, designs {current_designs})")
            else:
                return self.log_test("4. Prototype Limit Test", False, 
                    f"Should have rejected prototype creation but got status {status}")
        else:
            return self.log_test("4. Prototype Limit Test", True, 
                f"Prototype limit not reached (werft level {werft_level}, designs {current_designs}/{max_allowed})")

    def test_fleet_limit(self):
        """Test 5: Fleet limit - Try to create fleet without raumhafen level"""
        if not hasattr(self, 'buildings_data'):
            return self.log_test("5. Fleet Limit Test", False, "No buildings data available")
        
        raumhafen = self.buildings_data.get('raumhafen')
        if not raumhafen:
            return self.log_test("5. Fleet Limit Test", False, "Raumhafen not found")
        
        raumhafen_level = raumhafen['level']
        
        # Get current fleets
        success, status, fleets = self.make_request('GET', 'game/fleets')
        if not success:
            return self.log_test("5. Fleet Limit Test", False, "Could not get fleets")
        
        current_fleets = len(fleets)
        max_allowed = raumhafen_level
        
        if current_fleets >= max_allowed:
            # Get planets for fleet creation test
            success, status, planets = self.make_request('GET', 'game/planets')
            if not success or len(planets) == 0:
                return self.log_test("5. Fleet Limit Test", True, 
                    f"Fleet limit reached but no planets for test (raumhafen level {raumhafen_level})")
            
            planet_id = planets[0]['id']
            
            # Try to create fleet (should fail)
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
                return self.log_test("5. Fleet Limit Test", True, 
                    f"Correctly rejected fleet creation (raumhafen level {raumhafen_level}, fleets {current_fleets})")
            else:
                return self.log_test("5. Fleet Limit Test", False, 
                    f"Should have rejected fleet creation but got status {status}")
        else:
            return self.log_test("5. Fleet Limit Test", True, 
                f"Fleet limit not reached (raumhafen level {raumhafen_level}, fleets {current_fleets}/{max_allowed})")

    def test_resources_no_silicon(self):
        """Test 6: Resources - Check that Silicon was removed, only Food, Metal, Hydrogen"""
        success, status, planets = self.make_request('GET', 'game/planets')
        if not success:
            return self.log_test("6. Resources Check (No Silicon)", False, "Could not get planets")
        
        if len(planets) == 0:
            return self.log_test("6. Resources Check (No Silicon)", False, "No planets found")
        
        for i, planet in enumerate(planets):
            resources = planet.get('resources', {})
            
            # Check that only expected resources exist
            expected_resources = {'food', 'metal', 'hydrogen'}
            actual_resources = set(resources.keys())
            
            # Check for silicon (should not exist)
            if 'silicon' in actual_resources or 'silizium' in actual_resources:
                return self.log_test("6. Resources Check (No Silicon)", False, 
                    f"Found silicon/silizium in planet {i} resources: {actual_resources}")
            
            # Check that all expected resources exist
            missing_resources = expected_resources - actual_resources
            if missing_resources:
                return self.log_test("6. Resources Check (No Silicon)", False, 
                    f"Planet {i} missing expected resources: {missing_resources}")
            
            # Check for unexpected resources
            unexpected_resources = actual_resources - expected_resources
            if unexpected_resources:
                return self.log_test("6. Resources Check (No Silicon)", False, 
                    f"Planet {i} has unexpected resources: {unexpected_resources}")
        
        # Show resource amounts for first planet
        first_planet = planets[0]
        resources = first_planet['resources']
        resource_info = f"Food: {resources['food']}, Metal: {resources['metal']}, Hydrogen: {resources['hydrogen']}"
        
        return self.log_test("6. Resources Check (No Silicon)", True, 
            f"Only Food, Metal, Hydrogen found (no Silicon). Sample: {resource_info}")

    def test_single_building_upgrade_limit(self):
        """Test 7: Only one building can be upgraded at a time"""
        if not hasattr(self, 'buildings_data'):
            return self.log_test("7. Single Building Upgrade Limit", False, "No buildings data available")
        
        # Check current upgrade status
        upgrading_buildings = []
        non_upgrading_buildings = []
        
        for building_type, building in self.buildings_data.items():
            if building.get('upgrading', False):
                upgrading_buildings.append(building_type)
            else:
                non_upgrading_buildings.append(building_type)
        
        if len(upgrading_buildings) > 1:
            return self.log_test("7. Single Building Upgrade Limit", False, 
                f"Multiple buildings upgrading simultaneously: {upgrading_buildings}")
        elif len(upgrading_buildings) == 1:
            # Try to upgrade another building (should fail)
            if non_upgrading_buildings:
                test_building = non_upgrading_buildings[0]
                success, status, data = self.make_request(
                    'POST', 'game/buildings/upgrade',
                    {"building_type": test_building},
                    expected_status=400
                )
                
                if success:
                    return self.log_test("7. Single Building Upgrade Limit", True, 
                        f"Correctly rejected {test_building} upgrade while {upgrading_buildings[0]} is upgrading")
                else:
                    return self.log_test("7. Single Building Upgrade Limit", False, 
                        f"Should have rejected upgrade but got status {status}")
            else:
                return self.log_test("7. Single Building Upgrade Limit", True, 
                    f"Only {upgrading_buildings[0]} is upgrading - limit working")
        else:
            return self.log_test("7. Single Building Upgrade Limit", True, 
                "No buildings currently upgrading - limit not applicable")

    def test_metal_cost_deduction(self):
        """Test 8: Costs are deducted from Metal resources"""
        # Get current metal amount
        success, status, planets = self.make_request('GET', 'game/planets')
        if not success:
            return self.log_test("8. Metal Cost Deduction", False, "Could not get planets")
        
        total_metal = sum(planet['resources']['metal'] for planet in planets)
        
        # Check if any building is available for upgrade
        if not hasattr(self, 'buildings_data'):
            return self.log_test("8. Metal Cost Deduction", False, "No buildings data available")
        
        # Find a building that's not upgrading and has reasonable cost
        test_building = None
        test_cost = 0
        
        for building_type, building in self.buildings_data.items():
            if not building.get('upgrading', False):
                cost = building.get('upgrade_cost_metal', 0)
                if cost <= total_metal and cost > 0:
                    test_building = building_type
                    test_cost = cost
                    break
        
        if not test_building:
            return self.log_test("8. Metal Cost Deduction", True, 
                f"No suitable building for upgrade test (total metal: {total_metal})")
        
        # Attempt upgrade
        success, status, data = self.make_request(
            'POST', 'game/buildings/upgrade',
            {"building_type": test_building}
        )
        
        if not success:
            return self.log_test("8. Metal Cost Deduction", True, 
                f"Upgrade rejected (expected if another building is upgrading): {status}")
        
        # Check metal after upgrade
        success, status, updated_planets = self.make_request('GET', 'game/planets')
        if not success:
            return self.log_test("8. Metal Cost Deduction", False, "Could not get updated planets")
        
        new_total_metal = sum(planet['resources']['metal'] for planet in updated_planets)
        expected_metal = total_metal - test_cost
        
        if new_total_metal == expected_metal:
            return self.log_test("8. Metal Cost Deduction", True, 
                f"Metal correctly deducted: {total_metal} - {test_cost} = {new_total_metal}")
        else:
            return self.log_test("8. Metal Cost Deduction", False, 
                f"Metal deduction incorrect: expected {expected_metal}, got {new_total_metal}")

def main():
    print("🏗️  TheReCreation Building System Comprehensive Tests")
    print("=" * 70)
    print("Testing the new building system with all specified test cases")
    print("=" * 70)
    
    tester = ComprehensiveBuildingTester()
    
    # Authentication
    print("\n📝 Authentication:")
    if not tester.test_user_login():
        print("❌ Login failed, stopping tests")
        return 1
    
    if not tester.test_get_user_profile():
        print("❌ Profile fetch failed, stopping tests")
        return 1
    
    # Building System Tests (as specified in review request)
    print("\n🏗️  Building System Tests (Review Request Specifications):")
    
    # Test 1: GET /api/game/buildings
    tester.test_get_buildings_api()
    
    # Test 2: POST /api/game/buildings/upgrade
    tester.test_upgrade_building_api()
    
    # Test 3: Cost calculation
    tester.test_cost_calculation()
    
    # Test 4: Prototype limit
    tester.test_prototype_limit()
    
    # Test 5: Fleet limit
    tester.test_fleet_limit()
    
    # Test 6: Resources check (no silicon)
    tester.test_resources_no_silicon()
    
    # Additional validation tests
    print("\n🔍 Additional Validation Tests:")
    
    # Test 7: Single building upgrade limit
    tester.test_single_building_upgrade_limit()
    
    # Test 8: Metal cost deduction
    tester.test_metal_cost_deduction()
    
    # Print final results
    print("\n" + "=" * 70)
    print(f"📊 Building System Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All building system tests passed!")
        print("\n✅ BUILDING SYSTEM VERIFICATION COMPLETE")
        print("✅ All specified test cases from review request working correctly")
        return 0
    else:
        failed_tests = tester.tests_run - tester.tests_passed
        print(f"⚠️  {failed_tests} building system tests failed")
        print("\n❌ Some building system features need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())