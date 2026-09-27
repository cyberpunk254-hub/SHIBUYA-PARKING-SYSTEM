# main.py — Shibuya Parking System
# Entry point of the web application.

from fastapi import FastAPI

# Create the application object. Everything in the system attaches to this.
app = FastAPI()

# A "route" tells the app what to do when a browser visits a given address.
# "/" is the home page.
@app.get("/")
def home():
    return {"message": "Shibuya Parking System is running"}