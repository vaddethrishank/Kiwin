from fastapi import APIRouter, Depends
from app.api import deps

router = APIRouter()

@router.get("/me")
def read_user_me(current_user = Depends(deps.get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role
    }
