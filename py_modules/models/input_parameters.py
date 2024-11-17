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

    def __init__(self, name, versioncmd, entrypoint, icon, desktop):
        self.name = name
        self.entrypoint = os.path.abspath(entrypoint)
        self.icon = os.path.abspath(icon)
        self.desktop = os.path.abspath(desktop)
        self.version = None

        print(f"Getting version by running: {versioncmd}")
        result = subprocess.run(versioncmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if(result.returncode != 0):
            print(f"{result.stderr}")
            raise RuntimeError(f"Command finished with exit code {result.returncode}")

        self.version = result.stdout.decode().strip()

    @staticmethod
    def extract_params():
        """Extrae y valida los parámetros de entrada."""
        pattern = re.compile(r'--(?P<parametro>[-\w]+)=["\']?(?P<valor>[^"\']+)["\']?')
        required_params = {"name", "versioncmd", "entrypoint", "icon", "desktop"}
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
                    InputParameters.print_help()
            else:
                print(f"Formato incorrecto: {arg}")
                InputParameters.print_help()

        # Verificar si faltan parámetros requeridos
        missing_params = required_params - params.keys()
        if missing_params:
            print(f"Faltan los siguientes parámetros: {', '.join(missing_params)}")
            InputParameters.print_help()

        return InputParameters(
            params["name"],
            params["versioncmd"], 
            params["entrypoint"], 
            params["icon"],  
            params["desktop"]
        )
    
    @staticmethod
    def print_help():
        """Imprime el menú de ayuda."""
        print("""
    Uso: script.py --name="<nombre>" --appdir=<ruta> --entrypoint=<ruta> --icon=<ruta> --desktop=<ruta>

    Parámetros:
        --name           Nombre de la aplicación
        --appdir         Nombre de la carpeta
        --entrypoint     Ruta de entrada de la aplicación
        --icon           Ruta al icono de la aplicación
        --versioncmd        Número de versión
        --desktop        Ruta al fichero desktop
        """)
        sys.exit(1)

        