from .github_helper import GithubHelper

import os
import re
import shutil
import subprocess
import tempfile

class AppImageTool:
    def __init__(self, github_helper: GithubHelper) -> None:
        self.github_helper = github_helper
        self.working_dir = github_helper.action_path
        self.appimagetool_path = os.path.join(self.working_dir, "appimagetool")
        self.apprun_local_file = os.path.join(self.working_dir, "AppRun")
        self.tmp_path = tempfile.mkdtemp(prefix = "create-appimage-")
        self.apprun_file = os.path.join(self.tmp_path, "AppRun")
        print(f"Using tmp file '{self.tmp_path}'")
        
        shutil.copy2(self.apprun_local_file, self.apprun_file)
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
        os.chdir(prev_cwd)

    def create_appimage(self, name, version):
        prev_cwd=os.getcwd()
        os.chdir(self.tmp_path)
        file_name = re.sub(r"[^a-zA-Z0-9]", "-", name)
        appimage_path = os.path.join(self.working_dir, f"{file_name}-{version}.AppImage")
        print(f"Generating AppImage file '{file_name}'")
        command = (
            f'ARCH=x86_64 {self.appimagetool_path} --comp gzip {self.tmp_path} "{appimage_path}" '
            f'-u "gh-releases-zsync|{self.github_helper.repo.replace("/", "|")}|latest|'
            f'{file_name}-*.AppImage.zsync"'
        )
        print(f"Running '{command}'")
        
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"Error while running command:\n{result.stderr}")
            raise RuntimeError(f"Command finished with exit code {result.returncode}")

        shutil.move(os.path.join(self.tmp_path, f"{os.path.basename(appimage_path)}.zsync"), f"{appimage_path}.zsync")

        self.github_helper.set_github_env_variable("APPIMAGE_PATH", appimage_path)

        os.chdir(prev_cwd)

    def cleanup(self):
        print("Cleaning workspace and temporal files")
        shutil.rmtree(self.tmp_path)