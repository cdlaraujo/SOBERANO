import random
import re
import glob

# Tenta carregar a biblioteca da IA
LLM_INSTANCE = None
try:
    from llama_cpp import Llama
    
    def inicializar_llm():
        """Busca modelo .gguf e inicia a IA."""
        model_files = glob.glob("*.gguf")
        if model_files:
            print(f">>> CARREGANDO MODELO: {model_files[0]} ...")
            return Llama(model_path=model_files[0], n_ctx=2048, n_gpu_layers=-1, verbose=False)
        print(">>> NENHUM MODELO ENCONTRADO. MODO LOBOTOMIA ATIVADO.")
        return None

except ImportError:
    print(">>> LLAMA_CPP NÃO INSTALADO. MODO LOBOTOMIA ATIVADO.")
    def inicializar_llm(): return None

def traduzir_estado_para_texto(gamestate):
    """Converte números do jogo em prosa para o prompt."""
    s = gamestate['stats']
    descricoes = []
    
    # Tesouro
    if s['tesouro'] > 80: descricoes.append("O Reino está obscenamente rico.")
    elif s['tesouro'] < 20: descricoes.append("O tesouro está vazio, falência iminente.")
    
    # Estabilidade vs Popularidade
    if s['popularidade'] < 30 and s['estabilidade'] > 70: descricoes.append("O povo teme o Rei tirano.")
    elif s['popularidade'] > 70 and s['estabilidade'] < 30: descricoes.append("O Rei é amado, mas o reino é caótico.")
    elif s['popularidade'] < 30 and s['estabilidade'] < 30: descricoes.append("Revolução iminente.")
    
    # Militar
    if s['militar'] > 80: descricoes.append("O exército é imenso.")
    elif s['militar'] < 20: descricoes.append("Fronteiras indefesas.")

    # Políticas
    if "teocracia" in gamestate['politicas_ativas']: descricoes.append("A Igreja domina.")
    
    texto = " ".join(descricoes)
    return texto if texto else "O reino está estável e medíocre."

def escolher_evento(llm, gamestate, lista_eventos):
    """Lógica principal de escolha de eventos."""
    
    # Filtra eventos aleatórios para análise (evita contexto infinito)
    candidatos = random.sample(lista_eventos, k=min(len(lista_eventos), 6))
    
    if not llm:
        return random.choice(candidatos)

    contexto = traduzir_estado_para_texto(gamestate)
    opcoes = "\n".join([f"ID {e['id']}: {e['titulo']} ({e.get('tema','geral')})" for e in candidatos])

    prompt = f"""<|im_start|>system
Você é o Diretor Narrativo de um jogo. Escolha o Próximo Evento baseado no Estado.
Regras:
1. Puna arrogância se rico.
2. Chute quem está caído se pobre.
3. Responda APENAS com o ID numérico.
<|im_end|>
<|im_start|>user
ESTADO: {contexto}
OPÇÕES:
{opcoes}
Qual o ID?
<|im_end|>
<|im_start|>assistant
ID"""

    try:
        output = llm(prompt, max_tokens=10, stop=["\n", "."], echo=False, temperature=0.3)
        resp = output['choices'][0]['text'].strip()
        print(f">>> IA Sugere: {resp}")
        
        match = re.search(r'\d+', resp)
        if match:
            eid = int(match.group())
            found = next((e for e in candidatos if e['id'] == eid), None)
            if found: return found
            
    except Exception as e:
        print(f"Erro na inferência: {e}")

    return random.choice(candidatos)