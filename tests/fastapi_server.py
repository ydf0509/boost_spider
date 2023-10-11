import uvicorn
from fastapi import FastAPI

app = FastAPI()

import nb_log
nb_log.get_logger(None)
@app.get("/")
async def hello():
    return {"message": "Hello"}

if __name__ == '__main__':
    uvicorn.run(app,host="0.0.0.0", port=8000)