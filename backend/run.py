import os
from flask import send_from_directory, redirect
from app import create_app, verify_database_connection

env_name = os.getenv("FLASK_ENV", "development")
app = create_app(env_name)

# Root route to serve the frontend single-page application and static pages
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/pages/<path:path>")
def serve_pages(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, "pages"), path)

@app.route("/css/<path:path>")
def serve_css(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), path)

@app.route("/js/<path:path>")
def serve_js(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), path)

@app.route("/assets/<path:path>")
def serve_assets(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, "assets"), path)

@app.route("/favicon.ico")
def serve_favicon():
    return send_from_directory(os.path.join(FRONTEND_DIR, "favicon"), "favicon.ico")

if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))

    is_ok, db_msg = verify_database_connection(app)
    if is_ok:
        print(f"[DATABASE] {db_msg}")
    else:
        print(f"[DATABASE WARNING] {db_msg}")

    print(f"PG Connect Server starting at http://{host}:{port}/")
    app.run(host=host, port=port, debug=True)

