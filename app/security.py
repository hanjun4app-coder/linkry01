"""✅ JWT 认证和安全模块"""
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthCredential
from pydantic import BaseModel
from app.config import settings
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


class TokenPayload(BaseModel):
    """Token 载荷"""
    device_id: str
    family_id: str
    exp: int
    iat: int


def create_access_token(
    device_id: str,
    family_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 JWT token

    Args:
        device_id: 设备ID
        family_id: 家庭ID
        expires_delta: 过期时间，默认 365 天

    Returns:
        JWT token 字符串
    """
    if expires_delta is None:
        expires_delta = timedelta(days=365)

    expire = datetime.utcnow() + expires_delta
    payload = {
        "device_id": device_id,
        "family_id": family_id,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
    }

    try:
        encoded_jwt = jwt.encode(
            payload,
            str(settings.SECRET_KEY),
            algorithm="HS256"
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access token"
        )


async def verify_token(credentials: HTTPAuthCredential = Depends(security)) -> TokenPayload:
    """
    验证 JWT token

    Args:
        credentials: HTTPBearer 凭证

    Returns:
        TokenPayload 对象

    Raises:
        HTTPException: 如果 token 无效或过期
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            str(settings.SECRET_KEY),
            algorithms=["HS256"]
        )

        # 验证过期时间
        exp = payload.get("exp", 0)
        if exp < datetime.utcnow().timestamp():
            logger.warning(f"Token expired for device {payload.get('device_id')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )

        return TokenPayload(**payload)

    except jwt.ExpiredSignatureError:
        logger.warning("Expired token received")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token"
        )
