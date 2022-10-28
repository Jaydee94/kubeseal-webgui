import uvicorn
from os import environ

bind_address = environ.get("HOST", "127.0.0.1")
listen_port = int(environ.get("PORT", "5000"))

if __name__ == "__main__":
    uvicorn.run("kswg_mock.app:app", host=bind_address, port=listen_port)
