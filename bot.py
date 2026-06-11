import os
import sys
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO = "Friczh/Lithium"
WORKFLOW_FILE = "build.yml"
POLL_INTERVAL = 600  # 10 minutes

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()


def get_latest_run():
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/runs"
    r = requests.get(url, headers=HEADERS, params={"per_page": 1})
    r.raise_for_status()
    runs = r.json().get("workflow_runs", [])
    return runs[0] if runs else None


def trigger_workflow():
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    payload = {
        "ref": "main",
        "inputs": {
            "skip_setup": "true",
            "skip_cache": "false",
            "cache_run": "0",
            "skip_caching": "false",
        },
    }
    r = requests.post(url, headers=HEADERS, json=payload)
    return r.status_code == 204


def watcher():
    log("[bot] Watcher started")
    while True:
        try:
            run = get_latest_run()
            if run:
                status = run.get("status")
                conclusion = run.get("conclusion")
                run_id = run.get("id")
                log(f"[bot] Run #{run_id} — status={status} conclusion={conclusion}")

                if status == "completed" and conclusion == "cancelled":
                    log("[bot] Cancelled run detected. Triggering resume...")
                    ok = trigger_workflow()
                    log("[bot] Resume triggered successfully" if ok else "[bot] Failed to trigger resume")
                else:
                    log("[bot] No action needed")
            else:
                log("[bot] No runs found")
        except Exception as e:
            log(f"[bot] Error: {e}")

        time.sleep(POLL_INTERVAL)


# Start watcher thread at module load — works with gunicorn
t = threading.Thread(target=watcher, daemon=True)
t.start()


@app.route("/")
def index():
    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
