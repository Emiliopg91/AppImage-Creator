from py_modules.models.input_parameters import InputParameters
from py_modules.utils.appimage_tool import AppImageTool
from py_modules.utils.github_helper import GithubHelper

import os

if __name__ == "__main__":
    github_helper = GithubHelper()
    appimagetool = AppImageTool(github_helper)

    try:
        parametros = InputParameters.from_desktop_file(github_helper.action_path)

        github_helper.check_update_required(parametros.version)
        github_helper.set_github_env_variable("APP_VERSION", parametros.version)
        github_helper.set_github_out_variable("version", parametros.version)

        appimagetool.create_resources(parametros.name, parametros.version, parametros.icon, parametros.entrypoint, parametros.desktop)
        appimagetool.create_appimage(parametros.name, parametros.version)
    except Exception as e:
        raise e
    finally:
        appimagetool.cleanup()