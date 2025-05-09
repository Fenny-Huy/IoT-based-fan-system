fetch("http://192.168.68.124:5000/summary")
  .then(res => res.json())
  .then(data => {
    document.getElementById("avg_temp").textContent = data.avg_temperature;
    document.getElementById("min_temp").textContent = data.min_temperature;
    document.getElementById("max_temp").textContent = data.max_temperature;

    document.getElementById("avg_hum").textContent = data.avg_humidity;
    document.getElementById("min_hum").textContent = data.min_humidity;
    document.getElementById("max_hum").textContent = data.max_humidity;

    document.getElementById("avg_light").textContent = data.avg_light;
    document.getElementById("min_light").textContent = data.min_light;
    document.getElementById("max_light").textContent = data.max_light;
  })
  .catch(err => {
    console.error("Failed to fetch summary:", err);
    alert("Error fetching summary data");
  });
