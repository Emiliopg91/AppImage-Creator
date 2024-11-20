import certifi
import json
import os
import requests
import ssl
import urllib

GITHUB_API_URL = "https://api.github.com"

TOKEN = os.getenv("GITHUB_TOKEN")  # You need to export this environment variable
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

class GithubHelper:
    def __init__(self) -> None:
        self.on_github = os.getenv("GITHUB_ACTIONS") == "true"
        self.repo = os.getenv("GITHUB_REPOSITORY")
        self.env_path = os.getenv("GITHUB_ENV")
        self.out_path = os.getenv("GITHUB_OUTPUT")
        self.action_path = os.getenv("GITHUB_ACTION_PATH")
        self.trigger = os.getenv("github.event_name")
        self.latest_url = f"{GITHUB_API_URL}/repos/{self.repo}/releases/latest"

        if os.getenv("GITHUB_ACTIONS") == "true":
            print(f"GitHub run triggered by {self.trigger}")
        else:
            print("Local run detected")
            self.env_path = os.path.join(os.getcwd(), "git.env")
            if os.path.isfile(self.env_path):
                os.unlink(self.env_path)

            self.out_path = os.path.join(os.getcwd(), "git.out")
            if os.path.isfile(self.out_path):
                os.unlink(self.out_path)

        print(f"Job environment file: {self.env_path}")
        print(f"Job output file: {self.out_path}")

    def set_github_env_variable(self, variable_name, value):
        if self.env_path:
            with open(self.env_path, "a") as f:
                f.write(f"{variable_name}={value}\n")
        else:
            print("Failed to locate $GITHUB_ENV. Are you running this script inside GitHub Actions?")

    def set_github_out_variable(self, variable_name, value):
        if self.out_path:
            with open(self.out_path, "a") as f:
                f.write(f"{variable_name}={value}\n")
        else:
            print("Failed to locate $GITHUB_OUTPUT. Are you running this script inside GitHub Actions?")

    def get_latest_version(self):
        url = self.latest_url
        response = urllib.request.urlopen(url, context=ssl.create_default_context(cafile=certifi.where()))
        json_data = json.load(response)

        return json_data.get("tag_name")

    def check_update_required(self, new_version):
        update = False
        try:
            vers = self.get_latest_version()

            if vers and vers != new_version:
                print(f"New available version {vers} -> {new_version}")
                update = True
            else:
                print("AppImage is up-to-date")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"No previous releases found for {self.repo}")
                update = True
            else:
                raise e

        self.set_github_env_variable("IS_UPDATE", f"{update}".lower())
        self.set_github_out_variable("is_update", f"{update}".lower())
        return update

    def delete_release(self, tag_name):
        response = requests.get(f"{GITHUB_API_URL}/repos/{self.repo}/releases", headers=HEADERS)
        response.raise_for_status()
        releases = response.json()

        for release in releases:
            if release["tag_name"] == tag_name:
                release_id = release["id"]
                delete_url = f"{GITHUB_API_URL}/repos/{self.repo}/releases/{release_id}"
                delete_response = requests.delete(delete_url, headers=HEADERS)
                delete_response.raise_for_status()
                print(f"Release '{tag_name}' deleted.")
                return

    def delete_tag(self, tag_name):
        response = requests.get(f"{GITHUB_API_URL}/repos/{self.repo}/git/refs/tags", headers=HEADERS)
        response.raise_for_status()
        tags = response.json()

        for tag in tags:
            if tag["ref"] == f"refs/tags/{tag_name}":
                delete_url = f"{GITHUB_API_URL}/repos/{self.repo}/git/refs/tags/{tag_name}"
                delete_response = requests.delete(delete_url, headers=HEADERS)
                delete_response.raise_for_status()
                print(f"Tag '{tag_name}' deleted.")
                return

    def create_tag(self, new_version):
        """Creates a new tag."""
        payload = {
            "ref": f"refs/tags/{new_version}",
            "sha": self.get_default_branch_sha()
        }
        response = requests.post(f"{GITHUB_API_URL}/repos/{self.repo}/git/refs", headers=HEADERS, json=payload)
        response.raise_for_status()
        print(f"Tag '{new_version}' created.")

    def get_default_branch_sha(self):
        """Gets the SHA of the default branch."""
        response = requests.get(f"{GITHUB_API_URL}/repos/{self.repo}", headers=HEADERS)
        response.raise_for_status()
        repo_data = response.json()
        default_branch = repo_data["default_branch"]

        branch_response = requests.get(f"{GITHUB_API_URL}/repos/{self.repo}/git/ref/heads/{default_branch}", headers=HEADERS)
        branch_response.raise_for_status()
        branch_data = branch_response.json()
        return branch_data["object"]["sha"]

    def create_release(self, new_version):
        """Creates a new release."""
        payload = {
            "tag_name": new_version,
            "name": new_version,
            "body": f"Version {new_version} generated automatically.",
            "draft": False,
            "prerelease": False,
        }
        response = requests.post(f"{GITHUB_API_URL}/repos/{self.repo}/releases", headers=HEADERS, json=payload)
        response.raise_for_status()
        print(f"Release '{new_version}' created.")

    def increment_version(self, version):
        """Increments the patch version."""
        major, minor, patch = map(int, version.split("."))
        patch += 1
        return f"{major}.{minor}.{patch}"
