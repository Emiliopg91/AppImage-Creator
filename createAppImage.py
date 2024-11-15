import certifi
import json
import os
import re
import ssl
import sys
import tempfile
import urllib.request
import shutil
import subprocess

class InputParameters:
    name: str
    version: str
    description: str
    appdir: str
    entrypoint: str
    icon: str
    desktop: str

    def __init__(self, name, version, entrypoint, icon, description, desktop):
        self.name = name
        self.version = version
        self.entrypoint = os.path.abspath(entrypoint)
        self.icon = os.path.abspath(icon)
        self.description = description
        self.desktop = os.path.abspath(desktop)

def print_help():
    """Imprime el menú de ayuda."""
    print("""
Uso: script.py --name="<nombre>" --description="<descripción>" --appdir=<ruta> --entrypoint=<ruta> --icon=<ruta> --desktop=<ruta>

Parámetros:
    --name           Nombre de la aplicación
    --description    Breve descripción de la aplicación
    --appdir         Nombre de la carpeta
    --entrypoint     Ruta de entrada de la aplicación
    --icon           Ruta al icono de la aplicación
    --version        Número de versión
    --desktop        Ruta al fichero desktop
    """)
    sys.exit(1)

def extract_params():
    """Extrae y valida los parámetros de entrada."""
    pattern = re.compile(r'--(?P<parametro>[-\w]+)=["\']?(?P<valor>[^"\']+)["\']?')
    required_params = {"name", "version", "entrypoint", "icon", "description", "desktop"}
    params = {}

    for arg in sys.argv[1:]:
        match = pattern.match(arg)
        if match:
            parametro = match.group("parametro")
            valor = match.group("valor")
            
            if parametro in required_params:
                params[parametro] = valor                
            else:
                print(f"Parámetro no reconocido: {parametro}")
                print_help()
        else:
            print(f"Formato incorrecto: {arg}")
            print_help()

    # Verificar si faltan parámetros requeridos
    missing_params = required_params - params.keys()
    if missing_params:
        print(f"Faltan los siguientes parámetros: {', '.join(missing_params)}")
        print_help()

    return InputParameters(
        params["name"],
        params["version"], 
        params["entrypoint"], 
        params["icon"], 
        params["description"], 
        params["desktop"]
    )

parametros = extract_params()

home_dir = os.path.expanduser("~")
appimagetool_path = os.path.join(home_dir, "appimagetool")
tmp_path = tempfile.mkdtemp(prefix = "create-appimage-")

on_github = os.getenv("GITHUB_ACTIONS") == "true"
github_repo = f"Emiliopg91/{parametros.name}"
github_env_path = os.getenv("GITHUB_ENV")

if os.getenv("GITHUB_ACTIONS") == "true":
    github_repo = os.getenv("GITHUB_REPOSITORY")
else:
    github_env_path = os.path.join(home_dir, "git.env")
    if(os.path.isfile(github_env_path)):
        os.unlink(github_env_path)
    with open(github_env_path, "w") as archivo:
        pass

def set_github_env_variable(variable_name, value):
    if github_env_path:
        # Escribe la variable de entorno en el archivo $GITHUB_ENV
        with open(github_env_path, "a") as f:
            f.write(f"{variable_name}={value}\n")
    else:
        print("No se pudo encontrar la ruta de $GITHUB_ENV. ¿Estás ejecutando este script dentro de GitHub Actions?")

def check_plugin_latest_version():
    url = f"http://api.github.com/repos/{github_repo}/releases/latest"
    
    update = False
    try:
        response = urllib.request.urlopen(url, context=ssl.create_default_context(cafile=certifi.where()))
        json_data = json.load(response)

        vers = json_data.get("name")
        
        if vers and vers != parametros.version:
            print(f"New available version {vers} -> {parametros.version}")
            update = True
        else:
            print("AppImage is up to date")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"No previous releases found for {github_repo}")
            update = True
        else:
            raise e
        
    set_github_env_variable("IS_UPDATE", f"{update}".lower())
    return update

def download_appimagetool():
    if not os.path.isfile(appimagetool_path):
        url = "https://github.com/AppImage/AppImageKit/releases/latest/download/appimagetool-x86_64.AppImage"
        print("Descargando appimagetool...")
        urllib.request.urlretrieve(url, appimagetool_path)
        os.chmod(appimagetool_path, 0o755)
    else:
        print("appimagetool ya existe")

    return appimagetool_path

def create_resources():
    srcDir = os.path.dirname(parametros.entrypoint)
    usrBin = os.path.abspath(os.path.join(".", "usr", "bin"))
    logoPath = os.path.abspath(os.path.join(".","logo.png"))
    desktop_entry = os.path.join(tmp_path, f"{parametros.name}.desktop")
    
    shutil.copytree(srcDir, usrBin)

    shutil.copy2(parametros.icon, logoPath)

    content = ""
    with open(parametros.desktop, 'r') as file:
        content = file.read()    
    new_content = content.replace("{name}", f"{parametros.name}") \
                     .replace("{version}", f"{parametros.version}") \
                     .replace("{entrypoint}", f"{os.path.basename(parametros.entrypoint)}") \
                     .replace("{icon}", "logo")
    with open(desktop_entry, 'w') as file:
        file.write(new_content)

    apprun_file = os.path.join(tmp_path, "AppRun")
    url = "https://raw.githubusercontent.com/AppImage/AppImageKit/master/resources/AppRun"
    urllib.request.urlretrieve(url, apprun_file)
    os.chmod(apprun_file, 0o777)


def create_appimage():
    print("Generando AppImage...")
    appimage_path = os.path.join(home_dir, f"{parametros.name}-{parametros.version}.AppImage")
    command = f'ARCH=x86_64 {appimagetool_path} --comp gzip {tmp_path} "{appimage_path}" -u "gh-releases-zsync|{github_repo.replace("/", "|")}|latest|{parametros.name}-*.AppImage.zsync"'
    print(f"Ejecutando: {command}")
    
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command finished with exit code {result.returncode}")

    shutil.move(os.path.join(tmp_path, f"{os.path.basename(appimage_path)}.zsync"), f"{appimage_path}.zsync")

    set_github_env_variable("APPIMAGE_PATH", appimage_path)

def clear_workspace():
    shutil.rmtree(tmp_path)
    os.unlink(appimagetool_path)

if __name__ == "__main__":
    check_plugin_latest_version()
    set_github_env_variable("APP_VERSION", parametros.version)
    os.chdir(tmp_path)
    create_resources()
    download_appimagetool()
    create_appimage()
