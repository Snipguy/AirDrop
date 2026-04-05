// Request data from PC
fetch("http://PC_IP:5000/send_to_phone", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ data: "Hello from PC" }),
  })
.then(r => r.json())
.then(result => console.log(result));