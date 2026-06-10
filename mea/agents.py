import os
import json
import ast
import urllib.request
import urllib.parse
from openai import AsyncOpenAI  # Importa o cliente assíncrono oficial

class RepoMapGenerator:
    """Gera um mapa estrutural do repositório usando o analisador AST nativo do Python."""
    def __init__(self, base_path: str):
        self.base_path = base_path

    def identificar_contexto_universal(self) -> dict:
        """Detecta a tecnologia dominante e a raiz real de qualquer repositório no mundo."""
        assinaturas = {
            "Python": ["pyproject.toml", "requirements.txt", "setup.py", "manage.py"],
            "NodeJS": ["package.json", "tsconfig.json"],
            "Go": ["go.mod"],
            "Rust": ["Cargo.toml"]
        }
        contexto = {"tech": "Unknown", "root": ".", "folders_relevantes": []}
        
        for root, dirs, files in os.walk(self.base_path):
            for tech, anchors in assinaturas.items():
                if any(a in files for a in anchors):
                    contexto["tech"] = tech
                    contexto["root"] = os.path.relpath(root, self.base_path)
                    break
            if contexto["tech"] != "Unknown":
                break

        # Identifica pastas de interesse
        workspace_path = os.path.join(self.base_path, "workspace")
        if os.path.exists(workspace_path):
            for d in os.listdir(workspace_path):
                if os.path.isdir(os.path.join(workspace_path, d)) and d not in [".git", "__pycache__"]:
                    contexto["folders_relevantes"].append(d)
        
        return contexto


    def analisar_arquivo_ast(self, file_path: str) -> dict:
        """Extrai classes, métodos e funções globais com suas assinaturas."""
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
                    estrutura["classes"].append({
                        "nome": item.name,
                        "metodos": metodos
                    })
                elif isinstance(item, ast.FunctionDef):
                    args = [arg.arg for arg in item.args.args]
                    estrutura["funcoes_globais"].append(f"{item.name}({', '.join(args)})")
            
            return estrutura
        except Exception as e:
            return {"erro": f"Falha ao processar AST: {str(e)}"}

    def obter_mapa_repositorio(self) -> dict:
        mapa = {}
        pastas_ignorar = {".git", ".mea", "venv", "__pycache__", "node_modules", "uploads", "frontend", "dist", "build"}
        
        for root, dirs, files in os.walk(self.base_path):
            dirs[:] = [d for d in dirs if d not in pastas_ignorar]
            
            for file in files:
                if file.endswith((".py", ".js", ".ts")):
                    caminho_completo = os.path.join(root, file)
                    caminho_relativo = os.path.relpath(caminho_completo, self.base_path)
                    mapa[caminho_relativo] = self.analisar_arquivo_ast(caminho_completo)
        return mapa

class ClassificadorIA:
    """Especialista em Triagem Cognitiva de Velocidade com blindagem contra falsos positivos."""
    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model

    async def classificar(self, prompt: str) -> str:
        system_instruction = (
            "You are the MEA 5.0 High-Speed Input Classifier.\n"
            "Your sole task is to triage the user message into one of three processing categories:\n\n"
            "1. 'CHAT': Simple conversation, greetings, general theoretical doubts, "
            "OR conceptual questions about your capabilities (e.g., 'what can you do?', 'how do you work?', "
            "'can you self-code?', 'show me your code'). \n"
            "**CRITICAL RULE:** If the user is only ASKING if you are capable of doing something, without a direct order for change, you MUST classify it as CHAT.\n\n"
            "2. 'MEMORIA': Specific questions about the past or historical lessons learned recorded in your memory.\n\n"
            "3. 'EVOLUIR': Only when there is an EXPLICIT COMMAND, DIRECT INSTRUCTION, or a clear ORDER to "
            "modify, create, delete, or refactor the physical source code (e.g., 'create file X', 'refactor state.py', 'add a log', 'fix bug Y').\n\n"
            "Respond strictly with only one of the three words: 'CHAT', 'MEMORIA', or 'EVOLUIR'."
        )
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=5
        )
        resultado = response.choices[0].message.content.strip().upper()
        return resultado if resultado in ["CHAT", "MEMORIA", "EVOLUIR"] else "CHAT"

