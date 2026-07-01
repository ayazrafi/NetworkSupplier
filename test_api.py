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
    
    # 3. Organization CRUD
    print("\n3. Creating Organization Master...")
    org_data = {
        "OrganizationCode": "ORG_TEST_01",
        "OrganizationName": "Test Org Ltd",
        "Description": "Test Org Description",
        "IsActive": True
    }
    status, res = request_json("/api/v1/organization", "POST", data=org_data, token=token)
    assert status in (201, 400), f"Create Org failed: {res}"
    if status == 201:
        org_id = res["data"]["organization"]["OrganizationId"]
    else:
        # Retrieve existing
        status, get_res = request_json("/api/v1/organization", "GET", token=token)
        assert status == 200
        org_id = next(o["OrganizationId"] for o in get_res["data"]["organizations"] if o["OrganizationCode"] == "ORG_TEST_01")
    print(f"Organization ID acquired: {org_id}")

    # 4. WorkZone CRUD
    print("\n4. Creating WorkZone Master...")
    wz_data = {
        "WorkZoneCode": "WZ_TEST_01",
        "WorkZoneName": "Test Work Zone Anand",
        "OrganizationId": "6582a8b9f0290e21703043ad",
        "Description": "Test Work Zone Description",
        "IsActive": True
    }
    status, res = request_json("/api/v1/workzone", "POST", data=wz_data, token=token)
    assert status in (201, 400), f"Create WorkZone failed: {res}"
    if status == 201:
        wz_id = res["data"]["workzone"]["WorkZoneId"]
    else:
        status, get_res = request_json("/api/v1/workzone", "GET", token=token)
        assert status == 200
        wz_id = next(w["WorkZoneId"] for w in get_res["data"]["workzones"] if w["WorkZoneCode"] == "WZ_TEST_01")
    print(f"WorkZone ID acquired: {wz_id}")

    # 5. Create BMC Master (requires WorkZoneId)
    print("\n5. Creating BMC Master...")
    bmc_data = {
        "BMCCode": "BMC_TEST_01",
        "BMCName": "BMC Test Anand",
        "WorkZoneId": wz_id,
        "Address": "Anand GIDC Industrial Estate",
        "Latitude": 22.5645,
        "Longitude": 72.9289,
        "ContactPerson": "Mr. Test Manager",
        "MobileNumber": "9998887770",
        "IsActive": True
    }
    status, res = request_json("/api/v1/bmc", "POST", data=bmc_data, token=token)
    assert status in (201, 400), f"Create BMC failed: {res}"
    if status == 201:
        bmc_id = res["data"]["bmc"]["BMCId"]
    else:
        status, get_res = request_json("/api/v1/bmc", "GET", token=token)
        assert status == 200
        bmc_id = next(b["BMCId"] for b in get_res["data"]["bmcs"] if b["BMCCode"] == "BMC_TEST_01")
    print(f"BMC ID acquired: {bmc_id}")

    # 6. Search BMC
    print("\n6. Searching BMC...")
    status, res = request_json("/api/v1/bmc/search?q=Anand", "GET", token=token)
    assert status == 200, f"Search BMC failed: {res}"
    assert len(res["data"]["results"]) > 0, "No search results returned"
    print(f"Search successful. Found {res['data']['count']} results.")

    # 7. Create Plant Master (requires WorkZoneId)
    print("\n7. Creating Plant Master...")
    plant_data = {
        "PlantCode": "PLANT_TEST_01",
        "PlantName": "Anand Cheese Factory",
        "WorkZoneId": wz_id,
        "Address": "Plant Area 1",
        "Latitude": 22.5800,
        "Longitude": 72.9500,
        "Capacity": 12000.0,
        "IsActive": True
    }
    status, res = request_json("/api/v1/plant", "POST", data=plant_data, token=token)
    assert status in (201, 400), f"Create Plant failed: {res}"
    if status == 201:
        plant_id = res["data"]["plant"]["PlantId"]
    else:
        status, get_res = request_json("/api/v1/plant", "GET", token=token)
        assert status == 200
        plant_id = next(p["PlantId"] for p in get_res["data"]["plants"] if p["PlantCode"] == "PLANT_TEST_01")
    print(f"Plant ID acquired: {plant_id}")

    # 8. Create Vehicle Master
    print("\n8. Creating Vehicle Master...")
    veh_data = {
        "VehicleType": "10 L Tanker",
        "VehicleCapacity": 10000.0,
        "CapacityUnit": "L",
        "Description": "Standard 10KL tanker",
        "IsActive": True
    }
    status, res = request_json("/api/v1/vehicle", "POST", data=veh_data, token=token)
    assert status in (201, 400), f"Create Vehicle failed: {res}"
    if status == 201:
        vehicle_id = res["data"]["vehicle"]["VehicleId"]
    else:
        status, get_res = request_json("/api/v1/vehicle", "GET", token=token)
        assert status == 200
        vehicle_id = next(v["VehicleId"] for v in get_res["data"]["vehicles"] if v["VehicleType"] == "10 L Tanker")
    print(f"Vehicle ID acquired: {vehicle_id}")

    # 9. Create VehicleType Master (requires WorkZoneId)
    print("\n9. Creating VehicleType Master...")
    vt_data = {
        "VehicleTypeCode": "VT_TEST_01",
        "VehicleTypeName": "10 KL Tanker Type",
        "WorkZoneId": wz_id,
        "Description": "Seeded vehicle type",
        "IsActive": True
    }
    status, res = request_json("/api/v1/vehicletype", "POST", data=vt_data, token=token)
    assert status in (201, 400), f"Create VehicleType failed: {res}"
    print("VehicleType created or already exists.")

    # 10. Create Supplier Master (requires WorkZoneId, old Cluster)
    print("\n10. Creating Supplier Master...")
    sup_data = {
        "SupplierCode": "SUP_TEST_01",
        "SupplierName": "Anand Area Supplier",
        "WorkZoneId": wz_id,
        "Description": "Test Supplier 1",
        "Vehicles": [{"vehicleId": vehicle_id, "count": 5}],
        "IsActive": True
    }
    status, res = request_json("/api/v1/supplier", "POST", data=sup_data, token=token)
    assert status in (201, 400), f"Create Supplier failed: {res}"
    if status == 201:
        supplier_id = res["data"]["supplier"]["SupplierId"]
    else:
        status, get_res = request_json("/api/v1/supplier", "GET", token=token)
        assert status == 200
        supplier_id = next(s["SupplierId"] for s in get_res["data"]["suppliers"] if s["SupplierCode"] == "SUP_TEST_01")
    print(f"Supplier ID acquired: {supplier_id}")

    # 11. Create Cluster Master (requires WorkZoneId, old SubCluster)
    print("\n11. Creating Cluster Master...")
    cluster_data = {
        "ClusterCode": "CL_TEST_01",
        "ClusterName": "Anand East Cluster",
        "WorkZoneId": wz_id,
        "Description": "Test Cluster 1",
        "IsActive": True
    }
    status, res = request_json("/api/v1/cluster", "POST", data=cluster_data, token=token)
    assert status in (201, 400), f"Create Cluster failed: {res}"
    if status == 201:
        cluster_id = res["data"]["cluster"]["ClusterId"]
    else:
        status, get_res = request_json("/api/v1/cluster", "GET", token=token)
        assert status == 200
        cluster_id = next(c["ClusterId"] for c in get_res["data"]["clusters"] if c["ClusterCode"] == "CL_TEST_01")
    print(f"Cluster ID acquired: {cluster_id}")

    # 12. Create Supplier-Cluster Mapping (old Cluster-SubCluster Mapping)
    print("\n12. Creating Supplier-Cluster Mapping...")
    map_data = {
        "SupplierId": supplier_id,
        "ClusterId": cluster_id,
        "IsActive": True
    }
    status, res = request_json("/api/v1/supplier-cluster-mapping", "POST", data=map_data, token=token)
    assert status in (201, 400), f"Create Supplier-Cluster Mapping failed: {res}"
    print("Supplier-Cluster Mapping created or already exists.")

    # 13. Duplicate Mapping Check
    print("\n13. Verifying duplicate mapping constraint...")
    status, res = request_json("/api/v1/supplier-cluster-mapping", "POST", data=map_data, token=token)
    assert status == 400, f"Expected duplicate mapping to fail with 400, got: {status}"
    print("Duplicate mapping rejected as expected:", res.get("error", res.get("detail")))

    # 13a. Create BMC-Supplier-Cluster Mapping
    print("\n13a. Creating BMC-Supplier-Cluster Mapping...")
    bsc_map_data = {
        "BMCId": bmc_id,
        "SupplierId": supplier_id,
        "ClusterId": cluster_id,
        "Vehicles": [{"vehicleId": vehicle_id, "count": 3}],
        "IsActive": True
    }
    status, res = request_json("/api/v1/bmc-supplier-cluster-mapping", "POST", data=bsc_map_data, token=token)
    assert status in (201, 400), f"Create BMC-Supplier-Cluster Mapping failed: {res}"
    if status == 201:
        bsc_map_id = res["data"]["mapping"]["MappingId"]
        print(f"BMC-Supplier-Cluster Mapping created successfully. MappingId: {bsc_map_id}")
    else:
        status, get_res = request_json("/api/v1/bmc-supplier-cluster-mapping", "GET", token=token)
        assert status == 200
        bsc_map_id = next(m["MappingId"] for m in get_res["data"]["mappings"] if m["BMCId"] == bmc_id and m["SupplierId"] == supplier_id and m["ClusterId"] == cluster_id)
        print(f"BMC-Supplier-Cluster Mapping already exists. MappingId: {bsc_map_id}")

    # 13b. Verify duplicate mapping constraint for BMC-Supplier-Cluster Mapping
    print("\n13b. Verifying duplicate BMC-Supplier-Cluster mapping constraint...")
    status, res = request_json("/api/v1/bmc-supplier-cluster-mapping", "POST", data=bsc_map_data, token=token)
    assert status == 400, f"Expected duplicate BMC-Supplier-Cluster mapping to fail with 400, got: {status}"
    print("Duplicate BMC-Supplier-Cluster mapping rejected as expected:", res.get("error", res.get("detail")))

    # 14. Test Excel Upload Job
    print("\n14. Testing Excel Upload Job...")
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
        print("\n15. Downloading Result Excel file...")
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
        import traceback
        traceback.print_exc()
        print(f"\n[TEST FAILURE] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[UNEXPECTED ERROR] {e}", file=sys.stderr)
        sys.exit(1)
