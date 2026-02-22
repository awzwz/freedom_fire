"""Processing endpoints — ingest CSV, process tickets."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import shutil
import zipfile
import tempfile
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.database import get_session
from app.adapters.persistence.repositories import SqlTicketRepository
from app.application.use_cases.process_ticket import BatchProcessUseCase, ProcessTicketUseCase
from app.config import settings
from app.infrastructure.api.dependencies import get_batch_process_uc, get_process_ticket_uc
from app.tools.seed_db import seed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/process", tags=["processing"])


@router.post("/ingest")
async def ingest_csv(drop: bool = False):
    """Load CSV data into the database."""
    data_dir = Path(settings.csv_data_path)
    if not data_dir.exists():
        raise HTTPException(status_code=400, detail=f"Data directory not found: {data_dir}")

    try:
        counts = await seed(data_dir, drop=drop)
        return {
            "status": "ok",
            "message": "CSV data ingested successfully",
            "counts": counts,
            "drop": drop,
        }
    except Exception as e:
        logger.exception("Error ingesting CSV data")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_files(
    file: UploadFile = File(...),
    batch_uc: BatchProcessUseCase = Depends(get_batch_process_uc),
    session: AsyncSession = Depends(get_session),
):
    """Upload a CSV or ZIP file, parse/seed it, and run processing."""
    data_dir = Path(settings.csv_data_path)
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        
    image_dir = data_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    try:
        filename = file.filename.lower()
        if filename.endswith(".zip"):
            with tempfile.TemporaryDirectory() as td:
                zip_path = Path(td) / "upload.zip"
                with open(zip_path, "wb") as f:
                    shutil.copyfileobj(file.file, f)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(td)
                
                # Move extracted files to their proper permanent directories
                for path in Path(td).rglob("*"):
                    # Ignore macOS hidden/metadata files
                    if path.is_file() and not path.name.startswith("._") and not path.name.startswith(".DS_Store"):
                        if path.suffix.lower() == ".csv":
                            shutil.copy2(path, data_dir / path.name)
                        elif path.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
                            shutil.copy2(path, image_dir / path.name)
                            
        elif filename.endswith(".csv"):
            dest_path = data_dir / file.filename
            with open(dest_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        else:
            raise HTTPException(status_code=400, detail="Only .csv and .zip files are supported.")
            
        # 1. Ingest newly uploaded data (skip logic handles duplicates)
        counts = await seed(data_dir, drop=False)
        
        # 2. Process all pending tickets
        results = await batch_uc.execute()
        await session.commit()
        
        successful = [r for r in results if r.error is None]
        failed = [r for r in results if r.error is not None]
        
        return {
            "status": "ok",
            "message": "Files uploaded and processed successfully",
            "ingested_counts": counts,
            "processed": {
                "total_processed": len(results),
                "successful": len(successful),
                "failed": len(failed),
            }
        }
    except Exception as e:
        logger.exception("Error processing upload file")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def process_all(
    batch_uc: BatchProcessUseCase = Depends(get_batch_process_uc),
    session: AsyncSession = Depends(get_session),
):
    """Process all unprocessed tickets (LLM + geocoding + assignment)."""
    results = await batch_uc.execute()
    await session.commit()

    successful = [r for r in results if r.error is None]
    failed = [r for r in results if r.error is not None]

    return {
        "status": "ok",
        "total_processed": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "results": [
            {
                "ticket_id": r.ticket_id,
                "ticket_guid": r.ticket_guid,
                "assigned_manager": r.assigned_manager,
                "assigned_office": r.assigned_office,
                "distance_km": r.distance_km,
                "fallback_used": r.fallback_used,
                "error": r.error,
            }
            for r in results
        ],
    }


@router.post("/{ticket_id}")
async def process_single(
    ticket_id: int,
    process_uc: ProcessTicketUseCase = Depends(get_process_ticket_uc),
    session: AsyncSession = Depends(get_session),
):
    """Process a single ticket by ID."""
    ticket_repo = SqlTicketRepository(session)
    ticket = await ticket_repo.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    result = await process_uc.execute(ticket)
    await session.commit()

    if result.error:
        return {"status": "error", "error": result.error, **_result_to_dict(result)}

    return {"status": "ok", **_result_to_dict(result)}


def _result_to_dict(r) -> dict:
    return {
        "ticket_id": r.ticket_id,
        "ticket_guid": r.ticket_guid,
        "assigned_manager": r.assigned_manager,
        "assigned_office": r.assigned_office,
        "distance_km": r.distance_km,
        "fallback_used": r.fallback_used,
    }
