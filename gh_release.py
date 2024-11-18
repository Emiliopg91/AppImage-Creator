from py_modules.utils.github_helper import GithubHelper

import requests
import sys

if __name__ == "__main__":
    try:
        helper = GithubHelper()

        helper.delete_release("latest")
        helper.delete_tag("latest")

        # Obtener la última versión y calcular la nueva
        latest_version = helper.get_latest_version()
        new_version = helper.increment_version(latest_version)

        # Crear nueva tag y release
        helper.create_tag(new_version)
        helper.create_release(new_version)
        helper.create_tag("latest")
        helper.create_release("latest")

    except requests.exceptions.RequestException as e:
        print(f"Error en la API de GitHub: {e}")
        sys.exit(1)
