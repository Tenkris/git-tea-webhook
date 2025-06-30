from fastapi import FastAPI, Request
import httpx
import re
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

PLANE_TOKEN = os.getenv("PLANE_API_TOKEN")
WORKSPACE_SLUG = "aoc"

headers = {
    "X-API-Key": PLANE_TOKEN,
    "Content-Type": "application/json"
}

def extract_plane_task_id(text: str) -> str | None:
    """
    Extract task ID from Plane link pattern: https://plane.loolootest.com/aoc/browse/{TASK-ID}/
    Returns the task ID (e.g., 'WEB-39') if found, None otherwise
    """
    match = re.search(r"https://plane\.loolootest\.com/aoc/browse/([A-Z]+-\d+)/?", text)
    return match.group(1) if match else None

async def post_comment_to_plane_issue(issue_identifier: str, comment_body: str) -> bool:
    """
    Post a comment to a Plane issue using the issue identifier (e.g., 'WEB-28')
    Returns True if successful, False otherwise
    """
    try:
        # Step 1: Get issue info from short identifier
        issue_url = f"https://plane.loolootest.com/api/v1/workspaces/{WORKSPACE_SLUG}/issues/{issue_identifier}/"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(issue_url, headers=headers)
            print(f"Issue fetch status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Failed to fetch issue: {response.text}")
                return False
                
            issue_data = response.json()
            issue_id = issue_data.get("id")
            project_id = issue_data.get("project")
            
            if not issue_id or not project_id:
                print("❌ Missing issue_id or project_id in response")
                return False
                
            print(f"✅ Issue UUID: {issue_id}")
            print(f"✅ Project ID: {project_id}")
            
            # Step 2: Post the comment
            comment_url = (
                f"https://plane.loolootest.com/api/v1/workspaces/"
                f"{WORKSPACE_SLUG}/projects/{project_id}/issues/{issue_id}/comments/"
            )
            
            payload = {"comment_html": comment_body}
            
            comment_response = await client.post(comment_url, headers=headers, json=payload)
            print(f"Comment post status: {comment_response.status_code}")
            
            if comment_response.status_code == 201:
                print("✅ Comment posted successfully!")
                print(comment_response.json())
                return True
            else:
                print("❌ Failed to post comment:")
                print(comment_response.text)
                return False
                
    except Exception as e:
        print(f"❌ Error posting comment to Plane: {str(e)}")
        return False

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/gitea-webhook")
async def gitea_webhook(request: Request):
    payload = await request.json()
    
    try:
        pull_request_link = payload["pull_request"]["url"]
        pull_request_body = payload['pull_request']['body']  
        pull_request_title = payload['pull_request']['title'] 
        sender_name = payload['sender']['login']
        sender_email = payload['sender']['email']
        
        print(f"📧 Processing webhook from {sender_name} ({sender_email})")
        print(f"📝 PR Title: {pull_request_title}")
        print(f"🔗 PR Link: {pull_request_link}")
        
        # Extract Plane task ID from pull request body
        plane_task_id = extract_plane_task_id(pull_request_body)
        
        if plane_task_id:
            print(f"🎯 Found Plane task: {plane_task_id}")
            
            # Create comment body with PR information
            comment_body = f"""
            <h3>🔄 Pull Request Update</h3>
            <p><strong>Title:</strong> {pull_request_title}</p>
            <p><strong>Author:</strong> {sender_name} ({sender_email})</p>
            <p><strong>PR Link:</strong> <a href="{pull_request_link}" target="_blank">{pull_request_link}</a></p>
            <p><em>This comment was automatically generated from a Gitea webhook.</em></p>
            """
            
            # Post comment to Plane issue
            success = await post_comment_to_plane_issue(plane_task_id, comment_body)
            
            if success:
                print(f"✅ Successfully posted comment to Plane issue {plane_task_id}")
                return {
                    "status": "success", 
                    "message": f"Comment posted to Plane issue {plane_task_id}",
                    "plane_task_id": plane_task_id
                }
            else:
                print(f"❌ Failed to post comment to Plane issue {plane_task_id}")
                return {
                    "status": "error", 
                    "message": f"Failed to post comment to Plane issue {plane_task_id}",
                    "plane_task_id": plane_task_id
                }
        else:
            print("⚠️  No Plane link found in PR body")
            return {
                "status": "success", 
                "message": "Webhook processed but no Plane link found"
            }
            
    except KeyError as e:
        error_msg = f"Missing required field: {str(e)}"
        print(f"❌ {error_msg}")
        return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"status": "error", "message": error_msg} 