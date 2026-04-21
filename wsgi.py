from app.main import app

if __name__ == "__main__":
    # Para desenvolvimento local
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)