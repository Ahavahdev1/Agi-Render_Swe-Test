# app.py (Código completo do cliente corrigido contra erro 403 e estruturado para o Render)
import os
import sys
import re
import json
import ast
import uuid
import base64
import shutil
import asyncio
import subprocess
import time
from datetime import datetime
from typing import Set

from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from dotenv import load_dotenv
import httpx

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

# >>> COLOQUE A SUA URL REAL DO RENDER AQUI <<<
# Acesse o seu painel do Render, copie a URL do seu serviço "MEA" e cole no lugar desta de baixo:
MEA_BRAIN_URL = "https://mea-gaya.onrender.com" 

app = FastAPI(title="MEA 4.0.0 - Local Client")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-4o-mini"

class LocalRepoMapper:
    """Mapeador AST leve integrado diretamente no cliente para custo zero de tokens."""
    def __init__(self, base_path: str = "."):
        self.base_path = base_path

    def analisar_arquivo_ast(self, file_path: str) -> dict:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                node = ast.parse(f.read(), filename=file_path)
            estrutura = {"classes": [], "funcoes_globais": []}
            for item in node.body:
                if isinstance(item, ast.ClassDef):
                    metodos = []
                    for sub_item in item.body:
                        if isinstance(sub_item, ast.FunctionDef):
                            args = [arg.arg for arg in sub_item.args.args if arg.arg != "self"]
                            metodos.append(f"{sub_item.name}({', '.join(args)})")
                    estrutura["classes"].append({"nome": item.name, "metodos": metodos})
                elif isinstance(item, ast.FunctionDef):
                    args = [arg.arg for arg in item.args.args]
                    estrutura["funcoes_globais"].append(f"{item.name}({', '.join(args)})")
            return estrutura
        except Exception as e:
            return {"erro": str(e)}

    def obter_mapa_repositorio(self) -> dict:
        mapa = {}
        pastas_ignorar = {".git", ".mea", "venv", "__pycache__", "node_modules", "uploads", "frontend", "workspace"}
        for root, dirs, files in os.walk(self.base_path):
            dirs[:] = [d for d in dirs if d not in pastas_ignorar]
            for file in files:
                if file.endswith(".py") and file != "app.py" and file != "benchmark_sre.py":
                    caminho_completo = os.path.join(root, file)
                    caminho_relativo = os.path.relpath(caminho_completo, self.base_path)
                    mapa[caminho_relativo] = self.analisar_arquivo_ast(caminho_completo)
        return mapa

