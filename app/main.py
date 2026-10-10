import os

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.runner import readiness

app = FastAPI(title='Counterexample Lab', docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]'])


@app.get('/api/health')
def health():
    provider = os.getenv('MODEL_PROVIDER', 'lmstudio')
    return {
        'runner': readiness(),
        'provider': {
            'name': provider,
            'configured': bool(os.getenv('GEMINI_API_KEY')) if provider == 'gemini' else True,
            'model': os.getenv('GEMINI_MODEL', 'gemini-3.8-flash') if provider == 'gemini' else os.getenv('LMSTUDIO_MODEL', 'counterexample-local'),
            'generation_verified': False,
        },
    }
