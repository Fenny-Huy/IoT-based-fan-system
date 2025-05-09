async function loadSettings() {
  try {
    const res = await fetch("http://192.168.68.124:5000/settings");
    if (!res.ok) throw new Error("Failed to fetch settings");
    const data = await res.json();

    if (data.temp_high_threshold !== undefined && data.temp_low_threshold !== undefined && data.light_threshold !== undefined) {
      document.getElementById("temp-high").value = data.temp_high_threshold;
      document.getElementById("temp-low").value = data.temp_low_threshold;
      document.getElementById("light-threshold").value = data.light_threshold;
    } else {
      document.getElementById("response-msg").textContent = "No settings available. Please set them.";
      document.getElementById("response-msg").style.color = "orange";
    }
  } catch (err) {
    document.getElementById("response-msg").textContent = "Error loading settings.";
    document.getElementById("response-msg").style.color = "red";
  }
}

document.getElementById("settings-form").addEventListener("submit", async function(e) {
  e.preventDefault();

  const payload = {
    temp_high_threshold: parseFloat(document.getElementById("temp-high").value),
    temp_low_threshold: parseFloat(document.getElementById("temp-low").value),
    light_threshold: parseInt(document.getElementById("light-threshold").value)
  };

  try {
    const res = await fetch("http://192.168.68.124:5000/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const msg = document.getElementById("response-msg");
    if (res.ok) {
      msg.textContent = "Settings updated successfully!";
      msg.style.color = "green";
    } else {
      const errorData = await res.json();
      msg.textContent = errorData.error || "Failed to update settings.";
      msg.style.color = "red";
    }
  } catch (err) {
    document.getElementById("response-msg").textContent = "Error updating settings.";
    document.getElementById("response-msg").style.color = "red";
  }
});

loadSettings();
