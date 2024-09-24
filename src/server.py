import datetime
from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
import os
import json
import time
import hashlib
import uuid

import bs4


# -------- Globals --------
# WARNING: / or \ SHOULD NEVER BE ALLOWED FOR PATH SECURITY
USERNAME_CHARSET = set("abcdefghijklmnopqrstuvwxyz-_")


# -------- Utility --------
def validate_username(username: str) -> bool:
    return (
        3 <= len(username) <= 28
        and all(ch in USERNAME_CHARSET for ch in username)
        and "__" not in username
        and "--" not in username
    )
    

def generate_token() -> str:
    token = uuid.uuid4().hex
    return token

    
class HTTPHandler(SimpleHTTPRequestHandler):
    """This handler uses server.base_path instead of always using os.getcwd()"""

    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(self.server.base_path, relpath)
        return fullpath

    def _respond_bad(self):
        self.send_response(400)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        # message = "Bad Request"
        # self.wfile.write(bytes(message, "utf8"))

    def do_POST_register(self, token:str, username:str):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Content Type should be JSON.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        try:
            username = post_data["username"]
            displayname = post_data["displayname"]
            password = post_data["password"]
        except KeyError:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "JSON object needs to have attributes: 'username', 'displayname', 'password'.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        if not validate_username(username):
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Username should be a 3-28 character string of alphanumeric characters including '-' and '_'. There should be no consecutive hyphens or underscores.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        if not (1 <= len(displayname) <= 48):
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Display Name should be a 1-48 character string.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        if not (1 <= len(password) <= 128):  # TODO maybe only (certain) ascii chars?
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Password should be a 1-128 character string.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        user_dir = os.path.join(backend_dir, "accounts", username)
        meta_file = os.path.join(user_dir, "meta.json")

        try:
            with open(meta_file, "r") as file:
                pass

        except FileNotFoundError:
            pass
        else:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "User already exists.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return
        
        # Success!
        m = hashlib.sha256()
        m.update(bytes(password, 'utf-8'))
        # TODO salting?
        #m.update(salt)
        password_hash = m.hexdigest()
        
        meta = {
            "displayname": displayname,
            "accountCreated": int(time.time()),
            "passwordHash": password_hash,
            "validTokens": [],
        }

        os.makedirs(user_dir)
        with open(meta_file, "w") as file:
            json.dump(meta, file, indent=4)

        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()

        response = {}
        self.wfile.write(bytes(json.dumps(response), "utf8"))


    def do_POST_login(self, token: str, username: str):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Content Type should be JSON.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        try:
            username = post_data["username"]
            password = post_data["password"]
        except KeyError:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "JSON object needs to have attributes: 'username', 'password'.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        if not validate_username(username):
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Username should a 3-28 character string of alphanumeric characters including '-' and '_'.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        if not (1 <= len(password) <= 128):
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Password should be a 1-128 character string.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        user_dir = os.path.join(backend_dir, "accounts", username)
        meta_file = os.path.join(user_dir, "meta.json")

        try:
            with open(meta_file, "r") as file:
                meta = json.load(file)

        except FileNotFoundError:
            self.send_response(404)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "User not found.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        # Success!
        stored_password_hash = meta["passwordHash"]
        m = hashlib.sha256()
        m.update(bytes(password, 'utf-8'))
        password_hash = m.hexdigest()

        if stored_password_hash != password_hash:
            self.send_response(401)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Incorrect password.",
            }
            message = json.dumps(response)
            self.wfile.write(bytes(message, "utf8"))
            return

        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        
        generated_token = generate_token()
        meta['validTokens'].append(generated_token)
        
        with open(meta_file, 'w') as file:
            json.dump(meta, file, indent=4)

        response = {'generatedToken': generated_token}
        self.wfile.write(bytes(json.dumps(response), "utf8"))

    
    def do_POST_send_message(self, token:str, username:str):
        content_length = int(self.headers["Content-Length"])
        post_data_raw = self.rfile.read(content_length)

        try:
            post_data = json.loads(post_data_raw)
        except ValueError:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {
                "error": "Content Type should be JSON.",
            }
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        try:
            sent_message_text = post_data["text"].strip()
            channel_id = post_data["channel"]
        except KeyError:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {"error": "JSON object needs to have attributes: 'text', 'channel'."}
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return
    
        if not 1 <= len(sent_message_text) < 4096:
            self.send_response(400)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {"error": "Message text should have a length between 1 and 4096."}
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return
        
        self.send_response(200)
        self.send_header('Content-Type', "text/json")
        self.end_headers()
        
        channel_dir = os.path.join(backend_dir, "channels", str(channel_id))
        channel_messages_file = os.path.join(channel_dir, "messages.json")
        
        try:
            with open(channel_messages_file, 'r') as file:
                channel_messages = json.load(file)
                
        except FileNotFoundError:
            self.send_response(404)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            
            response = {"error": "Channel not found."}
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return
    
        except OSError:
            self.send_response(500)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            
            response = {"error": "(Server Error) Could not read channel messages file."}
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return
        
        message_obj = {
            "author": username,
            "text": sent_message_text,
            "timestamp": int(time.time()),
        }
        channel_messages.append(message_obj)
        
        try:
            with open(channel_messages_file, 'w') as file:
                json.dump(channel_messages, file, indent=4)
        except OSError:
            self.send_response(500)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            
            response = {"error": "(Server Error) Could not write to channel messages file."}
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        response = {}
        self.wfile.write(bytes(json.dumps(response), "utf8"))


    def do_POST(self):
        print("[POST]", self.path)
        
        cookies = SimpleCookie(self.headers.get('Cookie'))
        try:
            token = cookies['token'].value
            username = cookies['username'].value
        except KeyError:
            token = None
            username = None

        if self.path == "/register":
            self.do_POST_register(token=token, username=username)
        elif self.path == "/login":
            self.do_POST_login(token=token, username=username)
        elif self.path == "/send_message":
            self.do_POST_send_message(token=token, username=username)
        else:
            self.send_response(404)
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            response = {'error': "Invalid post URI!"}
            self.wfile.write(bytes(json.dumps(response), "utf8"))
    
    
    def do_GET(self):
        cookies = SimpleCookie(self.headers.get('Cookie'))
        try:
            token = cookies['token'].value
        except KeyError:
            token = None
        
        if self.path in {"/login.html", "/register.html"} and token is not None:
            self.send_response(303)
            self.send_header('Location', "/")  # redirect to index if already logged in
            self.send_header('Content-Type', "text/json")
            self.end_headers()
            
            response = {}
            self.wfile.write(bytes(json.dumps(response), "utf8"))
            return

        if self.path.startswith("/channels/"):
            try:
                channel_id = int(self.path[len("/channels/"):])
            except (ValueError, IndexError):
                self.send_response(400)
                self.send_header('Content-Type', "text/json")
                self.end_headers()
                
                response = {"error": "Invalid channel ID."}
                self.wfile.write(bytes(json.dumps(response), "utf8"))
                return
            
            channel_dir = os.path.join(backend_dir, "channels", str(channel_id))
            channel_messages_file = os.path.join(channel_dir, "messages.json")
            
            try:
                with open(channel_messages_file, 'r') as file:
                    channel_messages = json.load(file)
                    
            except FileNotFoundError:
                self.send_response(404)
                self.send_header('Content-Type', "text/json")
                self.end_headers()
                
                response = {"error": "Channel not found."}
                self.wfile.write(bytes(json.dumps(response), "utf8"))
                return
        
            except OSError:
                self.send_response(500)
                self.send_header('Content-Type', "text/json")
                self.end_headers()
                
                response = {"error": "(Server Error) Could not read channel messages file."}
                self.wfile.write(bytes(json.dumps(response), "utf8"))
                return
            
            
            # Success! Send index.html with the messages edited in.
            with open(os.path.join(web_dir, "index.html"), 'r') as file:
                index_html = file.read()
                
            soup = bs4.BeautifulSoup(index_html, "html.parser")
            messages_div = soup.find('div', {'id': "messages"})
            
            for message_obj in channel_messages:
                # surely there must be a better way to do this right?
                author_tag = soup.new_tag('span', attrs={'class': "message-author"})
                author_tag.string = message_obj['author']
                
                timestamp_tag = soup.new_tag('span', attrs={'class': "message-timestamp"})
                date = datetime.datetime.fromtimestamp(message_obj['timestamp'])
                timestamp_tag.string = date.strftime("%Y-%m-%d %H:%M")
                
                br_tag = soup.new_tag('br')
                text_tag = soup.new_tag('span', attrs={'class': "message-text"})
                text_tag.string = message_obj['text']
                
                message_tag = soup.new_tag('div', attrs={'class': "message"})
                message_tag.append(author_tag)
                message_tag.append(timestamp_tag)
                message_tag.append(br_tag)
                message_tag.append(text_tag)
                
                messages_div.append(message_tag)
            
            
            self.send_response(200)
            self.send_header('Content-Type', "text/html")
            self.end_headers()
            
            response = str(soup)
            self.wfile.write(bytes(response, "utf8"))
            return


        super().do_GET()


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
