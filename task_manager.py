import uuid
from typing import Dict, Any, Optional
from datetime import datetime

# In-memory task tracker. For production, this would be Redis/Postgres.
TASKS: Dict[str, Dict[str, Any]] = {}

def create_task(name: str) -> str:
    """Create a new background task and return its ID."""
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "id": task_id,
        "name": name,
        "status": "pending",  # pending, running, completed, failed
        "progress": 0.0,      # 0.0 to 1.0 (or 0 to 100)
        "message": "Initializing...",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "result": None,
        "error": None
    }
    return task_id

def update_task(task_id: str, status: Optional[str] = None, 
                progress: Optional[float] = None, message: Optional[str] = None, 
                result: Any = None, error: Optional[str] = None) -> None:
    """Update an existing task's state."""
    if task_id not in TASKS:
        return
        
    task = TASKS[task_id]
    if status is not None:
        task["status"] = status
    if progress is not None:
        task["progress"] = progress
    if message is not None:
        task["message"] = message
    if result is not None:
        task["result"] = result
    if error is not None:
        task["error"] = error
        task["status"] = "failed"
        
    task["updated_at"] = datetime.now().isoformat()

def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a task's current state."""
    return TASKS.get(task_id)