class LocalMEAClient:
    """Gerencia a fila e a execução do Aider local com base no cérebro SaaS do Render."""
    def __init__(self, app_inst: FastAPI):
        self.app = app_inst
        self.active_connections: Set[WebSocket] = set()
        self.system_logs = ["[SISTEMA] Cliente Local MEA 4.0 Online e conectado ao Cérebro no Render."]
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.current_task = "idle"
        self.mapper = LocalRepoMapper(".")
        self.router = APIRouter(prefix="/api", tags=["MEA Local"])
        self._register_routes()
        self.app.include_router(self.router)

        @self.app.on_event("startup")
        async def startup_event():
            asyncio.create_task(self._queue_worker_loop())

    def log_evento(self, mensagem: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_formatado = f"[{timestamp}] -> {mensagem}"
        self.system_logs.append(log_formatado)
        print(f"[CLIENTE LOG] {log_formatado}")
        for ws in list(self.active_connections):
            asyncio.create_task(ws.send_json({"step": "log", "message": mensagem, "timestamp": time.time()}))

    def _gerar_backup_seguranca(self, arquivos: list):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pasta = os.path.join(".mea", "backups", ts)
        os.makedirs(pasta, exist_ok=True)
        for arq in arquivos:
            if os.path.exists(arq):
                dest = os.path.join(pasta, arq)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(arq, dest)
        self.log_evento(f"Backup preventivo criado em: {pasta}")

    async def gerar_voz_base64(self, texto: str) -> str:
        try:
            import edge_tts
            t_limpo = re.sub(r'[*_#`\-]', '', texto)
            comm = edge_tts.Communicate(t_limpo, "pt-BR-FranciscaNeural", rate="+20%")
            audio_bytes = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio": audio_bytes.extend(chunk["data"])
            return base64.b64encode(bytes(audio_bytes)).decode("utf-8")
        except: return ""

    def _register_routes(self):
        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            with open("frontend/index.html", "r", encoding="utf-8") as f: return f.read()

        # WebSocket mapeado diretamente na raiz do app para evitar erros 403 de roteador
        @self.app.websocket("/api/ws/logs")
        async def websocket_endpoint_mea(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.add(websocket)
            try:
                while True: 
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)

        # Rota WebSocket secundária global direta exigida pelo frontend para compatibilidade
        @self.app.websocket("/mea/ws/logs")
        async def websocket_endpoint_mea_global(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.add(websocket)
            try:
                while True: await websocket.receive_text()
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)

        @self.router.get("/status")
        async def status():
            return {
                "status": "online",
                "total_arquivos": len(list(self.mapper.obter_mapa_repositorio().keys())),
                "alma_restaurada": False,
                "queue_pending": self.task_queue.qsize(),
                "current_task": self.current_task
            }

        @self.router.post("/interagir")
        async def interagir(prompt: str = Form(...)):
            prompt_strip = prompt.strip()
            
            # FILTRO SINTÁTICO DE SEGURANÇA
            if prompt_strip.lower().startswith("/evolve"):
                prompt_limpo = re.sub(r"^/evolve\s*", "", prompt_strip, flags=re.IGNORECASE)
                task_id = str(uuid.uuid4())[:8]
                await self.task_queue.put({"prompt": prompt_limpo, "task_id": task_id})
                return {
                    "modo": "EVOLUIR", 
                    "status": "queued", 
                    "task_id": task_id, 
                    "message": "Tarefa de evolução aceita localmente."
                }
            
            # CHAT COMUM: O próprio cliente conversa usando sua chave local para economizar custos do servidor central
            system_prompt = "Você é o MEA 4.0 Client. Dê suporte amigável e técnico de engenharia de software."
            res = await client.chat.completions.create(
                model=model,
                messages=[{"role":"system","content":system_prompt},{"role":"user","content":prompt_strip}]
            )
            texto = res.choices[0].message.content
            return {
                "modo": "CHAT", 
                "status": "chat",
                "resposta": texto, 
                "response": texto,
                "audio_base64": await self.gerar_voz_base64(texto)
            }

    async def _queue_worker_loop(self):
        """Worker local que consulta o cérebro no Render e executa o Aider no computador do usuário."""
        while True:
            task = await self.task_queue.get()
            try:
                prompt = task["prompt"]
                task_id = task.get("task_id", "N/A")
                self.current_task = prompt[:40]
                self.log_evento(f"Iniciando Evolução Local [ID {task_id}]...")

                # 1. Gera o Repo Map da máquina do usuário localmente
                self.log_evento("Compilando mapa de arquivos AST local...")
                mapa_local = self.mapper.obter_mapa_repositorio()

                # 2. Faz a chamada HTTP segura para o Cérebro hospedado no Render enviando a chave local do usuário
                self.log_evento("Consultando cérebro central no Render para obter plano de tarefas...")
                async with httpx.AsyncClient() as http_client:
                    response = await http_client.post(
                        f"{MEA_BRAIN_URL}/api/planejar",
                        data={
                            "prompt": prompt, 
                            "mapa_repositorio": json.dumps(mapa_local),
                            "api_key": os.getenv("OPENAI_API_KEY")  # Envia a chave do usuário de forma segura
                        },
                        timeout=30.0
                    )
                
                if response.status_code != 200:
                    self.log_evento(f"[ERRO] Falha ao obter plano. Código HTTP: {response.status_code}. Detalhes: {response.text}")
                    continue
                
                data_plano = response.json()
                
                # Trata erros estruturais de exceções capturadas no Render
                if data_plano.get("status") == "error":
                    self.log_evento(f"[ERRO DO CÉREBRO] O servidor no Render reportou uma falha: {data_plano.get('message')}")
                    continue
                
                # Trata casos em que a IA classificou o prompt como conversação simples
                if data_plano.get("modo") == "CHAT":
                    self.log_evento("[AVISO SRE] O cérebro central classificou esta tarefa como CHAT (conversação) e não gerou nenhum plano de escrita.")
                    continue
                
                plano = data_plano.get("plano", {})
                plano_tarefas = plano.get("plano_tarefas", [])

                if not plano_tarefas:
                    self.log_evento("[AVISO] Nenhum plano de tarefas foi encontrado no payload de evolução do cérebro central.")
                    continue

                self.log_evento(f"Plano recebido. Total de tarefas: {len(plano_tarefas)}")
                
                # 3. Execução das Tarefas na Máquina Local (A Mão Mecânica)
                for i, tarefa in enumerate(plano_tarefas, 1):
                    t_id = tarefa.get("id")
                    arqs = tarefa.get("arquivos_afetados", [])
                    instrucao_tecnica = tarefa.get("instrucao_tecnica", "")

                    self.log_evento(f"[{i}/{len(plano_tarefas)}] Executando micro-tarefa local: {t_id}")
                    if arqs:
                        self._gerar_backup_seguranca(arqs)
                        
                        cmd = [
                            sys.executable, "-m", "aider", 
                            "--model", model, 
                            "--yes", 
                            "--no-git", 
                            "--no-auto-commits",
                            "--no-analytics",
                            "--no-check-update",
                            "--no-stream",
                            "--edit-format", "diff",
                            "--message", f"AGENTE LOCAL: EXECUTE COM PRECISÃO.\nINSTRUÇÃO: {instrucao_tecnica}"
                        ] + arqs
                        
                        process = await asyncio.create_subprocess_exec(
                            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, stdin=subprocess.DEVNULL
                        )
                        stdout, stderr = await process.communicate()
                        
                        if process.returncode != 0:
                            self.log_evento(f"[AVISO] Falha ao executar tarefa {t_id} na máquina local.")
                        else:
                            self.log_evento(f"Micro-tarefa local {t_id} executada com sucesso.")
                    else:
                        self.log_evento(f"Micro-tarefa {t_id} ignorada por falta de arquivos de destino.")
                
                self.log_evento("Ciclo de Evolução Local concluído com sucesso!")

            except Exception as e:
                self.log_evento(f"[ERRO CRÍTICO] Falha no fluxo do cliente: {e}")
            finally:
                self.current_task = "idle"
                self.task_queue.task_done()

# Inicializa o cliente local injetando as rotas de suporte
client_local_mea = LocalMEAClient(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, access_log=False)