class ArchitectAgent:
    """O Cérebro do MEA 5.0: Planejamento baseado em Primeiros Princípios de Engenharia."""
    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model

    async def planejar_mudanca_universal(self, prompt: str, mapa: dict, contexto: dict, memoria: str) -> dict:
        ancoras = [f for f in mapa.keys() if any(x in f.lower() for x in ["registry", "factory", "config", "const", "models", "enum", "main", "server", "auth"])]

        is_security = any(x in prompt.lower() for x in ["audit", "security", "vulnerability", "exploit", "poc", "scan", "red team"])
        is_translation = any(x in prompt.lower() for x in ["translation", "translate", "english", "portuguese", "refactor to english"])

        if is_translation:
            system_instruction = (
                "You are the MEA 5.0 Translation Expert. Your mission is to refactor code from Portuguese to English.\n\n"
                "1. **Full Localization:** Rename all functions, variables, and comments to professional English.\n"
                "2. **Logic Preservation:** Do NOT change the code logic. Only change the names and strings.\n"
                "3. **Consistency:** Ensure internal imports match the new English names.\n"
                "Output MUST be a JSON with 'plano_tarefas'."
            )
        elif is_security:
            system_instruction = (
                "You are the MEA 5.0 'Red Team' Security Architect. Your mission is to find critical vulnerabilities for Bug Bounties.\n\n"
                "STRICT INVESTIGATION PROTOCOLS:\n"
                "1. **Active Hunter Mode:** You MUST order a 'Deep Analysis' of high-risk files. Never return empty tasks.\n"
                "2. **Mandatory Deliverable:** Include a task to create a physical file named 'AUDIT_REPORT.md' or 'poc_exploit.py' so Aider can write findings.\n"
                f"3. **Context Awareness:** Tech: {contexto.get('tech', 'Python')}. Root: '{contexto.get('root', '.')}'.\n"
                "4. **Vulnerability Focus:** Specifically search for RCE, Insecure Deserialization, and SSRF.\n\n"
                "Output MUST be a structured JSON object with 'plano_tarefas'."
            )
        else:
            system_instruction = (
                "You are the MEA 5.0 'Elite SRE' Architect. You are a Senior Software Engineer with 20+ years of experience.\n\n"
                "MANDATORY CONSTITUTION (THE LAWS OF MEA):\n"
                "1. **PRESERVATION OVER REPLACEMENT:** NEVER delete or overwrite existing robust production logic with simple implementations. You are an EXTENDER, not a REWRITER.\n"
                "2. **SHADOWING PROTECTION:** NEVER create files with names that conflict with Python Standard Libraries (e.g., logging.py, json.py, random.py). If you need a logging module, name it 'custom_logging.py'.\n"
                "3. **CONTRACT COMPLIANCE:** Implement ALL required abstract methods when inheriting. Never leave 'pass' or placeholders.\n"
                "4. **CONTEXTUAL INTEGRITY:** Mirror the existing coding style and architecture exactly. Do not introduce foreign patterns.\n"
                "5. **SELF-CORRECTION:** If a test fails, perform a 'Root Cause Analysis' and provide a surgical fix.\n"
                f"6. **WORKSPACE AWARENESS:** The project root is '{contexto.get('root', '.')}'. All file paths must be precisely relative to this root.\n"
                "7. **CLI PARAMETER SYNCHRONIZATION:** When adding or modifying configuration options, you MUST ensure that all parameter signatures, argument options, default values, and decorators are perfectly synchronized across CLI files, configurations, and main entrypoints (e.g., matching config.py defaults and parameter types exactly with run() function signatures in main.py).\n"
                "8. **MEA SANITIZATION:** NEVER create helper files or configuration structures named 'mea.py' or 'requirements.txt' inside the target project workspace. You are working solely on the target codebase.\n"
                "9. **ENGLISH EXCLUSIVITY:** All generated task descriptions, instructions, variable names, functions, code additions, documentation, and comments MUST be written strictly in professional, clean, and idiomatic ENGLISH.\n"
                "10. **STRICT PRESERVATION OF ALL OTHER ARGUMENTS:** When modifying a function signature or parameter list, you MUST preserve all pre-existing parameters, default values, and decorators. NEVER omit, truncate, or summarize parameters with placeholders like '...' or etc. You must write out the complete parameter definitions in full.\n\n"
                "JSON FORMAT RULES:\n"
                "- Return a FLAT list in 'plano_tarefas'. No nested 'steps'.\n"
                "- Each task MUST contain: 'id', 'arquivos_afetados' (list of paths), 'instrucao_tecnica' (detailed steps), and 'depende_de' (list of IDs).\n"
                "- Use the detected root root: '{contexto.get('root', '.')}' for all paths.\n"
                "- Required keys: 'id', 'arquivos_afetados', 'instrucao_tecnica', 'depende_de'.\n"
            )

        user_content = (
            f"REPO_MAP (Signatures):\n{json.dumps(mapa, indent=2)}\n\n"
            f"CRITICAL_ANCHORS: {ancoras}\n\n"
            f"MEMORY: {memoria}\n\n"
            f"USER_REQUEST: {prompt}"
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ],
            temperature=0.1
        )

        try:
            plano = json.loads(response.choices[0].message.content)
            
            # --- TRAVA DE SEGURANÇA CONTRA PLANOS VAZIOS ---
            if not plano.get("plano_tarefas") or len(plano["plano_tarefas"]) == 0:
                folders = contexto.get("folders_relevantes", [])
                pasta_projeto = folders[0] if (folders and len(folders) > 0) else "projeto"
                nome_relatorio = "AUDIT_REPORT.md" if is_security else "DEVELOPMENT_PLAN.md"
                
                plano["plano_tarefas"] = [{
                    "id": "forced_task_01",
                    "arquivos_afetados": [f"workspace/{pasta_projeto}/{nome_relatorio}"],
                    "instrucao_tecnica": f"Review {pasta_projeto} layout and document current architectural assumptions.",
                    "depende_de": []
                }]
            return plano
        except Exception:
            folders = contexto.get("folders_relevantes", [])
            pasta_projeto = folders[0] if (folders and len(folders) > 0) else "projeto"
            return {
                "complexidade": "BAIXA",
                "plano_tarefas": [{
                    "id": "fallback_task",
                    "arquivos_afetados": [f"workspace/{pasta_projeto}/FALLBACK.md"],
                    "instrucao_tecnica": f"Execute/Analyze: {prompt}",
                    "depende_de": []
                }]
            }

    async def planejar_reparo_universal(self, error_traceback: str, mapa: dict, contexto: dict, affected_files: list) -> dict:
        """SRE Autonomous Repair Planner: Analisa falhas de testes e correlaciona arquivos economizando tokens."""
        import re
        
        # 1. Compressão de Traceback (Mantém apenas frames locais e mensagens de erro cruciais)
        tb_lines = []
        local_files_mentioned = set()
        
        for line in error_traceback.splitlines():
            if ".py" in line:
                match = re.search(r'File "([^"]+)"', line)
                if match:
                    f_path = match.group(1)
                    if "site-packages" not in f_path and "Lib" not in f_path and "lib" not in f_path:
                        base_name = os.path.basename(f_path)
                        local_files_mentioned.add(base_name)
                        tb_lines.append(line)
                else:
                    tb_lines.append(line)
            elif any(err in line for err in ["AssertionError", "Error", "Exception", "Differing", "Omitting", "Left contains"]):
                tb_lines.append(line)
            elif line.strip().startswith(("+", "-")):
                tb_lines.append(line)

        compressed_tb = "\n".join(tb_lines[:30])  # Limita a 30 linhas relevantes de erro

        # 2. Filtro do Mapa AST (Envia apenas assinaturas dos arquivos envolvidos)
        filtered_map = {}
        for caminho, assinatura in mapa.items():
            base_name = os.path.basename(caminho)
            is_affected = any(os.path.basename(af) == base_name for af in affected_files)
            is_mentioned = any(base_name == local_f for local_f in local_files_mentioned)
            
            if is_affected or is_mentioned:
                filtered_map[caminho] = assinatura

        system_instruction = (
            "You are the MEA 5.0 Elite SRE Repair Planner.\n"
            "An automated test has FAILED. Your job is to analyze the compressed traceback and the relevant repository signatures to determine which files need to be modified or synchronized to fix the issue.\n\n"
            "STRICT PROTOCOL:\n"
            "1. Analyze the failure and identify where function, class, or parameter discrepancies exist.\n"
            "2. Generate a plan of tasks to fix the discrepancy. You must include any files in the workspace that are involved or need to be synchronized.\n"
            "3. Output a JSON object with 'plano_tarefas'.\n\n"
            "JSON FORMAT RULES:\n"
            "- Return a FLAT list in 'plano_tarefas'. No nested 'steps'.\n"
            "- Each task MUST contain: 'id', 'arquivos_afetados' (list of paths to modify), 'instrucao_tecnica' (detailed steps), and 'depende_de' (list of IDs).\n"
            "All instructions must be written in professional ENGLISH."
        )
        
        user_content = (
            f"COMPRESSED_TRACEBACK:\n{compressed_tb}\n\n"
            f"RELEVANT_REPO_SIGNATURES:\n{json.dumps(filtered_map, indent=2)}\n\n"
            f"CONTEXT:\n{json.dumps(contexto, indent=2)}"
        )
        
        response = await self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ],
            temperature=0.1
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {"plano_tarefas": []}

class SREAuditorAgent:
    """SRE Auditor Agent: Especializado em detectar alucinações, falhas de testes e garantir conformidade de contratos."""
    def __init__(self, client: AsyncOpenAI, model: str):
        self.client = client
        self.model = model

    async def audit_execution(self, prompt: str, modified_files: list, test_output: str, repo_map: dict) -> dict:
        system_instruction = (
            "You are the MEA 5.0 SRE Auditor and Quality Assurance Lead.\n"
            "An evolutionary change has been applied to the repository. Your task is to audit the current state, detect if there are any hallucinations, and verify the test traceback.\n\n"
            "CRITICAL CHECKLIST:\n"
            "1. **Hallucination Detection:** Check if any files have been created that were not requested or do not belong to the project (e.g., creating custom '__main__.py', 'mea.py', or 'requirements.txt' inside the codebase is a HALLUCINATION and must be REJECTED).\n"
            "2. **CLI & Parameter Synchronization:** If a configuration option was changed (like 'access_log_format'), verify if the parameters across 'config.py' and 'main.py' match. If they don't, this is a synchronization failure and must be REJECTED.\n"
            "3. **Traceback Analysis:** Inspect the test suite traceback. Pinpoint exactly why any assertions failed and identify the root cause.\n"
            "4. **Logging & Syntax Formatting Verification:** Inspect tracebacks for log formatting errors. "
            "If you see 'ValueError: unsupported format character' or similar, it means a percentage-style '%' format string contains curly braces '{}' (e.g., '%{request_line}s') instead of parenthesized keys (e.g., '%(request_line)s'). "
            "Using curly braces in percentage-style formatting is syntactically invalid in Python and will break at runtime. "
            "If you detect this, REJECT the execution and explicitly instruct the coder to replace the curly braces '{}' with parentheses '()' in all configuration defaults and CLI signatures.\n"
            "5. **Parameter Integrity and Signature Completeness:** Ensure that when parameters are synchronized, they are completely declared in all relevant function signatures (e.g., if 'access_log_format' is added, it must exist as an argument in the Click option list, the 'def main(...)' function signature, the 'def run(...)' function signature, and the Config class constructor). REJECT any partial or lazy edits that omit other existing parameters.\n\n"
            "OUTPUT FORMAT:\n"
            "Return a JSON object containing:\n"
            "- 'status': 'APPROVED' or 'REJECTED'\n"
            "- 'reason': A detailed description in English of your findings.\n"
            "- 'files_to_delete': A list of file paths (like '__main__.py') that were hallucinated and must be immediately deleted.\n"
            "- 'repair_instruction': If REJECTED, a highly precise, surgical instruction in ENGLISH telling the coder exactly what files to modify and how to fix the issue."
        )

        user_content = (
            f"ORIGINAL_PROMPT: {prompt}\n\n"
            f"FILES_MODIFIED_BY_CODER: {modified_files}\n\n"
            f"TEST_TRACEBACK:\n{test_output}\n\n"
            f"RELEVANT_SIGNATURES:\n{json.dumps(repo_map, indent=2)}"
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ],
            temperature=0.1
        )

        try:
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {"status": "APPROVED", "reason": "Failed to parse audit JSON, bypassing to prevent lock."}

class MEAAgents:
    """Facade de Integração para Agentes e Ferramentas Externas."""
    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o-mini", base_path: str = "."):
        self.client = client
        self.model = model
        self.base_path = base_path
        self.classificador = ClassificadorIA(client, model)
        self.architect = ArchitectAgent(client, model)
        self.auditor = SREAuditorAgent(client, model)  # Facade Instancia o Auditor
        self.repo_mapper = RepoMapGenerator(base_path)

    def classificar_requisicao(self, prompt: str) -> str:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.classificador.classificar(prompt))
        except RuntimeError:
            return asyncio.run(self.classificador.classificar(prompt))

    def planejar_evolucao_larga_escala(self, prompt: str, contexto_memoria: str) -> dict:
        """Gera o Repo Map via AST e planeja a evolução em larga escala de forma síncrona."""
        import asyncio
        mapa = self.repo_mapper.obter_mapa_repositorio()
        contexto = self.repo_mapper.identificar_contexto_universal()
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self.architect.planejar_mudanca_universal(prompt, mapa, contexto, contexto_memoria)
            )
        except RuntimeError:
            return asyncio.run(
                self.architect.planejar_mudanca_larga_escala(prompt, mapa, contexto_memoria)
            )

    def pesquisar_web_hermes(self, query: str) -> str:
        try:
            from hermes import Hermes # type: ignore
            agent = Hermes()
            return agent.search(query)
        except ImportError:
            try:
                query_encoded = urllib.parse.quote(query)
                url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={query_encoded}&limit=3&format=json"
                req = urllib.request.Request(url, headers={"User-Agent": "MEA-v4"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    if len(data) >= 4 and data[1]:
                        res = []
                        for i in range(len(data[1])):
                            res.append(f"Fact: {data[1][i]} - Link: {data[3][i]}")
                        return "\n".join(res)
                return "No relevant information found on the web."
            except Exception as e:
                return f"Contingency search error: {str(e)}"