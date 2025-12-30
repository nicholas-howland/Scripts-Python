import os
from pathlib import Path
from flask import Flask, request, redirect, url_for, send_from_directory, render_template_string, abort
from werkzeug.utils import secure_filename

APP_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Basic limits/safety (tweak as needed)
MAX_CONTENT_LENGTH = 250 * 1024 * 1024  # 250 MB
ALLOWED_EXTENSIONS = None  # e.g. set({"txt","png","jpg","pdf"}) to restrict

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>File Upload</title>
  <style>
    body {
      margin: 0;
      padding: 24px;
      background: #000;
      color: #fff;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      line-height: 1.4;
    }
    a { color: #fff; }
    .box {
      border: 1px solid #444;
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 16px;
      background: #0a0a0a;
    }
    input[type="file"] { color: #fff; }
    input[type="submit"]{
      background: #111;
      color: #fff;
      border: 1px solid #555;
      padding: 8px 14px;
      border-radius: 8px;
      cursor: pointer;
    }
    input[type="submit"]:hover { border-color: #aaa; }
    .msg { color: #9f9; margin-top: 8px; }
    .err { color: #f99; margin-top: 8px; }
    ul { margin: 0; padding-left: 22px; }
    li { margin: 4px 0; }
    .small { color: #bbb; font-size: 12px; }
  </style>
</head>
<body>
  <h1>Upload Server</h1>

  <div class="box">
    <form method="POST" action="/upload" enctype="multipart/form-data">
      <input type="file" name="file" required>
      <input type="submit" value="Upload">
    </form>
    {% if message %}<div class="msg">{{ message }}</div>{% endif %}
    {% if error %}<div class="err">{{ error }}</div>{% endif %}
    <div class="small">Files are stored in: {{ upload_dir }}</div>
  </div>

  <div class="box">
    <h2>Uploaded files ({{ files|length }})</h2>
    {% if files %}
      <ul>
        {% for f in files %}
          <li><a href="/files/{{ f }}">{{ f }}</a></li>
        {% endfor %}
      </ul>
    {% else %}
      <div class="small">No files uploaded yet.</div>
    {% endif %}
  </div>
</body>
</html>
"""

def allowed_file(filename: str) -> bool:
    if not filename or filename in {".", ".."}:
        return False
    if ALLOWED_EXTENSIONS is None:
        return True
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXTENSIONS

def list_files():
    files = []
    for p in UPLOAD_DIR.iterdir():
        if p.is_file():
            files.append(p.name)
    return sorted(files, key=str.lower)

@app.get("/")
def index():
    return render_template_string(PAGE, files=list_files(), message=None, error=None, upload_dir=str(UPLOAD_DIR))

@app.post("/upload")
def upload():
    if "file" not in request.files:
        return render_template_string(PAGE, files=list_files(), message=None, error="No file part in request.", upload_dir=str(UPLOAD_DIR))

    f = request.files["file"]
    if not f or f.filename == "":
        return render_template_string(PAGE, files=list_files(), message=None, error="No file selected.", upload_dir=str(UPLOAD_DIR))

    filename = secure_filename(f.filename)
    if not filename:
        return render_template_string(PAGE, files=list_files(), message=None, error="Invalid filename.", upload_dir=str(UPLOAD_DIR))

    if not allowed_file(filename):
        return render_template_string(PAGE, files=list_files(), message=None, error="File type not allowed.", upload_dir=str(UPLOAD_DIR))

    dest = UPLOAD_DIR / filename

    # Avoid overwriting: if exists, append -N
    if dest.exists():
        stem = dest.stem
        suffix = dest.suffix
        i = 1
        while True:
            candidate = UPLOAD_DIR / f"{stem}-{i}{suffix}"
            if not candidate.exists():
                dest = candidate
                break
            i += 1

    f.save(dest)
    return render_template_string(PAGE, files=list_files(), message=f"Uploaded: {dest.name}", error=None, upload_dir=str(UPLOAD_DIR))

@app.get("/files/<path:filename>")
def download(filename):
    # Prevent sneaky paths
    safe = secure_filename(Path(filename).name)
    if not safe:
        abort(404)
    file_path = UPLOAD_DIR / safe
    if not file_path.exists():
        abort(404)
    return send_from_directory(UPLOAD_DIR, safe, as_attachment=False)

if __name__ == "__main__":
    # 0.0.0.0 exposes to your LAN; change to 127.0.0.1 for local-only
    app.run(host="0.0.0.0", port=80, debug=False)
