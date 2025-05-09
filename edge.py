import serial
import pymysql
from datetime import datetime

# --- Initialize ---
device = '/dev/ttyACM0'
arduino = serial.Serial(device, 9600, timeout=1)

db = pymysql.connect(
    host="localhost",
    user="pi",
    password="",
    database="individual_assign",
    autocommit=True,  # Optional but may help if issues persist
    cursorclass=pymysql.cursors.Cursor
)
db.begin()  # Start transaction explicitly if autocommit is False

cursor = db.cursor()

last_mode = None
last_sensor = {"temperature": None, "humidity": None, "light": None}
last_fan_speed = None
last_fan_source = None

buzzer_state = None  # None, "ON", or "OFF"

import time

buzzer_thresholds = {
    "temp_high": 30.0,
    "temp_low": 15.0,
    "light": 30
}

last_threshold_update = 0

def fetch_thresholds():
    global cursor
    try:
        # Re-create the cursor to force a fresh context
        cursor.close()
        cursor = db.cursor()
        
        cursor.execute("SELECT temp_high_threshold, temp_low_threshold, light_threshold FROM settings ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        if result:
            buzzer_thresholds["temp_high"] = result[0]
            buzzer_thresholds["temp_low"] = result[1]
            buzzer_thresholds["light"] = result[2]
            
    except Exception as e:
        print(f"Error fetching thresholds: {e}")




def sensor_changed(temp, hum, light):
    global last_sensor
    if last_sensor["temperature"] is None:
        return True
    return (
        abs(temp - last_sensor["temperature"]) > 0.5 or
        abs(hum - last_sensor["humidity"]) > 2 or
        abs(light - last_sensor["light"]) > 8
    )

print("System started and connected.")

try:
    while True:
        # Periodically update thresholds

        if time.time() - last_threshold_update > 3:
            fetch_thresholds()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Thresholds updated: {buzzer_thresholds}")
            last_threshold_update = time.time()


        line = arduino.readline().decode('utf-8').strip()
        if not line:
            continue

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if line.startswith("MODE:"):
            mode = line.split(":")[1]
            if mode != last_mode:
                print(f"[{now}] Attempting to insert MODE: {mode}")
                try:
                    cursor.execute("INSERT INTO mode_log (mode) VALUES (%s)", (mode,))
                    db.commit()
                    print(f"[{now}] MODE insert successful")
                    last_mode = mode
                except Exception as e:
                    print(f"[{now}] MODE insert failed: {e}")

        elif last_mode == "AUTO" and line.startswith("TEMP:"):
            temp = float(line.split(":")[1].replace("C", ""))

        elif last_mode == "AUTO" and line.startswith("HUM:"):
            hum = float(line.split(":")[1].replace("%", ""))

        elif last_mode == "AUTO" and line.startswith("LIGHT:"):
            light_str = line.split(":")[1].replace("%", "")
            light = int(light_str)

            # Debug print for sensor values
            print(f"[{now}] SENSOR READINGS - Temp: {temp}, Hum: {hum}, Light: {light}")
            # Edge Analytics: control buzzer from Pi based on temperature with state tracking
            if light > buzzer_thresholds["light"]:
                if temp > buzzer_thresholds["temp_high"]:
                    if buzzer_state != "ON":
                        arduino.write(b"BUZZ:ON\n")
                        buzzer_state = "ON"
                        print(f"[{now}] BUZZER ACTIVATED (HIGH TEMP) due to temp={temp}")
                elif temp < buzzer_thresholds["temp_low"]:
                    if buzzer_state != "ON":
                        arduino.write(b"BUZZ:ON\n")
                        buzzer_state = "ON"
                        print(f"[{now}] BUZZER ACTIVATED (LOW TEMP) due to temp={temp}")
                else:
                    if buzzer_state != "OFF":
                        arduino.write(b"BUZZ:OFF\n")
                        buzzer_state = "OFF"
                        print(f"[{now}] BUZZER DEACTIVATED due to temp={temp}")
            else:
                if buzzer_state != "OFF":
                    arduino.write(b"BUZZ:OFF\n")
                    buzzer_state = "OFF"
                    print(f"[{now}] BUZZER DEACTIVATED due to light={light}")


            print(f"[{now}] LAST SENSOR - {last_sensor}")

            if sensor_changed(temp, hum, light):
                print(f"[{now}] Attempting to insert SENSOR: Temp={temp}, Hum={hum}, Light={light}")
                try:
                    cursor.execute(
                        "INSERT INTO sensor_log (temperature, humidity, light) VALUES (%s, %s, %s)",
                        (temp, hum, light)
                    )
                    db.commit()
                    print(f"[{now}] SENSOR insert successful")
                    last_sensor = {"temperature": temp, "humidity": hum, "light": light}
                except Exception as e:
                    print(f"[{now}] SENSOR insert failed: {e}")
            else:
                print(f"[{now}] SENSOR values unchanged, skipping insert.")

        elif last_mode == "MANUAL" and line.startswith("FAN:"):
            parts = line.split("=")
            if len(parts) == 2:
                source_part = parts[0]  # FAN:POT or FAN:FIXED
                source = source_part.split(":")[1]
                speed = int(parts[1].replace("%", ""))

                # Debug print for fan values
                print(f"[{now}] FAN READINGS - Source: {source}, Speed: {speed}")
                print(f"[{now}] LAST FAN - Source: {last_fan_source}, Speed: {last_fan_speed}")

                if last_fan_speed is None or abs(speed - last_fan_speed) > 2 or source != last_fan_source:
                    print(f"[{now}] Attempting to insert FAN: Source={source}, Speed={speed}")
                    try:
                        cursor.execute(
                            "INSERT INTO fan_log (source, speed) VALUES (%s, %s)",
                            (source, speed)
                        )
                        db.commit()
                        print(f"[{now}] FAN insert successful")
                        last_fan_speed = speed
                        last_fan_source = source
                    except Exception as e:
                        print(f"[{now}] FAN insert failed: {e}")
                else:
                    print(f"[{now}] FAN values unchanged, skipping insert.")

except KeyboardInterrupt:
    print("Stopped by user.")
finally:
    cursor.close()
    db.close()
