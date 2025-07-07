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

def extract_plane_task_ids(text: str) -> list[str]:
    """
    Extract all task IDs from both Plane link patterns and direct task ID patterns:
    1. From URL: {PLANE_BASE_URL}/{WORKSPACE_SLUG}/browse/{TASK-ID}/
    2. From string: {PROJECT}-{NUMBER} (e.g., WEB-102)
    Returns a list of unique task IDs (e.g., ['WEB-39', 'WEB-40']) if found, empty list otherwise
    """
    task_ids = set()
    
    # Extract from URL patterns
    escaped_base_url = re.escape(PLANE_BASE_URL)
    url_pattern = rf"{escaped_base_url}/{re.escape(WORKSPACE_SLUG)}/browse/([A-Z]+-\d+)/?"
    url_matches = re.findall(url_pattern, text)
    task_ids.update(url_matches)
    
    # Extract from direct task ID patterns (e.g., WEB-102)
    task_id_pattern = r'\b([A-Z]+-\d+)\b'
    task_id_matches = re.findall(task_id_pattern, text)
    task_ids.update(task_id_matches)
    
    return list(task_ids)

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
        action = payload.get("action", "")
        pull_request_link = payload["pull_request"]["url"]
        pull_request_body = payload['pull_request']['body']  
        pull_request_title = payload['pull_request']['title'] 
        sender_name = payload['sender']['login']
        sender_email = payload['sender']['email']
        
        # Check if PR is merged (could be "closed" with merged = true or "merged" action)
        is_merged = (
            action == "merged" or 
            (action == "closed" and payload.get("pull_request", {}).get("merged", False))
        )
        
        # Extract all Plane task IDs from pull request body
        plane_task_ids = extract_plane_task_ids(pull_request_body)
        
        if plane_task_ids:
            # Create comment body based on action type
            if is_merged:
                comment_body = f"""<h3>✅ Pull Request Merged</h3>
<p><strong>Title:</strong> {pull_request_title}</p>
<p><strong>Author:</strong> {sender_name} ({sender_email})</p>
<p><strong>PR Link:</strong> <a href="{pull_request_link}" target="_blank">{pull_request_link}</a></p>
<p><strong>Status:</strong> 🎉 Successfully merged!</p>
<p><em>This comment was automatically generated from a Gitea webhook.</em></p>"""
            else:
                comment_body = f"""<h3>🔄 Pull Request Update</h3>
<p><strong>Title:</strong> {pull_request_title}</p>
<p><strong>Author:</strong> {sender_name} ({sender_email})</p>
<p><strong>PR Link:</strong> <a href="{pull_request_link}" target="_blank">{pull_request_link}</a></p>
<p><strong>Action:</strong> {action}</p>
<p><em>This comment was automatically generated from a Gitea webhook.</em></p>"""
            
            # Post comment to all Plane issues
            successful_posts = []
            failed_posts = []
            
            for task_id in plane_task_ids:
                success = await post_comment_to_plane_issue(task_id, comment_body)
                if success:
                    successful_posts.append(task_id)
                else:
                    failed_posts.append(task_id)
            
            # Return status based on results
            if successful_posts and not failed_posts:
                return {
                    "status": "success", 
                    "message": f"Comments posted to {len(successful_posts)} Plane issues",
                    "successful_tasks": successful_posts,
                    "action": action
                }
            elif successful_posts and failed_posts:
                return {
                    "status": "partial_success", 
                    "message": f"Comments posted to {len(successful_posts)} out of {len(plane_task_ids)} Plane issues",
                    "successful_tasks": successful_posts,
                    "failed_tasks": failed_posts,
                    "action": action
                }
            else:
                return {
                    "status": "error", 
                    "message": f"Failed to post comments to all {len(plane_task_ids)} Plane issues",
                    "failed_tasks": failed_posts,
                    "action": action
                }
        else:
            return {
                "status": "success", 
                "message": "Webhook processed but no Plane link found",
                "action": action
            }
            
    except KeyError as e:
        error_msg = f"Missing required field: {str(e)}"
        return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        return {"status": "error", "message": error_msg} 