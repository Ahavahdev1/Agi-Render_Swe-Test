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

    # <--- ADICIONE ESTA FUNÇÃO EXATAMENTE AQUI:
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

        # Identifica pastas de interesse (Adicionamos o uvicorn e o litellm)
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
        # Removemos 'workspace' da lista de ignorados para permitir a auditoria
        pastas_ignorar = {".git", ".mea", "venv", "__pycache__", "node_modules", "uploads", "frontend", "dist", "build"}
        
        for root, dirs, files in os.walk(self.base_path):
            # Apenas remove as pastas proibidas, mantém o resto
            dirs[:] = [d for d in dirs if d not in pastas_ignorar]
            
            for file in files:
                # Agora aceitamos arquivos .py, .js, .ts sem restrições de nome
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
            "Você é o classificador de entrada do MEA 4.0.\n"
            "Sua única tarefa é triar a mensagem do usuário em uma de três categorias de processamento:\n\n"
            "1. 'CHAT': Conversa simples, saudações, dúvidas teóricas gerais "
            "OU perguntas conceituais sobre suas capacidades (ex: 'o que você sabe fazer?', 'como você funciona?', "
            "'você pode se autocodificar?', 'mostre-me seu código'). "
            "Se o usuário estiver apenas PERGUNTANDO se você é capaz de fazer algo, sem ordenar uma mudança direta, classifique obrigatoriamente como CHAT.\n\n"
            "2. 'MEMORIA': Perguntas específicas sobre o passado ou lições aprendidas registradas em sua memória histórica.\n\n"
            "3. 'EVOLUIR': Apenas quando houver um COMANDO EXPLÍCITO, INSTRUÇÃO DIRETA ou ORDEM clara para "
            "alterar, criar, deletar ou refatorar o código-fonte físico do projeto (ex: 'crie o arquivo X', 'refatore o state.py', 'adicione um log', 'corrija o bug Y').\n\n"
            "Responda estritamente com apenas uma das três palavras: 'CHAT', 'MEMORIA' ou 'EVOLUIR'."
        )
        
        # Corrigido: Dicionário de mensagens do sistema formatado corretamente como dict
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
        # Identifica âncoras de registro (Onde o código se acopla ao sistema)
        ancoras = [f for f in mapa.keys() if any(x in f.lower() for x in ["registry", "factory", "config", "const", "models", "enum", "main"])]

        # --- DYNAMIC PERSONA ROUTER ---
        # Detecta se a intenção do usuário é auditoria de segurança ou desenvolvimento de recursos
        is_security = any(x in prompt.lower() for x in ["audit", "security", "vulnerability", "exploit", "poc", "scan", "red team"])

        if is_security:
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
            "You are the MEA 5.0 Lead Software Engineer. Your mission is to implement features in production codebases.\n\n"
            "STRICT DEVELOPMENT PROTOCOLS (MANDATORY):\n"
            "1. **PRESERVATION PRINCIPLE:** NEVER replace or overwrite existing robust methods. You are an EXTENDER, not a REWRITER. "
            "If you need to change existing logic, use 'SEARCH/REPLACE' blocks that only touch the specific lines needed. "
            "Always call 'super().method()' if you are overriding a base class method.\n"
            "2. **CODE INTEGRITY:** Do not simplify code or remove production-grade complexity. If the existing code handles edge-cases, your modifications must handle them too.\n"
            "3. **CONTRACT COMPLIANCE:** If implementing an interface, implement ALL abstract methods. NEVER leave 'pass' or empty placeholders.\n"
            f"4. **CONTEXT AWARENESS:** Tech: {contexto.get('tech', 'Python')}. Root: '{contexto.get('root', '.')}'. Files must be relative to the detected root.\n"
            f"5. **AUTOMATIC REGISTRATION:** Update configuration/factory files (Found anchors: {ancoras}) to register new modules following existing patterns.\n"
            "6. **NO EAGER IMPORTS:** When editing 'factory.py' or 'registry.py', maintain the lazy-loading architecture. Do not add top-level imports that break the lazy-loading pattern.\n\n"
            "JSON FORMAT RULES:\n"
            "- Return a flat list in 'plano_tarefas'.\n"
            "- Required keys: 'id', 'arquivos_afetados', 'instrucao_tecnica', 'depende_de'.\n"
            "- NO NESTED 'STEPS'. Every task must be a flat, executable instruction."
        )
        # ------------------------------

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

class MEAAgents:
    """Facade de Integração para Agentes e Ferramentas Externas."""
    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o-mini", base_path: str = "."):
        self.client = client
        self.model = model
        self.base_path = base_path
        self.classificador = ClassificadorIA(client, model)
        self.architect = ArchitectAgent(client, model)
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
        # 1. Recuperamos o contexto universal detectado
        contexto = self.repo_mapper.identificar_contexto_universal()
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                # 2. Chamamos a nova função 'planejar_mudanca_universal' passando o contexto
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
                url = f"https://pt.wikipedia.org/w/api.php?action=opensearch&search={query_encoded}&limit=3&format=json"
                req = urllib.request.Request(url, headers={"User-Agent": "MEA-v4"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    if len(data) >= 4 and data[1]:
                        res = []
                        for i in range(len(data[1])):
                            res.append(f"Fato: {data[1][i]} - Link: {data[3][i]}")
                        return "\n".join(res)
                return "Nenhuma informação relevante encontrada na web."
            except Exception as e:
                return f"Erro na busca de contingência: {str(e)}"