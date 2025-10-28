from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import json
import datetime
import os
import uuid
import webbrowser
import threading
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'disaster_management_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Create uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Database setup
def init_db():
    conn = sqlite3.connect('disaster_app.db')
    cursor = conn.cursor()
    
    # Create safe locations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS safe_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            capacity INTEGER,
            contact TEXT,
            type TEXT,
            description TEXT
        )
    ''')
    
    # Create emergency reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emergency_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            latitude REAL,
            longitude REAL,
            timestamp TEXT,
            status TEXT DEFAULT 'active',
            video_path TEXT,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample safe locations
    sample_locations = [
        ('Emergency Shelter Alpha', 37.78825, -122.4324, 200, '+1-555-0101', 'shelter', 'Community Center - Capacity: 200 people'),
        ('Safe House Beta', 37.78425, -122.4284, 150, '+1-555-0102', 'safehouse', 'School Gymnasium - Medical facilities available'),
        ('Emergency Bunker Gamma', 37.79225, -122.4364, 75, '+1-555-0103', 'bunker', 'Underground facility - Storm shelter'),
        ('Rescue Station Delta', 37.78025, -122.4244, 50, '+1-555-0104', 'rescue', 'Fire Station - Emergency services')
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO safe_locations (name, latitude, longitude, capacity, contact, type, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', sample_locations)
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    print("🌐 Serving main page...")
    return render_template('index.html')

@app.route('/admin')
def admin_dashboard():
    print("🔧 Admin dashboard accessed")
    return render_template('admin.html')

@app.route('/monitor')
def emergency_monitor():
    print("📺 Emergency monitor screen accessed")
    return render_template('monitor.html')

@app.route('/api/safe-locations')
def get_safe_locations():
    print("📍 Fetching safe locations...")
    conn = sqlite3.connect('disaster_app.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM safe_locations')
    locations = cursor.fetchall()
    conn.close()
    
    location_list = []
    for loc in locations:
        location_list.append({
            'id': loc[0],
            'name': loc[1],
            'latitude': loc[2],
            'longitude': loc[3],
            'capacity': loc[4],
            'contact': loc[5],
            'type': loc[6],
            'description': loc[7]
        })
    
    print(f"📍 Found {len(location_list)} safe locations")
    return jsonify(location_list)

@app.route('/api/emergency', methods=['POST'])
def emergency_alert():
    print("🚨 EMERGENCY ALERT RECEIVED!")
    data = request.json
    user_id = data.get('user_id', 'anonymous')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    description = data.get('description', 'Emergency alert activated')
    video_path = data.get('video_path', '')
    
    print(f"🚨 User: {user_id}")
    print(f"🚨 Location: {latitude}, {longitude}")
    print(f"🚨 Description: {description}")
    if video_path:
        print(f"🚨 Video: {video_path}")
    
    # Save to database
    conn = sqlite3.connect('disaster_app.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO emergency_reports (user_id, latitude, longitude, timestamp, status, description, video_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, latitude, longitude, datetime.datetime.now().isoformat(), 'active', description, video_path))
    conn.commit()
    conn.close()
    
    # Log emergency alert (for emergency services monitoring)
    print(f"🚨 EMERGENCY ALERT: User {user_id} at {latitude}, {longitude}")
    print(f"Description: {description}")
    print(f"Time: {datetime.datetime.now()}")
    
    return jsonify({'status': 'success', 'message': 'Emergency alert sent'})

@app.route('/api/emergency-reports')
def get_emergency_reports():
    conn = sqlite3.connect('disaster_app.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM emergency_reports ORDER BY timestamp DESC LIMIT 50')
    reports = cursor.fetchall()
    conn.close()
    
    report_list = []
    for report in reports:
        report_list.append({
            'id': report[0],
            'user_id': report[1],
            'latitude': report[2],
            'longitude': report[3],
            'timestamp': report[4],
            'status': report[5],
            'video_path': report[6],
            'description': report[7]
        })
    
    return jsonify(report_list)

@app.route('/api/status')
def get_status():
    print("🔍 Status check requested")
    return jsonify({'status': 'connected', 'message': 'Emergency system is online'})

# Admin API routes
@app.route('/api/resolve-report/<int:report_id>', methods=['POST'])
def resolve_report(report_id):
    print(f"✅ Resolving report #{report_id}")
    conn = sqlite3.connect('disaster_app.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE emergency_reports SET status = ? WHERE id = ?', ('resolved', report_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Report resolved'})

@app.route('/api/delete-report/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):
    print(f"🗑️ Deleting report #{report_id}")
    conn = sqlite3.connect('disaster_app.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM emergency_reports WHERE id = ?', (report_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Report deleted'})

@app.route('/api/upload-video', methods=['POST'])
def upload_video():
    print("📹 Video upload request received")
    if 'video' not in request.files:
        return jsonify({'status': 'error', 'message': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400
    
    if file:
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        print(f"📹 Video saved: {filepath}")
        return jsonify({'status': 'success', 'file_path': filepath})
    
    return jsonify({'status': 'error', 'message': 'Upload failed'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def open_monitor():
    """Open monitoring screen in browser after 2 seconds"""
    threading.Timer(2, lambda: webbrowser.open('http://localhost:5000/monitor')).start()

if __name__ == '__main__':
    init_db()
    print("🚀 Starting Disaster Management App...")
    print("📱 Main App: http://localhost:5000")
    print("🔧 Admin Dashboard: http://localhost:5000/admin")
    print("📺 Emergency Monitor: http://localhost:5000/monitor")
    print("\n🖥️  Opening Emergency Monitoring Screen...")
    
    # Auto-open monitoring screen
    open_monitor()
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
