import os
import re
import requests
from flask import Flask, request, jsonify, send_from_directory, abort
import hmac
import hashlib
import zipfile
import datetime
import shutil
import subprocess
import sys
from werkzeug.utils import secure_filename
import platform
import urllib.request
import tarfile
import tempfile
import secretkey

# ==== CONFIGURATION ====
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # optional, for private repos
AUTHOR = "jonasb2510"
PROJECT = "godot-platformer-v2"
REPO = f"{AUTHOR}/{PROJECT}"  # e.g. "octocat/Hello-World"
DOWNLOAD_DIR = "downloads"
WEBAPP_DIR = "web"
TEMP_DIR = "temp"
EXCLUDE_FROM_RM = ["debug"]
GODOT_PATH = "E:\Godot_v4.4.1-stable_win64.exe\Godot_v4.4.1-stable_win64.exe"
PREFIX_OLD = "platformerv2"
PREFIX_NEW = "index"
GODOT_DIR = "godot"
GODOT_VER = "4.5.1"
GODOT_EXEC = os.path.join(GODOT_DIR, f"Godot_v{GODOT_VER}-stable_linux.x86_64")
EXPORT_TEMPLATES_DIR = os.path.expanduser("~/.local/share/godot/export_templates")#"templates"#os.path.expanduser("~/.local/share/godot/export_templates")
GODOT_DOWNLOAD_ENV = "GODOT_DOWNLOAD"
VERSION_EXPORT_DIR = f"{GODOT_VER}.stable"

