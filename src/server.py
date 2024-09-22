from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler
import os
import json
import time


# -------- Globals --------
# WARNING: / or \ SHOULD NEVER BE ALLOWED FOR PATH SECURITY
USERNAME_CHARSET = set("abcdefghijklmnopqrstuvwxyz-_")


class HTTPHandler(SimpleHTTPRequestHandler):
    """This handler uses server.base_path instead of always using os.getcwd()"""

    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(self.server.base_path, relpath)
        return fullpath

    def _respond_bad(self):
        self.send_response(400)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        # message = "Bad Request"
        # self.wfile.write(bytes(message, "utf8"))

    def do_POST_register(self):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self._respond_bad(); return


        try:
            username = post_data["username"]
            displayname = post_data["displayname"]
            password = post_data["password"]
        except KeyError:
            self._respond_bad(); return

        if not (
            3 <= len(username) <= 28
            and all(ch in USERNAME_CHARSET for ch in username)
            and "__" not in username
            and "--" not in username
        ):
            self._respond_bad(); return

        if not (1 <= len(displayname) <= 48):
            self._respond_bad(); return

        if not (1 <= len(password) <= 128):
            self._respond_bad(); return

        user_dir = os.path.join(backend_dir, "accounts", username)
        meta_file = os.path.join(user_dir, "meta.json")

        try:
            with open(meta_file, "r") as file:
                pass

        except FileNotFoundError:
            pass
        else:
            self._respond_bad(); return

        # Success!
        meta = {
            "displayname": displayname,
            "accountCreated": int(time.time()),
            "passwordHash": hash(password),  # TODO actual hashing lmao
        }

        os.makedirs(user_dir)
        with open(meta_file, "w") as file:
            json.dump(meta, file, indent=4)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        response = {"success": True}

        message = json.dumps(response)
        self.wfile.write(bytes(message, "utf8"))


    def do_POST_login(self):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self._respond_bad(); return
        
        try:
            username = post_data["username"]
            password = post_data["password"]
        except KeyError:
            self._respond_bad(); return

        if not (
            3 <= len(username) <= 28
            and all(ch in USERNAME_CHARSET for ch in username)
        ):
            self._respond_bad(); return

        if not (1 <= len(password) <= 128):
            self._respond_bad(); return
            
        user_dir = os.path.join(backend_dir, "accounts", username)
        meta_file = os.path.join(user_dir, "meta.json")

        try:
            with open(meta_file, "r") as file:
                pass

        except FileNotFoundError:
            pass
        else:
            self._respond_bad(); return

        # Success!
        meta = {
            "displayname": displayname,
            "accountCreated": int(time.time()),
            "passwordHash": hash(password),  # TODO actual hashing lmao
        }

        os.makedirs(user_dir)
        with open(meta_file, "w") as file:
            json.dump(meta, file, indent=4)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        response = {"success": True}

        message = json.dumps(response)
        self.wfile.write(bytes(message, "utf8"))
        


    def do_POST(self):
        print("[POST]", self.path)

        if self.path == "/register":
            self.do_POST_register()
        elif self.path == "/login":
            self.do_POST_login()
        elif self.path == "/send_message":
            self.do_POST_send_message()
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            message = "Invalid post URI!"
            self.wfile.write(bytes(message, "utf8"))


class HTTPServer(BaseHTTPServer):
    """The main server, you pass in base_path which is the path you want to serve requests from"""

    def __init__(self, base_path, server_address, RequestHandlerClass=HTTPHandler):
        self.base_path = base_path
        BaseHTTPServer.__init__(self, server_address, RequestHandlerClass)


web_dir = os.path.join(os.path.dirname(__file__), "../frontend_files")
backend_dir = os.path.join(os.path.dirname(__file__), "../backend_files")
httpd = HTTPServer(web_dir, ("", 8000))

if __name__ == "__main__":
    print("Started.")
    httpd.serve_forever()
