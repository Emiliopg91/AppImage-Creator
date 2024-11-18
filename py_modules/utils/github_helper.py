import certifi
import json
import os
import ssl
import urllib

class GithubHelper:
    def __init__(self) -> None:
        self.on_github = os.getenv("GITHUB_ACTIONS") == "true"
        self.github_repo = f"Emiliopg91/VSCode-AppImage"
        self.github_env_path = os.getenv("GITHUB_ENV")
        self.github_out_path = os.getenv("GITHUB_OUTPUT")
        self.trigger = os.getenv("github.event_name")

        if os.getenv("GITHUB_ACTIONS") == "true":
            self.github_repo = os.getenv("GITHUB_REPOSITORY")
            print(f"GitHub run triggered by {os.getenv("github.event_name")}")
        else:
            print(f"Local run")
            self.github_env_path = os.path.join(os.getcwd(), "git.env")
            if(os.path.isfile(self.github_env_path)):
                os.unlink(self.github_env_path)
            with open(self.github_env_path, "w") as file:
                pass
            self.github_env_path = os.path.join(os.getcwd(), "git.out")
            if(os.path.isfile(self.github_env_path)):
                os.unlink(self.github_env_path)
            with open(self.github_env_path, "w") as file:
                pass

        print(f"Job environment file: {self.github_env_path}")
        print(f"Job output file: {self.github_env_path}")

    
    def set_github_env_variable(self, variable_name, value):
        if self.github_env_path:
            with open(self.github_env_path, "a") as f:
                f.write(f"{variable_name}={value}\n")
        else:
            print("No se pudo encontrar la ruta de $GITHUB_ENV. ¿Estás ejecutando este script dentro de GitHub Actions?")
    

    def check_update_required(self, newVersion):
        url = f"http://api.github.com/repos/{self.github_repo}/releases/latest"
        
        update = False
        try:
            response = urllib.request.urlopen(url, context=ssl.create_default_context(cafile=certifi.where()))
            json_data = json.load(response)

            vers = json_data.get("name")
            
            if vers and vers != newVersion:
                print(f"New available version {vers} -> {newVersion}")
                update = True
            else:
                print("AppImage is up to date")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"No previous releases found for {self.github_repo}")
                update = True
            else:
                raise e
            
        self.set_github_env_variable("IS_UPDATE", f"{update}".lower())
        return update