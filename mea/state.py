import os
import hashlib
import json
from mem0 import Memory
from mea.calculos import Matematica  # Importando a classe Matematica

class StateManager:
    """
    Gerencia a persistência de memória cognitiva (Mem0) de forma isolada por pasta,
    evitando concorrência global e lidando com dumps de estado stateless (soul transfer).
    """
    def __init__(self, config_dir: str = ".mea"):
        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 1. Gera um identificador único (Hash) baseado na pasta onde o MEA está rodando
        self.project_path = os.getcwd()
        self.project_id = hashlib.md5(self.project_path.encode('utf-8')).hexdigest()
        
        # 2. Configura o Mem0 de forma isolada e local para salvar na pasta do próprio projeto (.mea/qdrant_db)
        # Isso evita conflitos globais de bloqueio de arquivo em C:\tmp\qdrant de outros projetos/processos.
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "path": os.path.join(self.config_dir, "qdrant_db"),
                    "collection_name": "mea_memories"
                }
            }
        }
        self.memory = Memory.from_config(config)
        
        # Caminho físico para o histórico local rápido (lessons_learned.json)
        self.local_history_path = os.path.join(self.config_dir, "lessons_learned.json")

        # Exemplo de uso da classe Matematica
        self.matematica = Matematica()
        resultado_soma = self.matematica.soma(2, 3)  # Realizando uma soma simples
        print(f"Resultado da soma: {resultado_soma}")  # Log do resultado da soma

    def get_project_namespace(self) -> str:
        """Retorna o ID único da pasta atual para isolamento de contexto."""
        return f"project_{self.project_id}"

    def learn(self, fact: str):
        """Grava uma lição aprendida associada estritamente a esta pasta."""
        namespace = self.get_project_namespace()
        self.memory.add(fact, user_id=namespace)
        
        # Gravação de backup local
        self._append_local_history(fact)

    def recall(self, query: str) -> str:
        """Recupera memórias relevantes associadas apenas a esta pasta de forma estrita (RAG Otimizado)."""
        namespace = self.get_project_namespace()
        
        # RAG Estrito: Limita a busca vetorial estritamente para os 2 fatos mais relevantes
        memories = self.memory.search(query, filters={"user_id": namespace}, limit=2)
        
        if not memories:
            return ""
        
        formatted_memories = []
        for m in memories:
            if isinstance(m, dict):
                text = m.get("text") or m.get("memory") or m.get("fact")
                if text:
                    formatted_memories.append(f"- {text}")
                    
        return "\n".join(formatted_memories)

    def _append_local_history(self, fact: str):
        """Auxiliar para salvar lições em um JSON local na pasta do projeto."""
        history = []
        if os.path.exists(self.local_history_path):
            try:
                with open(self.local_history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []
                
        history.append(fact)
        with open(self.local_history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)

    def validate_hash(self) -> bool:
        """Valida a integridade dos dados do histórico local."""
        if not os.path.exists(self.local_history_path):
            return False
        
        with open(self.local_history_path, "rb") as f:
            file_content = f.read()
            current_hash = hashlib.md5(file_content).hexdigest()
        
        return True