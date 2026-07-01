import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:3056"

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

def run_tests():
    print("=== STARTING PRODUCT INTEGRATION TESTS ===")
    
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
    
    # 2. Get a valid WorkZone ID
    status, res = request_json("/api/v1/workzone", "GET", token=token)
    assert status == 200, f"Get WorkZone list failed: {res}"
    workzones = res["data"]["workzones"]
    assert len(workzones) > 0, "No workzones found to associate with product"
    valid_wz_id = workzones[0]["WorkZoneId"]
    print(f"Valid WorkZone ID: {valid_wz_id}")
    
    # 3. Try to create a product with an invalid/non-existent WorkZone ID
    print("\n2. Creating product with invalid WorkZone ID (should fail)...")
    invalid_wz_id = "6582a8b9f0290e21703043af" # valid ObjectId format but doesn't exist
    prod_data_invalid = {
        "ProductCode": "PROD_TEST_ERR",
        "ProductName": "Invalid WZ Product",
        "WorkZoneId": invalid_wz_id,
        "Description": "This should fail",
        "IsActive": True
    }
    status, res = request_json("/api/v1/product", "POST", data=prod_data_invalid, token=token)
    assert status == 400, f"Expected 400 Bad Request, got {status}: {res}"
    print("Failed as expected:", res.get("detail", res.get("message")))
    
    # 4. Create product with valid WorkZone ID
    print("\n3. Creating product with valid WorkZone ID (should succeed)...")
    import time
    timestamp = int(time.time())
    prod_code = f"P_{timestamp}"
    prod_data_valid = {
        "ProductCode": prod_code,
        "ProductName": f"Product {timestamp}",
        "WorkZoneId": valid_wz_id,
        "Description": "Test Product",
        "IsActive": True
    }
    status, res = request_json("/api/v1/product", "POST", data=prod_data_valid, token=token)
    assert status == 201, f"Create Product failed: {res}"
    product = res["data"]["product"]
    product_id = product["ProductId"]
    assert product["WorkZoneId"] == valid_wz_id
    print(f"Created Product successfully. ProductId: {product_id}, WorkZoneId: {product['WorkZoneId']}")
    
    # 5. Try to update product with an invalid WorkZone ID
    print("\n4. Updating product with invalid WorkZone ID (should fail)...")
    update_data_invalid = {
        "WorkZoneId": invalid_wz_id
    }
    status, res = request_json(f"/api/v1/product/{product_id}", "PUT", data=update_data_invalid, token=token)
    assert status == 400, f"Expected 400 Bad Request on update, got {status}: {res}"
    print("Failed as expected:", res.get("detail", res.get("message")))
    
    # 6. Update product with valid WorkZone ID (or update other fields)
    print("\n5. Updating product fields (should succeed)...")
    update_data_valid = {
        "ProductName": f"Updated Product {timestamp}",
        "Description": "Updated Description"
    }
    status, res = request_json(f"/api/v1/product/{product_id}", "PUT", data=update_data_valid, token=token)
    assert status == 200, f"Update Product failed: {res}"
    updated_product = res["data"]["product"]
    assert updated_product["ProductName"] == f"Updated Product {timestamp}"
    assert updated_product["Description"] == "Updated Description"
    print("Product updated successfully.")

    # 7. Get product list filtering by workZoneId
    print("\n6. Listing products filtered by workZoneId...")
    status, res = request_json(f"/api/v1/product?workZoneId={valid_wz_id}", "GET", token=token)
    assert status == 200, f"Get Product list failed: {res}"
    products_list = res["data"]["products"]
    assert any(p["ProductId"] == product_id for p in products_list), f"Created product {product_id} not in filtered list"
    print(f"Found {len(products_list)} products under WorkZone ID {valid_wz_id}.")

    # 8. List products filtering by a different workZoneId (should not find the created product)
    print("\n7. Listing products filtered by a different workZoneId...")
    status, res = request_json(f"/api/v1/product?workZoneId={invalid_wz_id}", "GET", token=token)
    assert status == 200, f"Get Product list with inactive workzone failed: {res}"
    products_list_other = res["data"]["products"]
    assert not any(p["ProductId"] == product_id for p in products_list_other), f"Created product {product_id} should not be in other workzone's list"
    print(f"Verified product list filtering works correctly.")
    
    print("\n=== ALL PRODUCT INTEGRATION TESTS PASSED SUCCESSFULLY! ===")

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
