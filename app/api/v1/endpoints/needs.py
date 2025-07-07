from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_need  # Import the new crud_need
from app.db.database import get_db
from app.schemas import schemas

router = APIRouter(
    prefix="/needs",  # Plural prefix for the resource
    tags=["Needs"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=schemas.Need, status_code=status.HTTP_201_CREATED)
def create_need(need: schemas.NeedCreate, db: Session = Depends(get_db)):
    # No email uniqueness check for needs, since multiple
    # needs can have the same contact email
    return crud_need.create_need(db=db, need=need)


@router.get("/", response_model=List[schemas.Need])
def read_needs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    needs = crud_need.get_needs(db, skip=skip, limit=limit)
    return needs


@router.get("/{need_id}", response_model=schemas.Need)
def read_need(need_id: int, db: Session = Depends(get_db)):
    db_need = crud_need.get_need(db, need_id=need_id)
    if db_need is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Need not found"
        )
    return db_need


@router.put("/{need_id}", response_model=schemas.Need)
def update_need(need_id: int, need: schemas.NeedCreate, db: Session = Depends(get_db)):
    db_need = crud_need.update_need(db, need_id, need)
    if db_need is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Need not found"
        )
    return db_need


@router.delete("/{need_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_need(need_id: int, db: Session = Depends(get_db)):
    success = crud_need.delete_need(db, need_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Need not found"
        )
    return {"message": "Need deleted successfully"}
