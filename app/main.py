from fastapi import FastAPI

app = FastAPI(title="Real-Time Docs API")


@app.get("/")
async def health_check():
  return {"status": "Ready"}