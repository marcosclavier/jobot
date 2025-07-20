
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
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
from resume_parser import parse_resume
from gemini_services import enhance_profile_with_gemini
from job_matching_service import run_job_matching_for_all_users

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("job_bot.log"),
                        logging.StreamHandler()
                    ])

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logging.error("GEMINI_API_KEY not found in .env file.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()

# --- Static Files ---
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Security ---
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    logging.warning("SECRET_KEY not found in .env file. Using a default, insecure key. This is not safe for production.")
    SECRET_KEY = "a_very_secret_and_insecure_default_key"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

# --- Database Connection ---
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client.job_bot_db
users_collection = db.users
profiles_collection = db.profiles
seen_jobs_collection = db.seen_jobs
recommended_jobs_collection = db.recommended_jobs
password_reset_tokens_collection = db.password_reset_tokens

# --- Pydantic Models ---
class User(BaseModel):
    email: str

class UserInDB(User):
    password: str
    mfa_secret: str | None = None
    mfa_enabled: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    email: str
    token: str
    new_password: str

class MFASetup(BaseModel):
    email: str
    password: str

class MFAVerify(BaseModel):
    email: str
    token: str

class MFADisable(BaseModel):
    email: str
    password: str
    token: str

class JobFeedback(BaseModel):
    feedback: bool # True for thumbs up, False for thumbs down

# --- Helper Functions ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = await users_collection.find_one({"email": token_data.email})
    if user is None:
        raise credentials_exception
    return user

# --- API Endpoints ---
@app.post("/api/register")
async def register(user: UserInDB):
    try:
        logging.info(f"Starting registration for email: {user.email}")
        db_user = await users_collection.find_one({"email": user.email})
        logging.info("Checked if user exists in DB")
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        hashed_password = get_password_hash(user.password)
        logging.info("Password hashed successfully")
        user_document = {"email": user.email, "hashed_password": hashed_password, "mfa_enabled": False, "mfa_secret": None}
        await users_collection.insert_one(user_document)
        logging.info("User inserted into DB successfully")
        return {"message": "User registered successfully"}
    except Exception as e:
        logging.error(f"Error during user registration: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during registration")

@app.post("/api/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await users_collection.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/password-reset-request")
async def password_reset_request(request: PasswordResetRequest):
    user = await users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate a secure, time-limited token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1) # Token valid for 1 hour

    await password_reset_tokens_collection.insert_one({
        "email": request.email,
        "token": token,
        "expires_at": expires_at
    })

    # In a real application, you would send this token via email to the user
    logging.info(f"Password reset token for {request.email}: {token}")
    return {"message": "Password reset link sent to your email (check logs for token)."}

