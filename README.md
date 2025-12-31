# 👑 Sovereign: The Living Chronicle (Soberano)

Um simulador narrativo de gestão de reino medieval onde cada decisão molda o destino do seu reinado.

## 📜 Sobre o Jogo

**Sovereign** não é apenas mais um jogo de gerenciamento. Você assume o papel de Monarca de um reino medieval, tomando decisões difíceis que definem não apenas números, mas a própria história do seu reinado.

O jogo utiliza um sistema inovador de **"Diretor Inteligente"** em três camadas que analisa seu estilo de jogo, sua reputação (Tags) e o estado do reino para selecionar dinamicamente o próximo evento narrativo. Sua história pode se tornar uma tragédia de Hubris, uma guerra pela sobrevivência, ou uma era de Iluminismo.

## ✨ Características Principais

### 🎭 Diretor Narrativo Dinâmico
Sistema de três camadas (Regras → IA → Drama) que monitora suas estatísticas e histórico:
- Acumule ouro demais? Prepare-se para a "Maldição de Midas"
- Pareça fraco? Seus vizinhos irão invadir
- Seja tirânico? Conspirações surgirão

### 🏅 Sistema de Reputação (Tags)
Suas ações definem quem você é:
- **Tirano** - governe com punho de ferro
- **Santo** - lidere com compaixão
- **Belicista** - expanda através da guerra
- **Burocrata** - administre com eficiência

Essas tags desbloqueiam ou bloqueiam eventos específicos no futuro.

### ⚖️ O Conselho (Políticas)
Promulgue ou revogue leis que transformam seu reino:
- **Servidão** - força de trabalho garantida, mas população insatisfeita
- **Livre Comércio** - prosperidade comercial com riscos
- **Inquisição** - controle ideológico através do medo
- **Magna Carta** - limite seu próprio poder em favor da estabilidade

Cada lei traz benefícios passivos e custos políticos.

### 📊 Gestão de Recursos
Equilibre seis pilares fundamentais do seu reino:
- 💰 **Tesouro** - Recursos financeiros
- ⚔️ **Militar** - Poder de defesa e conquista
- ❤️ **Popularidade** - Amor do povo
- 🏛️ **Estabilidade** - Ordem interna
- 🌾 **Agricultura** - Segurança alimentar
- 🏪 **Comércio** - Prosperidade econômica

### 🤖 Motor de IA Híbrido
Suporte opcional para integração com LLM local (via llama-cpp-python) que atua como um Mestre de RPG, escolhendo eventos baseado em potencial dramático e coerência narrativa.

## 🛠️ Stack Tecnológico

- **Backend**: Python 3.x com Flask
- **Frontend**: HTML5, CSS3 (tipografia Cinzel & Playfair Display), JavaScript Vanilla
- **Armazenamento**: Sistema de banco de dados baseado em JSON
- **IA/Inferência**: llama-cpp-python para suporte a modelos GGUF

## 📂 Estrutura do Projeto

```
soberano/
├── data/                  # Definições de conteúdo do jogo
│   ├── config.json        # Regras do jogo e temas narrativos
│   ├── events.json        # Base de dados de eventos narrativos e desfechos
│   └── policies.json      # Base de dados de leis e seus efeitos
├── src/                   # Lógica Central
│   ├── director.py        # Lógica do "Diretor" (coordenação IA + Regras)
│   ├── engine.py          # Gerenciamento de estado, estatísticas e cálculo de tags
│   ├── inference.py       # Integração LLM para seleção de eventos
│   ├── rules.py           # Filtros determinísticos (restrições rígidas)
│   ├── prompts.py         # Instruções do sistema de IA
│   └── database.py        # Utilitários de carregamento de dados
├── templates/
│   └── index.html         # Interface da "Sala do Trono" e "Conselho"
└── main.py                # Ponto de entrada da aplicação Flask
```

## 🚀 Instalação e Configuração

### 1. Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### 2. Instalar Dependências

```bash
# Dependências básicas
pip install flask

# Opcional: Para capacidades do Diretor com IA
pip install llama-cpp-python
```

### 3. Executar o Jogo

```bash
python main.py
```

Abra seu navegador e acesse: **http://127.0.0.1:5000**

## 🧠 Como Funciona o Sistema de Diretor

O jogo seleciona eventos através de três camadas distintas:

### 1️⃣ Motor de Regras (rules.py)
Filtra eventos impossíveis baseado no estado atual:
- Não pode ter evento "Rei Rico" se o tesouro está vazio
- Não pode ter "Revolta Camponesa" se a popularidade está alta
- Bloqueia eventos incompatíveis com políticas ativas

### 2️⃣ Camada de IA (inference.py)
Se um LLM estiver presente, classifica eventos viáveis baseado na "vibração" do seu reinado atual:
- Analisa seu histórico de decisões
- Considera suas tags de reputação
- Avalia o arco narrativo em desenvolvimento
- Escolhe eventos que criam drama significativo

### 3️⃣ Fallback Dramático
Se não houver IA, ordena eventos por `drama_weight` para garantir que pontos de enredo significativos aconteçam no momento certo.

### 🔮 Ativar o Modo IA

Coloque qualquer modelo em formato GGUF (como Qwen, Llama ou Mistral) no diretório raiz. O jogo detectará automaticamente e mudará para o modo Diretor Inteligente.

## 📖 Guia de Gameplay

### 📖 A Crônica
Seu histórico é registrado conforme você joga. Observe como suas decisões afetam a "Exibição do Ano" (em números romanos).

### ⚖️ Políticas
Acessadas via botão **"LEIS"**:
- Algumas leis são incompatíveis (ex: você não pode ter Absolutismo Real e Magna Carta ativos simultaneamente)
- Leis têm efeitos permanentes enquanto ativas
- Revogar uma lei pode ter consequências políticas

### 💀 Game Over
Cuidado! Atingir **0** em Estabilidade, Popularidade ou Militar resulta no fim da sua dinastia.

### 🎯 Dicas Estratégicas

- **Equilíbrio é chave**: Ignorar qualquer recurso pode levar ao colapso
- **Tags importam**: Suas ações passadas influenciam eventos futuros
- **Leia os eventos**: Muitas vezes há pistas sobre as consequências
- **Planeje a longo prazo**: Benefícios imediatos podem ter custos futuros

## 🤝 Contribuindo

Adicionar novo conteúdo é simples! Basta editar os arquivos JSON na pasta `/data`:

### Adicionar Novos Eventos

Edite `events.json`:

```json
{
  "id": "my_custom_event",
  "title": "Título do Evento",
  "description": "Descrição do que está acontecendo...",
  "theme": "prosperity",
  "drama_weight": 5,
  "requires_tags": ["peaceful"],
  "blocks_tags": ["warmonger"],
  "options": [
    {
      "text": "Opção 1",
      "effects": {
        "treasury": 10,
        "popularity": -5
      },
      "narrative": "Resultado da escolha...",
      "adds_tags": ["generous"]
    }
  ]
}
```

### Adicionar Novas Leis

Edite `policies.json`:

```json
{
  "id": "my_custom_law",
  "name": "Nome da Lei",
  "description": "O que esta lei faz...",
  "cost": 50,
  "passive_effects": {
    "commerce": 2,
    "stability": -1
  },
  "permanent_tags": ["reformer"],
  "incompatible_with": ["serfdom"]
}
```

## 📝 Licença

Este projeto está disponível para uso educacional e modificação.

## 🎮 Aproveite seu Reinado!

Que sua dinastia seja próspera e sua crônica seja lembrada através dos séculos! 👑

---

*"Um rei não é medido pela coroa que usa, mas pelas decisões que toma."*
