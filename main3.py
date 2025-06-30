import httpx
from dotenv import load_dotenv
import os

load_dotenv()

PLANE_TOKEN = os.getenv("PLANE_API_TOKEN")
WORKSPACE_SLUG = "aoc"
ISSUE_IDENTIFIER = "WEB-28"
COMMENT_BODY = "✅ Comment from script!"

headers = {
    "X-API-Key": PLANE_TOKEN,
    "Content-Type": "application/json"
}

# Step 1: Get issue info from short identifier like WEB-28
issue_url = f"https://plane.loolootest.com/api/v1/workspaces/{WORKSPACE_SLUG}/issues/{ISSUE_IDENTIFIER}/"

response = httpx.get(issue_url, headers=headers)
print(f"Issue fetch status: {response.status_code}")

if response.status_code == 200:
    issue_data = response.json()
    print(issue_data)
    issue_id = issue_data.get("id")
    project_id = issue_data.get("project")
    print("✅ Issue UUID:", issue_id)
    print("✅ Project ID:", project_id)

    # Step 2: Post the comment
    comment_url = (
        f"https://plane.loolootest.com/api/v1/workspaces/"
        f"{WORKSPACE_SLUG}/projects/{project_id}/issues/{issue_id}/comments/"
    )

    payload = {"comment_html": "ten test test"}

    comment_response = httpx.post(comment_url, headers=headers, json=payload)
    print(f"Comment post status: {comment_response.status_code}")

    if comment_response.status_code == 201:
        print("✅ Comment posted successfully!")
        print(comment_response.json())
    else:
        print("❌ Failed to post comment:")
        print(comment_response.text)

else:
    print("❌ Failed to fetch issue:")
    print(response.text)
