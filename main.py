from fastapi import FastAPI, Request
import httpx
import re
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

PLANE_TOKEN = os.getenv("PLANE_API_TOKEN")
WORKSPACE_SLUG = os.getenv("WORKSPACE_SLUG", "aoc") 
PLANE_BASE_URL = os.getenv("PLANE_BASE_URL", "https://plane.loolootest.com")

headers = {
    "X-API-Key": PLANE_TOKEN,
    "Content-Type": "application/json"
}

def extract_plane_task_id(text: str) -> str | None:
    """
    Extract task ID from Plane link pattern: {PLANE_BASE_URL}/{WORKSPACE_SLUG}/browse/{TASK-ID}/
    Returns the task ID (e.g., 'WEB-39') if found, None otherwise
    """
    escaped_base_url = re.escape(PLANE_BASE_URL)
    pattern = rf"{escaped_base_url}/{re.escape(WORKSPACE_SLUG)}/browse/([A-Z]+-\d+)/?"
    match = re.search(pattern, text)
    return match.group(1) if match else None

async def post_comment_to_plane_issue(issue_identifier: str, comment_body: str) -> bool:
    """
    Post a comment to a Plane issue using the issue identifier (e.g., 'WEB-28')
    Returns True if successful, False otherwise
    """
    try:
        issue_url = f"{PLANE_BASE_URL}/api/v1/workspaces/{WORKSPACE_SLUG}/issues/{issue_identifier}/"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(issue_url, headers=headers)
            
            if response.status_code != 200:
                return False
                
            issue_data = response.json()
            issue_id = issue_data.get("id")
            project_id = issue_data.get("project")
            
            if not issue_id or not project_id:
                return False
            
            comment_url = (
                f"{PLANE_BASE_URL}/api/v1/workspaces/"
                f"{WORKSPACE_SLUG}/projects/{project_id}/issues/{issue_id}/comments/"
            )
            
            payload = {"comment_html": comment_body}
            
            comment_response = await client.post(comment_url, headers=headers, json=payload)
            
            if comment_response.status_code == 201:
                return True
            else:
                return False
                
    except Exception as e:
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
        
        # Extract Plane task ID from pull request body
        plane_task_id = extract_plane_task_id(pull_request_body)
        
        if plane_task_id:
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
                return {
                    "status": "success", 
                    "message": f"Comment posted to Plane issue {plane_task_id}",
                    "plane_task_id": plane_task_id
                }
            else:
                return {
                    "status": "error", 
                    "message": f"Failed to post comment to Plane issue {plane_task_id}",
                    "plane_task_id": plane_task_id
                }
        else:
            return {
                "status": "success", 
                "message": "Webhook processed but no Plane link found"
            }
            
    except KeyError as e:
        error_msg = f"Missing required field: {str(e)}"
        return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        return {"status": "error", "message": error_msg} 