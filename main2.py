import httpx

PLANE_TOKEN = "plane_api_f829675edd9f482ca86c494b14dda68a"
WORKSPACE_SLUG = "aoc"

url = f"https://plane.loolootest.com/api/v1/workspaces/{WORKSPACE_SLUG}/projects/"

headers = {
    "X-API-Key": PLANE_TOKEN
}

response = httpx.get(url, headers=headers)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✅ Token is valid. Response:")
    print(response.json())
elif response.status_code == 401:
    print("❌ Unauthorized. Check your token.")
elif response.status_code == 404:
    print("❌ Not Found. Check the workspace slug.")
else:
    print("❌ Something went wrong.")
    print(response.text)
