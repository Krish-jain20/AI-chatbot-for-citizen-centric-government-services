import os

from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from supabase import create_client

from backend.agent import graph


load_dotenv()

app = FastAPI(title="CivicBridge API")


# -------------------------
# Supabase Setup
# -------------------------

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise RuntimeError("Supabase credentials not found")

supabase = create_client(url, key)


# -------------------------
# Home
# -------------------------

@app.get("/")
def home():
    return {
        "message": "CivicBridge backend is running"
    }


# -------------------------
# Get All Services
# -------------------------

@app.get("/services")
def get_services():

    response = (
        supabase
        .table("services")
        .select("*")
        .execute()
    )

    return response.data


# -------------------------
# Get Single Service
# -------------------------

@app.get("/services/{service_id}")
def get_service(service_id: str):

    response = (
        supabase
        .table("services")
        .select("*")
        .eq("service_id", service_id)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )

    return response.data[0]


# -------------------------
# Chat Request
# -------------------------

class ChatRequest(BaseModel):
    message: str


# -------------------------
# Chat Endpoint
# -------------------------

@app.post("/chat")
def chat(request: ChatRequest):

    result = graph.invoke({
        "user_message": request.message,
        "service_id": "",
        "service_data": {},
        "final_response": ""
    })

    return {
        "service_id": result["service_id"],
        "message": result["final_response"]
    }