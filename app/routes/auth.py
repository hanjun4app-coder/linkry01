"""Authentication routes - Login, password setup, token management"""
from fastapi import APIRouter, HTTPException, Header, status, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import jwt
import secrets
from app.config import settings
from app.database import get_db
from app.models import User, InstallationProfile, Family
from app.security import get_password_hash, verify_password, enforce_rate_limit, token_fingerprint
from app.email_service import send_internal_registration_completed_email
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# ==================== Test User (for development) ====================

TEST_USER = {
    "email": "test@example.com",
    "password": "password123",
    "user_id": "test_user",
    "family_id": 1,
    "role": "family_member"
}


# ==================== Schemas ====================

class LoginRequest(BaseModel):
    """Login request"""
    email: str
    password: str


class SetupPasswordRequest(BaseModel):
    """Password setup request"""
    token: str
    password: str
    password_confirm: str = ""
    confirm_password: str = ""


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token: str
    token_type: str = "bearer"
    role: str = ""


class UserInfo(BaseModel):
    """User information"""
    user_id: str
    family_id: str
    role: str


# ==================== Helper Functions ====================

def create_token(user_id: str, family_id, role: str) -> str:
    """Create JWT token"""
    now = datetime.utcnow()
    exp = now + timedelta(days=30)
    payload = {
        "user_id": user_id,
        "family_id": str(family_id),
        "role": role,
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp())
    }
    try:
        token = jwt.encode(payload, str(settings.SECRET_KEY), algorithm="HS256")
        return token
    except Exception as e:
        logger.error(f"Failed to create token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create token"
        )


def create_password_setup_token(data: dict) -> str:
    """Create password setup token (expires in 24 hours)"""
    now = datetime.utcnow()
    exp = now + timedelta(hours=24)
    payload = {
        **data,
        "type": "password_setup",
        "jti": secrets.token_urlsafe(24),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp())
    }
    token = jwt.encode(payload, str(settings.SECRET_KEY), algorithm="HS256")
    return token


def verify_password_setup_token(token: str) -> dict:
    """Verify password setup token"""
    try:
        payload = jwt.decode(
            token,
            str(settings.SECRET_KEY),
            algorithms=["HS256"],
            options={"verify_iat": False}
        )
        if payload.get("type") != "password_setup":
            raise HTTPException(status_code=401, detail="Invalid token type")
        exp = payload.get("exp", 0)
        if isinstance(exp, datetime):
            exp = int(exp.timestamp())
        if exp < datetime.utcnow().timestamp():
            raise HTTPException(status_code=401, detail="Token expired")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def decode_token(token: str) -> dict:
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, str(settings.SECRET_KEY), algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def validate_setup_password_strength(password: str):
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    if not any(char.isalpha() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must include at least one letter"
        )
    if not any(char.isdigit() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must include at least one number"
        )


# ==================== Routes ====================

@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    User login
    
    Checks:
    1. User exists with email
    2. Password is set (not empty)
    3. Password matches hash
    4. For family users: Installation must be completed
    """
    enforce_rate_limit(
        "login",
        request.email,
        max_attempts=10,
        window_seconds=3600,
        message="Too many sign-in attempts. Please wait and try again."
    )
    
    # First try test user (for development)
    if request.email == TEST_USER["email"] and request.password == TEST_USER["password"]:
        token = create_token(
            TEST_USER["user_id"],
            TEST_USER["family_id"],
            TEST_USER["role"]
        )
        logger.info(f"Login successful for test user")
        return TokenResponse(access_token=token, token=token, token_type="bearer", role=TEST_USER["role"])
    
    # Then try database users
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        logger.warning(f"Login failed: user not found for {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Gate 1: Check if password is set
    if not user.hashed_password or user.hashed_password == "":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password not yet set. Check your email for setup link."
        )
    
    # Gate 2: Verify password matches
    if not verify_password(request.password, user.hashed_password):
        logger.warning(f"Login failed: wrong password for {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # All gates passed - create JWT
    runtime_family_id = str(user.family_id or 0)
    if user.family_id:
        family = db.query(Family).filter(Family.id == user.family_id).first()
        if family:
            runtime_family_id = family.family_id

    token = create_token(
        str(user.id),
        runtime_family_id,
        user.role
    )
    
    logger.info(f"Login successful for {request.email}")
    return TokenResponse(access_token=token, token=token, token_type="bearer", role=user.role)


@router.post("/setup-password")
async def setup_password(
    request: SetupPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Family sets password using token from email
    
    Token must be valid and not expired.
    Passwords must match and meet minimum requirements.
    """
    enforce_rate_limit(
        "setup-password",
        token_fingerprint(request.token),
        max_attempts=5,
        window_seconds=3600,
        message="Too many password setup attempts. Please wait and try again."
    )
    
    # Validate passwords match
    confirm_password = request.password_confirm or request.confirm_password
    if request.password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    validate_setup_password_strength(request.password)
    
    # Verify token
    token_data = verify_password_setup_token(request.token)
    
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role != "family":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only family users can set password"
        )
    
    # Check if password already set
    if user.hashed_password and user.hashed_password != "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This setup link has already been used. Please sign in or request a new setup email."
        )
    
    # Hash and store password
    user.hashed_password = get_password_hash(request.password)
    user.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info("Password set for user_id=%s", user.id)

    try:
        send_internal_registration_completed_email(
            customer_email=user.email,
            user_id=str(user.id),
            family_id=str(user.family_id or ""),
        )
    except Exception as exc:
        logger.error(
            "Internal registration notification failed for user_id=%s: %s",
            user.id,
            exc.__class__.__name__,
        )
    
    return {
        "success": True,
        "message": "Password set successfully. You can now log in."
    }


@router.get("/verify-setup-token")
async def verify_setup_token(token: str, db: Session = Depends(get_db)):
    """Verify password setup token before showing the password form."""
    enforce_rate_limit(
        "setup-token-verify",
        token_fingerprint(token),
        max_attempts=5,
        window_seconds=3600,
        message="Too many setup link checks. Please wait and try again."
    )

    token_data = verify_password_setup_token(token)
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.hashed_password and user.hashed_password != "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This setup link has already been used. Please sign in or request a new setup email."
        )

    return {
        "success": True,
        "email": user.email,
        "password_set": bool(user.hashed_password),
        "expires_at": token_data.get("exp")
    }


@router.get("/me")
async def get_me(authorization: str = Header(None)):
    """Get current user information"""
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )

    try:
        parts = authorization.split()
        if len(parts) != 2:
            raise ValueError("Invalid format")

        scheme, token = parts
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization scheme"
            )

        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

        return UserInfo(
            user_id=payload.get("user_id"),
            family_id=payload.get("family_id"),
            role=payload.get("role")
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
