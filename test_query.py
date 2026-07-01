import urllib.request
import json

BASE_URL = "http://127.0.0.1:3056"

# 1. Login
login_data = {
    "username": "admin",
    "password": "Password123!",
    "organizationCode": "NET_SUP"
}
req_data = json.dumps(login_data).encode("utf-8")
req = urllib.request.Request(f"{BASE_URL}/api/v1/auth/login", data=req_data, headers={"Content-Type": "application/json"}, method="POST")

try:
    with urllib.request.urlopen(req) as res:
        login_res = json.loads(res.read().decode("utf-8"))
        token = login_res["data"]["token"]
        print("Login successful.")
        
        # 2. Get BMCs
        req_bmc = urllib.request.Request(f"{BASE_URL}/api/v1/bmc", headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req_bmc) as res_bmc:
                print("GET BMC status:", res_bmc.status)
                print("GET BMC response:", json.loads(res_bmc.read().decode("utf-8")))
        except urllib.error.HTTPError as e:
            print("GET BMC HTTP Error status:", e.code)
            print("GET BMC HTTP Error response:", e.read().decode("utf-8"))
except Exception as e:
    print("Error:", e)
