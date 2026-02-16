from flask import Flask, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
import re, secrets, webbrowser, pyperclip, os



app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

PASSWORD = input("Set session password: ")
UPLOAD_FOLDER = r"C:\Users\Babak\Downloads\AriDrop"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")

        if password == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("send_page"))
        else:
            return "Wrong password"

    return '''
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial; padding: 40px; text-align:center; }
            input, button { width: 100%; padding: 15px; font-size: 18px; margin-top:10px; }
            .card { max-width: 400px; margin:auto; padding:30px; border-radius:15px; box-shadow:0 0 20px rgba(0,0,0,0.1);}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Login</h2>
            <form method="POST">
                <input type="password" name="password" placeholder="Enter password">
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    '''


# ---------------- MAIN APP ----------------
@app.route("/send", methods=["GET"])
def send_page():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    return '''
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: 'Segoe UI', sans-serif;
                background: #121212;
                color: white;
                padding: 20px;
            }

            .card {
                background: #1e1e1e;
                padding: 25px;
                border-radius: 20px;
                box-shadow: 0 0 25px rgba(0,0,0,0.6);
            }

            textarea {
                width:100%;
                height:120px;
                background:#2a2a2a;
                color:white;
                border:none;
                border-radius:12px;
                padding:10px;
            }

            button {
                width:100%;
                padding:14px;
                border:none;
                border-radius:12px;
                margin-top:10px;
                font-weight:bold;
            }

            .send { background:#00c853; }
            .upload { background:#2962ff; }
            .logout { background:#d50000; }

            button:hover { opacity:0.85; transition:0.2s; }

            .msg { margin-top:15px; text-align:center; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Send to PC</h2>

            <textarea id="text" placeholder="Type text here"></textarea>
            <button class="send" onclick="sendText()">Send Text</button>

            <br><br>
            <input type="file" id="fileInput" hidden>
            <button onclick="document.getElementById('fileInput').click()" class="upload">
                Choose File
            </button>
            <button class="upload" onclick="uploadFile()">Upload File</button>

            <button class="logout" onclick="logout()">Logout</button>

            <div class="msg" id="message"></div>
        </div>

<script>
function sendText(){
    fetch("/api/send_text", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({text: document.getElementById("text").value})
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("message").innerText = data.message;
        document.getElementById("text").value = "";
    });
}

function uploadFile(){
    let file = document.getElementById("fileInput").files[0];
    let formData = new FormData();
    formData.append("file", file);

    fetch("/api/upload", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("message").innerText = data.message;
    });
}

function logout(){
    window.location.href = "/logout";
}
</script>

    </body>
    </html>
    '''


# ---------------- TEXT API ----------------
@app.route("/api/send_text", methods=["POST"])
def api_send_text():
    if not session.get("logged_in"):
        return jsonify({"message": "Not authorized"})

    data = request.get_json()
    text = data.get("text")

    pyperclip.copy(text)

    # Detect URL
    url_pattern = r"(https?://[^\s]+)"
    match = re.search(url_pattern, text)

    if match:
        webbrowser.open(match.group())

    print("Received:", text)
    print("-" * 40)

    return jsonify({"message": "Text copied!"})

# ---------------- FILE API ----------------
@app.route("/api/upload", methods=["POST"])
def upload_file():
    if not session.get("logged_in"):
        return jsonify({"message": "Not authorized"})

    file = request.files.get("file")
    if not file:
        return jsonify({"message": "No file selected"})

    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    print("File saved:", path)

    return jsonify({"message": "File uploaded successfully!"})


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


app.run(host="10.152.59.118", port=5000, debug=True)