@app.post("/api/password-reset-confirm")
async def password_reset_confirm(request: PasswordResetConfirm):
    reset_record = await password_reset_tokens_collection.find_one({
        "email": request.email,
        "token": request.token
    })

    if not reset_record or reset_record["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    hashed_password = get_password_hash(request.new_password)
    await users_collection.update_one(
        {"email": request.email},
        {"$set": {"hashed_password": hashed_password}}
    )
    await password_reset_tokens_collection.delete_one({"_id": reset_record["_id"]})

    return {"message": "Password has been reset successfully."}

@app.post("/api/mfa-setup")
async def mfa_setup(mfa_data: MFASetup):
    user = await users_collection.find_one({"email": mfa_data.email})
    if not user or not verify_password(mfa_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA is already enabled for this user.")

    secret = pyotp.random_base32()
    await users_collection.update_one(
        {"email": mfa_data.email},
        {"$set": {"mfa_secret": secret}}
    )
    
    # In a real app, you'd return a QR code image or URI for the authenticator app
    otp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=mfa_data.email,
        issuer_name="JobBot"
    )
    logging.info(f"MFA Setup URI for {mfa_data.email}: {otp_uri}")
    return {"message": "MFA setup initiated. Scan the QR code with your authenticator app (check logs for URI).", "otp_uri": otp_uri}

@app.post("/api/mfa-verify")
async def mfa_verify(mfa_data: MFAVerify):
    user = await users_collection.find_one({"email": mfa_data.email})
    if not user or not user.get("mfa_secret"):
        raise HTTPException(status_code=400, detail="MFA not set up for this user.")

    totp = pyotp.TOTP(user["mfa_secret"])
    if totp.verify(mfa_data.token):
        await users_collection.update_one(
            {"email": mfa_data.email},
            {"$set": {"mfa_enabled": True}}
        )
        return {"message": "MFA verified and enabled successfully."}
    else:
        raise HTTPException(status_code=401, detail="Invalid MFA token.")

@app.post("/api/mfa-disable")
async def mfa_disable(mfa_data: MFADisable):
    user = await users_collection.find_one({"email": mfa_data.email})
    if not user or not verify_password(mfa_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA is not enabled for this user.")

    totp = pyotp.TOTP(user["mfa_secret"])
    if totp.verify(mfa_data.token):
        await users_collection.update_one(
            {"email": mfa_data.email},
            {"$set": {"mfa_enabled": False, "mfa_secret": None}}
        )
        return {"message": "MFA disabled successfully."}
    else:
        raise HTTPException(status_code=401, detail="Invalid MFA token.")

@app.post("/api/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await users_collection.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.get("mfa_enabled"):
        # If MFA is enabled, the user needs to provide an MFA token
        # This is a simplified flow. In a real app, you'd have a separate MFA verification step after initial login.
        # For now, we'll assume the password field might contain "password|mfa_token" or similar for testing.
        # Or, you'd have a separate endpoint for MFA verification after a successful password login.
        # For this implementation, we'll just return a message indicating MFA is required.
        raise HTTPException(
            status_code=403,
            detail="MFA required. Please provide MFA token.",
            headers={"X-MFA-Required": "true"}
        )

    access_token = create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = await users_collection.find_one({"email": token_data.email})
    if user is None:
        raise credentials_exception
    
    # If MFA is enabled, ensure the token was generated after MFA verification
    # This is a placeholder. A more robust solution would involve a separate MFA-verified token.
    # For now, we'll assume if MFA is enabled, the user must have gone through the MFA login flow.
    # This might need refinement based on how the frontend handles MFA.
    if user.get("mfa_enabled") and not payload.get("mfa_verified"):
        raise HTTPException(
            status_code=403,
            detail="MFA verification required for this token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# --- Constants for File Upload ---
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_FILE_TYPES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]

@app.post("/api/cv-upload")
async def cv_upload(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    # Validate file size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds the limit of {MAX_FILE_SIZE / (1024 * 1024)} MB.")

    # Validate file type
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF and DOCX files are allowed.")

    temp_file_path = f"/tmp/{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        buffer.write(file_content)

    resume_text = parse_resume(temp_file_path)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Could not parse the resume. Ensure it's a valid PDF or DOCX.")

    profile_data = enhance_profile_with_gemini(resume_text)
    if not profile_data:
        raise HTTPException(status_code=500, detail="Could not enhance profile with Gemini. Please try again later.")

    await profiles_collection.update_one(
        {"user_id": current_user["_id"]},
        {"$set": {"user_id": current_user["_id"], **profile_data}},
        upsert=True
    )

    os.remove(temp_file_path)

    return {"message": f"CV uploaded and profile updated successfully for {current_user['email']}"}

@app.get("/api/matches")
async def get_job_matches(current_user: User = Depends(get_current_user), status: str | None = None):
    logging.info(f"Fetching job matches for user: {current_user['email']} with status filter: {status}")
    query = {"user_id": current_user["_id"]}
    if status:
        query["application_status"] = status

    matches = await recommended_jobs_collection.find(query).to_list(length=None)
    # Convert ObjectId to string for JSON serialization
    for match in matches:
        match["_id"] = str(match["_id"])
        if "timestamp" in match:
            match["timestamp"] = match["timestamp"].isoformat()
    logging.info(f"Found {len(matches)} job matches for user: {current_user['email']}")
    return matches

@app.post("/api/matches/{job_id}/feedback")
async def submit_job_feedback(job_id: str, feedback: JobFeedback, current_user: User = Depends(get_current_user)):
    logging.info(f"User {current_user['email']} submitting feedback for job_id: {job_id}, feedback: {feedback.feedback}")
    
    job_match = await recommended_jobs_collection.find_one({"user_id": current_user["_id"], "job_id": job_id})
    if not job_match:
        raise HTTPException(status_code=404, detail="Job match not found for this user.")

    update_result = await recommended_jobs_collection.update_one(
        {"_id": job_match["_id"]},
        {"$set": {"user_feedback": feedback.feedback, "feedback_timestamp": datetime.utcnow()}}
    )

    if update_result.modified_count == 0:
        logging.warning(f"Job match {job_id} for user {current_user['email']} feedback was not updated.")
        raise HTTPException(status_code=500, detail="Failed to record feedback.")

    logging.info(f"Feedback recorded for job {job_id} for user {current_user['email']}.")
    return {"message": "Feedback recorded successfully."}


@app.post("/api/matches/{job_id}/apply")
async def apply_for_job(job_id: str, current_user: User = Depends(get_current_user)):
    logging.info(f"User {current_user['email']} attempting to apply for job_id: {job_id}")
    job_match = await recommended_jobs_collection.find_one({"user_id": current_user["_id"], "job_id": job_id})

    if not job_match:
        logging.warning(f"Job match {job_id} not found for user {current_user['email']}.")
        raise HTTPException(status_code=404, detail="Job match not found for this user.")

    # Update the job match status
    update_result = await recommended_jobs_collection.update_one(
        {"_id": job_match["_id"]},
        {"$set": {"application_status": "applied", "applied_at": datetime.utcnow()}}
    )
    
    if update_result.modified_count == 0:
        logging.warning(f"Job match {job_id} for user {current_user['email']} was not updated (might already be applied).")
        # Even if not modified, if it was already applied, we still return the URL
        if job_match.get("application_status") == "applied":
            logging.info(f"Job {job_id} already marked as applied for user {current_user['email']}.")
        else:
            logging.error(f"Failed to update job match {job_id} for user {current_user['email']}.")
            raise HTTPException(status_code=500, detail="Failed to update job application status.")


    application_url = job_match["job_details"].get("ats_url") or job_match["job_details"].get("redirect_url")
    if not application_url:
        logging.error(f"Application URL not available for job {job_id} for user {current_user['email']}.")
        raise HTTPException(status_code=500, detail="Application URL not available for this job.")
    
    logging.info(f"Job {job_id} marked as applied for user {current_user['email']}. URL: {application_url}")
    return {"message": "Job marked as applied.", "application_url": application_url}

@app.delete("/api/matches/{job_id}")
async def delete_job_match(job_id: str, current_user: User = Depends(get_current_user)):
    logging.info(f"User {current_user['email']} attempting to delete job_id: {job_id}")
    result = await recommended_jobs_collection.delete_one({"user_id": current_user["_id"], "job_id": job_id})
    
    if result.deleted_count == 0:
        logging.warning(f"Job match {job_id} not found or already deleted for user {current_user['email']}.")
        raise HTTPException(status_code=404, detail="Job match not found or already deleted for this user.")
    
    logging.info(f"Job match {job_id} removed successfully for user {current_user['email']}.")
    return {"message": "Job match removed successfully."}

@app.post("/api/run-job-matching")
async def trigger_job_matching(current_user: User = Depends(get_current_user)):
    logging.info(f"Job matching triggered by user: {current_user['email']}")
    await run_job_matching_for_all_users(users_collection, profiles_collection, seen_jobs_collection, recommended_jobs_collection)
    return {"message": "Job matching process initiated."}

async def cleanup_old_recommended_jobs():
    logging.info("Starting cleanup of old recommended jobs.")
    # Define what 'old' means, e.g., older than 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    result = await recommended_jobs_collection.delete_many({"timestamp": {"$lt": thirty_days_ago}})
    logging.info(f"Cleaned up {result.deleted_count} old recommended jobs.")

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    logging.info("Starting scheduler...")
    # Schedule job matching to run daily at a specific time (e.g., 3 AM UTC)
    scheduler.add_job(
        run_job_matching_for_all_users,
        "cron",
        hour=3, minute=0,
        args=[users_collection, profiles_collection, seen_jobs_collection, recommended_jobs_collection],
        id="daily_job_matching"
    )
    # Schedule cleanup of old recommended jobs to run daily at a specific time (e.g., 4 AM UTC)
    scheduler.add_job(
        cleanup_old_recommended_jobs,
        "cron",
        hour=4, minute=0,
        id="daily_cleanup_old_jobs"
    )
    scheduler.start()
    logging.info("Scheduler started.")

@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Shutting down scheduler...")
    scheduler.shutdown()
    logging.info("Scheduler shut down.")

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Job Bot API"}
