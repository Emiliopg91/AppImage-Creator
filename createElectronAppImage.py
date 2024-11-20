from py_modules.utils.appimage_tool import AppImageTool
from py_modules.utils.desktop_parser import DesktopParser
from py_modules.utils.github_helper import GithubHelper

import os
import shutil

def remove_unneeded_dist_entries():
    print("Removing unneeded entries on dist folder")
    files = os.listdir(".")

    for file in files:
        if not file.endswith(".AppImage"):
            if os.path.isfile(file):
                os.remove(file)
            else:
                shutil.rmtree(file)

def find_appimage():
    print("Looking for AppImage file")
    files = os.listdir(".")

    for file in files:
        if file.endswith(".bk.AppImage"):
            print(f"Restoring AppImage for tests: {file}")
            shutil.move(file, ".".join(file.split(".bk.")))
            break

    files = os.listdir(".")

    for file in files:
        if file.endswith(".AppImage"):
            file = os.path.abspath(file)
            print(f"Found Appimage: {file}")
            return file
        
    return None

def modify_squashfs_root(appimagetool:AppImageTool, appname:str, latest_url:str):
    print("Modifying squashfs-root")
    pwd = os.getcwd()
    os.chdir("squashfs-root")

    os.remove("AppRun")
    os.remove(".DirIcon")
    statics = ["usr", f"{appname.lower()}.png", f"{appname.lower()}.desktop"]
    os.mkdir(appname)

    files = os.listdir(".")
    for file in files:
        if file not in statics and file != appname:
            shutil.move(file, os.path.join(appname, file))

    shutil.copy2(appimagetool.apprun_file, os.path.basename(appimagetool.apprun_file))
    shutil.copy2(appimagetool.autoup_file, os.path.basename(appimagetool.autoup_file))

    shutil.move(appname, os.path.join("usr", "bin", appname))

    print("Modifying desktop file")
    desktop = DesktopParser(f"{appname.lower()}.desktop")
    desktop.data["Desktop Entry"]["Exec"] = f"{appname}/{appname.lower()}"
    desktop.data["Desktop Entry"]["X-GitHub-Api"] = latest_url
    desktop.persist(f"{appname.lower()}.desktop")

    os.chdir(pwd)
    shutil.move("squashfs-root", appname)

if __name__ == "__main__":
    github_helper = GithubHelper()
    appimagetool = AppImageTool(github_helper)
    appimage = None

    os.chdir(os.path.join(os.getenv("GITHUB_WORKSPACE"), "dist"))
    try:
        appimage = find_appimage()
        appname = os.path.basename(appimage).removesuffix(".AppImage")
        if appimage is None:
            raise FileNotFoundError("AppImage file not found")
        
        remove_unneeded_dist_entries()
        appimagetool.extract_appimage(appimage)
        modify_squashfs_root(appimagetool, appname, github_helper.latest_url)

        desktop = DesktopParser(os.path.join(appname, f"{appname.lower()}.desktop"))
        version = desktop.data["Desktop Entry"]["X-AppImage-Version"]

        appimagetool.create_appimage(appname, version, os.path.abspath(appname))
    except Exception as e:
        raise e
    finally:
        appimagetool.cleanup()