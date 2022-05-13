import fastapi

from .routers import kubernetes

app = fastapi.FastAPI()

app.include_router(
    kubernetes.router,
    prefix='/api/v1',
)

@app.get('/')
def root():
    return {'status': 'KubeSeal WebGui Mock'}
