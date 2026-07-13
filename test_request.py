import urllib.request
import json
import sys
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = "http://127.0.0.1:3056"

# Load environment configuration manually to connect to MongoDB in test
import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "Network-Planner")

def request_json(url_path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{url_path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    req_data = None        
    if data:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode("utf-8")
            return response.status, json.loads(res_body)
    except urllib.error.HTTPError as e:
        try:
            res_body = e.read().decode("utf-8")
            return e.code, json.loads(res_body)
        except Exception:
            return e.code, {"success": False, "error": e.reason}
    except Exception as e:
        return 500, {"success": False, "error": str(e)}

async def verify_db_records(request_id):
    print(f"\nVerifying database records for requestId: {request_id}...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]

    # 1. Verify OptimizationRequests
    opt_req = await db["OptimizationRequests"].find_one({"requestId": request_id})
    assert opt_req is not None, "OptimizationRequests document not found!"
    assert opt_req["requestName"] == "July Planning Integration Test", f"Unexpected requestName: {opt_req.get('requestName')}"
    assert opt_req["status"] == "Pending", f"Unexpected status: {opt_req.get('status')}"
    assert opt_req["createdBy"] == "System", f"Unexpected createdBy: {opt_req.get('createdBy')}"
    assert opt_req["createdOn"] is not None, "createdOn field is missing"
    print("OK: OptimizationRequests document verified.")

    # 2. Verify RequestPlants
    plant = await db["RequestPlants"].find_one({"requestId": request_id})
    assert plant is not None, "RequestPlants document not found!"
    assert plant["plantCode"] == "P001", f"Unexpected plantCode: {plant.get('plantCode')}"
    assert plant["productCode"] == "MILK", f"Unexpected productCode: {plant.get('productCode')}"
    assert plant["demand"] == 50000, f"Unexpected demand: {plant.get('demand')}"
    print("OK: RequestPlants document verified.")

    # 3. Verify RequestMMCs
    mmc = await db["RequestMMCs"].find_one({"requestId": request_id})
    assert mmc is not None, "RequestMMCs document not found!"
    assert mmc["mmcCode"] == "MMC001", f"Unexpected mmcCode: {mmc.get('mmcCode')}"
    assert mmc["supplierCode"] == "SUP001", f"Unexpected supplierCode: {mmc.get('supplierCode')}"
    assert mmc["productCode"] == "MILK", f"Unexpected productCode: {mmc.get('productCode')}"
    assert mmc["availableSupply"] == 25000, f"Unexpected availableSupply: {mmc.get('availableSupply')}"
    print("OK: RequestMMCs document verified.")

    # 4. Verify RequestVehicles
    vehicle = await db["RequestVehicles"].find_one({"requestId": request_id})
    assert vehicle is not None, "RequestVehicles document not found!"
    assert vehicle["supplierCode"] == "SUP001", f"Unexpected supplierCode: {vehicle.get('supplierCode')}"
    assert vehicle["vehicleType"] == "10L", f"Unexpected vehicleType: {vehicle.get('vehicleType')}"
    assert vehicle["vehicleCount"] == 8, f"Unexpected vehicleCount: {vehicle.get('vehicleCount')}"
    print("OK: RequestVehicles document verified.")

    # 5. Verify RequestSettings
    setting = await db["RequestSettings"].find_one({"requestId": request_id})
    assert setting is not None, "RequestSettings document not found!"
    assert setting["maxDistance"] == 150, f"Unexpected maxDistance: {setting.get('maxDistance')}"
    assert setting["leaveQuantity"] == 1000, f"Unexpected leaveQuantity: {setting.get('leaveQuantity')}"
    assert setting["createdOn"] is not None, "createdOn field in settings is missing"
    print("OK: RequestSettings document verified.")

    # 6. Verify RequestPlantSupplierMappings
    mapping = await db["RequestPlantSupplierMappings"].find_one({"requestId": request_id})
    assert mapping is not None, "RequestPlantSupplierMappings document not found!"
    assert mapping["plantCode"] == "P001", f"Unexpected plantCode: {mapping.get('plantCode')}"
    assert mapping["supplierCode"] == "SUP001", f"Unexpected supplierCode: {mapping.get('supplierCode')}"
    assert mapping["productCode"] == "MILK", f"Unexpected productCode: {mapping.get('productCode')}"
    print("OK: RequestPlantSupplierMappings document verified.")

    client.close()

def run_tests():
    print("=== STARTING REQUEST INTEGRATION TESTS ===")
    
    # 1. Login
    print("\n1. Logging in...")
    login_data = {
        "username": "admin",
        "password": "Password123!",
        "organizationCode": "NET_SUP"
    }
    status, res = request_json("/api/v1/auth/login", "POST", data=login_data)
    assert status == 200, f"Login failed: {res}"
    token = res["data"]["token"]
    print("Login successful. Token acquired.")
    
    # 2. Create Request with vechicles (alias) payload
    print("\n2. Creating request via POST API...")
    payload = {
        "requestName": "July Planning Integration Test",
        "plants": [
            {
                "plantCode": "P001",
                "product": "MILK",
                "demand": 50000
            }
        ],
        "mmcs": [
            {
                "mmcCode": "MMC001",
                "supplierCode": "SUP001",
                "product": "MILK",
                "supply": 25000
            }
        ],
        "vechicles": [
            {
                "supplierCode": "SUP001",
                "vehicleType": "10L",
                "count": 8
            }
        ],
        "plantSupplierMapping": [
            {
                "plantCode": "P001",
                "supplierCode": "SUP001",
                "productCode": "MILK"
            }
        ],
        "maxDistance": 150,
        "leaveQuantity": 1000
    }
    status, res = request_json("/api/v1/request", "POST", data=payload, token=token)
    assert status == 201, f"Expected 201 Created, got {status}: {res}"
    
    assert res["success"] is True, f"Response success flag is not True: {res}"
    request_data = res["data"]["request"]
    request_id = request_data["requestId"]
    assert request_id.startswith("REQ"), f"Request ID does not start with REQ: {request_id}"
    print(f"Created request successfully. Generated ID: {request_id}")
    
    # 3. Verify database records
    asyncio.run(verify_db_records(request_id))

    print("\n=== ALL REQUEST INTEGRATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        import traceback
        traceback.print_exc()
        print(f"\n[TEST FAILURE] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[UNEXPECTED ERROR] {e}", file=sys.stderr)
        sys.exit(1)
