from fastapi import FastAPI, Request

app = FastAPI()
latest_data = {}

@app.get("/")
def home():
    return {"message": "server running"}

@app.get("/latest")
def get_latest():
    return latest_data

@app.post("/api/test")
async def test_post(request: Request):
    global latest_data
    latest_data = await request.json()
    print("Received payload:", latest_data)
    return {"status": "ok", "received": latest_data}