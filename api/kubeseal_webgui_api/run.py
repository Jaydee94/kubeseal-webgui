#!/usr/bin/env python

from os import environ

from . import create_app

app = create_app()
bind_address = environ.get("HOST", "127.0.0.1")
listen_port = int(environ.get("PORT", "5000"))

if __name__ == "__main__":
    app.run(debug=True, host=bind_address, port=listen_port)
