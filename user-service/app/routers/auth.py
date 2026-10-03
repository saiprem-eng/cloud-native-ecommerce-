"""Auth router for User Service — register, login, logout, token refresh, password management."""

from fastapi import APIRouter, status
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    ConfirmRegistrationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    RefreshTokenRequest,
    LogoutRequest,
    TokenResponse,
    MessageResponse,
)
from app.services.cognito_service import cognito_service

router = APIRouter()


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(payload: RegisterRequest):
    """
    Register a new user account.

    - Creates user in AWS Cognito User Pool
    - Sends verification email with OTP
    - Returns confirmation that registration email was sent
    """
    result = cognito_service.register_user(
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
        role=payload.role.value,
    )
    return MessageResponse(message=result["message"], success=True)


@router.post(
    "/confirm",
    response_model=MessageResponse,
    summary="Confirm email with OTP",
)
async def confirm_registration(payload: ConfirmRegistrationRequest):
    """Confirm user registration using the 6-digit OTP sent to email."""
    result = cognito_service.confirm_registration(
        email=payload.email,
        confirmation_code=payload.confirmation_code,
    )
    return MessageResponse(**result)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT tokens",
)
async def login(payload: LoginRequest):
    """
    Authenticate user credentials.

    Returns:
    - **access_token**: Short-lived token for API calls (1 hour)
    - **refresh_token**: Long-lived token to get new access tokens (30 days)
    - **id_token**: JWT containing user identity claims
    """
    result = cognito_service.login_user(
        email=payload.email,
        password=payload.password,
    )
    return TokenResponse(**result)


@router.post(
    "/refresh",
    response_model=dict,
    summary="Refresh access token",
)
async def refresh_token(payload: RefreshTokenRequest):
    """Obtain a new access token using a valid refresh token."""
    # Note: In production, derive email from the refresh token's stored session
    # For simplicity, this uses a stored mapping; add Redis session store if needed
    result = cognito_service.refresh_token(
        refresh_token=payload.refresh_token,
        email="",  # Will be enhanced with session store
    )
    return result


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and invalidate tokens",
)
async def logout(payload: LogoutRequest):
    """
    Globally sign out user — invalidates ALL tokens (access + refresh) across all devices.
    """
    result = cognito_service.logout_user(access_token=payload.access_token)
    return MessageResponse(**result)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request password reset",
)
async def forgot_password(payload: ForgotPasswordRequest):
    """Trigger password reset flow — sends OTP code to user's registered email."""
    result = cognito_service.forgot_password(email=payload.email)
    return MessageResponse(**result)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password with OTP",
)
async def reset_password(payload: ResetPasswordRequest):
    """Complete password reset using the OTP code received via email."""
    result = cognito_service.reset_password(
        email=payload.email,
        code=payload.confirmation_code,
        new_password=payload.new_password,
    )
    return MessageResponse(**result)
