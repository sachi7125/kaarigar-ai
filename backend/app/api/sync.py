from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from typing import Optional
import os

router = APIRouter()

# In-memory storage for deduplication (since DB isn't wired up yet)
synced_client_ids = set()

# Ensure temp directory exists for uploads
os.makedirs("data/uploads", exist_ok=True)

@router.post("/sync")
async def sync_draft(
    client_id: str = Form(...),
    image: UploadFile = File(...),
    audio: UploadFile = File(...)
):
    """
    Receives an offline draft (image + audio) from the mobile client.
    Implements server-side deduplication based on client_id.
    """
    if client_id in synced_client_ids:
        # Deduplication: already synced, return success without doing anything
        return {"status": "success", "message": "Already synced (deduplicated)", "client_id": client_id}

    # Save files to disk (mock processing)
    image_path = f"data/uploads/{client_id}_image_{image.filename}"
    audio_path = f"data/uploads/{client_id}_audio_{audio.filename}"

    with open(image_path, "wb") as buffer:
        buffer.write(await image.read())
        
    with open(audio_path, "wb") as buffer:
        buffer.write(await audio.read())

    # Mark as synced
    synced_client_ids.add(client_id)

    return {
        "status": "success", 
        "message": "Draft synced successfully", 
        "client_id": client_id,
        "image_path": image_path,
        "audio_path": audio_path
    }
