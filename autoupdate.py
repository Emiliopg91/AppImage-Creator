import os
import requests
import shutil
import subprocess
import sys
import tempfile
import traceback

from py_modules.msync import MSync

def get_latest_release(api_url):
    response = requests.get(api_url)
    response.raise_for_status()
    return response.json()
    
def get_latest_msync_url(release):
    for asset in release["assets"]:
        if str(asset["name"]).lower().endswith(".msync"):
            return asset["browser_download_url"]
    raise FileNotFoundError("MSync file not found")

if __name__ == "__main__":
    try:
        version=sys.argv[1]
        github_url = sys.argv[2]
        name = sys.argv[3]
        appimage = sys.argv[4]

        print(f"{name} v.{version}")
        print(f"Checking for updates on {github_url}")
        
        release = get_latest_release(github_url)

        latest_version = release["tag_name"]

        if latest_version!=version:
            print(f"New version {latest_version} available")
            msync_url = get_latest_msync_url(release)
            subprocess.run(["notify-send", "Installing update", "Please wait, App will start automatically", "--icon", os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")])

            print(f"Updating AppImage")

            MSync.from_url(msync_url).patch(appimage)

            print("Launching new instance")
            subprocess.run([appimage])
            sys.exit(1)
        else:
            print("AppImage up to date")
    except Exception:
        print(f"Error on autoupdate:\n{traceback.format_exc()}")
        sys.exit(0)