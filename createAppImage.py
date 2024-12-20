from py_modules.input_parameters import InputParameters
from py_modules.appimage_tool import AppImageTool
from py_modules.github_helper import GithubHelper

import os

if __name__ == "__main__":
    github_helper = GithubHelper()
    appimagetool = AppImageTool(github_helper)

    os.chdir(os.getenv("GITHUB_WORKSPACE"))
    try:
        parametros = InputParameters.from_desktop_file()

        github_helper.check_update_required(parametros.version)
        github_helper.set_github_env_variable("APP_VERSION", parametros.version)
        github_helper.set_github_out_variable("version", parametros.version)

        appimagetool.create_resources(parametros.name, parametros.version, parametros.icon, parametros.entrypoint, parametros.desktop)
        appimagetool.create_appimage(parametros.name, parametros.version)
    except Exception as e:
        raise e
    finally:
        appimagetool.cleanup()