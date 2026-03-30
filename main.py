from flask import Flask, request, redirect, url_for, session, jsonify, abort, send_file
from flask_socketio import SocketIO, emit
import pyperclip
import os, re, datetime
import winsound
import secrets
import qrcode
import socket ,time, uuid
import webbrowser
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from zeroconf import ServiceInfo, Zeroconf
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask import render_template
import shutil

# ---------------- CONFIG ---------------

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
# app.secret_key =  input("Set session password: ")
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

# --------- DataBase ---------

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///airdrop_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String, nullable=False)
    sender = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class UploadHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String, nullable=False)
    sender = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)


# --------- STARTUP SETUP ---------
APP_PIN = input("🔐 Set access PIN for phone: ").strip()
SESSION_TOKEN = secrets.token_urlsafe(24)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not require internet — just finds LAN IP
        s.connect(("192.168.0.1", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

LOCAL_IP = get_local_ip()
BASE_URL = f"http://{LOCAL_IP}:5000"


# ---------------- m DNS ----------------

info = ServiceInfo(
    "_http._tcp.local.",
    "AirDropServer._http._tcp.local.",
    addresses=[socket.inet_aton(LOCAL_IP)],
    port=5000,
    properties={},
    server="airdrop.local."
)
zeroconf = Zeroconf()
zeroconf.register_service(info)


# ---------------- HTTPS CERT ----------------
def generate_cert():
    if os.path.exists("key.pem") and os.path.exists("cert.pem"):
        return "cert.pem", "key.pem"

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"MyApp"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"MyApp LAN"),
    ])
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(
        key.public_key()
    ).serial_number(x509.random_serial_number()).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).sign(key, hashes.SHA256(), default_backend())

    with open("key.pem", "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    with open("cert.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    return "cert.pem", "key.pem"

cert_file, key_file = generate_cert()

# ---------------- LOGIN ----------------

@app.route("/qr")
def generate_qr():
    url = f"{BASE_URL}/connect?token={SESSION_TOKEN}"
    img = qrcode.make(url)
    img.save("connect_qr.png")

    print("\n📱 Scan this QR with your phone:")
    print(url)
    print("QR saved as connect_qr.png\n")



# def show_qr():
#     hostname = socket.gethostname()
#     local_ip = socket.gethostbyname(hostname)

#     url = f"https://{local_ip}:5000/connect?token={SESSION_TOKEN}"

#     img = qrcode.make(url)

#     file_path = "./qr/connect_qr.png"

#     img.save(file_path, format="PNG")

#     print("\nQR Saved:", os.path.abspath(file_path))
#     print("Open this URL on phone: ", url)


#     return send_file(file_path, mimetype="image/png")

@app.before_request
def capture_user_agent():
    ua = request.headers.get("User-Agent")
    # Send UA to JS if you want
    print("Connected device UA:", ua)

    device = session.get("device_name", "Unknown Device")

@app.route("/connect")
def connect():
    token = request.args.get("token")

    if token != SESSION_TOKEN:
        abort(403)

    session["logged_in"] = True
    return redirect(url_for("send_page"))

@app.route("/", methods=["GET", "POST"])
def login():
    db.create_all()

    if request.method == "POST":
        password = request.form.get("password")

        if password == APP_PIN:
            session["logged_in"] = True
            return redirect(url_for("send_page"))
        else:
            return "<script>alert('Wrong PIN'); window.location='/';</script>"

    return render_template("login.html")

# @app.route("/", methods=["GET", "POST"])
# def login():
#     if request.method == "POST":
#         password = request.form.get("password")
#         if password == app.secret_key:
#             session["logged_in"] = True
#             return redirect(url_for("send_page"))
#         else:
#             return "Wrong password"
#     return '''
#     <html>
#     <head>
#         <meta name="viewport" content="width=device-width, initial-scale=1">
#         <style>
#             body { font-family: 'Segoe UI', sans-serif; background:#121212; color:white; text-align:center; padding:40px;}
#             .card { background:#1e1e1e; padding:30px; border-radius:20px; box-shadow:0 0 25px rgba(0,0,0,0.6);}
#             input, button { width:100%; padding:15px; margin-top:10px; border-radius:12px; border:none; font-size:18px;}
#             button { font-weight:bold; }
#             button:hover { opacity:0.85; transition:0.2s; }
#         </style>
#     </head>
#     <body>
#         <div class="card">
#             <h2>Login</h2>
#             <form method="POST">
#                 <input type="password" name="password" placeholder="Enter password">
#                 <button type="submit">Login</button>
#             </form>
#         </div>
#     </body>
#     </html>
#     '''

# ---------------- SEND PAGE ----------------
@app.route("/send")
def send_page():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("send.html")


# ---------------- WEBSOCKET ----------------
@socketio.on("send_message")
def handle_message(data):
    text = data.get("text")
    pyperclip.copy(text)

    sender = session.get("device_name", "Unknown")
    db.session.add(Message(content=text, sender=sender))
    db.session.commit()

    # Auto open URL
    url_pattern = r"(http?://[^\s]+)"
    match = re.search(url_pattern, text)
    if match:
        import webbrowser
        webbrowser.open(match.group())

    winsound.MessageBeep(winsound.MB_OK)
    print("Received:", text)
    emit("receive_message", {"text": text}, broadcast=True)

@socketio.on('start_text_send')
def send_progress(data):
    text = data["text"]
    for i in range(len(text)):
        time.sleep(0.01)
        percent = int((i+1)/len(text)*100)
        emit('progress_update', {'progress': percent})

# ---------------- FILE UPLOAD ----------------
@app.route("/api/upload", methods=["POST"])
def upload_file():
    if not session.get("logged_in"):
        return jsonify({"message": "Not authorized"})
    file = request.files.get("file")
    if not file:
        return jsonify({"message":"No file selected"})
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)
    print("File saved:", path)
    winsound.MessageBeep(winsound.MB_OK)
    return jsonify({"message":"File uploaded successfully!"})


