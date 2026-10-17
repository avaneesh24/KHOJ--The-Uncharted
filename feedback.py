from datetime import datetime
from fastapi import APIRouter
from app.database import get_db_connection
from app.schemas import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["Feedback & Corrections"])

@router.post("", response_model=FeedbackResponse)
async def submit_feedback(data: FeedbackCreate):
    """
    Submits a report for outdated or inaccurate information on a place.
    Saved to database and monitored for quality assurance.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.utcnow().isoformat()

    cursor.execute("""
    INSERT INTO feedback_reports (place_id, place_name, report_type, notes, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (
        data.place_id,
        data.place_name.strip(),
        data.report_type,
        data.notes.strip(),
        now_str
    ))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return FeedbackResponse(
        id=new_id,
        place_id=data.place_id,
        place_name=data.place_name,
        report_type=data.report_type,
        notes=data.notes,
        created_at=now_str,
        status="received"
    )

@router.get("", response_model=list[FeedbackResponse])
async def list_feedback():
    """Lists recent feedback and inaccuracy reports."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM feedback_reports ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    return [
        FeedbackResponse(
            id=r["id"],
            place_id=r["place_id"],
            place_name=r["place_name"],
            report_type=r["report_type"],
            notes=r["notes"],
            created_at=r["created_at"],
            status="received"
        )
        for r in rows
    ]
