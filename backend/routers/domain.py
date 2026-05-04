import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.operational import ExpenseReport, TransportationCost
from models.user import User
from schemas.domain import ApiEnvelope, ExpenseReportIn, ExpenseReportOut, TransportationCostOut
from utils.auth import get_current_user
from utils.observability import request_id_ctx
from utils.masking import mask_sensitive
from utils.remote_fetch import fetch_remote_text

router = APIRouter(prefix="/api/domain", tags=["domain"])


def _report_out(report: ExpenseReport, costs: list[TransportationCost]) -> ExpenseReportOut:
    return ExpenseReportOut(
        id=report.id,
        employee_name=report.employee_name,
        report_number=report.report_number,
        status=report.status,
        currency=report.currency,
        total_amount=report.total_amount,
        source_file_url=report.source_file_url,
        transportation_costs=[
            TransportationCostOut(
                id=c.id,
                report_id=c.report_id,
                transport_type=c.transport_type,
                origin=c.origin,
                destination=c.destination,
                distance_km=c.distance_km,
                amount=c.amount,
                currency=c.currency,
                receipt_url=c.receipt_url,
                occurred_at=c.occurred_at,
            )
            for c in costs
        ],
    )


@router.post("/expense-reports", response_model=ApiEnvelope, status_code=201)
def create_expense_report(
    body: ExpenseReportIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report_id = str(uuid.uuid4())
    total = sum(item.amount for item in body.transportation_costs)
    report = ExpenseReport(
        id=report_id,
        user_id=current_user.id,
        employee_name=body.employee_name,
        report_number=body.report_number,
        status=body.status,
        currency=body.currency,
        total_amount=total,
        source_file_url=body.source_file_url,
    )
    db.add(report)
    costs = []
    for item in body.transportation_costs:
        cost = TransportationCost(id=str(uuid.uuid4()), report_id=report_id, **item.model_dump())
        db.add(cost)
        costs.append(cost)
    db.commit()
    return ApiEnvelope(data=_report_out(report, costs).model_dump(), request_id=request_id_ctx.get())


@router.get("/expense-reports", response_model=ApiEnvelope)
def list_expense_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reports = db.query(ExpenseReport).filter(ExpenseReport.user_id == current_user.id).order_by(ExpenseReport.created_at.desc()).all()
    data: list[dict[str, Any]] = []
    for report in reports:
        costs = db.query(TransportationCost).filter(TransportationCost.report_id == report.id).all()
        data.append(_report_out(report, costs).model_dump())
    return ApiEnvelope(data=mask_sensitive(data), request_id=request_id_ctx.get())


@router.get("/application-info", response_model=ApiEnvelope)
def application_info(current_user: User = Depends(get_current_user)):
    return ApiEnvelope(
        data={
            "name": "MCP Hub Expense Reimbursement",
            "domain": "expense_report_transportation_cost",
            "capabilities": [
                "create_expense_report",
                "list_expense_reports",
                "download_file",
                "normalize_transportation_costs",
            ],
        },
        request_id=request_id_ctx.get(),
    )


@router.get("/files", response_model=ApiEnvelope)
def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(ExpenseReport).filter(
        ExpenseReport.user_id == current_user.id,
        ExpenseReport.source_file_url.isnot(None),
    ).order_by(ExpenseReport.created_at.desc()).all()
    return ApiEnvelope(
        data=[
            {
                "report_id": row.id,
                "report_number": row.report_number,
                "url": row.source_file_url,
            }
            for row in rows
        ],
        request_id=request_id_ctx.get(),
    )


@router.post("/file-download", response_model=ApiEnvelope)
async def download_file(url: str = Query(...), current_user: User = Depends(get_current_user)):
    try:
        result = await asyncio.to_thread(fetch_remote_text, url, request_id=request_id_ctx.get())
    except ValueError as exc:
        raise HTTPException(400, f"Blocked URL: {exc}")
    return ApiEnvelope(
        data=result.as_dict(),
        request_id=request_id_ctx.get(),
    )