# ---------------- FILE CHUNK UPLOAD ----------------
CHUNKS_FOLDER = "uploads/chunks"
if not os.path.exists(CHUNKS_FOLDER):
    os.makedirs(CHUNKS_FOLDER)

UPLOAD_PROGRESS = {}

@app.route("/api/upload_chunk", methods=["POST"])
def upload_chunk():
    file_id = request.form["file_id"]
    chunk_index = int(request.form["chunk_index"])
    total_chunks = int(request.form["total_chunks"])
    chunk = request.files["chunk"]

    file_dir = os.path.join(CHUNKS_FOLDER, file_id)
    os.makedirs(file_dir, exist_ok=True)

    chunk_path = os.path.join(file_dir, str(chunk_index))
    chunk.save(chunk_path)

    UPLOAD_PROGRESS.setdefault(file_id, set()).add(chunk_index)

    if len(UPLOAD_PROGRESS[file_id]) == total_chunks:
        final_path = os.path.join(UPLOAD_FOLDER, file_id)

        with open(final_path, "wb") as f:
            for i in range(total_chunks):
                with open(os.path.join(file_dir, str(i)), "rb") as part:
                    f.write(part.read())

        shutil.rmtree(file_dir)
        del UPLOAD_PROGRESS[file_id]

        return jsonify({"status": "complete"})

    return jsonify({"status": "incomplete"})


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@socketio.on("connect")
def client_connect():
    print(f"📶 Client connected: {request.remote_addr}")
    emit("status", {"message": "connected", "ip": request.remote_addr}, broadcast=True)

@socketio.on("disconnect")
def client_disconnect():
    print(f"📴 Client disconnected: {request.remote_addr}")
    emit("status", {"message": "disconnected"}, broadcast=True)



# ---------------- RUN ----------------
@app.route("/history")
def show_history():
    messages = Message.query.order_by(Message.timestamp.desc()).all()
    uploads = UploadHistory.query.order_by(UploadHistory.timestamp.desc()).all()
    return render_template("history.html", messages=messages, uploads=uploads)


@app.route("/info", methods=["GET", "POST"])
def show_info():
    QR_CODE_FILENAME = "connect_qr.png"

    return render_template(
        "info.html",
        token = SESSION_TOKEN,
        BaseUrl = BASE_URL,
        IP = LOCAL_IP,
        qr_code_url = QR_CODE_FILENAME,
        pin = APP_PIN
    )


def run_server():
    # webbrowser.open(BASE_URL)
    webbrowser.open("http://airdrop.local:5000/info")

    print("-" * 60)
    print(f"⚡️ Server starting...")
    print(f"   Local IP Address: {LOCAL_IP}")
    print(f"   Base URL (IP): {BASE_URL}")
    print(f"   Access URL: http://airdrop.local:5000")
    print(f"   QR Code saved as: connect-qr.png")
    print("-" * 60)

    socketio.run(
        app,
        # host="172.20.32.1",
        # host=f"{LOCAL_IP}",
        host=f"0.0.0.0",
        use_reloader=False,
        # ssl_context=(cert_file, key_file), # needs to be commented if there is no internet
        debug=True
    )


if __name__ == "__main__":
    run_server()