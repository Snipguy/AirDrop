# 📡 AirDrop LAN - Flask File Sharing App

A lightweight AirDrop-style LAN file and text sharing application built with **Flask + Socket.IO**.

Share files and messages between devices on the same network with a clean modern UI and PWA support.

---

## 🚀 Features

- 🔐 PIN-protected login
- 📤 Send text messages instantly
- 📂 Drag & Drop file upload
- 📊 Chunked file uploads (large file support)
- ⚡ Real-time progress tracking
- 🌗 Dark / Light mode
- 📲 PWA install support
- 🔊 Upload completion sound
- ☕ Optional donation banner integration

---

## 📁 Project Structure

project/
│
├── main.py
├── requirements.txt
│
├── templates/
│ ├── base.html
│ ├── login.html
│ └── send.html
│
├── static/
│ ├── style.css
│ ├── app.js
│ └── assets/
│
└── uploads/

---

## ⚙ Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/snipguy/LAN_AirDrop.git
cd LAN_AirDrop
```
2️⃣ Create Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```
3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```
If Your can't acsess the main Pypi you can use the megan backup servers
```bash
pip install -r requirements.txt --index-url https://hub.megan.ir/pypi/simple
```

▶ Run the App
```bash
python main.py
```

Then open:

http://127.0.0.1:5000
http://airdrop.local:5000

To access from another device on LAN:

http://YOUR_LOCAL_IP:5000
http://airdrop.local:5000

📲 PWA Support

To enable installable PWA:

App must be served over HTTPS (or localhost)

manifest.json must be configured

Service worker must be registered

🔐 Security Note

This project is designed for local network usage only.
Do not expose it directly to the public internet without proper authentication and HTTPS configuration.

💡 Future Improvements

📡 Real-time device status indicator

📊 Upload ETA counter

🔐 FaceID-style unlock animation

📱 Mobile-optimized UI refinements

☁ Optional cloud relay mode

☕ Support

If you find this project useful, consider supporting it:

👉 https://coffeebede.com/snipguy

## If you find this project useful, consider supporting it:
👉 https://coffeebede.com/snipguy

# 📜 License

MIT License

---



# 💎 Optional: Add .gitignore

You should also create:
.gitignore


With:

```txt
venv/
__pycache__/
uploads/
.env