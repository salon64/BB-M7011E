from fastapi import APIRouter, HTTPException, Depends
from supabase import Client
from postgrest.exceptions import APIError
from app.models import UserCreate, addBalance, user_set_status_response, user_set_status, fetch_user_info
from app.database import get_supabase
from fastapi_keycloak import FastAPIKeycloak
import logging, traceback
from keycloak import KeycloakAdmin
from app.config import settings

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')

# Keycloak config from settings
#keycloak = FastAPIKeycloak(
#    server_url=settings.keycloak_url,
#    client_id=settings.keycloak_client_id,
#    client_secret=settings.keycloak_client_secret,
#    admin_client_secret=settings.keycloak_client_secret,
#    realm=settings.keycloak_realm,
#    callback_uri=settings.keycloak_callback_uri,
#    ssl_verification=False
#)


router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


#@router.get("/auth/me")
#async def get_current_user(user=Depends(keycloak.get_current_user)):
#    """Get information about the currently authenticated user"""
#    return {
#        "user_id": user.sub,
#        "username": user.preferred_username,
#        "email": user.email,
#        "roles": user.roles,
#        "service": "user-service",
#    }


@router.post("/users")
async def create_user(
    request: UserCreate,
    supabase: Client = Depends(get_supabase),
    #token_data: dict = Depends(require_admin),
    #user=Depends(keycloak.get_current_user),
):
    """
    Create a user in Supabase and Keycloak. Requires valid JWT (Keycloak) auth.
    token_data contains the decoded JWT payload.
    """
    logger = logging.getLogger("routes")
    logger.info("/users endpoint called with: %s", request.dict())
    print("/users endpoint called with:", request.dict())
    try:
        logger.info("Calling Supabase RPC create_user...")
        print("Calling Supabase RPC create_user...")
        db_result = supabase.rpc(
            "create_user",
            {
                "name_input": request.name,
                "email_input": request.email,
                "password_input": request.password,
            }, 
        ).execute()
        logger.info("Supabase RPC result: %s", db_result)
        db_result = {"status": "success"}
    except Exception as e:
        logger.error("Supabase error: %s", e)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Supabase error: {e}")
    
    try:
        keycloak_admin = KeycloakAdmin(
            server_url=settings.keycloak_url,
            username=settings.keycloak_admin_user,
            password=settings.keycloak_admin_pass, 
            realm_name=settings.keycloak_realm,
            client_id="admin-cli",
            verify=False  # Set to True if using trusted SSL certs
        )
        user_id = keycloak_admin.create_user({
            "email": request.email,
            "username": request.name,
            "enabled": True,
            "firstName": request.name,
            "lastName": request.Lastname,
            "credentials": [{"value": request.password, "type": "password"}]
        })
        kc_result = {"status": "created", "user_id": user_id}
    except Exception as e:
        logging.error("Keycloak error: %s", e)
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Keycloak error: {e}")
    return {"db": db_result , "keycloak": kc_result}


@router.post("/user/add_balance")
async def add_balance(
    user_id: str,
    amount: int,
    request: addBalance,
    supabase: Client = Depends(get_supabase),
    #user=Depends(keycloak.get_current_user),
):
    """
    Add balance to a user's account. Requires authentication.
    """
    try:
        result = supabase.rpc(
            "add_balance",
            {
                "user_id_input": request.card_id,
                "balance_input": request.amount,
            },
        ).execute()
        return {"user_id_input": request.card_id, "new_balance": int(result.data)}
    except APIError as e:
        error_msg = e.message.lower()
        if "user not found" in error_msg:
            raise HTTPException(status_code=404, detail="User not found")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )
    
@router.post("/user/set_status")
async def set_user_status(
    request: user_set_status,
    supabase: Client = Depends(get_supabase),
    #user=Depends(keycloak.get_current_user),
):
    """
    Set a user's active status. Requires authentication.
    """
    try:
        result = supabase.rpc(
            "user_status",
            {
                "user_id_input": request.user_id_input,
                "user_status_input": request.user_status_input,
            },
        ).execute()
        return user_set_status_response(response=result.data)
    except APIError as e:
        error_msg = e.message.lower()
        if "user not found" in error_msg:
            raise HTTPException(status_code=404, detail="User not found")
        elif "User status is already active=TRUE" in error_msg:
            raise HTTPException(status_code=400, detail="User status is already active=TRUE")
        elif "User status is already active=FALSE" in error_msg:
            raise HTTPException(status_code=400, detail="User status is already active=FALSE")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )
    
@router.post("/user/fetch_info")
async def fetch_user_info(
    request: fetch_user_info,
    supabase: Client = Depends(get_supabase),
    #user=Depends(keycloak.get_current_user),
):
    """
    Fetch user information by user ID. Requires authentication.
    """
    try:
        result = supabase.rpc(
            "fetch_user_info",
            {
                "user_id_input": request.user_id,
            },
        ).execute()
        user_info = result.data
        return {
            "user_name": user_info['user_name'],
            "user_email": user_info['user_email'],
            "user_balance": user_info['user_balance'],
            "user_status": user_info['user_status'],
        }
    except APIError as e:
        error_msg = e.message.lower()
        if "user not found" in error_msg:
            raise HTTPException(status_code=404, detail="User not found")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {e.message}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )