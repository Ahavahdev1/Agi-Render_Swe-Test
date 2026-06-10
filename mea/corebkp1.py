import os
import sys
import re
import json
import ast
import base64
import shutil
import uuid
import asyncio
import subprocess
import threading
import time
import logging
import traceback
from datetime import datetime
from typing import Set, Dict, Any, List, Tuple

from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

# Internal Imports
from .state import StateManager
from .agents import MEAAgents

class MEA:
    def __init__(self, app: FastAPI, client: AsyncOpenAI, model: str = "gpt-4o-mini"):
        self.app = app
        self.client = client
        self.model = model
        
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

        self.state = StateManager()
        self.agents = MEAAgents(client=self.client, model=self.model, base_path=".")
        self.soul_file = os.path.join(".mea", "soul_transfer.json")
        self.alma_restaurada_just_now = False
        self.current_task = "idle"
        
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.active_connections: Set[WebSocket] = set()

        if os.path.exists(self.soul_file):
            try:
                with open(self.soul_file, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                if state_data.get("_schema_version") == "4.0.0":
                    self.system_logs = state_data.get("system_logs", [])
                    self.system_logs.append("[SYSTEM] Consciousness successfully rehydrated!")
                    self.alma_restaurada_just_now = True
                os.remove(self.soul_file)
            except: 
                self.system_logs = ["[SYSTEM] Level 5 Reboot."]
        else:
            self.system_logs = ["[SYSTEM] MEA 4.0 Online in Autonomous Stateless Mode."]

        self.app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
        self.router = APIRouter(prefix="/api", tags=["MEA Core"])
        self._register_routes()
        self.app.include_router(self.router)
        
        self._gitops = None

        @self.app.on_event("startup")
        async def startup_event():
            asyncio.create_task(self._queue_worker_loop())

    @property
    def gitops(self):
        if self._gitops is None:
            try:
                from .git import GitOpsManager
                self._gitops = GitOpsManager()
            except ImportError: 
                pass
        return self._gitops

    def log_evento(self, mensagem: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_formatado = f"[{timestamp}] -> {mensagem}"
        self.system_logs.append(log_formatado)
        print(f"[MEA LOG] {log_formatado}")
        for ws in list(self.active_connections):
            asyncio.create_task(ws.send_json({"step": "log", "message": mensagem, "timestamp": time.time()}))

    def _gerar_backup_seguranca(self, arquivos: list) -> str:
        """SRE Backup Guard: Safely saves backup copies flattening absolute paths."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pasta = os.path.join(".mea", "backups", ts)
        os.makedirs(pasta, exist_ok=True)
        for arq in arquivos:
            if os.path.exists(arq):
                nome_seguro = arq.replace(":", "").replace("\\", "_").replace("/", "_")
                dest = os.path.join(pasta, nome_seguro)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(arq, dest)
        return pasta

    def _validar_sintaxe_local(self, arquivos: list) -> tuple[bool, str]:
        for arq in arquivos:
            if arq.endswith(".py") and os.path.exists(arq):
                try:
                    with open(arq, "r", encoding="utf-8") as f: 
                        ast.parse(f.read())
                except Exception as e: 
                    return False, str(e)
        return True, ""

    def _ordenar_tarefas_dag(self, tarefas: list) -> list:
        """SRE Autonomous Parser: Translates any AI-generated JSON format to SRE Pipeline."""
        if not tarefas:
            return []

        normalizadas = []
        for i, t in enumerate(tarefas):
            arqs = t.get("arquivos_afetados") or t.get("files") or t.get("filename") or t.get("output_file") or t.get("target") or []
            if isinstance(arqs, str): arqs = [arqs]
            
            instr = t.get("instrucao_tecnica") or t.get("task") or t.get("action") or t.get("description") or t.get("goal") or "Analyze and improve code"
            
            if "steps" in t and isinstance(t["steps"], list) and len(t["steps"]) > 0:
                step0 = t["steps"][0]
                instr = f"{instr} | Step: " + (step0.get("description") or step0.get("step") or "")

            normalizadas.append({
                "id": str(t.get("id") or i),
                "arquivos_afetados": arqs,
                "instrucao_tecnica": instr,
                "depende_de": t.get("depende_de") or []
            })

        ordenadas, visitados = [], set()
        t_dict = {t["id"]: t for t in normalizadas}

        def visitar(tid):
            tid_str = str(tid)
            if tid_str in visitados: return
            task = t_dict.get(tid_str)
            if not task: return
            for dep in task.get("depende_de", []): 
                visitar(str(dep))
            visitados.add(tid_str)
            ordenadas.append(task)

        for t in normalizadas: 
            visitar(t["id"])
            
        return ordenadas

    def _imprimir_relatorio_sre(self, tempos: dict, custos: dict, paralelo_usado: bool = False):
        swe_bench_time = tempos['ast_map'] + tempos['arquiteto'] + tempos['aider'] + tempos['linter']
        modo_aider = "PARALLEL TURBO" if paralelo_usado else "SEQUENTIAL TURBO"
        
        report = (
            "\n"
            "=================================================================\n"
            "                  MEA SRE TELEMETRY & COST REPORT                \n"
            "=================================================================\n"
            f" ⏱️  AST Mapping (Repo Map)         : {tempos['ast_map']:.3f}s\n"
            f" ⏱️  Planning (Architect DAG)      : {tempos['arquiteto']:.3f}s\n"
            f" ⏱️  Physical Construction (Aider)  : {tempos['aider']:.3f}s ({modo_aider})\n"
            f" ⏱️  Syntax Linting (ast.parse)     : {tempos['linter']:.3f}s\n"
            "-----------------------------------------------------------------\n"
            f" 🚀  SWE-BENCH NET TIME             : {swe_bench_time:.2f}s  <-- [OFFICIAL RECORD]\n"
            "-----------------------------------------------------------------\n"
            f" ⏱️  GitOps Pipeline (API PR)       : {tempos['gitops']:.3f}s\n"
            f" ⏱️  TOTAL TIME (Final Deploy)      : {tempos['total']:.2f}s\n"
            f" 💵  TOTAL REAL API COST            : ${custos['total_usd']:.7f} USD\n"
            "================================================================="
        )
        for linha in report.splitlines(): 
            self.log_evento(linha)

    async def executar_motor_aider_turbo_async(self, t_id: str, arquivos: list, instrucao: str, mapa: dict, root_path: str = ".") -> tuple[bool, str, float]:
        hint = "\n".join([f"Signature {a}: {mapa.get(a, '')}" for a in arquivos])
        
        # SRE Global Guardrails Shield (Strict English & Anti-Hallucination)
        shield = (
            "AIDER AGENT: SURGICAL TURBO FOCUS.\n"
            f"RELEVANT STRUCTURE:\n{hint}\n\n"
            "STRICT SYSTEM DIRECTIVES:\n"
            "1. ONLY alter what is strictly requested. PRESERVE all other code exactly as it is.\n"
            "2. IGNORE all environment/runtime errors regarding '-n' or 'pytest'. They are out of scope.\n"
            "3. NEVER create files named 'mea.py' or 'requirements.txt'. You are a Core Engineer working on the TARGET PROJECT, not MEA.\n"
            "4. All code edits, variables, documentation, comments, and explanations MUST be written strictly in ENGLISH."
        )
        
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["TERM"] = "dumb"

        temp_chat_dir = os.path.join(".mea", "temp")
        os.makedirs(temp_chat_dir, exist_ok=True)
        unique_chat_history = os.path.join(temp_chat_dir, f"chat_history_{t_id}_{uuid.uuid4().hex[:6]}.md")

        work_dir = os.path.abspath(root_path)
        arquivos_relativos = [os.path.relpath(os.path.abspath(a), work_dir) for a in arquivos]

        cmd = [
            sys.executable, "-m", "aider", 
            "--model", self.model, 
            "--yes", 
            "--no-git", 
            "--no-auto-commits",  
            "--edit-format", "whole",
            "--no-auto-lint",
            "--chat-history-file", unique_chat_history,
            "--message", f"{shield}\nACTION: {instrucao}"
        ] + arquivos_relativos
        
        process = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.STDOUT, 
            env=env, 
            stdin=subprocess.DEVNULL,
            cwd=work_dir
        )
        
        stdout_data = []
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            decoded_line = line.decode("utf-8", errors="ignore")
            stdout_data.append(decoded_line)
            
            sys.stdout.write(decoded_line)
            sys.stdout.flush()
            
        await process.wait()
        full_stdout = "".join(stdout_data)

        real_run_cost = 0.0
        try:
            cost_pattern = re.compile(r"Cost:\s+\$([\d.]+)\s+session")
            msg_cost_pattern = re.compile(r"Cost:\s+\$([\d.]+)\s+message")
            
            session_costs = [float(m) for m in cost_pattern.findall(full_stdout)]
            if session_costs:
                real_run_cost = session_costs[-1]
            else:
                msg_costs = [float(m) for m in msg_cost_pattern.findall(full_stdout)]
                real_run_cost = sum(msg_costs) if msg_costs else 0.0
        except Exception as e:
            print(f"[MEA WARNING] Could not parse Aider cost: {e}")

        try:
            if os.path.exists(unique_chat_history):
                os.remove(unique_chat_history)
        except Exception:
            pass

        return process.returncode == 0, full_stdout, real_run_cost

    def _discover_relevant_tests(self, afetados: list, root_path: str) -> list:
        """SRE Heuristic: Identifies relevant test files based on code edits."""
        test_folder = os.path.join(root_path, "tests")
        if not os.path.exists(test_folder):
            return []
        todos_os_testes = []
        for root, _, files in os.walk(test_folder):
            for f in files:
                if f.startswith("test_") and f.endswith(".py"):
                    todos_os_testes.append(os.path.join(root, f))
        relevantes = []
        for arq in afetados:
            nome_base = os.path.basename(arq).replace(".py", "")
            for teste in todos_os_testes:
                if nome_base in teste.lower():
                    relevantes.append(teste)
        return list(set(relevantes)) if relevantes else [test_folder]

    async def _run_tdd_test_cycle(self, afetados: list, root_path: str) -> Tuple[bool, str]:
        """SRE TDD Cycle v5.2: Runs tests and auto-installs missing dependencies."""
        alvos_teste = self._discover_relevant_tests(afetados, root_path)
        if not alvos_teste:
            return True, "No tests found."

        self.log_evento(f"🧪 SRE TDD: Testing {len(alvos_teste)} files...")
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.abspath(root_path)
            
            cmd = [sys.executable, "-m", "pytest", "-p", "no:xdist", "--tb=short", "--maxfail=1"] + alvos_teste
            
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=root_path, env=env
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()

            if process.returncode != 0:
                match = re.search(r"ModuleNotFoundError: No module named '([\w-]+)'", output)
                if not match:
                    match = re.search(r"E\s+ImportError: No module named '([\w-]+)'", output)
                
                if match:
                    missing_lib = match.group(1)
                    if missing_lib == "pytest_mock": 
                        missing_lib = "pytest-mock"
                    
                    if await self._auto_install_dependency(missing_lib):
                        return await self._run_tdd_test_cycle(afetados, root_path)
                
                return False, output[-2000:]
            
            return True, "Tests passed."
        except Exception as e:
            return False, str(e)

    def _register_routes(self):
        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            frontend_path = os.path.join(base_dir, "frontend", "index.html")
            
            if not os.path.exists(frontend_path):
                parent_dir = os.path.dirname(base_dir)
                frontend_path = os.path.join(parent_dir, "frontend", "index.html")
                
            if not os.path.exists(frontend_path):
                return f"<h1>MEA 5.0 Error</h1><p>Frontend not found. Looked in: {frontend_path}</p>"
                
            with open(frontend_path, "r", encoding="utf-8") as f: 
                return f.read()

        @self.router.websocket("/ws/logs")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.add(websocket)
            try:
                while True: 
                    await websocket.receive_text()
            except WebSocketDisconnect: 
                self.active_connections.remove(websocket)

        @self.router.get("/status")
        async def status():
            return {"status": "online", "alma_restaurada": self.alma_restaurada_just_now}

        @self.router.post("/interagir")
        async def interagir(prompt: str = Form(...)):
            p_strip = prompt.strip()
            if p_strip.lower().startswith("/evolve"):
                await self.task_queue.put({"prompt": p_strip[8:], "task_id": str(uuid.uuid4())[:8]})
                return {"modo": "EVOLUIR", "status": "queued"}
            res = await self.client.chat.completions.create(model=self.model, messages=[{"role":"user","content":p_strip}])
            return {"modo": "CHAT", "resposta": res.choices[0].message.content}

    async def _queue_worker_loop(self):
        while True:
            task = await self.task_queue.get()
            tempos = {k: 0.0 for k in ["ast_map", "arquiteto", "aider", "linter", "gitops", "total"]}
            t_global = time.time()
            try:
                prompt = task["prompt"]
                self.log_evento(f"🚀 Global Autonomous Sync Started...")
                
                t_m = time.time()
                contexto = self.agents.repo_mapper.identificar_contexto_universal()
                
                match_path = re.search(r"Project\s*Path:\s*['\"]?([^\s'\"]+)['\"]?", prompt, re.IGNORECASE)
                if match_path:
                    root_real = os.path.abspath(match_path.group(1))
                else:
                    folders = contexto.get("folders_relevantes", [])
                    pasta_projeto = folders[0] if (folders and len(folders) > 0) else ""
                    root_real = os.path.abspath(os.path.join(os.getcwd(), "workspace", pasta_projeto))

                self.log_evento(f"🔍 [SRE DEBUG] Resolved Physical Working Directory: {root_real}")

                self.agents.repo_mapper.base_path = root_real
                mapa = self.agents.repo_mapper.obter_mapa_repositorio()

                self.log_evento(f"🔍 [SRE DEBUG] Total Mapped Files: {len(mapa)}")
                self.log_evento(f"🔍 [SRE DEBUG] Mapped Files: {list(mapa.keys())[:5]} (showing top 5)")

                tempos["ast_map"] = time.time() - t_m
                
                t_a = time.time()
                plano = await self.agents.architect.planejar_mudanca_universal(prompt, mapa, contexto, "")
                
                self.log_evento(f"🔍 [SRE DEBUG] Planner Response: {json.dumps(plano, indent=2)}")
                tempos["arquiteto"] = time.time() - t_a
                
                custo_base_api = ((len(json.dumps(mapa)) + len(prompt))/4 * 0.00000015) + (len(json.dumps(plano))/4 * 0.00000060)
                
                tarefas = self._ordenar_tarefas_dag(plano.get("plano_tarefas", []))
                
                self.log_evento(f"🔍 [SRE DEBUG] Tasks queued for execution after normalization: {tarefas}")
                
                if not tarefas: 
                    tarefas = [{
                        "id": "t1",
                        "arquivos_afetados": plano.get("affected_files") or [],
                        "instrucao_tecnica": plano.get("technical_instruction") or prompt
                    }]

                # --- 🛡️ SHADOWING SHIELD (PREVENÇÃO DE IMPORT CIRCULAR) ---
                STD_LIBS = {"logging", "json", "random", "csv", "sys", "os", "math", "datetime", "re", "config", "utils"}

                arqs_afetados = []
                for t in tarefas: 
                    if t.get("arquivos_afetados"): 
                        corrigidos = []
                        for a in t["arquivos_afetados"]:
                            a_clean = a.replace("workspace/", "").split("/", 1)[-1] if "workspace" in a else a
                            path_final = os.path.abspath(os.path.join(root_real, a_clean))
                            
                            # --- 🛡️ SHADOWING SHIELD (PREVENÇÃO DE IMPORT CIRCULAR) ---
                            base_name = os.path.basename(path_final).replace(".py", "")
                            if base_name in STD_LIBS and os.path.dirname(path_final) == root_real:
                                nome_projeto = os.path.basename(root_real)
                                sub_pkg_path = os.path.join(root_real, nome_projeto)
                                if os.path.exists(sub_pkg_path):
                                    path_final = os.path.join(sub_pkg_path, os.path.basename(path_final))
                                    self.log_evento(f"🛡️ SRE Shield: Redirected '{base_name}.py' inside '{nome_projeto}/'")
                            
                            corrigidos.append(path_final)

                        self._gerar_backup_seguranca(corrigidos)
                        arqs_afetados.extend(corrigidos)
                        t["arquivos_afetados"] = corrigidos 

                # --- ANÁLISE DE CONCORRÊNCIA E PREVENÇÃO DE CONFLITO ---
                t_aider_start = time.time()
                custo_aider_total = 0.0
                
                arquivos_vistos = set()
                sobreposicao = False
                for t in tarefas:
                    for arq in t.get("arquivos_afetados", []):
                        if arq in arquivos_vistos:
                            sobreposicao = True
                            break
                        arquivos_vistos.add(arq)
                    if sobreposicao:
                        break

                permitir_paralelo = os.getenv("ALLOW_PARALLEL_AIDER", "true").lower() == "true"
                paralelo_efetivo = permitir_paralelo and not sobreposicao and len(tarefas) > 1

                if paralelo_efetivo:
                    self.log_evento(f"Executing {len(tarefas)} micro-tasks in PARALLEL...")
                    resultados = await asyncio.gather(*[
                        self.executar_motor_aider_turbo_async(
                            t["id"], t["arquivos_afetados"], t["instrucao_tecnica"], mapa, root_path=root_real
                        ) for t in tarefas if t.get("arquivos_afetados")
                    ])
                    for ok, out, cost in resultados:
                        custo_aider_total += cost
                else:
                    msg_modo = "Executing tasks SEQUENTIALLY"
                    if sobreposicao:
                        msg_modo += " (Conflict prevention: file overlap detected)"
                    else:
                        msg_modo += " (sequential mode active / single task)"
                    self.log_evento(msg_modo)
                    
                    for t in tarefas:
                        if t.get("arquivos_afetados"):
                            ok, out, cost = await self.executar_motor_aider_turbo_async(
                                t["id"], t["arquivos_afetados"], t["instrucao_tecnica"], mapa, root_path=root_real
                            )
                            custo_aider_total += cost

                tempos["aider"] = time.time() - t_aider_start

                max_retries = 3
                test_success = False
                for attempt in range(max_retries):
                    test_success, test_output = await self._run_tdd_test_cycle(list(set(arqs_afetados)), root_real)
                    
                    if test_success:
                        self.log_evento(f"✅ TDD Status: Green! {test_output}")
                        break
                    
                    self.log_evento(f"⚠️ TDD Fail (Attempt {attempt+1}/{max_retries}). Triggering Autonomous Auto-Repair...")
                    
                    # Invoca o planejador cognitivo de reparo passando a lista de arquivos afetados para otimização de tokens
                    self.log_evento("🧠 SRE Planner: Analyzing traceback and repository structure for cross-file repair plan...")
                    reparo_plano = await self.agents.architect.planejar_reparo_universal(
                        test_output, mapa, contexto, list(set(arqs_afetados))
                    )
                    reparo_tarefas = self._ordenar_tarefas_dag(reparo_plano.get("plano_tarefas", []))
                    
                    if reparo_tarefas:
                        self.log_evento(f"🧠 SRE Planner: Generated repair plan with {len(reparo_tarefas)} task(s).")
                        for rt in reparo_tarefas:
                            if rt.get("arquivos_afetados"):
                                # Normaliza caminhos de reparo e realiza backups de segurança dos novos alvos
                                corrigidos_rt = []
                                for a in rt["arquivos_afetados"]:
                                    a_clean = a.replace("workspace/", "").split("/", 1)[-1] if "workspace" in a else a
                                    path_final = os.path.abspath(os.path.join(root_real, a_clean))
                                    corrigidos_rt.append(path_final)
                                    
                                self._gerar_backup_seguranca(corrigidos_rt)
                                rt["arquivos_afetados"] = corrigidos_rt
                                arqs_afetados.extend(corrigidos_rt)
                                
                                # Executa o motor Aider aplicando a correção planejada de forma cirúrgica
                                await self.executar_motor_aider_turbo_async(
                                    f"repair_{attempt}_{rt['id']}", rt["arquivos_afetados"], rt["instrucao_tecnica"], mapa, root_path=root_real
                                )
                    else:
                        # Fallback seguro caso o planejador de IA falhe em gerar um plano estruturado
                        self.log_evento("⚠️ SRE Planner: No plan generated. Falling back to standard single-file repair.")
                        repair_prompt = (
                            f"The project tests FAILED with the following error:\n\n{test_output}\n\n"
                            "Please analyze the traceback, identify the logic error, and apply a surgical fix. "
                            "Do NOT simplify the code. Maintain the original architecture."
                        )
                        await self.executar_motor_aider_turbo_async(
                            f"repair_{attempt}", list(set(arqs_afetados)), repair_prompt, mapa, root_path=root_real
                        )

                t_l = time.time()
                self._validar_sintaxe_local(arqs_afetados)
                tempos["linter"] = time.time() - t_l
                
                # --- [CHAVE DE CONTROLE GITOPS] ---
                t_g = time.time()
                run_gitops = os.getenv("ENABLE_GITOPS", "false").lower() == "true"
                
                if run_gitops and self.gitops and self.gitops.verificar_credenciais():
                    ok, branch, _ = self.gitops.criar_branch_e_push(list(set(arqs_afetados)), prompt)
                    if ok: 
                        self.gitops.criar_pull_request(branch, prompt)
                elif not run_gitops:
                    self.log_evento("SWE-Bench Mode Active: Skipping GitOps Pipeline (Speedrun).")
                    
                tempos["gitops"] = time.time() - t_g
                # ----------------------------------

                tempos["total"] = time.time() - t_global
                
                custos = {"total_usd": custo_base_api + custo_aider_total}
                
                self._imprimir_relatorio_sre(tempos, custos, paralelo_usado=paralelo_efetivo)

                current_mea_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
                
                should_restart = False
                for a in arqs_afetados:
                    if os.path.abspath(a).startswith(current_mea_dir) or "app.py" in a:
                        should_restart = True
                        break

                if should_restart:
                    self.log_evento("🔄 Soul Transfer: Real core modified. Restarting...")
                    with open(self.soul_file, "w", encoding="utf-8") as f: 
                        json.dump({"_schema_version":"4.0.0", "system_logs":self.system_logs}, f)
                    await asyncio.sleep(2)
                    subprocess.Popen([sys.executable, "app.py"])
                    os._exit(0)

            except Exception as e: 
                self.log_evento(f"❌ Critical Error in Pipeline: {e}")
                traceback.print_exc()
            finally: 
                self.task_queue.task_done()