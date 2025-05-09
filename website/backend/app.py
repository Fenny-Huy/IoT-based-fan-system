from flask import Flask, jsonify, request
from flask_cors import CORS
import pymysql

app = Flask(__name__)
CORS(app, origins="*")  # Enable CORS

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="pi",
        password="",
        database="individual_assign",
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/status', methods=['GET'])
def get_status():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Get current mode
            cursor.execute("SELECT mode FROM mode_log ORDER BY timestamp DESC LIMIT 1")
            mode_result = cursor.fetchone()
            mode = mode_result['mode'] if mode_result else "UNKNOWN"

            # Get latest sensor values
            cursor.execute("SELECT * FROM sensor_log ORDER BY timestamp DESC LIMIT 1")
            sensor = cursor.fetchone()

            # Get latest fan settings
            cursor.execute("SELECT * FROM fan_log ORDER BY timestamp DESC LIMIT 1")
            fan = cursor.fetchone()

        return jsonify({
            "mode": mode,
            "sensor": sensor,
            "fan": fan
        })
    finally:
        conn.close()

@app.route('/summary', methods=['GET'])
def get_summary():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM sensor_log ORDER BY timestamp ASC")
            rows = cursor.fetchall()

        if not rows or len(rows) < 2:
            return jsonify({"message": "Not enough data to summarize"}), 400

        total_time = 0.0
        weighted = {"temperature": 0.0, "humidity": 0.0, "light": 0.0}

        for i in range(len(rows) - 1):
            t1 = rows[i]['timestamp']
            t2 = rows[i+1]['timestamp']
            dt = (t2 - t1).total_seconds()

            weighted["temperature"] += rows[i]['temperature'] * dt
            weighted["humidity"] += rows[i]['humidity'] * dt
            weighted["light"] += rows[i]['light'] * dt
            total_time += dt

        result = {
            "avg_temperature": round(weighted["temperature"] / total_time, 2),
            "avg_humidity": round(weighted["humidity"] / total_time, 2),
            "avg_light": round(weighted["light"] / total_time, 2),
            "min_temperature": min(row['temperature'] for row in rows),
            "max_temperature": max(row['temperature'] for row in rows),
            "min_humidity": min(row['humidity'] for row in rows),
            "max_humidity": max(row['humidity'] for row in rows),
            "min_light": min(row['light'] for row in rows),
            "max_light": max(row['light'] for row in rows)
        }

        return jsonify(result)
    finally:
        conn.close()

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'GET':
                cursor.execute("SELECT * FROM settings ORDER BY updated_at DESC LIMIT 1")
                setting = cursor.fetchone()
                return jsonify(setting if setting else {})

            elif request.method == 'POST':
                data = request.json
                temp_high = data.get("temp_high_threshold")
                temp_low = data.get("temp_low_threshold")
                light = data.get("light_threshold")

                if None in [temp_high, temp_low, light]:
                    return jsonify({"error": "Missing one or more required fields"}), 400

                cursor.execute("""
                    INSERT INTO settings (
                        temp_high_threshold,
                        temp_low_threshold,
                        light_threshold
                    ) VALUES (%s, %s, %s)
                """, (temp_high, temp_low, light))
                
                conn.commit()
                return jsonify({"message": "Settings updated successfully"}), 201
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
