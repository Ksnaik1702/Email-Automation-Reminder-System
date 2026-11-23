"""
Webhooks and tracking router:
Records email opens via 1x1 transparent pixel and click redirections.
"""
import base64
from fastapi import APIRouter, Response, HTTPException, status
from fastapi.responses import RedirectResponse
from db.database import get_connection

router = APIRouter(prefix="/t", tags=["tracking"])

# 1x1 transparent PNG payload
TRANSPARENT_PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGP4BwQACfsD/UE8oRUAAAAASUVORK5CYII="
)

@router.get("/o/{message_id}.png")
def track_open(message_id: str):
    """Tracking pixel endpoint: updates message status to 'opened'."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE messages SET status = 'opened' WHERE id = ? AND status = 'sent';",
            (message_id,)
        )
        conn.commit()
    finally:
        conn.close()
    
    return Response(
        content=TRANSPARENT_PIXEL,
        media_type="image/png",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@router.get("/c/{message_id}")
def track_click(message_id: str, url: str):
    """Click tracking endpoint: updates status to 'clicked' and redirects."""
    if not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing redirect target url")

    conn = get_connection()
    try:
        conn.execute(
            "UPDATE messages SET status = 'clicked' WHERE id = ? AND status IN ('sent', 'opened');",
            (message_id,)
        )
        conn.commit()
    finally:
        conn.close()

    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
