from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer


# ============================================================
# SIMPLE USER
# ============================================================

USERNAME = "admin"
PASSWORD = "admin123"


# ============================================================
# OAUTH2
# ============================================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token"
)


# ============================================================
# VERIFY TOKEN
# ============================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
):
    if token != USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return token