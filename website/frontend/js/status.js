fetch("http://192.168.68.124:5000/status")
  .then(res => res.json())
  .then(data => {
    document.getElementById("mode").textContent = data.mode || "UNKNOWN";

    if (data.sensor) {
      document.getElementById("temperature").textContent = data.sensor.temperature;
      document.getElementById("humidity").textContent = data.sensor.humidity;
      document.getElementById("light").textContent = data.sensor.light;
    }

    if (data.fan) {
      document.getElementById("fan_speed").textContent = data.fan.speed;
      document.getElementById("fan_source").textContent = data.fan.source;
    }
  })
  .catch(err => {
    console.error("Failed to fetch status:", err);
    alert("Error fetching status data");
  });
