from pathlib import Path
from typing import List, Optional
import uuid
from fastapi import APIRouter, File, UploadFile, Query, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.config import DATASETS_DIR, STORAGE_DIR
from app.inspection.dataset import create_industrial_inspection_dataset
from app.inspection.pipeline import VisionInspectionEngine, InspectionResult, EvaluationMetrics
from app.db.session import get_db
from app.db.models import InspectionRecord

router = APIRouter(prefix="/inspection", tags=["Quality Inspection"])

# Initialize vision engine and dataset
inspection_engine = VisionInspectionEngine()
manifest_cache = None


def get_dataset_manifest() -> dict:
    global manifest_cache
    if manifest_cache is None:
        manifest_cache = create_industrial_inspection_dataset(DATASETS_DIR.parent)
    return manifest_cache


@router.get("/samples")
def get_sample_images():
    data = get_dataset_manifest()
    samples = []
    for item in data["manifest"]:
        samples.append({
            "id": item["id"],
            "filename": item["filename"],
            "ground_truth": item["ground_truth"],
            "defect_type": item["defect_type"],
            "split": item["split"],
        })
    return samples


@router.post("/analyze", response_model=InspectionResult)
async def analyze_product_image(
    sample_id: Optional[str] = Query(None, description="ID of a sample part from the dataset"),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    if not sample_id and not file:
        raise HTTPException(status_code=400, detail="Must provide either sample_id or an uploaded image file")

    result = None
    saved_path = None
    target_sample_id = sample_id or "uploaded_user_file"

    if file:
        # Validate MIME type
        if file.content_type not in ("image/jpeg", "image/png", "image/bmp", "image/webp"):
            raise HTTPException(status_code=400, detail=f"Unsupported image type: {file.content_type}. Use JPEG, PNG or WebP.")

        # Read and validate size (max 5 MB)
        contents = await file.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (exceeds 5 MB limit)")

        # Save to storage
        upload_name = f"{uuid.uuid4().hex}_{file.filename}"
        saved_file = STORAGE_DIR / "uploads" / upload_name
        with open(saved_file, "wb") as f:
            f.write(contents)
        saved_path = str(saved_file)

        result = inspection_engine.analyze_image_bytes(contents)
    else:
        # Find sample by ID
        data = get_dataset_manifest()
        match = next((s for s in data["manifest"] if s["id"] == sample_id), None)
        if not match:
            raise HTTPException(status_code=404, detail=f"Sample part {sample_id} not found")
        saved_path = match["filepath"]
        result = inspection_engine.analyze_file(match["filepath"])

    # Persist to SQLite
    try:
        rec = InspectionRecord(
            id=f"INSP-{uuid.uuid4().hex[:8].upper()}",
            sample_id=target_sample_id,
            prediction=result.prediction,
            confidence=result.confidence,
            anomaly_score=result.anomaly_score,
            defect_type=result.defect_type,
            defect_count=result.defect_count,
            max_defect_area_px=result.max_defect_area_px,
            inference_time_ms=result.inference_time_ms,
            image_path=saved_path,
        )
        db.add(rec)
        db.commit()
    except Exception:
        pass

    return result


@router.get("/metrics", response_model=EvaluationMetrics)
def get_evaluation_metrics():
    data = get_dataset_manifest()
    metrics = inspection_engine.evaluate_test_set(data["manifest"])
    return metrics


@router.get("/results")
def get_inspection_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(InspectionRecord).order_by(InspectionRecord.created_at.desc())
    total = query.count()
    records = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "sample_id": r.sample_id,
                "prediction": r.prediction,
                "confidence": r.confidence,
                "anomaly_score": r.anomaly_score,
                "defect_type": r.defect_type,
                "defect_count": r.defect_count,
                "inference_time_ms": r.inference_time_ms,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
    }
