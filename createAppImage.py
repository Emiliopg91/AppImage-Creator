import json
import os
import re
import ssl
import sys
import tempfile
import urllib.request
import shutil
import subprocess


home_dir = os.path.expanduser("~")
appimagetool_path = os.path.join(home_dir, "appimagetool")
tmp_path = tempfile.mkdtemp(prefix = "create-appimage-")

on_github = os.getenv("GITHUB_ACTIONS") == "true"
github_repo = "Emiliopg91/AllyDeckyCompanion"
github_env_path = os.getenv("GITHUB_ENV")

if os.getenv("GITHUB_ACTIONS") == "true":
    github_repo = os.getenv("GITHUB_REPOSITORY")
else:
    github_env_path = os.path.join(home_dir, "git.env")
    if(os.path.isfile(github_env_path)):
        os.unlink(github_env_path)
    with open(github_env_path, "w") as archivo:
        pass

class InputParameters:
    name: str
    version: str
    description: str
    appdir: str
    entrypoint: str
    icon: str
    type: str
    categories: str
    desktop_params: dict  # Nuevo atributo para parámetros adicionales

    def __init__(self, name, version, entrypoint, icon, description, type="Application", categories="", desktop_params=None):
        if desktop_params is None:
            desktop_params = {}
        self.name = name
        self.version = version
        self.entrypoint = os.path.abspath(entrypoint)
        self.icon = os.path.abspath(icon)
        self.description = description
        self.type = type
        self.categories = categories
        self.desktop_params = desktop_params  # Almacena los parámetros adicionales

def set_github_env_variable(variable_name, value):
    if github_env_path:
        # Escribe la variable de entorno en el archivo $GITHUB_ENV
        with open(github_env_path, "a") as f:
            f.write(f"{variable_name}={value}\n")
    else:
        print("No se pudo encontrar la ruta de $GITHUB_ENV. ¿Estás ejecutando este script dentro de GitHub Actions?")

def check_plugin_latest_version(parametros:InputParameters):
    url = f"http://api.github.com/repos/{github_repo}/releases/latest"
    response = urllib.request.urlopen(url, context=ssl.SSLContext())
    json_data = json.load(response)

    vers = json_data.get("name")

    update = False
    if vers and vers != parametros.version:
        print(f"New available version {vers} -> {parametros.version}")
        update = True
    else:
        print("AppImage is up to date")

    set_github_env_variable("IS_UPDATE", update)
    return update


def print_help():
    """Imprime el menú de ayuda."""
    print("""
Uso: script.py --name="<nombre>" --description="<descripción>" --appdir=<ruta> --entrypoint=<ruta> --icon=<ruta> [--type="<tipo>"] [--categories="<categorías>"]

Parámetros:
    --name           Nombre de la aplicación
    --description    Breve descripción de la aplicación
    --appdir         Nombre de la carpeta
    --entrypoint     Ruta de entrada de la aplicación
    --icon           Ruta al icono de la aplicación
    --version        Número de versión
    --type           Tipo de la aplicación (por defecto: 'Application')
    --categories     Categorías de la aplicación (por defecto: '')
    --desktop-*      Cualquier parámetro adicional que empiece con 'desktop-' se almacenará en el diccionario de configuración.
    """)
    sys.exit(1)

def extract_params():
    """Extrae y valida los parámetros de entrada."""
    pattern = re.compile(r'--(?P<parametro>[-\w]+)=["\']?(?P<valor>[^"\']+)["\']?')
    required_params = {"name", "version", "entrypoint", "icon", "description"}
    params = {}
    desktop_params = {}

    for arg in sys.argv[1:]:
        match = pattern.match(arg)
        if match:
            parametro = match.group("parametro")
            valor = match.group("valor")
            
            if parametro.startswith("desktop-"):
                # Si el parámetro empieza con 'desktop-', se guarda en 'desktop_params'
                desktop_key = parametro[len("desktop-"):]  # Eliminar el prefijo 'desktop-'
                desktop_params[desktop_key] = valor
            elif parametro in required_params:
                params[parametro] = valor
            elif parametro == "type":
                params["type"] = valor
            elif parametro == "categories":
                params["categories"] = valor
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

    # Crear y devolver una instancia de InputParameters
    return InputParameters(
        name=params["name"],
        version=params["version"],
        entrypoint=params["entrypoint"],
        icon=params["icon"],
        description=params["description"],
        type=params.get("type", "Application"),
        categories=params.get("categories", "Utility"),
        desktop_params=desktop_params  # Pasar los parámetros 'desktop-' al diccionario
    )

def download_appimagetool():
    if not os.path.isfile(appimagetool_path):
        url = "https://github.com/AppImage/AppImageKit/releases/latest/download/appimagetool-x86_64.AppImage"
        print("Descargando appimagetool...")
        urllib.request.urlretrieve(url, appimagetool_path)
        os.chmod(appimagetool_path, 0o755)
    else:
        print("appimagetool ya existe")

    return appimagetool_path

def create_resources(parametros: InputParameters):
    srcDir = os.path.dirname(parametros.entrypoint)
    usrBin = os.path.abspath(os.path.join(".", "usr", "bin"))
    logoPath = os.path.abspath(os.path.join(".","logo.png"))
    
    shutil.copytree(srcDir, usrBin)

    shutil.copy2(parametros.icon, logoPath)

    desktop_entry = os.path.join(tmp_path, f"{parametros.name}.desktop")
    with open(desktop_entry, "w") as f:
        f.write(f"""
[Desktop Entry]
Name={parametros.name}
X-AppImage-Version={parametros.version}
Comment={parametros.description}
Exec={os.path.basename(parametros.entrypoint)}
Icon=logo
Type={parametros.type}
Categories={parametros.categories};
""")

        for key, value in parametros.desktop_params.items():
            f.write(f"\n{key}={value}")

    apprun_file = os.path.join(tmp_path, "AppRun")
    url = "https://raw.githubusercontent.com/AppImage/AppImageKit/master/resources/AppRun"
    urllib.request.urlretrieve(url, apprun_file)
    os.chmod(apprun_file, 0o777)


def create_appimage(parametros: InputParameters):
    print("Generando AppImage...")
    command = f'ARCH=x86_64 {appimagetool_path} {tmp_path} {home_dir}/{parametros.name}-{parametros.version}.AppImage -u "gh-releases-zsync|{github_repo.replace("/","|")}|latest|{parametros.name}-*.AppImage.zsync"'
    print(f"Ejecutando: {command}")
    
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout.decode()

def clear_workspace():
    shutil.rmtree(tmp_path)
    os.unlink(appimagetool_path)

if __name__ == "__main__":
    parametros = extract_params()
    print(f"GitHub Action? {on_github}")
    check_plugin_latest_version(parametros)
    print(f"Working directory: {tmp_path}")
    os.chdir(tmp_path)
    create_resources(parametros)
    download_appimagetool()
    create_appimage(parametros)
    clear_workspace()
