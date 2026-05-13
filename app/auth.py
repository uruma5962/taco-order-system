"""Basic 認証。環境変数 APP_USER / APP_PASS で資格情報を設定する。"""
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

_security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> HTTPBasicCredentials:
    user_ok = secrets.compare_digest(credentials.username, settings.app_user)
    pass_ok = secrets.compare_digest(credentials.password, settings.app_pass)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials
