from .desktop_parser import DesktopParser

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
    def from_desktop_file():
        desktop_file = InputParameters.find_desktop_file()

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

        desktop_path = os.path.abspath("aux.desktop")
        desktop.data = new_desktop_data
        desktop.persist(desktop_path)

        return InputParameters(name, version, entrypoint, icon, desktop_path)
    
    @staticmethod
    def find_desktop_file():
        current_directory = os.getcwd()
        print(f"Looking for .desktop file in '{current_directory}'")
        for file_name in os.listdir(current_directory):
            if file_name.endswith('.desktop') and file_name != "aux.desktop" and os.path.isfile(file_name):
                print(f"Found '{os.path.join(current_directory, file_name)}'")
                return file_name
        raise FileNotFoundError("Couldn't find .desktop file")