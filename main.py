import socket
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


# ---------------- CONFIG ---------------

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
# app.secret_key =  input("Set session password: ")
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

socketio = SocketIO(app, async_mode="threading")

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




@app.route("/", methods=["GET", "POST"])
def login():
    db.create_all()
    if request.method == "POST":
        if request.form.get("password") == APP_PIN:
            session["logged_in"] = True
            return redirect(url_for("send_page"))
    return render_template("login.html")

@app.route("/send")
def send_page():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("send.html")



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
            return '''
            <script>alert("Wrong PIN"); window.location="/";</script>
            '''

    return  f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="manifest" href="/static/manifest.json">
        <script>
            if ('serviceWorker' in navigator) {{
                navigator.serviceWorker.register('/static/sw.js');
            }}
        </script>
        <style>
            body {{
                margin:0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: linear-gradient(135deg, #1e1e2f, #121212);
                display:flex;
                justify-content:center;
                align-items:center;
                height:100vh;
                color:white;
            }}

            .card {{
                display:block;
                background:#1c1c1c;
                padding:40px 30px;
                border-radius:25px;
                width:90%;
                max-width:400px;
                text-align:center;
                box-shadow:0 10px 40px rgba(0,0,0,0.6);
            }}

            h1 {{
                margin-bottom:20px;
                font-weight:600;
            }}

            input {{
                width:90%;
                padding:16px;
                border:none;
                border-radius:15px;
                font-size:18px;
                margin-top:10px;
                background:#2a2a2a;
                color:white;
                text-align:center;
                letter-spacing:3px;
            }}

            button {{
                width:100%;
                padding:16px;
                border:none;
                border-radius:15px;
                margin-top:15px;
                font-size:18px;
                font-weight:600;
                background:#00c853;
                color:white;
                cursor:pointer;
            }}

            button:active {{
                transform:scale(0.97);
            }}

            .hint {{
                margin-top:15px;
                font-size:14px;
                color:#aaa;
            }}

            .ad-container {{
                position: fixed;
                bottom: 15px;
                width: 100%;
                display: flex;
                justify-content: center;
            }}

            .ad-container img {{
                max-width: 300px;
                width: 80%;
                border-radius: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="ad-container">
                <a href="https://coffeebede.com/snipguy" target="_blank">
                    <img src="https://coffeebede.ir/DashboardTemplateV2/app-assets/images/banner/default-yellow.svg">
                </a>
            </div>
            <h1>🔐 Unlock PC</h1>
            <form method="POST">
                <input type="password" name="password" placeholder="Enter PIN" autofocus>
                <button type="submit">Unlock</button>
            </form>
            <div class="hint">Scan QR from PC screen for instant login</div>
        </div>
    </body>
    </html>
    '''


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
@app.route("/send", methods=["GET"])
def send_page():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return '''
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family:'Segoe UI', sans-serif; background:#121212; color:white; padding:20px;}
            .card { background:#1e1e1e; padding:25px; border-radius:20px; box-shadow:0 0 20px rgba(0,0,0,0.6);}
            textarea { width:100%; height:120px; padding:10px; border-radius:12px; border:none; background:#2a2a2a; color:white; font-size:16px;}
            .button { width:100%; padding:14px; border:none; border-radius:12px; margin-top:10px; font-weight:bold; font-size:18px; cursor:pointer; }
            .send { background:#00c853; color:white; }
            .upload { background:#2962ff; color:white; }
            .logout { background:#d50000; color:white; }
            button:hover { opacity:0.85; transition:0.2s; }
            .msg { margin-top:15px; text-align:center; font-weight:bold; }
            #dropZone { border:2px dashed #555; padding:40px; text-align:center; border-radius:15px; margin-top:15px;}
        </style>
    </head>
    <style>
        .toast {
            position: fixed;
            bottom: 10px;
            left: 50%;
            transform: translateX(-50%);
            background: #444;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        .toast.show {
            opacity: 1;
        }
    </style>
    <div id="toast" class="toast"></div>
    <script>
        function showToast(msg) {
            const toast = document.getElementById("toast");
            toast.innerText = msg;
            toast.classList.add("show");
            setTimeout(() => toast.classList.remove("show"), 2000);
        }
    </script>

    <body>
        <div>

        </div>
        <div class="card">
            <div style="margin-bottom:10px; color:#ccc;">Connected: {{ device }}</div>
            <h2>Send to PC</h2>
            <textarea id="text" placeholder="Type text here"></textarea>
            <button class="button send" onclick="sendText()">Send Text</button>

            <div id="dropZone">Drag & Drop File Here</div>
            <input type="file" id="fileInput" hidden>
            <button class="button upload" onclick="document.getElementById('fileInput').click()">Choose File</button>

            <button class="button logout" onclick="logout()">Logout</button>
            <div class="msg" id="message"></div>
            <progress id="uploadProgress" value="0" max="100" style="width: 100%; display:none;"></progress>
            <div id="uploadProgressText" style="color:white; margin-top:8px;"></div>

            <script>
                function uploadFile(file) {
                    let chunkSize = 5 * 1024 * 1024; // 5 MB chunks
                    let totalChunks = Math.ceil(file.size / chunkSize);
                    let fileId = Date.now() + "_" + file.name.replace(/ /g, "_");
                    let currentChunk = 0;

                    function sendNextChunk() {
                        let start = currentChunk * chunkSize;
                        let end = Math.min(start + chunkSize, file.size);
                        let blob = file.slice(start, end);

                        let formData = new FormData();
                        formData.append("file_id", fileId);
                        formData.append("chunk_index", currentChunk);
                        formData.append("total_chunks", totalChunks);
                        formData.append("chunk", blob);

                        let xhr = new XMLHttpRequest();
                        xhr.open("POST", "/api/upload_chunk", true);

                        xhr.onload = function () {
                            currentChunk++;
                            let percent = Math.floor((currentChunk / totalChunks) * 100);
                            document.getElementById("uploadProgress").value = percent;
                            document.getElementById("uploadProgressText").innerText = "Uploading... " + percent + "%";

                            if (currentChunk < totalChunks) {
                                sendNextChunk();
                            } else {
                                document.getElementById("uploadProgressText").innerText = "Upload complete!";
                                showToast("Upload finished");
                            }
                        };

                        xhr.onerror = function () {
                            showToast("Error uploading chunk " + currentChunk);
                        };

                        xhr.send(formData);
                    }

                    sendNextChunk(); // start upload
                }
            </script>

            <div id="toast" style="
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: #4CAF50;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                display: none;
            ">
                Sent!
            </div>

            <script>
            function showToast(msg) {
                let t = document.getElementById("toast");
                t.innerText = msg;
                t.style.display = "block";
                setTimeout(() => t.style.display = "none", 2000);
            }
            </script>
        </div>

<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<script>
var socket = io();

// Send text
function sendText(){
    let text = document.getElementById("text").value;
    document.getElementById("message").innerText = "Sending...";
    document.getElementById("message").style.opacity = "0.6";
    socket.emit("send_message", { text: text });
    document.getElementById("text").value = "";
}

socket.on("receive_message", function(data){
    document.getElementById("message").innerText = "Sent: " + data.text;
    document.getElementById("message").style.opacity = "1";
});


// Drag & Drop
let dropZone = document.getElementById("dropZone");
dropZone.addEventListener("dragover", e=>{ e.preventDefault(); dropZone.style.background="#333"; });
dropZone.addEventListener("dragleave", e=>{ dropZone.style.background=""; });
dropZone.addEventListener("drop", e=>{
    e.preventDefault(); dropZone.style.background="";
    let file = e.dataTransfer.files[0];
    uploadFile(file);
});

// File upload
document.getElementById("fileInput").addEventListener("change", function(){
    let file = this.files[0];
    uploadFile(file);
});

// status indicator
socket.on("status", (s) => {
    document.getElementById("status").innerText = s;
});

// Logout

function logout(){ window.location.href="/logout"; }
</script>

    </body>
    </html>
    '''

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

# Directory for chunk temp storage
CHUNKS_FOLDER = "uploads/chunks"
if not os.path.exists(CHUNKS_FOLDER):
    os.makedirs(CHUNKS_FOLDER)

@app.route("/api/upload_chunk", methods=["POST"])
def upload_chunk():
    file_id = request.form.get("file_id")
    chunk_index = request.form.get("chunk_index", type=int)
    total_chunks = request.form.get("total_chunks", type=int)
    chunk = request.files.get("chunk")

    # Save chunk
    file_chunk_path = os.path.join(CHUNKS_FOLDER, f"{file_id}_chunk_{chunk_index}")
    chunk.save(file_chunk_path)

    # If all chunks received, reassemble
    existing_chunks = [
        f for f in os.listdir(CHUNKS_FOLDER)
        if f.startswith(f"{file_id}_chunk_")
        
    ]

    if len(existing_chunks) == total_chunks:
        final_path = os.path.join(UPLOAD_FOLDER, file_id + "_" + secure_filename(chunk.filename))
        with open(final_path, "wb") as final_file:
            for i in range(total_chunks):
                part_path = os.path.join(CHUNKS_FOLDER, f"{file_id}_chunk_{i}")
                with open(part_path, "rb") as part:
                    final_file.write(part.read())
                os.remove(part_path)  # remove chunk
                db.session.add(UploadHistory(filename=final_path, sender=session.get("device_name", "Unknown")))
                db.session.commit()
        return jsonify({"status":"complete", "file": final_path})

    return jsonify({"status":"incomplete", "chunk_index": chunk_index})

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

webbrowser.open(BASE_URL)

socketio.run(
    app,
    # host="10.45.157.118",
    # host=f"{LOCAL_IP}",
    host=f"0.0.0.0",
    use_reloader=False,
    # ssl_context=(cert_file, key_file), # needs to be commented if there is no internet
    debug=True
)
