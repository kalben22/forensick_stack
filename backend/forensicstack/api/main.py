from fastapi import FastAPI

app = FastAPI(title='ForensicStack API')

@app.get('/')
def root():
    return {'message': 'ForensicStack API is running!', 'status': 'ok'}

@app.get('/health')
def health():
    return {'status': 'healthy'}