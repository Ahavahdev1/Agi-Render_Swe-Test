import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import subprocess
import time

class GitOpsManager:
    """
    Gerencia o ciclo de entrega contínua (CD) de forma 100% HEADLESS.
    Injeta credenciais via URL para evitar popups de login no Windows/Linux.
    """
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.owner = os.getenv("GITHUB_OWNER")
        self.repo = os.getenv("GITHUB_REPO")
        
    def verificar_credenciais(self) -> bool:
        return bool(self.token and self.owner and self.repo)

    def _executar(self, cmd: list) -> tuple[int, str, str]:
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            process = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="ignore", env=env)
            return process.returncode, process.stdout.strip(), process.stderr.strip()
        except Exception as e:
            return -1, "", str(e)

    def criar_branch_e_push(self, arquivos: list, prompt: str) -> tuple[bool, str, str]:
        if not self.verificar_credenciais():
            return False, "", "Credenciais ausentes no .env"

        branch_name = f"evolucao-{int(time.time())}"
        
        # 1. Preparação Local
        self._executar(["git", "checkout", "-b", branch_name])
        for arq in arquivos:
            if os.path.exists(arq):
                self._executar(["git", "add", arq])

        commit_msg = f"fix(autonomo): {prompt[:50]}"
        ret, out, err = self._executar(["git", "commit", "-m", commit_msg])
        
        if ret != 0 and "nothing to commit" not in out:
            return False, "", f"Erro no commit: {err}"

        # 2. PUSH HEADLESS (A MÁGICA DO NÍVEL 5)
        # Construímos a URL com o token embutido: https://TOKEN@github.com/USER/REPO.git
        authenticated_url = f"https://{self.token}@github.com/{self.owner}/{self.repo}.git"
        
        self.log_evento_interno(f"Iniciando Push Headless para branch {branch_name}...")
        
        # Forçamos o push usando a URL autenticada em vez do nome 'origin'
        ret_p, out_p, err_p = self._executar(["git", "push", authenticated_url, branch_name])

        if ret_p != 0:
            self._executar(["git", "checkout", "main"]) # Volta por segurança
            return False, "", f"Falha no Push Silencioso: {err_p}"

        self._executar(["git", "checkout", "main"])
        return True, branch_name, ""

    def criar_pull_request(self, branch_name: str, prompt: str) -> tuple[bool, str]:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls"
        payload = {
            "title": f"🧬 MEA v4: {prompt[:60]}",
            "body": f"## Evolução Autônoma de Nível 5\n\n**Solicitação:** {prompt}\n\n*Este PR foi validado e enviado sem intervenção humana.*",
            "head": branch_name,
            "base": "main"
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "MEA-Headless-Agent")

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res = json.loads(response.read().decode("utf-8"))
                return True, res.get("html_url")
        except Exception as e:
            return False, str(e)

    def log_evento_interno(self, msg):
        print(f"[MEA GIT] {msg}")