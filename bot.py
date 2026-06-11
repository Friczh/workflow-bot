import os
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


def get_latest_run():
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/runs"
    params = {"per_page": 1}
    r = requests.get(url, headers=HEADERS, params=params)
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
    print("[bot] Watcher started")
    while True:
        try:
            run = get_latest_run()
            if run:
                status = run.get("status")
                conclusion = run.get("conclusion")
                run_id = run.get("id")
                print(f"[bot] Run #{run_id} — status={status} conclusion={conclusion}")

                if status == "completed" and conclusion == "cancelled":
                    print(f"[bot] Cancelled run detected. Triggering resume...")
                    ok = trigger_workflow()
                    if ok:
                        print("[bot] Resume triggered successfully")
                    else:
                        print("[bot] Failed to trigger resume")
                else:
                    print("[bot] No action needed")
            else:
                print("[bot] No runs found")
        except Exception as e:
            print(f"[bot] Error: {e}")

        time.sleep(POLL_INTERVAL)


@app.route("/")
def index():
    return "OK", 200


if __name__ == "__main__":
    t = threading.Thread(target=watcher, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
