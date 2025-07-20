from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import secrets
import pyotp
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import google.generativeai as genai
from dotenv import load_dotenv
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from typing import Optional, List
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import asyncio

# These imports are based on your original file structure.
# Ensure these files exist and the functions are correctly defined.
from .resume_parser import parse_resume
from .gemini_services import enhance_profile_with_gemini, generate_application_materials
from .job_matching_service import run_job_matching_for_all_users

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("job_bot.log"),
                        logging.StreamHandler()
                    ])

# --- Environment and API Key Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logging.error("GEMINI_API_KEY not found in .env file.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# --- Rate Limiting ---
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


# --- Security and JWT Configuration ---
SECRET_KEY = os.environ.get("SECRET_KEY", "a_very_secret_and_insecure_default_key_for_dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

# --- Database Connection ---
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client.job_bot_db
users_collection = db.users
profiles_collection = db.profiles
seen_jobs_collection = db.seen_jobs
recommended_jobs_collection = db.recommended_jobs
saved_jobs_collection = db.saved_jobs
password_reset_tokens_collection = db.password_reset_tokens

# --- Pydantic Models ---
class User(BaseModel):
    email: EmailStr

class UserCreate(User):
    password: str

class UserInDB(UserCreate):
    hashed_password: str
    mfa_secret: Optional[str] = None
    mfa_enabled: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    token: str
    new_password: str

class MFASetup(BaseModel):
    email: EmailStr
    password: str

class MFAVerify(BaseModel):
    email: EmailStr
    token: str

class MFADisable(BaseModel):
    email: EmailStr
    password: str
    token: str

class JobFeedback(BaseModel):
    feedback: bool # True for thumbs up, False for thumbs down

# --- Helper Functions ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = request.cookies.get("access_token")
    logging.info(f"Token from cookie in get_current_user: {token}")
    logging.info(f"SECRET_KEY used for decoding: {SECRET_KEY}")

    if not token:
        logging.warning("No token found in cookie.")
        raise credentials_exception

    logging.info(f"Attempting to decode token: {token}")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logging.warning("Token payload missing 'sub' (email).")
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError as e:
        logging.error(f"JWT decoding failed: {e}", exc_info=True)
        raise credentials_exception
    except Exception as e:
        logging.error(f"Unexpected error during token decoding: {e}", exc_info=True)
        raise credentials_exception

    user = await users_collection.find_one({"email": token_data.email})
    if user is None:
        logging.warning(f"User not found for email: {token_data.email}")
        raise credentials_exception
    logging.info(f"User {user['email']} successfully authenticated.")
    return user

# --- Standard API Endpoints (Register, Token, etc.) ---
@app.post("/api/register")
@limiter.limit("5/minute")
async def register(request: Request, user: UserCreate):
    db_user = await users_collection.find_one({"email": user.email})
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    user_document = {"email": user.email, "hashed_password": hashed_password, "mfa_enabled": False}
    await users_collection.insert_one(user_document)
    return {"message": "User registered successfully"}

@app.post("/api/token", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user = await users_collection.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60}

# --- OAuth2 Provider for Chrome Extension ---
AUTHORIZED_CLIENT_IDS = [
    "kaodidikhmkbfbbfghmjdlfjjplaceih",
]

@app.get("/api/oauth2/authorize", response_class=HTMLResponse)
async def authorize_form(request: Request, client_id: str, redirect_uri: str, response_type: str):
    if client_id not in AUTHORIZED_CLIENT_IDS:
        raise HTTPException(status_code=400, detail="Invalid or unauthorized client_id")
    if response_type != 'token':
        raise HTTPException(status_code=400, detail="Unsupported response_type. Please use 'token'.")

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login to Job Bot</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #f4f7f9; }}
            .login-container {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); width: 100%; max-width: 400px; text-align: center; }}
            h1 {{ color: #1a202c; }}
            p {{ color: #555; margin-bottom: 25px;}}
            form {{ display: flex; flex-direction: column; }}
            input {{ padding: 12px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 8px; font-size: 16px; }}
            button {{ padding: 12px; font-size: 16px; cursor: pointer; background-color: #4285f4; color: white; border: none; border-radius: 8px; transition: background-color 0.3s; }}
            button:hover {{ background-color: #357ae8; }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <h1>Job Bot</h1>
            <p>Log in to authorize the Chrome Extension</p>
            <form action="/api/oauth2/login" method="post">
                <input type="hidden" name="client_id" value="{client_id}">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                <input type="email" name="username" placeholder="Email" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Log In & Authorize</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.post("/api/oauth2/login")
async def authorize_login(client_id: str = Form(...), redirect_uri: str = Form(...), username: str = Form(...), password: str = Form(...)):
    if client_id not in AUTHORIZED_CLIENT_IDS:
        raise HTTPException(status_code=400, detail="Invalid or unauthorized client_id")

    user = await users_collection.find_one({"email": username})
    if not user or not verify_password(password, user.get("hashed_password")):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user["email"]}, expires_delta=expires)
    return RedirectResponse(f"{redirect_uri}#access_token={access_token}&token_type=bearer")

# --- Password Reset and MFA Endpoints ---
@app.post("/api/password-reset-request")
@limiter.limit("5/minute")
async def password_reset_request(request: Request, reset_request: PasswordResetRequest):
    user = await users_collection.find_one({"email": reset_request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    await password_reset_tokens_collection.insert_one({"email": reset_request.email, "token": token, "expires_at": expires_at})
    logging.info(f"Password reset token for {reset_request.email}: {token}")
    return {"message": "Password reset link sent to your email (check logs for token)."}

@app.post("/api/password-reset-confirm")
@limiter.limit("5/minute")
async def password_reset_confirm(request: Request, confirm_request: PasswordResetConfirm):
    reset_record = await password_reset_tokens_collection.find_one({"email": confirm_request.email, "token": confirm_request.token})
    if not reset_record or reset_record["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    hashed_password = get_password_hash(confirm_request.new_password)
    await users_collection.update_one({"email": confirm_request.email}, {"$set": {"hashed_password": hashed_password}})
    await password_reset_tokens_collection.delete_one({"_id": reset_record["_id"]})
    return {"message": "Password has been reset successfully."}

@app.post("/api/mfa-setup")
@limiter.limit("5/minute")
async def mfa_setup(request: Request, mfa_data: MFASetup):
    user = await users_collection.find_one({"email": mfa_data.email})
    if not user or not verify_password(mfa_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA is already enabled.")
    secret = pyotp.random_base32()
    await users_collection.update_one({"email": mfa_data.email}, {"$set": {"mfa_secret": secret}})
    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=mfa_data.email, issuer_name="JobBot")
    logging.info(f"MFA Setup URI for {mfa_data.email}: {otp_uri}")
    return {"message": "MFA setup initiated. Scan QR code (check logs for URI).", "otp_uri": otp_uri}

@app.post("/api/mfa-verify")
@limiter.limit("5/minute")
async def mfa_verify(request: Request, mfa_data: MFAVerify):
    user = await users_collection.find_one({"email": mfa_data.email})
    if not user or not user.get("mfa_secret"):
        raise HTTPException(status_code=400, detail="MFA not set up.")
    if pyotp.TOTP(user["mfa_secret"]).verify(mfa_data.token):
        await users_collection.update_one({"email": mfa_data.email}, {"$set": {"mfa_enabled": True}})
        return {"message": "MFA verified and enabled."}
    raise HTTPException(status_code=401, detail="Invalid MFA token.")

@app.post("/api/mfa-disable")
@limiter.limit("5/minute")
async def mfa_disable(request: Request, mfa_data: MFADisable):
    user = await users_collection.find_one({"email": mfa_data.email})
    if not user or not verify_password(mfa_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA is not enabled.")
    if pyotp.TOTP(user["mfa_secret"]).verify(mfa_data.token):
        await users_collection.update_one({"email": mfa_data.email}, {"$set": {"mfa_enabled": False, "mfa_secret": None}})
        return {"message": "MFA disabled."}
    raise HTTPException(status_code=401, detail="Invalid MFA token.")

# --- Core Application Endpoints (CV, Matches, etc.) ---
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_FILE_TYPES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]

@app.get("/api/me/profile")
@limiter.limit("60/minute")
async def get_my_profile(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Retrieves the profile for the currently authenticated user.
    """
    profile = await profiles_collection.find_one({"user_id": current_user["_id"]})
    if profile:
        # Convert ObjectId fields to string for JSON serialization
        if "_id" in profile:
            profile["_id"] = str(profile["_id"])
        if "user_id" in profile:
            profile["user_id"] = str(profile["user_id"])
        return profile
    raise HTTPException(status_code=404, detail="Profile not found. Please upload a CV.")

@app.post("/api/cv-upload")
@limiter.limit("5/minute")
async def cv_upload(request: Request, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 5 MB.")
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF and DOCX allowed.")
    
    temp_file_path = f"/tmp/{secrets.token_hex(8)}_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        buffer.write(file_content)
    
    resume_text = parse_resume(temp_file_path)
    profile_data = enhance_profile_with_gemini(resume_text)
    
    await profiles_collection.update_one(
        {"user_id": current_user["_id"]},
        {"$set": {"user_id": current_user["_id"], **profile_data}},
        upsert=True
    )
    os.remove(temp_file_path)
    return {"message": f"CV uploaded and profile updated for {current_user['email']}"}

@app.get("/api/matches", response_model=List[dict])
@limiter.limit("60/minute")
async def get_job_matches(request: Request, current_user: dict = Depends(get_current_user), status: Optional[str] = None):
    query = {"user_id": current_user["_id"]}
    if status:
        query["application_status"] = status
    matches = await recommended_jobs_collection.find(query).to_list(length=None)
    for match in matches:
        if "_id" in match:
            match["_id"] = str(match["_id"])
        if "user_id" in match:
            match["user_id"] = str(match["user_id"])
    return matches

@app.post("/api/matches/{job_id}/feedback")
@limiter.limit("60/minute")
async def submit_job_feedback(request: Request, job_id: str, feedback: JobFeedback, current_user: dict = Depends(get_current_user)):
    result = await recommended_jobs_collection.update_one(
        {"user_id": current_user["_id"], "job_id": job_id},
        {"$set": {"user_feedback": feedback.feedback, "feedback_timestamp": datetime.utcnow()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Job match not found.")
    return {"message": "Feedback recorded."}

@app.post("/api/matches/{job_id}/apply")
@limiter.limit("60/minute")
async def apply_for_job(request: Request, job_id: str, current_user: dict = Depends(get_current_user)):
    job_match = await recommended_jobs_collection.find_one({"user_id": current_user["_id"], "job_id": job_id})
    if not job_match:
        raise HTTPException(status_code=404, detail="Job match not found.")
    await recommended_jobs_collection.update_one(
        {"_id": job_match["_id"]},
        {"$set": {"application_status": "applied", "applied_at": datetime.utcnow()}}
    )
    application_url = job_match.get("job_details", {}).get("ats_url") or job_match.get("job_details", {}).get("redirect_url")
    if not application_url:
        raise HTTPException(status_code=500, detail="Application URL not available.")
    return {"message": "Job marked as applied.", "application_url": application_url}

@app.delete("/api/matches/{job_id}")
@limiter.limit("60/minute")
async def delete_job_match(request: Request, job_id: str, current_user: dict = Depends(get_current_user)):
    result = await recommended_jobs_collection.delete_one({"user_id": current_user["_id"], "job_id": job_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Job match not found.")
    return {"message": "Job match removed."}

@app.post("/api/matches/{job_id}/save")
@limiter.limit("60/minute")
async def save_job_match(request: Request, job_id: str, current_user: dict = Depends(get_current_user)):
    job_match = await recommended_jobs_collection.find_one({"user_id": current_user["_id"], "job_id": job_id})
    if not job_match:
        raise HTTPException(status_code=404, detail="Job match not found.")

    # Check if the job is already saved
    existing_saved_job = await saved_jobs_collection.find_one({"user_id": current_user["_id"], "job_id": job_id})
    if existing_saved_job:
        return {"message": "Job already saved.", "job_id": job_id}

    # Save the job to the saved_jobs_collection
    await saved_jobs_collection.insert_one({
        "user_id": current_user["_id"],
        "job_id": job_id,
        "job_details": job_match["job_details"],
        "saved_at": datetime.utcnow()
    })
    return {"message": "Job saved successfully.", "job_id": job_id}

@app.get("/api/saved-jobs", response_model=List[dict])
@limiter.limit("60/minute")
async def get_saved_jobs(request: Request, current_user: dict = Depends(get_current_user)):
    saved_jobs = await saved_jobs_collection.find({"user_id": current_user["_id"]}).to_list(length=None)
    for job in saved_jobs:
        if "_id" in job:
            job["_id"] = str(job["_id"])
        if "user_id" in job:
            job["user_id"] = str(job["user_id"])
    return saved_jobs

@app.delete("/api/saved-jobs/{job_id}")
@limiter.limit("60/minute")
async def delete_saved_job(request: Request, job_id: str, current_user: dict = Depends(get_current_user)):
    result = await saved_jobs_collection.delete_one({"user_id": current_user["_id"], "job_id": job_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Saved job not found.")
    return {"message": "Saved job removed."}

@app.post("/api/run-job-matching")
@limiter.limit("5/hour")
async def trigger_job_matching(request: Request, current_user: dict = Depends(get_current_user)):
    logging.info(f"Job matching triggered by user: {current_user['email']}")
    await run_job_matching_for_all_users(users_collection, profiles_collection, seen_jobs_collection, recommended_jobs_collection, saved_jobs_collection)
    return {"message": "Job matching process initiated."}

@app.post("/api/jobs/{job_id}/generate-documents")
@limiter.limit("10/minute")
async def generate_documents_for_job(request: Request, job_id: str, current_user: dict = Depends(get_current_user)):
    """
    Generates tailored application documents for a specific job match.
    """
    # 1. Fetch user profile
    profile = await profiles_collection.find_one({"user_id": current_user["_id"]})
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found. Please upload a CV first.")

    # 2. Fetch the specific job from recommended_jobs_collection
    job_data = await recommended_jobs_collection.find_one({"user_id": current_user["_id"], "job_id": job_id})
    if not job_data:
        raise HTTPException(status_code=404, detail="Job match not found.")

    loop = asyncio.get_event_loop()

    # 3. Generate application materials (cover letter, suggestions) in a thread
    materials = await loop.run_in_executor(
        None, generate_application_materials, job_data, profile
    )
    if not materials:
        raise HTTPException(status_code=500, detail="Failed to generate application materials.")

    # 5. Combine and return the results
    final_documents = {
        "cover_letter": materials.get("cover_letter"),
        "resume_suggestions": materials.get("resume_suggestions"),
        "question_answers": materials.get("question_answers"),
    }

    # Optionally, save the generated documents back to the job_data document
    await recommended_jobs_collection.update_one(
        {"_id": job_data["_id"]},
        {"$set": {"generated_documents": final_documents}}
    )

    return final_documents

# --- Scheduler ---
scheduler = AsyncIOScheduler()

async def cleanup_old_recommended_jobs():
    logging.info("Running daily cleanup of old recommended jobs.")
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    result = await recommended_jobs_collection.delete_many({"timestamp": {"$lt": thirty_days_ago}})
    logging.info(f"Cleaned up {result.deleted_count} old recommended jobs.")

@app.on_event("startup")
async def startup_event():
    logging.info("Starting scheduler...")
    scheduler.add_job(run_job_matching_for_all_users, "cron", hour=3, minute=0, args=[users_collection, profiles_collection, seen_jobs_collection, recommended_jobs_collection, saved_jobs_collection])
    scheduler.add_job(cleanup_old_recommended_jobs, "cron", hour=4, minute=0)
    scheduler.start()
    logging.info("Scheduler started.")

@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Shutting down scheduler...")
    scheduler.shutdown()
    logging.info("Scheduler shut down.")

# --- Root Endpoint ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Job Bot API"}


# --- Static Files ---
app.mount("/static", StaticFiles(directory="/home/cube/Documents/jobot/job_bot_project/backend/static"), name="static")

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    with open("/home/cube/Documents/jobot/job_bot_project/backend/static/login.html") as f:
        return HTMLResponse(content=f.read())

@app.get("/register", response_class=HTMLResponse)
async def register_page():
    with open("/home/cube/Documents/jobot/job_bot_project/backend/static/register.html") as f:
        return HTMLResponse(content=f.read())

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, current_user: dict = Depends(get_current_user)):
    # If we reach here, current_user is successfully authenticated
    with open("/home/cube/Documents/jobot/job_bot_project/backend/static/index.html") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
