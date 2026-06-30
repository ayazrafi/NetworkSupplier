import urllib.request
import urllib.parse
import json
import time
import os
import sys

BASE_URL = "http://127.0.0.1:3056"

def request_json(url_path, method="GET", data=None, token=None, files=None):
    url = f"{BASE_URL}{url_path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    req_data = None
    
    if files:
        # Handle multipart/form-data upload using standard library
        boundary = "===Boundary==="
        body = []
        for name, value in data.items():
            body.append(f"--{boundary}")
            body.append(f'Content-Disposition: form-data; name="{name}"')
            body.append('')
            body.append(str(value))
            
        for name, file_info in files.items():
            filename, file_content = file_info
            body.append(f"--{boundary}")
            body.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"')
            body.append('Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            body.append('')
            body.append(file_content)
            
        body.append(f"--{boundary}--")
        body.append('')
        
        # Join components with correct bytes endings
        body_bytes = []
        for x in body:
            if isinstance(x, bytes):
                body_bytes.append(x)
            else:
                body_bytes.append(x.encode('utf-8'))
        
        req_data = b'\r\n'.join(body_bytes)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif data:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
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

def run_tests():
    print("=== STARTING INTEGRATION TESTS ===")
    
    # 1. Test Seed database
    print("\n1. Seeding database...")
    status, res = request_json("/api/v1/auth/seed", "POST")
    assert status == 200, f"Seed failed: {res}"
    print("Seed response:", res["message"])
    
    # 2. Test Login
    print("\n2. Logging in...")
    login_data = {
        "username": "admin",
        "password": "Password123!",
        "organizationCode": "NET_SUP"
    }
    status, res = request_json("/api/v1/auth/login", "POST", data=login_data)
    assert status == 200, f"Login failed: {res}"
    token = res["data"]["token"]
    print("Login successful. Token acquired.")
    
    # 3. Create BMC Master
    print("\n3. Creating BMC Master...")
    bmc_data = {
        "BMCCode": "BMC_TEST_01",
        "BMCName": "BMC Test Anand",
        "Address": "Anand GIDC Industrial Estate",
        "Latitude": 22.5645,
        "Longitude": 72.9289,
        "ContactPerson": "Mr. Test Manager",
        "MobileNumber": "9998887770",
        "IsActive": True
    }
    status, res = request_json("/api/v1/bmc", "POST", data=bmc_data, token=token)
    assert status in (201, 400), f"Create BMC failed: {res}"
    print("BMC created or already exists.")

    # 4. Search BMC
    print("\n4. Searching BMC...")
    status, res = request_json("/api/v1/bmc/search?q=Anand", "GET", token=token)
    assert status == 200, f"Search BMC failed: {res}"
    assert len(res["data"]["results"]) > 0, "No search results returned"
    print(f"Search successful. Found {res['data']['count']} results.")

    # 5. Create Plant Master
    print("\n5. Creating Plant Master...")
    plant_data = {
        "PlantCode": "PLANT_TEST_01",
        "PlantName": "Anand Cheese Factory",
        "Address": "Plant Area 1",
        "Latitude": 22.5800,
        "Longitude": 72.9500,
        "Capacity": 12000.0,
        "IsActive": True
    }
    status, res = request_json("/api/v1/plant", "POST", data=plant_data, token=token)
    assert status in (201, 400), f"Create Plant failed: {res}"
    print("Plant created or already exists.")

    # 6. Create Vehicle Master
    print("\n6. Creating Vehicle Master...")
    veh_data = {
        "VehicleType": "10 L Tanker",
        "VehicleCapacity": 10000.0,
        "CapacityUnit": "L",
        "Description": "Standard 10KL tanker",
        "IsActive": True
    }
    status, res = request_json("/api/v1/vehicle", "POST", data=veh_data, token=token)
    assert status in (201, 400), f"Create Vehicle failed: {res}"
    print("Vehicle created or already exists.")

    # 7. Create Cluster Master
    print("\n7. Creating Cluster Master...")
    cluster_data = {
        "ClusterCode": "CL_TEST_01",
        "ClusterName": "Anand Area Cluster",
        "Description": "Test cluster 1",
        "IsActive": True
    }
    status, res = request_json("/api/v1/cluster", "POST", data=cluster_data, token=token)
    assert status in (201, 400), f"Create Cluster failed: {res}"
    print("Cluster created or already exists.")

    # 8. Create SubCluster Master
    print("\n8. Creating SubCluster Master...")
    sub_data = {
        "ClusterCode": "CL_TEST_01",
        "SubClusterCode": "SUBCL_TEST_01",
        "SubClusterName": "Anand East SubCluster",
        "Description": "Test sub-cluster 1",
        "IsActive": True
    }
    status, res = request_json("/api/v1/subcluster", "POST", data=sub_data, token=token)
    assert status in (201, 400), f"Create SubCluster failed: {res}"
    print("SubCluster created or already exists.")

    # 9. Create Mapping
    print("\n9. Creating Cluster-SubCluster Mapping...")
    map_data = {
        "ClusterCode": "CL_TEST_01",
        "SubClusterCode": "SUBCL_TEST_01",
        "IsActive": True
    }
    status, res = request_json("/api/v1/cluster-subcluster-mapping", "POST", data=map_data, token=token)
    assert status in (201, 400), f"Create Mapping failed: {res}"
    print("Mapping created or already exists.")

    # 10. Duplicate Mapping Check
    print("\n10. Verifying duplicate mapping constraint...")
    status, res = request_json("/api/v1/cluster-subcluster-mapping", "POST", data=map_data, token=token)
    assert status == 400, f"Expected duplicate mapping to fail with 400, got: {status}"
    print("Duplicate mapping rejected as expected:", res.get("error", res.get("detail")))

    # 11. Test Excel Upload Job
    print("\n11. Testing Excel Upload Job...")
    src_excel = r"d:\WRMSWork\SupplierNetwork\SupplierNetworkMap\static\Custom-Network-Optimizer.xlsx"
    if os.path.exists(src_excel):
        with open(src_excel, "rb") as f:
            excel_content = f.read()
        
        job_fields = {"JobName": "API Test Optimization Job"}
        job_files = {"file": ("test_network.xlsx", excel_content)}
        
        status, res = request_json("/api/v1/jobs/upload", "POST", data=job_fields, token=token, files=job_files)
        assert status == 201, f"Excel Upload failed: {res}"
        job_id = res["data"]["job"]["JobId"]
        print(f"Job uploaded and queued successfully. Job ID: {job_id}")
        
        # Poll status
        print("Polling job processing status...")
        for i in range(15):
            time.sleep(2)
            status, res = request_json(f"/api/v1/jobs/{job_id}", "GET", token=token)
            assert status == 200, f"Get Job failed: {res}"
            job_status = res["data"]["job"]["JobStatus"]
            print(f"Attempt {i+1}: Job Status is {job_status}")
            if job_status in ("Completed", "Failed"):
                break
        
        assert job_status == "Completed", f"Job failed: {res['data']['job'].get('ErrorMessage')}"
        print("Job completed processing successfully.")
        
        # Test download
        print("\n12. Downloading Result Excel file...")
        dl_url = f"{BASE_URL}/api/v1/jobs/{job_id}/download"
        req = urllib.request.Request(dl_url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as response:
            dl_content = response.read()
            assert len(dl_content) > 0, "Downloaded file is empty"
            print(f"Download successful. Downloaded {len(dl_content)} bytes of result Excel spreadsheet.")
    else:
        print(f"[SKIP] Test Excel Upload: Source file '{src_excel}' does not exist.")

    print("\n=== ALL INTEGRATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    try:
        run_tests()
    except AssertionError as e:
        print(f"\n[TEST FAILURE] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] {e}", file=sys.stderr)
        sys.exit(1)
