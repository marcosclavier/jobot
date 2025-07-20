
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import google.generativeai as genai
from dotenv import load_dotenv
import logging
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

# --- Pydantic Models ---
class User(BaseModel):
    email: str

class UserInDB(User):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None

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
        user_document = {"email": user.email, "hashed_password": hashed_password}
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

@app.post("/api/cv-upload")
async def cv_upload(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    temp_file_path = f"/tmp/{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        buffer.write(await file.read())

    resume_text = parse_resume(temp_file_path)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Could not parse the resume.")

    profile_data = enhance_profile_with_gemini(resume_text)
    if not profile_data:
        raise HTTPException(status_code=500, detail="Could not enhance profile with Gemini.")

    await profiles_collection.update_one(
        {"user_id": current_user["_id"]},
        {"$set": {"user_id": current_user["_id"], **profile_data}},
        upsert=True
    )

    os.remove(temp_file_path)

    return {"message": f"CV uploaded and profile updated successfully for {current_user['email']}"}

@app.post("/api/run-job-matching")
async def trigger_job_matching(current_user: User = Depends(get_current_user)):
    logging.info(f"Job matching triggered by user: {current_user['email']}")
    await run_job_matching_for_all_users(users_collection, profiles_collection, seen_jobs_collection, recommended_jobs_collection)
    return {"message": "Job matching process initiated."}

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Job Bot API"}
