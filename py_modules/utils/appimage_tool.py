from .github_helper import GithubHelper

import os
import re
import shutil
import subprocess
import tempfile
import urllib.request

class AppImageTool:
    def __init__(self, github_helper: GithubHelper) -> None:
        self.github_helper = github_helper
        self.home_dir = os.path.expanduser("~")
        self.appimagetool_path = os.path.join(self.home_dir, "appimagetool")
        self.apprun_local_file = os.path.join(self.home_dir, "AppRun")
        self.tmp_path = tempfile.mkdtemp(prefix = "create-appimage-")
        self.apprun_file = os.path.join(self.tmp_path, "AppRun")

        if not os.path.isfile(self.appimagetool_path):
            url = "https://github.com/AppImage/AppImageKit/releases/latest/download/appimagetool-x86_64.AppImage"
            print("Descargando appimagetool...")
            urllib.request.urlretrieve(url, self.appimagetool_path)
        os.chmod(self.appimagetool_path, 0o755)

        if not os.path.isfile(self.apprun_local_file):
            url = "https://raw.githubusercontent.com/AppImage/AppImageKit/master/resources/AppRun"
            urllib.request.urlretrieve(url, self.apprun_local_file)
        shutil.copy2(self.apprun_local_file, self.apprun_file)
        os.chmod(self.apprun_file, 0o777)

    def create_resources(self, name, version, icon, entrypoint, desktop):
        prev_cwd=os.getcwd()
        os.chdir(self.tmp_path)
        srcDir = os.path.dirname(entrypoint)
        usrBin = os.path.abspath(os.path.join(".", "usr", "bin"))
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
                            .replace("{url}", f"https://github.com/{self.github_helper.github_repo}")
        with open(desktop_entry, 'w') as file:
            file.write(new_content)
        os.chdir(prev_cwd)

    def create_appimage(self, name, version):
        prev_cwd=os.getcwd()
        os.chdir(self.tmp_path)
        print("Generando AppImage...")
        file_name = re.sub(r"[^a-zA-Z0-9]", "-", name)
        appimage_path = os.path.join(self.home_dir, f"{file_name}-{version}.AppImage")
        command = (
            f'ARCH=x86_64 {self.appimagetool_path} --comp gzip {self.tmp_path} "{appimage_path}" '
            f'-u "gh-releases-zsync|{self.github_helper.github_repo.replace("/", "|")}|latest|'
            f'{file_name}-*.AppImage.zsync"'
        )
        print(f"Ejecutando: {command}")
        
        result = subprocess.run(command, shell=True)
        if result.returncode != 0:
            raise RuntimeError(f"Command finished with exit code {result.returncode}")

        shutil.move(os.path.join(self.tmp_path, f"{os.path.basename(appimage_path)}.zsync"), f"{appimage_path}.zsync")

        self.github_helper.set_github_env_variable("APPIMAGE_PATH", appimage_path)

        os.chdir(prev_cwd)


    def clear_workspace(self):
        shutil.rmtree(self.tmp_path)
        os.unlink(self.appimagetool_path)