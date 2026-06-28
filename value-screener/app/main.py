import logging
import socket
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template

from app.config import DATA_FILE
from app.config_hk import HK_DATA_FILE
from app.scheduler import start_scheduler, stop_scheduler
from app.storage import (
    get_hk_screen_data,
    get_screen_data,
    is_refreshing,
    refresh_hk_screen,
    refresh_screen,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 5000
FALLBACK_PORT = 5001


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/hk")
    def hk_index():
        return render_template("hk.html")

    @app.route("/api/data")
    def api_data():
        return jsonify(get_screen_data())

    @app.route("/api/status")
    def api_status():
        data = get_screen_data()
        return jsonify({
            "refreshing": is_refreshing(),
            "last_updated": data.get("meta", {}).get("last_updated"),
            "next_refresh": data.get("meta", {}).get("next_refresh"),
            "counts": data.get("counts", {}),
        })

    @app.route("/api/refresh", methods=["POST"])
    def api_refresh():
        if is_refreshing():
            return jsonify({"status": "already_running"}), 409

        def _run():
            try:
                refresh_screen(force=True)
            except Exception:
                logging.exception("Manual refresh failed")

        threading.Thread(target=_run, daemon=True).start()
        return jsonify({"status": "started"})

    @app.route("/api/hk/data")
    def api_hk_data():
        return jsonify(get_hk_screen_data())

    @app.route("/api/hk/status")
    def api_hk_status():
        data = get_hk_screen_data()
        return jsonify({
            "refreshing": is_refreshing("hk"),
            "last_updated": data.get("meta", {}).get("last_updated"),
            "next_refresh": data.get("meta", {}).get("next_refresh"),
            "counts": data.get("counts", {}),
        })

    @app.route("/api/hk/refresh", methods=["POST"])
    def api_hk_refresh():
        if is_refreshing("hk"):
            return jsonify({"status": "already_running"}), 409

        def _run():
            try:
                refresh_hk_screen(force=True)
            except Exception:
                logging.exception("HK manual refresh failed")

        threading.Thread(target=_run, daemon=True).start()
        return jsonify({"status": "started"})

    with app.app_context():
        start_scheduler()

    return app


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _pick_port() -> int:
    if _port_free(DEFAULT_PORT):
        return DEFAULT_PORT
    if _port_free(FALLBACK_PORT):
        logging.warning("Port %s is busy — using %s instead", DEFAULT_PORT, FALLBACK_PORT)
        return FALLBACK_PORT
    raise SystemExit(
        f"ERROR: Ports {DEFAULT_PORT} and {FALLBACK_PORT} are both in use.\n"
        "Close other Python windows or run:\n"
        "  Stop-Process -Name python -Force\n"
        "Then try again."
    )


def _open_browser_later(url: str) -> None:
    def _open():
        webbrowser.open(url)

    threading.Timer(1.5, _open).start()


def _ensure_data() -> None:
    if not DATA_FILE.exists():
        print("  No US data — seeding from cache...")
        try:
            import seed_data
            seed_data.main()
            print("  US data seeded.")
        except Exception:
            print("  WARNING: Run: python seed_data.py")
            logging.exception("US seed failed")
    if not HK_DATA_FILE.exists():
        print("  No HK data — run: python seed_hk_data.py (or open /hk to auto-fetch)")


def main(open_browser: bool = True):
    _ensure_data()
    port = _pick_port()
    url = f"http://127.0.0.1:{port}"

    print()
    print("=" * 50)
    print("  Value Screener is starting (US + Hong Kong)")
    print("=" * 50)
    print(f"  US page:  {url}/")
    print(f"  HK page:  {url}/hk")
    print("  Keep this window open while using the site.")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 50)
    print()

    if open_browser:
        _open_browser_later(url)

    app = create_app()
    try:
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
    finally:
        stop_scheduler()


if __name__ == "__main__":
    main()