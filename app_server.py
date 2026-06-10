# app_server.py (SaaS unificado com modelo BYOK - "Bring Your Own Key")
import os
import json
import asyncio
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="MEA 4.0.0 - Central Brain API (BYOK)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

model = "gpt-4o-mini"

# Importa os agentes da sua pasta secreta 'mea/'
from mea.agents import ClassificadorIA, ArchitectAgent

@app.post("/api/planejar")
async def planejar_brain(
    prompt: str = Form(...), 
    mapa_repositorio: str = Form(...),
    api_key: str = Form(...)  # <<< ALTERADO: Recebe a chave da OpenAI do próprio usuário
):
    """
    Endpoint que recebe a chave do cliente, instancia um cliente temporário seguro,
    e planeja o DAG de tarefas sem persistir ou salvar a chave do usuário em disco.
    """
    try:
        prompt_strip = prompt.strip()
        mapa_dict = json.loads(mapa_repositorio)
        
        # Instancia o cliente da OpenAI temporário para esta requisição com a chave do usuário
        temp_client = AsyncOpenAI(api_key=api_key)
        classificador = ClassificadorIA(temp_client, model)
        architect = ArchitectAgent(temp_client, model)
        
        # 1. Executa a triagem cognitiva de forma assíncrona
        categoria = await classificador.classificar(prompt_strip)
        
        if categoria != "EVOLUIR":
            return {"modo": "CHAT", "status": "chat"}
        
        # 2. Gera o plano de tarefas estruturado (DAG)
        plano = await architect.planejar_mudanca_larga_escala(prompt_strip, mapa_dict, "")
        return {
            "modo": "EVOLUIR", 
            "status": "queued", 
            "plano": plano
        }
    except Exception as e:
        return {"modo": "CHAT", "status": "error", "message": f"Erro no cérebro central: {str(e)}"}