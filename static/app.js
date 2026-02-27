// ==========================
// SOCKET CONNECTION
// ==========================
var socket = io();


// ==========================
// SEND TEXT
// ==========================
function sendText() {
    let textArea = document.getElementById("text");
    if (!textArea) return;

    let text = textArea.value.trim();
    if (text === "") return;

    let messageBox = document.getElementById("message");
    if (messageBox) {
        messageBox.innerText = "Sending...";
        messageBox.style.opacity = "0.6";
    }

    socket.emit("send_message", { text: text });
    textArea.value = "";
}

// Receive confirmation
socket.on("receive_message", function(data) {
    let messageBox = document.getElementById("message");
    if (messageBox) {
        messageBox.innerText = "Sent: " + data.text;
        messageBox.style.opacity = "1";
    }
});

// ==========================
// STATUS INDICATOR
// ==========================
socket.on("status", function(data) {
    let statusEl = document.getElementById("status");
    if (statusEl && data.message) {
        statusEl.innerText = data.message;
    }
});

// ==========================
// TOAST FUNCTION
// ==========================
function showToast(msg) {
    let toast = document.getElementById("toast");
    if (!toast) return;

    toast.innerText = msg;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 2000);
}

// ==========================
// LOGOUT
// ==========================
function logout() {
    window.location.href = "/logout";
}

// ==========================
// FILE UPLOAD (CHUNKED)
// ==========================
function showSuccess() {
    const check = document.getElementById("successCheck");
    check.classList.add("show");

    setTimeout(() => {
        check.classList.remove("show");
    }, 2000);
}

function uploadFile(file) {
    if (!file) return;

    let chunkSize = 8 * 1024 * 1024; // 8MB
    let totalChunks = Math.ceil(file.size / chunkSize);
    let fileId = Date.now() + "_" + file.name.replace(/ /g, "_");
    let currentChunk = 0;

    let progressBar = document.getElementById("uploadProgress");
    let progressText = document.getElementById("uploadProgressText");

    if (progressBar) progressBar.style.display = "block";
    startUploadTimer()

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

        xhr.onload = function() {
            currentChunk++;

            let percent = Math.floor((currentChunk / totalChunks) * 100);
            updateProgress(percent, uploadedBytes);

            if (progressBar) progressBar.value = percent;

            if (progressText)
                progressText.innerText = "Uploading... " + percent + "%";

            if (currentChunk < totalChunks) {
                sendNextChunk();
            } else {
                if (progressText)
                    progressText.innerText = "Upload complete!";
                showToast("Upload finished");
                addToHistory(file.name);
            }
        };

        xhr.onerror = function() {
            showToast("Error uploading chunk " + currentChunk);
        };

        xhr.send(formData);
    }

    sendNextChunk();
}

// ==========================
// DRAG & DROP
// ==========================
document.addEventListener("DOMContentLoaded", function() {
    let dropZone = document.getElementById("dropZone");
    let fileInput = document.getElementById("fileInput");

    if (dropZone) {
        dropZone.addEventListener("dragover", function(e) {
            e.preventDefault();
            dropZone.style.background = "#333";
        });

        dropZone.addEventListener("dragleave", function() {
            dropZone.style.background = "";
        });

        dropZone.addEventListener("drop", function(e) {
            e.preventDefault();
            dropZone.style.background = "";

            let file = e.dataTransfer.files[0];
            uploadFile(file);
            showSuccess();
            playSuccessSound();
        });
    }

    if (fileInput) {
        fileInput.addEventListener("change", function() {
            let file = this.files[0];
            uploadFile(file);
            showSuccess();
            playSuccessSound();
        });
    }
});


function toggleTheme() {
    document.body.classList.toggle("light");
    localStorage.setItem("theme",
        document.body.classList.contains("light") ? "light" : "dark"
    );
}

window.onload = function() {
    if (localStorage.getItem("theme") === "light") {
        document.body.classList.add("light");
    }
};

function updateProgress(percent) {
    document.getElementById("uploadBar").style.width = percent + "%";
}

function addToHistory(filename) {
    const li = document.createElement("li");
    li.textContent = "📄 " + filename;
    document.getElementById("fileHistory").prepend(li);
}


let uploadStartTime = 0;

function startUploadTimer() {
    uploadStartTime = Date.now();
}

function updateProgress(percent, uploadedBytes) {
    document.getElementById("uploadBar").style.width = percent + "%";

    const elapsed = (Date.now() - uploadStartTime) / 1000;
    const speed = (uploadedBytes / 1024 / elapsed).toFixed(1);

    document.getElementById("uploadInfo").innerText =
        percent + "% • " + speed + " KB/s";
}


let deferredPrompt;

window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;

    showInstallButton();
});

function showInstallButton() {
    const btn = document.createElement("button");
    btn.innerText = "📲 Install App";
    btn.style.marginTop = "15px";
    btn.onclick = async() => {
        btn.remove();
        deferredPrompt.prompt();
        deferredPrompt = null;
    };

    document.querySelector(".card").appendChild(btn);
}


function playSuccessSound() {
    const audio = new Audio("https://actions.google.com/sounds/v1/cartoon/clang_and_wobble.ogg");
    audio.volume = 0.4;
    audio.play();
}