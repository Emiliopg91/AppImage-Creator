import certifi
import json
import os
import requests
import ssl
import urllib

GITHUB_API_URL = "https://api.github.com"

TOKEN = os.getenv("GITHUB_TOKEN")  # Debes exportar esta variable de entorno
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

class GithubHelper:
    def __init__(self) -> None:
        self.on_github = os.getenv("GITHUB_ACTIONS") == "true"
        self.github_repo = f"Emiliopg91/AppImage-Creator"
        self.github_env_path = os.getenv("GITHUB_ENV")
        self.github_out_path = os.getenv("GITHUB_OUTPUT")
        self.trigger = os.getenv("github.event_name")

        if os.getenv("GITHUB_ACTIONS") == "true":
            self.github_repo = os.getenv("GITHUB_REPOSITORY")
            print(f"GitHub run triggered by {self.trigger}")
        else:
            print(f"Local run")
            self.github_env_path = os.path.join(os.getcwd(), "git.env")
            if(os.path.isfile(self.github_env_path)):
                os.unlink(self.github_env_path)
            with open(self.github_env_path, "w") as file:
                pass
            self.github_out_path = os.path.join(os.getcwd(), "git.out")
            if(os.path.isfile(self.github_out_path)):
                os.unlink(self.github_out_path)
            with open(self.github_out_path, "w") as file:
                pass

        print(f"Job environment file: {self.github_env_path}")
        print(f"Job output file: {self.github_out_path}")

    
    def set_github_env_variable(self, variable_name, value):
        if self.github_env_path:
            with open(self.github_env_path, "a") as f:
                f.write(f"{variable_name}={value}\n")
        else:
            print("No se pudo encontrar la ruta de $GITHUB_ENV. ¿Estás ejecutando este script dentro de GitHub Actions?")

    
    def set_github_out_variable(self, variable_name, value):
        if self.github_out_path:
            with open(self.github_out_path, "a") as f:
                f.write(f"{variable_name}={value}\n")
        else:
            print("No se pudo encontrar la ruta de $GITHUB_OUT. ¿Estás ejecutando este script dentro de GitHub Actions?")
    
    def get_latest_version(self):
        url = f"{GITHUB_API_URL}/repos/{self.github_repo}/releases/latest"
        response = urllib.request.urlopen(url, context=ssl.create_default_context(cafile=certifi.where()))
        json_data = json.load(response)

        return json_data.get("tag_name")

    def check_update_required(self, newVersion):
        update = False
        try:
            vers = self.get_latest_version()
            
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
            
        self.set_github_env_variable("is_update", f"{update}".lower())
        self.set_github_out_variable("is_update", f"{update}".lower())
        return update
    
    def delete_release(self, tag_name):
        response = requests.get(f"{GITHUB_API_URL}/repos/{self.github_repo}/releases", headers=HEADERS)
        response.raise_for_status()
        releases = response.json()

        for release in releases:
            if release["tag_name"] == tag_name:
                release_id = release["id"]
                delete_url = f"{GITHUB_API_URL}/repos/{self.github_repo}/releases/{release_id}"
                delete_response = requests.delete(delete_url, headers=HEADERS)
                delete_response.raise_for_status()
                print(f"Release '{tag_name}' eliminada.")
                return

    def delete_tag(self, tag_name):
        response = requests.get(f"{GITHUB_API_URL}/repos/{self.github_repo}/git/refs/tags", headers=HEADERS)
        response.raise_for_status()
        tags = response.json()

        for tag in tags:
            if tag["ref"] == f"refs/tags/{tag_name}":
                delete_url = f"{GITHUB_API_URL}/repos/{self.github_repo}/git/refs/tags/{tag_name}"
                delete_response = requests.delete(delete_url, headers=HEADERS)
                delete_response.raise_for_status()
                print(f"Tag '{tag_name}' eliminada.")
                return
            

    def create_tag(self, new_version):
        """Crea una nueva tag."""
        payload = {
            "ref": f"refs/tags/{new_version}",
            "sha": self.get_default_branch_sha()
        }
        response = requests.post(f"{GITHUB_API_URL}/repos/{self.github_repo}/git/refs", headers=HEADERS, json=payload)
        response.raise_for_status()
        print(f"Tag '{new_version}' creada.")

    def get_default_branch_sha(self):
        """Obtiene el SHA de la rama por defecto."""
        response = requests.get(f"{GITHUB_API_URL}/repos/{self.github_repo}", headers=HEADERS)
        response.raise_for_status()
        repo_data = response.json()
        default_branch = repo_data["default_branch"]

        branch_response = requests.get(f"{GITHUB_API_URL}/repos/{self.github_repo}/git/ref/heads/{default_branch}", headers=HEADERS)
        branch_response.raise_for_status()
        branch_data = branch_response.json()
        return branch_data["object"]["sha"]

    def create_release(self, new_version):
        """Crea una nueva release."""
        payload = {
            "tag_name": new_version,
            "name": f"Release {new_version}",
            "body": f"Versión {new_version} generada automáticamente.",
            "draft": False,
            "prerelease": False,
        }
        response = requests.post(f"{GITHUB_API_URL}/repos/{self.github_repo}/releases", headers=HEADERS, json=payload)
        response.raise_for_status()
        print(f"Release '{new_version}' creada.")

    def increment_version(self, version):
        """Incrementa el patch de la versión."""
        major, minor, patch = map(int, version.split("."))
        patch += 1
        return f"{major}.{minor}.{patch}"