import json
import os

def carregar_dados():
    """
    Lê os arquivos JSON da pasta 'data' e combina em um dicionário único.
    """
    base_path = 'data'
    
    def ler(nome_arquivo):
        caminho = os.path.join(base_path, nome_arquivo)
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"ATENÇÃO: Arquivo não encontrado: {caminho}")
            return [] if 'config' not in nome_arquivo else {}
        except Exception as e:
            print(f"ERRO CRÍTICO ao carregar {caminho}: {e}")
            return []

    # Monta a estrutura unificada
    db = {
        "config": ler('config.json').get('regras', {}),
        "temas": ler('config.json').get('temas_narrativos', {}),
        "politicas": ler('politicas.json'),
        "eventos": ler('eventos.json')
    }

    # Validação simples
    if not db['politicas']: print(">>> AVISO: Nenhuma política carregada.")
    if not db['eventos']: print(">>> AVISO: Nenhum evento carregado.")
    
    return db