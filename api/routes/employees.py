"""
FastAPI Employee Management Router.
Provides enterprise endpoints for CRUD, CSV import/export, search, and metrics.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from db.database import get_db
from api.schemas import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeListResponse,
    EmployeeStatsResponse, CSVImportSummary
)
from src.services import employee_service

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("/stats", response_model=EmployeeStatsResponse)
def get_employee_metrics(db: Session = Depends(get_db)):
    """Returns overview statistics: total count, active count, and department breakdown."""
    return employee_service.get_employee_stats(db)


@router.get("/departments", response_model=List[str])
def list_departments(db: Session = Depends(get_db)):
    """Returns a unique list of departments for dropdown filters."""
    stats = employee_service.get_employee_stats(db)
    depts = sorted(list(stats["department_distribution"].keys()))
    return depts


@router.get("/export-csv")
def export_employees_csv(
    search: Optional[str] = Query(None, description="Search term filter"),
    department: Optional[str] = Query(None, description="Department filter"),
    db: Session = Depends(get_db)
):
    """Exports employee records to a downloadable CSV file."""
    csv_data = employee_service.export_employees_to_csv(db, search=search, department=department)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=employees_export.csv",
            "Cache-Control": "no-cache"
        }
    )


@router.post("/import-csv", response_model=CSVImportSummary, status_code=status.HTTP_200_OK)
async def import_employees_csv(
    file: UploadFile = File(..., description="CSV file with employee records"),
    db: Session = Depends(get_db)
):
    """
    Uploads and processes an employee CSV file.
    Validates headers, emails, timezones, and returns an import audit summary.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Uploaded file must be a .csv file."
        )

    content = await file.read()
    summary = employee_service.import_employees_from_csv(db, content)
    return summary


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    search: Optional[str] = Query(None, description="Search by name, email, or code"),
    department: Optional[str] = Query(None, description="Filter by department"),
    status: Optional[str] = Query(None, description="Filter by employment status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Lists company employees with search and filtering support."""
    skip = (page - 1) * page_size
    items, total = employee_service.list_employees(
        db,
        search=search,
        department=department,
        status=status,
        skip=skip,
        limit=page_size
    )
    return EmployeeListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_in: EmployeeCreate,
    db: Session = Depends(get_db)
):
    """Creates a new employee record. Validates code and email uniqueness."""
    try:
        new_emp = employee_service.create_employee(db, employee_in)
        return new_emp
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db)
):
    """Retrieves an employee by database primary key ID."""
    emp = employee_service.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found."
        )
    return emp


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    employee_in: EmployeeUpdate,
    db: Session = Depends(get_db)
):
    """Updates an employee record."""
    try:
        updated = employee_service.update_employee(db, employee_id, employee_in)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {employee_id} not found."
            )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{employee_id}", status_code=status.HTTP_200_OK)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db)
):
    """Deletes an employee record and associated relationships."""
    deleted = employee_service.delete_employee(db, employee_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with ID {employee_id} not found."
        )
    return {"message": f"Employee {employee_id} deleted successfully.", "deleted": True}