# ========================
app = Flask(__name__)

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
if not os.path.exists(WEBAPP_DIR):
    os.makedirs(WEBAPP_DIR, exist_ok=True)
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def verify_github_signature(request):
    """Verify GitHub webhook HMAC signature."""
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        abort(400, "Missing signature header")

    sha_name, signature = signature_header.split("=")
    if sha_name != "sha256":
        abort(400, "Unsupported hash type")

    # Compute our own HMAC
    mac = hmac.new(secretkey.secret, msg=request.data, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()

    # Compare securely to avoid timing attacks
    if not hmac.compare_digest(signature, expected_signature):
        abort(403, "Invalid signature")


def download_file(url, filename):
    """Download a file from GitHub and save it locally."""
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()

    filepath = os.path.join(DOWNLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"✅ Downloaded: {filepath}")
    return filepath

def process_branch_zip():
    ct = str(datetime.datetime.now())
    ct = ct.replace(" ", "_")
    ct = ct.replace(":", "-")
    zippath = os.path.join(DOWNLOAD_DIR, "main.zip")
    temp_path = os.path.join(TEMP_DIR, str(ct))
    temp_path_file = os.path.join(TEMP_DIR, str(ct), "main.zip")
    os.makedirs(temp_path)
    shutil.move(zippath, temp_path)
    with zipfile.ZipFile(temp_path_file, 'r') as zip_ref:
        zip_ref.extractall(temp_path)
    os.remove(temp_path_file)
    path_list = os.listdir(temp_path)
    for a in path_list:
        if a.startswith(PROJECT):
            folder = a
            break
    EXPORT_PRESET = "Web"
    PROJECT_PATH = os.path.join(os.getcwd(), temp_path, folder)
    OUTPUT_DIR = os.path.join(os.getcwd(), WEBAPP_DIR, "debug")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")
    if platform.system().lower() == "linux":
        os.chmod(GODOT_EXEC, 0o755)
        GODOT_PATH = os.path.join(os.getcwd(), GODOT_EXEC)
    cmd = [
    GODOT_PATH,
    "--headless",                # Run without GUI
    "--path", PROJECT_PATH,      # Project directory
    "--export-release", EXPORT_PRESET,  # Use export preset
    OUTPUT_FILE
    ]   
    print("Running:", " ".join(cmd))

    # Run the command
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(f"❌ Export failed with code {result.returncode}")
    else:
        print("✅ Export successful!")
    shutil.rmtree(temp_path)

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_web(path):
    """Serve files from ./web at root (/)"""
    path = secure_filename(path)
    full_path = os.path.join(WEBAPP_DIR, path)
    if os.path.isfile(full_path):
        return send_from_directory(WEBAPP_DIR, path)
    else:
        # Fallback to index.html if it exists (e.g., for SPAs)
        index_file = PREFIX_OLD + ".html"
        index_path = os.path.join(WEBAPP_DIR, index_file)
        print(index_path)
        if os.path.isfile(index_path):
            return send_from_directory(WEBAPP_DIR, index_file)
        return "File not found", 404


@app.route("/debug/", defaults={"path": ""})
@app.route("/debug/<path:path>")
def serve_debug(path):
    path = secure_filename(path)
    DEBUG_ROOT = os.path.join(WEBAPP_DIR, "debug")
    """Serve files from ./web/debug at /debug"""
    full_path = os.path.join(DEBUG_ROOT, path)
    if os.path.isfile(full_path):
        return send_from_directory(DEBUG_ROOT, path)
    else:
        index_path = os.path.join(DEBUG_ROOT, "index.html")
        if os.path.isfile(index_path):
            return send_from_directory(DEBUG_ROOT, "index.html")
        return "File not found", 404

def process_release_publish():
    ct = str(datetime.datetime.now())
    ct = ct.replace(" ", "_")
    ct = ct.replace(":", "-")
    zippath = os.path.join(DOWNLOAD_DIR, "web.zip")
    temp_path = os.path.join(TEMP_DIR, str(ct))
    temp_path_file = os.path.join(TEMP_DIR, str(ct), "web.zip")
    os.makedirs(temp_path)
    shutil.move(zippath, temp_path)
    with zipfile.ZipFile(temp_path_file, 'r') as zip_ref:
        zip_ref.extractall(temp_path)
    os.remove(temp_path_file)
    os.makedirs(WEBAPP_DIR, exist_ok=True)
    for b in os.listdir(WEBAPP_DIR):
        if b in EXCLUDE_FROM_RM:
            continue
        supidupipfad = os.path.join(WEBAPP_DIR, b)
        if os.path.isdir(supidupipfad):
            os.rmdir(supidupipfad)
        else:
            os.remove(supidupipfad)
    project_folder = temp_path
    for c in os.listdir(project_folder):
        shutil.move(os.path.join(project_folder, c), WEBAPP_DIR)
    shutil.rmtree(temp_path)

@app.route("/webhook", methods=["POST"])
def webhook():
    event_type = request.headers.get("X-GitHub-Event")
    payload = request.json

    verify_github_signature(request)

    if event_type == "push":
        branch = payload.get("ref", "").split("/")[-1]
        if branch == "main":
            print("📦 Push to main detected — downloading branch zip...")
            url = f"https://github.com/{REPO}/archive/refs/heads/main.zip"
            download_file(url, "main.zip")
            process_branch_zip()
        else:
            print(f"Push to {branch} ignored.")

    elif event_type == "release":
        action = payload.get("action")
        if action in ["published"]: #"released", 
            print("🚀 Release detected — fetching release assets...")
            release = payload.get("release", {})
            assets = release.get("assets", [])
            for asset in assets:
                name = asset.get("name", "")
                if re.match(r"web.*\.zip$", name):
                    download_url = asset["browser_download_url"]
                    if not download_url.startswith(f"https://github.com/{AUTHOR}/{PROJECT}/releases/download/"):
                        break
                    download_file(download_url, "web.zip")
                    process_release_publish()
                    break
            else:
                print("No matching web*.zip found in release assets.")
        else:
            print(f"Ignoring release action: {action}")

    else:
        print(f"Ignored event: {event_type}")

    return jsonify({"status": "ok"}), 200

def get_latest_godot_release():
    """Fetch the latest stable Godot version info from GitHub."""
    import urllib.request
    import json
    url = "https://api.github.com/repos/godotengine/godot/releases/latest"
    with urllib.request.urlopen(url) as response:
        data = json.load(response)
    version = data["tag_name"]
    assets = data["assets"]
    return version, assets

def download_file2(url, dest):
    """Download a file from URL to destination."""
    print(f"Downloading: {url}")
    urllib.request.urlretrieve(url, dest)
    print(f"Saved to {dest}")

def extract_archive(file_path, dest_dir):
    """Extracts .zip or .tar.* archives."""
    if file_path.endswith((".zip", ".tpz")):
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
    elif file_path.endswith((".tar.xz", ".tar.gz")):
        with tarfile.open(file_path, 'r:*') as tar_ref:
            tar_ref.extractall(dest_dir)
    else:
        raise ValueError(f"Unknown archive format: {file_path}")

def find_asset_url(assets, keyword):
    """Find asset URL containing a keyword (like 'linux.x86_64' or 'export_templates')."""
    for a in assets:
        if keyword in a["name"]:
            return a["browser_download_url"]
    return None

# --- Main Logic ---

def ensure_godot_installed():
    """Ensure Godot binary is downloaded."""
    if os.path.exists(GODOT_EXEC):
        print(f"Godot already installed at {GODOT_EXEC}")
        return

    version, assets = get_latest_godot_release()
    system = platform.system().lower()
    arch = platform.machine().lower()

    if system == "linux":
        keyword = "linux.x86_64"
    #elif system == "darwin":
    #    keyword = "macos.universal"
    elif system == "windows":
        keyword = "win64.exe"
    else:
        raise RuntimeError(f"Unsupported OS: {system}")

    url = find_asset_url(assets, keyword)
    if not url:
        raise RuntimeError("Could not find suitable Godot binary to download")

    os.makedirs(GODOT_DIR, exist_ok=True)
    tmp_file = os.path.join(tempfile.gettempdir(), os.path.basename(url))
    download_file2(url, tmp_file)
    extract_archive(tmp_file, GODOT_DIR)
    print(f"Godot installed to {GODOT_DIR}")

def ensure_export_templates():
    """Ensure export templates are downloaded."""
    if os.path.exists(EXPORT_TEMPLATES_DIR) and os.listdir(EXPORT_TEMPLATES_DIR):
        print("Export templates already installed.")
        return

    version, assets = get_latest_godot_release()
    url = find_asset_url(assets, "export_templates.tpz")
    if not url:
        raise RuntimeError("Could not find export templates for the latest release")

    os.makedirs(EXPORT_TEMPLATES_DIR, exist_ok=True)
    tmp_file = os.path.join(tempfile.gettempdir(), os.path.basename(url))
    download_file2(url, tmp_file)
    extract_archive(tmp_file, EXPORT_TEMPLATES_DIR)
    os.makedirs(os.path.join(EXPORT_TEMPLATES_DIR, VERSION_EXPORT_DIR), exist_ok=True)
    for a in os.listdir(os.path.join(EXPORT_TEMPLATES_DIR, "templates")):
        shutil.move(os.path.join(os.path.join(EXPORT_TEMPLATES_DIR, "templates", a)), os.path.join(EXPORT_TEMPLATES_DIR, VERSION_EXPORT_DIR))
    os.rmdir(os.path.join(EXPORT_TEMPLATES_DIR, "templates"))
    #os.rename(os.path.join(EXPORT_TEMPLATES_DIR, "templates"), f"{GODOT_VER}.stable")
    print(os.listdir(EXPORT_TEMPLATES_DIR))
    print("Export templates installed.")

def main():
    if not os.getenv(GODOT_DOWNLOAD_ENV):
        print(f"Environment variable {GODOT_DOWNLOAD_ENV} not set — skipping download.")
        return

    ensure_godot_installed()
    ensure_export_templates()


if __name__ == "__main__":
    # Run locally on port 5000+
    if os.getenv(GODOT_DOWNLOAD_ENV) and platform.system().lower() == "linux":
        GODOT_PATH = GODOT_EXEC
        ensure_godot_installed()
        ensure_export_templates()
    app.run(host="0.0.0.0", port=5025)
