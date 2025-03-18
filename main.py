from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from bson import ObjectId
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Appointments API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# MongoDB connection with error handling
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI environment variable is not set")

try:
    client = MongoClient(MONGODB_URI)
    # Test the connection
    client.admin.command('ping')
    db = client.appointments_db
    appointments_collection = db.appointments
    print("Successfully connected to MongoDB")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    raise

# Pydantic models
class AppointmentBase(BaseModel):
    name: str
    email: str
    service: str
    date: str
    time: str
    topic: str
    status: Optional[str] = "Pending"
    zoom_link: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class Appointment(AppointmentBase):
    id: str = Field(..., alias="_id")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}

# Helper function to convert MongoDB document to Appointment model
def document_to_appointment(doc) -> Appointment:
    doc["_id"] = str(doc["_id"])
    return Appointment(**doc)

# CRUD Routes
@app.post("/appointments/", response_model=Appointment)
async def create_appointment(appointment: AppointmentCreate):
    doc = appointment.dict()
    result = appointments_collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return Appointment(**doc)

@app.get("/appointments/", response_model=List[Appointment])
async def get_appointments():
    appointments = []
    for doc in appointments_collection.find():
        appointments.append(document_to_appointment(doc))
    return appointments

@app.get("/appointments/{appointment_id}", response_model=Appointment)
async def get_appointment(appointment_id: str):
    try:
        doc = appointments_collection.find_one({"_id": ObjectId(appointment_id)})
        if doc is None:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return document_to_appointment(doc)
    except:
        raise HTTPException(status_code=404, detail="Appointment not found")

@app.put("/appointments/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, appointment: AppointmentCreate):
    try:
        doc = appointment.dict()
        result = appointments_collection.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": doc}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        updated_doc = appointments_collection.find_one({"_id": ObjectId(appointment_id)})
        return document_to_appointment(updated_doc)
    except:
        raise HTTPException(status_code=404, detail="Appointment not found")

@app.delete("/appointments/{appointment_id}")
async def delete_appointment(appointment_id: str):
    try:
        result = appointments_collection.delete_one({"_id": ObjectId(appointment_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return {"message": "Appointment deleted successfully"}
    except:
        raise HTTPException(status_code=404, detail="Appointment not found")

# Additional routes for appointment management
@app.put("/appointments/{appointment_id}/approve")
async def approve_appointment(appointment_id: str):
    try:
        result = appointments_collection.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": {"status": "Approved"}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return {"message": "Appointment approved successfully"}
    except:
        raise HTTPException(status_code=404, detail="Appointment not found")

@app.put("/appointments/{appointment_id}/zoom-link")
async def set_zoom_link(appointment_id: str, zoom_link: str):
    try:
        result = appointments_collection.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": {"zoom_link": zoom_link}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return {"message": "Zoom link added successfully"}
    except:
        raise HTTPException(status_code=404, detail="Appointment not found")

# Add a health check endpoint
@app.get("/")
async def root():
    return {"status": "ok", "message": "Appointments API is running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 