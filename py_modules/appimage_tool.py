from .github_helper import GithubHelper
from .desktop_parser import DesktopParser
from .msync import MSync
from datetime import datetime

import base64
import hashlib
import math
import os
import re
import shutil
import subprocess
import tempfile
import yaml

class AppImageTool:
    def __init__(self, github_helper: GithubHelper) -> None:
        self.github_helper = github_helper
        self.working_dir = github_helper.action_path
        self.appimagetool_path = os.path.join(self.working_dir, "resources", "appimagetool")
        self.apprun_local_file = os.path.join(self.working_dir, "resources", "AppRun")
        self.autoup_local_file = os.path.join(self.working_dir, "autoupdate.py")
        self.msync_local_file = os.path.join(self.working_dir, "py_modules","msync.py")
        self.tmp_path = tempfile.mkdtemp(prefix = "create-appimage-")
        self.apprun_file = os.path.join(self.tmp_path, "AppRun")
        self.autoup_folder = os.path.join(self.tmp_path, "usr", "bin", "autoupdate")
        self.autoup_file = os.path.join(self.autoup_folder, "autoupdate.py")
        self.pymod_file = os.path.join(self.autoup_folder, "py_modules")
        self.msync_file = os.path.join(self.pymod_file, "msync.py")
        print(f"Using tmp file '{self.tmp_path}'")
        
        shutil.copy2(self.apprun_local_file, self.apprun_file)

        os.makedirs(self.autoup_folder)
        shutil.copy2(self.autoup_local_file, self.autoup_file)
        os.makedirs(self.pymod_file)
        shutil.copy2(self.msync_local_file, self.msync_file)

        os.chmod(self.apprun_file, 0o777)

    def create_resources(self, name, version, icon, entrypoint, desktop):
        prev_cwd=os.getcwd()
        os.chdir(self.tmp_path)
        srcDir = os.path.dirname(entrypoint)
        usrBin = os.path.abspath(os.path.join(".", "usr", "bin", name.replace(" ", "_")))
        logoPath = os.path.abspath(os.path.join(".","logo.png"))
        desktop_entry = os.path.join(self.tmp_path, f"{name}.desktop")
        
        shutil.copytree(srcDir, usrBin)

        shutil.copy2(icon, logoPath)

        content = ""
        with open(desktop, 'r') as file:
            content = file.read()    
        new_content = content.replace("{name}", f"{re.sub(r'-AppImage$', '', name)}") \
                            .replace("{version}", f"{version}") \
                            .replace("{entrypoint}", f"{os.path.basename(entrypoint)}") \
                            .replace("{icon}", "logo") \
                            .replace("{url}", f"https://github.com/{self.github_helper.repo}")
        with open(desktop_entry, 'w') as file:
            file.write(new_content)

        desktop = DesktopParser(desktop_entry)
        desktop.data["Desktop Entry"]["X-GitHub-Api"] = self.github_helper.latest_url
        desktop.persist(desktop_entry)

        os.chdir(prev_cwd)

    def create_appimage(self, name, version, directory = None):
        prev_cwd=os.getcwd()

        directory = self.tmp_path if directory is None else directory
        os.chdir(directory)        

        file_name = re.sub(r"[^a-zA-Z0-9]", "-", name)
        appimage_path = os.path.join(self.working_dir, f"{file_name}.AppImage")
        print(f"Generating AppImage file '{file_name}'")
        command = (
            f'ARCH=x86_64 {self.appimagetool_path} --comp gzip {directory} "{appimage_path}" '
            f'-u "gh-releases-zsync|{self.github_helper.repo.replace("/", "|")}|latest|'
            f'{file_name}.AppImage.zsync"'
        )
        print(f"Running '{command}'")
        
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"Error while running command:\n{result.stderr}")
            raise RuntimeError(f"Command finished with exit code {result.returncode}")

        shutil.move(os.path.join(directory, f"{os.path.basename(appimage_path)}.zsync"), f"{appimage_path}.zsync")

        print(f"Generating MSync file '{appimage_path}.msync'")
        MSync.from_binary(appimage_path).to_file(appimage_path+".msync")
        
        self.github_helper.set_github_env_variable("APPIMAGE_PATH", appimage_path)
        self.github_helper.set_github_env_variable("MSYNC_PATH", appimage_path+".msync")
        
        latest_linux_path = os.path.join(self.working_dir, "latest-linux.yml")
        print("Generating latest-linux.yml")

        sha512 = self.get_sha512(appimage_path)

        data={}
        data["version"] = version
        data["files"] = {}
        data["files"]["url"] = file_name + ".AppImage"
        data["files"]["sha512"] = sha512
        data["files"]["size"] = os.path.getsize(appimage_path)
        data["files"]["blockMapSize"] = math.floor(data["files"]["size"]/1024)
        data["path"] = file_name + ".AppImage"
        data["sha512"] = sha512
        data["releaseDate"] = self.get_release_date(appimage_path)
                
        with open(latest_linux_path, "w") as file:
                yaml.dump(data, file, default_flow_style=False, sort_keys=False)
        self.github_helper.set_github_env_variable("LATEST_LINUX_PATH", latest_linux_path)

        os.chdir(prev_cwd)

    def extract_appimage(self, file):
        command = f"{file} --appimage-extract"
        print(f"Running '{command}'")
        
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"Error while running command:\n{result.stderr}")
            raise RuntimeError(f"Command finished with exit code {result.returncode}")


    def get_release_date(self, path):
        try:
            timestamp = os.stat(path).st_birthtime
        except AttributeError:
            timestamp = os.stat(path).st_mtime

        dt = datetime.utcfromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    def get_sha512(self, path):
        sha512 = hashlib.sha512()

        with open(path, "rb") as archivo:
            for bloque in iter(lambda: archivo.read(8192), b""):
                sha512.update(bloque)
        
        hash_base64 = base64.b64encode(sha512.digest()).decode('utf-8')
        return hash_base64

    def cleanup(self):
        print("Cleaning workspace and temporal files")
        