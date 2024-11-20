from ..utils.desktop_parser import DesktopParser

import os
import re
import subprocess
import sys

class InputParameters:
    name: str
    version: str
    appdir: str
    entrypoint: str
    icon: str
    desktop: str
    
    def __init__(self, name, version, entrypoint, icon, desktop):
        self.name = name
        self.entrypoint = os.path.abspath(entrypoint)
        self.icon = os.path.abspath(icon)
        self.desktop = os.path.abspath(desktop)
        self.version = version
    
    @staticmethod
    def from_desktop_file(base_path:str = None):
        desktop_file = os.path.join(base_path, "app.desktop")
        print("Loading desktop file data")

        desktop = DesktopParser(desktop_file)

        name = desktop.data["Desktop Entry"]["Name"]
        entrypoint = desktop.data["AppImage Creator"]["Entrypoint"]
        icon = desktop.data["AppImage Creator"]["Icon"]
        versioncmd = desktop.data["AppImage Creator"]["Version-Cmd"]
        print(f"Getting version by running: {versioncmd}")
        result = subprocess.run(versioncmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if(result.returncode != 0): 
            print(f"{result.stderr}")
            raise RuntimeError(f"Command finished with exit code {result.returncode}")

        version = result.stdout.decode().strip()

        print("Saving working desktop file")

        new_desktop_data={}
        for section, values in desktop.data.items():
            if section != "AppImage Creator":
                new_desktop_section_data={}
                for key, value in values.items():
                    value = value.replace("{version}", f"{version}") \
                            .replace("{entrypoint}", os.path.join(name.replace(" ","_"), os.path.basename(entrypoint))) \
                            .replace("{icon}", "logo") 
                    new_desktop_section_data[key] = value
                new_desktop_data[section] = new_desktop_section_data            

        desktop_path = os.path.abspath(os.path.join(base_path, "aux.desktop"))
        desktop.data = new_desktop_data
        desktop.persist(desktop_path)

        return InputParameters(name, version, entrypoint, icon, desktop_path)
    