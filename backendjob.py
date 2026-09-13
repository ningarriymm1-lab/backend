from flask import Flask, render_template_string, request, redirect, url_for, jsonify, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
DB_NAME = 'storage.db'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            filename TEXT
        )
    ''')
    
    cursor.execute("PRAGMA table_info(items)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'filename' not in columns:
        cursor.execute("ALTER TABLE items ADD COLUMN filename TEXT")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('system_title', 'ระบบเก็บข้อมูลของฉัน')")
    
    conn.commit()
    conn.close()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ system_title }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #121212;
            --bg-card: #1E1F22;
            --bg-card-hover: #2B2D31;
            --text-main: #E3E3E3;
            --text-sub: #9E9E9E;
            --accent: #A4C8F0;
            --accent-hover: #8AB8EC;
            --border: #2D2F31;
            --danger: #F28B82;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Noto Sans Thai', sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background-color: var(--bg-main); color: var(--text-main); min-height: 100vh; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        
        header { margin-bottom: 20px; text-align: left; }
        h1 { font-size: 26px; font-weight: 700; color: #FFFFFF; margin-bottom: 5px; }
        
        .editable-title {
            background: transparent; border: 1px dashed transparent; color: var(--text-sub);
            font-size: 15px; padding: 4px 8px; border-radius: 6px; width: 100%; max-width: 350px; transition: all 0.2s;
        }
        .editable-title:hover, .editable-title:focus {
            background: var(--bg-card); border-color: var(--accent); color: var(--text-main); outline: none;
        }

        /* Toolbar & Mobile Friendly */
        .toolbar {
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;
            gap: 12px; margin-bottom: 20px; background-color: var(--bg-card); padding: 12px 16px;
            border-radius: 14px; border: 1px solid var(--border);
        }
        .tabs { display: flex; gap: 6px; flex-wrap: wrap; width: 100%; }
        .tab-btn {
            background: var(--bg-main); border: 1px solid var(--border); color: var(--text-sub); padding: 8px 12px;
            border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; flex: 1; text-align: center;
        }
        .tab-btn:hover { color: var(--text-main); background: var(--bg-card-hover); }
        .tab-btn.active { background-color: var(--accent); color: #121212; border-color: var(--accent); font-weight: 600; }

        .actions { display: flex; gap: 10px; width: 100%; align-items: center; }
        .search-box {
            background: var(--bg-main); border: 1px solid var(--border); color: var(--text-main);
            padding: 10px 14px; border-radius: 10px; font-size: 14px; outline: none; flex: 1;
        }
        .search-box:focus { border-color: var(--accent); }

        .btn-primary {
            background-color: var(--accent); color: #121212; border: none; padding: 10px 16px;
            border-radius: 10px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; text-decoration: none;
            white-space: nowrap; font-size: 14px; transition: background-color 0.2s;
        }
        .btn-primary:hover { background-color: var(--accent-hover); }

        /* Grid Cards */
        .grid-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
        .card {
            background-color: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
            padding: 14px; position: relative; display: flex; flex-direction: column; align-items: center; text-align: center;
            transition: border-color 0.2s;
        }
        .card:hover { border-color: var(--accent); }
        .card-icon { font-size: 36px; margin-bottom: 8px; height: 50px; display: flex; align-items: center; justify-content: center; }
        .card-title { font-size: 14px; font-weight: 500; color: var(--text-main); margin-bottom: 4px; width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .card-category { font-size: 11px; color: var(--text-sub); background: var(--bg-main); padding: 2px 6px; border-radius: 4px; margin-bottom: 10px; }
        
        .card-actions { display: flex; gap: 6px; width: 100%; margin-top: auto; }
        .card-btn { padding: 6px 4px; border-radius: 6px; border: none; font-size: 12px; cursor: pointer; font-weight: 500; display: inline-block; text-align: center; text-decoration: none;}
        .btn-download { background: rgba(164, 200, 240, 0.1); color: var(--accent); flex: 1; }
        .btn-download:hover { background: var(--accent); color: #121212; }
        .btn-delete { background: rgba(242, 139, 130, 0.1); color: var(--danger); flex: 1; }
        .btn-delete:hover { background: var(--danger); color: #121212; }

        .empty-state { grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-sub); font-size: 14px; }

        /* Modal ดีไซน์มือถือ */
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); backdrop-filter: blur(5px); justify-content: center; align-items: flex-end; z-index: 1000; }
        .modal.active { display: flex; }
        .modal-content { background: var(--bg-card); border: 1px solid var(--border); padding: 24px 20px 30px 20px; border-radius: 20px 20px 0 0; width: 100%; max-width: 500px; animation: slideUp 0.25s ease-out; }
        
        @keyframes slideUp {
            from { transform: translateY(100%); }
            to { transform: translateY(0); }
        }

        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
        .modal-content h3 { color: #fff; font-size: 18px; font-weight: 600; }
        .close-btn { background: none; border: none; color: var(--text-sub); font-size: 20px; cursor: pointer; }

        /* ปุ่มเลือกหมวดหมู่แบบ Grid ใน Modal */
        .category-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 15px; }
        .cat-select-btn {
            background: var(--bg-main); border: 2px solid var(--border); border-radius: 12px; padding: 12px;
            text-align: center; color: var(--text-main); cursor: pointer; font-size: 14px; font-weight: 500;
            display: flex; flex-direction: column; align-items: center; gap: 6px; transition: all 0.2s;
        }
        .cat-select-btn span { font-size: 22px; }
        .cat-select-btn.selected { border-color: var(--accent); background: rgba(164, 200, 240, 0.08); color: var(--accent); }

        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 12px; color: var(--text-sub); margin-bottom: 5px; font-weight: 500; }
        .form-control { width: 100%; background: var(--bg-main); border: 1px solid var(--border); color: var(--text-main); padding: 11px 14px; border-radius: 10px; font-size: 14px; outline: none; }
        .form-control:focus { border-color: var(--accent); }

        /* Dropzone อัปโหลดไฟล์ */
        .file-drop-area {
            border: 2px dashed var(--border); border-radius: 10px; padding: 18px; text-align: center;
            background: var(--bg-main); cursor: pointer; position: relative; transition: border-color 0.2s;
        }
        .file-drop-area input[type="file"] { position: absolute; left: 0; top: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
        .file-msg { font-size: 13px; color: var(--text-sub); pointer-events: none; }
        .file-msg span { color: var(--accent); font-weight: 500; }

        .modal-actions { display: flex; gap: 10px; margin-top: 20px; }
        .btn-secondary { background: transparent; border: 1px solid var(--border); color: var(--text-main); padding: 11px; border-radius: 10px; cursor: pointer; font-weight: 500; flex: 1; text-align: center; }
        .btn-submit { flex: 2; padding: 11px; border-radius: 10px; }

        @media(min-width: 600px) {
            body { padding: 30px; }
            h1 { font-size: 30px; }
            .modal { align-items: center; }
            .modal-content { border-radius: 16px; padding: 24px; animation: none; }
            .grid-container { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }
        }
    </style>
</head>
<body>

    <div class="container">
        <header>
            <h1>ระบบเก็บข้อมูล</h1>
            <input type="text" id="systemTitleInput" class="editable-title" value="{{ system_title }}" placeholder="คลิกเพื่อพิมพ์ชื่อระบบของคุณ...">
        </header>

        <div class="toolbar">
            <div class="actions">
                <input type="text" id="searchInput" class="search-box" placeholder="🔍 ค้นหาข้อมูล..." oninput="handleSearch()">
                <button class="btn-primary" onclick="openModal()">
                    ➕ เพิ่มข้อมูล
                </button>
            </div>
            <div class="tabs">
                <button class="tab-btn active" onclick="filterCategory('all', this)">ทั้งหมด</button>
                <button class="tab-btn" onclick="filterCategory('file', this)">📁 ไฟล์</button>
                <button class="tab-btn" onclick="filterCategory('image', this)">🖼️ รูป</button>
                <button class="tab-btn" onclick="filterCategory('drive', this)">💽 ไดรฟ์</button>
                <button class="tab-btn" onclick="filterCategory('album', this)">🗂️ อัลบั้ม</button>
            </div>
        </div>

        <div class="grid-container" id="itemGrid">
            {% for item in items %}
            <div class="card item-card" data-category="{{ item.category }}" data-name="{{ item.name | lower }}">
                <div class="card-icon">
                    {% if item.category == 'image' %}🖼️
                    {% elif item.category == 'drive' %}💽
                    {% elif item.category == 'album' %}🗂️
                    {% else %}📁{% endif %}
                </div>
                <div class="card-title" title="{{ item.name }}">{{ item.name }}</div>
                <div class="card-category">
                    {% if item.category == 'image' %}รูป
                    {% elif item.category == 'drive' %}ไดรฟ์
                    {% elif item.category == 'album' %}อัลบั้ม
                    {% else %}ไฟล์{% endif %}
                </div>
                <div class="card-actions">
                    {% if item.filename %}
                    <a href="{{ url_for('download_file', filename=item.filename) }}" class="card-btn btn-download" target="_blank">ดาวน์โหลด</a>
                    {% endif %}
                    <form action="{{ url_for('delete_item', item_id=item.id) }}" method="POST" style="flex: 1; display: flex;" onsubmit="return confirm('ต้องการลบข้อมูลนี้ใช่หรือไม่?');">
                        <button type="submit" class="card-btn btn-delete" style="width: 100%;">ลบ</button>
                    </form>
                </div>
            </div>
            {% endfor %}
            <div class="empty-state" id="emptyState" style="display: none;">ไม่พบข้อมูลที่คุณค้นหา</div>
        </div>
    </div>

    <!-- Modal เพิ่มข้อมูลแบบเลือกประเภทไฟล์ได้ง่ายบนมือถือ -->
    <div class="modal" id="addModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>เพิ่มข้อมูลใหม่</h3>
                <button class="close-btn" onclick="closeModal()">✕</button>
            </div>
            <form action="{{ url_for('add_item') }}" method="POST" enctype="multipart/form-data">
                
                <!-- เลือกประเภทไฟล์ผ่านปุ่มไอคอน -->
                <div class="form-group">
                    <label>เลือกประเภท (หมวดหมู่)</label>
                    <input type="hidden" name="category" id="selectedCategory" value="file">
                    <div class="category-grid">
                        <div class="cat-select-btn selected" id="cat-file" onclick="selectCategory('file')">
                            <span>📁</span> ไฟล์ทั่วไป
                        </div>
                        <div class="cat-select-btn" id="cat-image" onclick="selectCategory('image')">
                            <span>🖼️</span> รูปภาพ
                        </div>
                        <div class="cat-select-btn" id="cat-drive" onclick="selectCategory('drive')">
                            <span>💽</span> ไดรฟ์
                        </div>
                        <div class="cat-select-btn" id="cat-album" onclick="selectCategory('album')">
                            <span>🗂️</span> อัลบั้ม
                        </div>
                    </div>
                </div>

                <div class="form-group">
                    <label>ชื่อที่แสดง</label>
                    <input type="text" name="name" id="itemName" class="form-control" required placeholder="เช่น เอกสารงบประมาณ">
                </div>

                <div class="form-group">
                    <label>ไฟล์แนบ (มือถือเลือกได้ทุกไฟล์)</label>
                    <div class="file-drop-area">
                        <input type="file" name="file" id="fileInput" accept="*/*" required onchange="handleFileSelect(this)">
                        <div class="file-msg" id="fileMsg">
                            📂 แตะเพื่อเลือกไฟล์ (PDF, รูป, ซิป, อื่นๆ)
                        </div>
                    </div>
                </div>

                <div class="modal-actions">
                    <button type="button" class="btn-secondary" onclick="closeModal()">ยกเลิก</button>
                    <button type="submit" class="btn-primary btn-submit">อัปโหลด</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let currentCategory = 'all';

        const titleInput = document.getElementById('systemTitleInput');
        let timeout = null;
        titleInput.addEventListener('input', () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                fetch('/update_title', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: titleInput.value })
                });
            }, 500);
        });

        // ฟังก์ชันเลือกหมวดหมู่ใน Modal
        function selectCategory(cat) {
            document.getElementById('selectedCategory').value = cat;
            document.querySelectorAll('.cat-select-btn').forEach(btn => btn.classList.remove('selected'));
            document.getElementById('cat-' + cat).classList.add('selected');
        }

        // ฟังก์ชันแสดงชื่อไฟล์และเติมชื่อให้อัตโนมัติ
        function handleFileSelect(input) {
            const fileMsg = document.getElementById('fileMsg');
            const nameInput = document.getElementById('itemName');
            
            if (input.files && input.files.length > 0) {
                const fileName = input.files[0].name;
                fileMsg.innerHTML = `✅ เลือก: <strong style="color: var(--accent);">${fileName}</strong>`;
                
                if (!nameInput.value.trim()) {
                    const cleanName = fileName.substring(0, fileName.lastIndexOf('.')) || fileName;
                    nameInput.value = cleanName;
                }
            } else {
                fileMsg.innerHTML = `📂 แตะเพื่อเลือกไฟล์ (PDF, รูป, ซิป, อื่นๆ)`;
            }
        }

        function filterCategory(category, btnElement) {
            currentCategory = category;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btnElement.classList.add('active');
            handleSearch();
        }

        function handleSearch() {
            const query = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.item-card');
            let visibleCount = 0;

            cards.forEach(card => {
                const cat = card.getAttribute('data-category');
                const name = card.getAttribute('data-name');
                const matchCategory = currentCategory === 'all' || cat === currentCategory;
                const matchQuery = name.includes(query);

                if (matchCategory && matchQuery) {
                    card.style.display = 'flex';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            document.getElementById('emptyState').style.display = visibleCount === 0 ? 'block' : 'none';
        }

        function openModal() { document.getElementById('addModal').classList.add('active'); }
        function closeModal() { 
            document.getElementById('addModal').classList.remove('active');
            document.getElementById('fileMsg').innerHTML = `📂 แตะเพื่อเลือกไฟล์ (PDF, รูป, ซิป, อื่นๆ)`;
        }
    </script>
</body>
</html>
'''

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'system_title'")
    row = cursor.fetchone()
    system_title = row[0] if row else 'ระบบเก็บข้อมูลของฉัน'
    
    cursor.execute("SELECT id, name, category, filename FROM items ORDER BY id DESC")
    items = [{'id': r[0], 'name': r[1], 'category': r[2], 'filename': r[3]} for r in cursor.fetchall()]
    conn.close()
    return render_template_string(HTML_TEMPLATE, items=items, system_title=system_title)

@app.route('/add', methods=['POST'])
def add_item():
    name = request.form.get('name')
    category = request.form.get('category')
    file = request.files.get('file')
    
    filename = None
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        base, ext = os.path.splitext(filename)
        counter = 1
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        while os.path.exists(filepath):
            filename = f"{base}_{counter}{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            counter += 1
        file.save(filepath)

    if name:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO items (name, category, filename) VALUES (?, ?, ?)", (name, category, filename))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT filename FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if row and row[0]:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], row[0])
        if os.path.exists(filepath):
            os.remove(filepath)
            
    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/update_title', methods=['POST'])
def update_title():
    data = request.get_json()
    new_title = data.get('title')
    if new_title:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'system_title'", (new_title,))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
