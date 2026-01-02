from fastapi import APIRouter, HTTPException, Depends
from supabase import Client
from postgrest.exceptions import APIError
from app.models import UserCreate, addBalance, user_set_status_response, user_set_status, fetch_user_info
from app.database import get_supabase
from keycloak import KeycloakAdmin
from app.config import settings
from app.auth import require_auth
import logging, traceback

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')


router = APIRouter()


@router.get("/auth/jwt")
async def get_decoded_jwt(token_data: dict = Depends(require_auth)):
    """Return the decoded JWT payload for the current request."""
    return token_data


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
    # token_data: dict = Depends(require_admin),
    #user=Depends(keycloak.get_current_user),
):
    """
    Create a user in Supabase and Keycloak.
    """
    logger = logging.getLogger("routes")
    logger.info("/users endpoint called with: %s", request.dict())
    
    # Create user in Supabase
    try:
        logger.info("Calling Supabase RPC create_user...")
        db_result = supabase.rpc(
            "create_user",
            {
                "card_id_input": request.card_id,
                "first_name_input": request.first_name,
                "last_name_input": request.last_name,
            }, 
        ).execute()
        logger.info("Supabase RPC result: %s", db_result)
        db_result = {"status": "success", "card_id": request.card_id}
    except Exception as e:
        logger.error("Supabase error: %s", e)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Supabase error: {e}")
    # FIXME if user creation fails in Keycloak, we should roll back the Supabase creation
    # Create user in Keycloak
    try:
        logger.info("Creating Keycloak admin connection for realm: %s", settings.keycloak_realm)
        keycloak_admin = KeycloakAdmin(
            server_url=settings.keycloak_url,
            username=settings.keycloak_admin_user,
            password=settings.keycloak_admin_pass, 
            realm_name=settings.keycloak_realm,
            client_id="admin-cli",
            verify=False  # Set to True if using trusted SSL certs
        )
        logger.info("Keycloak admin authenticated successfully")
        
        logger.info("Creating user in Keycloak: email=%s, first_name=%s, last_name=%s", 
                    request.email, request.first_name, request.last_name)
        user_id = keycloak_admin.create_user({
            "email": request.email,
            "username": request.card_id,
            "enabled": True,
            "firstName": request.first_name,
            "lastName": request.last_name,
            "credentials": [{"value": request.password, "type": "password"}]
        })
        logger.info("User created in Keycloak with ID: %s", user_id)
        kc_result = {"status": "created", "user_id": user_id}
    except Exception as e:
        logger.error("Keycloak error: %s", e)
        logger.error("Error type: %s", type(e).__name__)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Keycloak error: {e}")
    
    return {"db": db_result, "keycloak": kc_result}


@router.post("/user/add_balance")
async def add_balance(
    user_id: str,
    amount: int,
    request: addBalance,
    supabase: Client = Depends(get_supabase),
    user_data: dict = Depends(require_auth),
    # user=Depends(keycloak.get_current_user),
):
    """
    Add balance to a user's account. Requires authentication.
    """

    if request.card_id != int(user_data.get("preferred_username", -1)) and not "bb_admin" in user_data.get("realm_access", {}).get("roles", []):
        raise HTTPException(status_code=403, detail="Cannot add balance to another user's account")
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
    user_data: dict = Depends(require_auth),
):
    """
    Set a user's active status. Requires authentication.
    """

    if not "bb_admin" in user_data.get("realm_access", {}).get("roles", []):
        raise HTTPException(status_code=403, detail="BB Admin privileges required to set user status")

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
        elif "user status is already active=true" in error_msg:
            raise HTTPException(status_code=400, detail="User status is already active=TRUE")
        elif "user status is already active=false" in error_msg:
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
    user_data: dict = Depends(require_auth),
):
    """
    Fetch user information by user ID.
    """

    if request.user_id != int(user_data.get("preferred_username", -1)) and not "bb_admin" in user_data.get("realm_access", {}).get("roles", []):
        raise HTTPException(status_code=403, detail="Cannot fetch another user's information")
    try:
        result = supabase.rpc(
            "fetch_user_info",
            {
                "user_id_input": request.user_id,
            },
        ).execute()
        user_info = result.data
        return {
            "first_name": user_info['first_name'],
            "last_name": user_info['last_name'],
            "balance": user_info['balance'],
            "active": user_info['active'],
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
