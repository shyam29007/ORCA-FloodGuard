"""Authentication API endpoints for login, registration, and role identity."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from backend.app.core.config import settings
from backend.app.schemas.auth import (
    UserRole,
    UserLoginRequest,
    UserRegisterRequest,
    UserProfile,
    TokenResponse,
)
from backend.app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    USERS_DATABASE,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="Log in with email and password")
def login(req: UserLoginRequest) -> TokenResponse:
    """Authenticate user credentials and issue cryptographically signed JWT access token."""
    email = req.email.strip().lower()
    user = USERS_DATABASE.get(email)

    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # In production environment, DEMO evaluation accounts are strictly disabled
    if getattr(settings, "APP_ENV", "development").lower() == "production" and user.get("role") == UserRole.DEMO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="DEMO evaluation accounts are disabled in production mode.",
        )

    profile = UserProfile(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        district=user["district"],
        created_at=user["created_at"],
    )

    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"].value,
        "district": user["district"],
    }
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=86400,
        user=profile,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user account")
def register(req: UserRegisterRequest) -> TokenResponse:
    """Register a new citizen or emergency response official account."""
    email = req.email.strip().lower()
    if email in USERS_DATABASE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    new_user = {
        "id": f"usr-{uuid.uuid4().hex[:8]}",
        "email": email,
        "full_name": req.full_name.strip(),
        "password_hash": hash_password(req.password),
        "role": req.role,
        "district": req.district,
        "created_at": datetime.now(timezone.utc),
    }
    USERS_DATABASE[email] = new_user

    profile = UserProfile(
        id=new_user["id"],
        email=new_user["email"],
        full_name=new_user["full_name"],
        role=new_user["role"],
        district=new_user["district"],
        created_at=new_user["created_at"],
    )

    token_data = {
        "sub": new_user["id"],
        "email": new_user["email"],
        "full_name": new_user["full_name"],
        "role": new_user["role"].value,
        "district": new_user["district"],
    }
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=86400,
        user=profile,
    )


@router.get("/me", response_model=UserProfile, summary="Get currently authenticated user identity")
def get_me(user: UserProfile = Depends(get_current_user)) -> UserProfile:
    """Return user profile for the validated bearer token session."""
    return user


@router.get("/demo-accounts", summary="Get pre-configured accounts for college hackathon evaluation")
def get_demo_accounts():
    """Return list of evaluator demo accounts for one-click authentication in the frontend.
    
    In production mode, pre-configured demo credentials are strictly disabled and return empty.
    """
    if getattr(settings, "APP_ENV", "development").lower() == "production":
        return []

    return [
        {
            "role": "DEMO",
            "email": "demo@orca.punjab.gov.in",
            "password": "Demo@123",
            "label": "Evaluation Sandbox (Restricted Observer)",
            "permissions": ["View Public Dashboard", "Run Simulated Flood Assessments", "View Agent Execution Traces", "Read-Only Advisory Queue (No Broadcast Rights)"],
        },
        {
            "role": "CITIZEN",
            "email": "citizen@orca.punjab.gov.in",
            "password": "Citizen@123",
            "label": "Local Citizen (Public Portal & Incident Reporting)",
            "permissions": ["View Public Dashboard", "Submit Flood Incident Reports", "View Verified Evacuation Maps"],
        },
        {
            "role": "OFFICIAL",
            "email": "official@orca.punjab.gov.in",
            "password": "Official@123",
            "label": "Disaster Management Official (SDMA / DDMA Punjab)",
            "permissions": ["Run Agentic Flood Assessments", "Review Citizen Reports", "Draft & Authorize Emergency Alerts"],
        },
        {
            "role": "ADMIN",
            "email": "admin@orca.punjab.gov.in",
            "password": "Admin@123",
            "label": "System Administrator",
            "permissions": ["Full System Control", "Configure Telemetry Providers", "System Diagnostics & RBAC Management"],
        },
    ]

