import os
import requests
import shutil
import subprocess
import sys
import tempfile
import traceback

def get_latest_release(api_url):
    response = requests.get(api_url)
    response.raise_for_status()
    return response.json()
    
def download_latest_appimage(release):
    for asset in release["assets"]:
        if str(asset["name"]).lower().endswith(".appimage"):
            size = asset["size"]
            url = asset["browser_download_url"]
            print(f"Downloading {size} bytes from '{url}'")

            response = requests.get(url, stream=True)
            response.raise_for_status()

            # Crear un archivo temporal
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            with open(temp_file.name, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):  # Descargar en bloques
                    f.write(chunk)

            print(f"File downloaded temporaly to '{temp_file.name}'")
            return temp_file.name

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
            subprocess.run(["notify-send", "Installing update", "Please wait, App will start automatically", "--icon", os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")])
            tmp_file = download_latest_appimage(release)

            permissions = os.stat(appimage).st_mode
            if os.path.isfile(appimage):
                os.unlink(appimage)

            shutil.copy2(tmp_file, appimage)
            os.unlink(tmp_file)
            os.chmod(appimage, permissions)
            print(f"Update AppImage copied to '{appimage}'")
            print("Launching new instance")
            subprocess.run([appimage])
            sys.exit(1)
        else:
            print("AppImage up to date")
    except Exception:
        print(f"Error on autoupdate:\n{traceback.format_exc()}")
        sys.exit(0)