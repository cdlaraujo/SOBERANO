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
    if s['tesouro'] > 80: descricoes.append("Cofres transbordam de ouro.")
    elif s['tesouro'] < 20: descricoes.append("Tesouro está vazio.")
    
    # Estabilidade vs Popularidade
    if s['popularidade'] < 30 and s['estabilidade'] > 70: 
        descricoes.append("Rei tirano mantém ordem pelo medo.")
    elif s['popularidade'] > 70 and s['estabilidade'] < 30: 
        descricoes.append("Rei amado governa reino caótico.")
    elif s['popularidade'] < 30 and s['estabilidade'] < 30: 
        descricoes.append("Revolução se aproxima.")
    
    # Militar
    if s['militar'] > 80: descricoes.append("Exército poderoso.")
    elif s['militar'] < 20: descricoes.append("Fronteiras indefesas.")

    # Políticas
    pols = []
    if "teocracia" in gamestate['politicas_ativas']: pols.append("teocracia")
    if "absolutismo" in gamestate['politicas_ativas']: pols.append("absolutismo")
    if "parlamentarismo" in gamestate['politicas_ativas']: pols.append("parlamento")
    if pols: descricoes.append(f"Governo: {', '.join(pols)}.")
    
    texto = " ".join(descricoes)
    return texto if texto else "Reino estável e equilibrado."

def escolher_evento(llm, gamestate, lista_eventos):
    """Lógica principal de escolha de eventos."""
    
    # Filtra eventos aleatórios para análise (evita contexto infinito)
    candidatos = random.sample(lista_eventos, k=min(len(lista_eventos), 6))
    
    if not llm:
        return random.choice(candidatos)

    contexto = traduzir_estado_para_texto(gamestate)
    opcoes = "\n".join([f"{e['id']}: {e['titulo']} (tema: {e.get('tema','geral')})" for e in candidatos])

    # Prompt genérico compatível com mais modelos
    prompt = f"""### TAREFA
Você é o Diretor Narrativo dramático de um jogo medieval.
Escolha o evento mais interessante baseado no estado atual.

REGRAS:
- Pune arrogância de reis ricos
- Castiga reis fracos e pobres
- Cria drama e consequências

ESTADO DO REINO: {contexto}

EVENTOS DISPONÍVEIS:
{opcoes}

Responda APENAS com o número do ID escolhido.
ID escolhido:"""

    try:
        output = llm(prompt, max_tokens=10, stop=["\n", ".", " "], echo=False, temperature=0.3)
        resp = output['choices'][0]['text'].strip()
        print(f">>> IA Resposta: '{resp}'")
        
        # Extrai primeiro número encontrado
        match = re.search(r'\d+', resp)
        if match:
            eid = int(match.group())
            found = next((e for e in candidatos if e['id'] == eid), None)
            if found: 
                print(f">>> IA Escolheu: {found['titulo']}")
                return found
            
    except Exception as e:
        print(f">>> Erro na inferência da IA: {e}")

    # Fallback inteligente: escolhe evento com maior peso dramático
    escolha = max(candidatos, key=lambda x: x.get('peso_drama', 50))
    print(f">>> Fallback: {escolha['titulo']}")
    return escolha