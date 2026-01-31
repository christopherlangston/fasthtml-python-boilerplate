import os
import resend
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

# --------------------------
# App setup
# --------------------------
app = FastAPI()

# --------------------------
# CORS
# Allow your static site (replace "*" with your site URL for production)
# --------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # e.g., ["https://www.yourdomain.com"]
    allow_methods=["POST"],
    allow_headers=["*"],
)

# --------------------------
# Rate limiting (5 requests per minute per IP)
# --------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": "Too many requests"}
    )

# --------------------------
# Resend setup
# --------------------------
resend.api_key = os.environ["RESEND_API_KEY"]

# --------------------------
# Contact endpoint
# --------------------------
@app.post("/api/contact")
@limiter.limit("5/minute")  # 5 requests per minute per IP
async def contact(request: Request):
    data = await request.json()
    email = data.get("email")
    message = data.get("message")
    honeypot = data.get("company")  # spam trap

    # --------------------------
    # Spam protection: honeypot
    # --------------------------
    if honeypot:
        return {"status": "ok"}  # pretend success for bots

    if not email or not message:
        return JSONResponse(status_code=400, content={"error": "Invalid input"})

    try:
        resend.Emails.send({
            "from": os.environ["FROM_EMAIL"],
            "to": os.environ["TO_EMAIL"],
            "subject": "New Contact Form Submission",
            "html": f"<p><strong>Email:</strong> {email}</p><p>{message}</p>"
        })
        return {"status": "sent"}
    except Exception:
        return JSONResponse(status_code=500, content={"error": "Email failed"})
