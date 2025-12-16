from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Demo DevOps CRNCY", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/version")
def version():
    return {"service": "demo-devops-crncy", "version": "0.1.0"}

@app.get("/funding/mock")
def funding_mock():
    # Data no oficial / sintética para demo
    return {
        "loanId": "LN-DEMO-0001",
        "amount": 1250.75,
        "currency": "USD",
        "status": "APPROVED",
        "bank": "DEMO_BANK",
    }
