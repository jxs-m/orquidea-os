# **PLANO TÉCNICO DE PROJETO: ORQUÍDEA OS & ASSISTENTE AGÊNTICO LINUX**

**Documento de Especificação de Engenharia e Roadmap de Implementação**  
**Versão:** 1.5  
**Ambiente Alvo:** Linux (Debian / Ubuntu / Arch / Fedora)  
**Stack de GUI:** Python com **PyQt6 / PySide6**  
**Design System & Identidade Visual:** Tema **"Orquídea Negra"** (Dark Velvet / Orchid Magenta)  
**Orquestrador Agêntico:** Antigravity CLI (AGY)  
**Provedores de Inferência:** Google AI Studio (Gemini 2.0 Flash) / OpenRouter (Omnirouter)  
**Origem & Evolução:** Integração e aprimoramento de conceitos do `fada_assistant` (Overlay Flutuante, Voz, Multimodalidade e HUD Rápido)

---

## **1. Visão Geral e Objetivos do Sistema**

O **Orquídea OS** é uma solução híbrida para administração de sistemas Linux e produtividade do operador que combina:
* **Mascote / Overlay Flutuante com Guia Rápido de Funções:** Mini-widget translúcido no desktop (a flor da Orquídea Negra) com animação suave de *idle*, que ao ser clicado abre um **Menu HUD Rápido** com acesso a:
  1. 🌸 **Abrir Orquídea OS** (Janela principal completa com visão de pastas lado a lado e abas completas);
  2. ⚡ **Chat Rápido com o AGY** (Prompt flutuante compacto para tarefas e perguntas imediatas com o Antigravity CLI);
  3. 📊 **Monitor Rápido de Recursos** (Mini-painel em tempo real de CPU, Memória RAM e Armazenamento);
  4. 🎵 **Controle Rápido do Spotify** (Play, Pause, faixa atual);
  5. 📸 **Captura Rápida de Tela** (Print com análise de IA multimodal).
* **Hub de Grupos Virtuais de Pastas:** Mapeamento de pastas dispersas (ex: `enem` na Área de Trabalho e `iffar` em Documentos) exibidas lado a lado em colunas paralelas;
* **Cofre e Auditor de Credenciais (*Orquídea Vault*):** Auditoria contínua de permissões em `~/.ssh`, scanner de segredos em código/downloads e cofre AES-256 local;
* **Central de Mídia (*Media Hub*):** Conexão nativa com o Spotify via D-Bus MPRIS2 e mixer de som via PipeWire;
* **Daemon de Baixo Consumo (*Orquídea Daemon*):** Monitoramento contínuo em background via `/proc` e D-Bus (< 25 MB RAM e < 0.3% CPU);
* **Execução Agêntica com Reversibilidade:** Tarefas executadas pelo Antigravity CLI com lixeira segura (`trash-cli`) e reversão 1-click (`orquidea undo`).

### **1.1 Objetivos Estratégicos e Critérios de Sucesso (KPIs)**
1. **Consumo Quase Nulo de Recursos:** Daemon residente consumindo **< 25 MB de RAM** e **< 0.3% de CPU**, baseado em leituras diretas de `/proc`, `statvfs` e subscrições D-Bus.
2. **Acesso Instantâneo via HUD Flutuante:** Abrir o chat do AGY ou consultar o consumo de CPU/RAM em **< 200 ms** com 1 clique na flor da Orquídea ou atalho global (`Ctrl + Shift + O` / `Super + Espaço`).
3. **Privacidade Absoluta (Zero-Trust Egress):** Nenhuma chave de API, chave SSH, senha ou credencial sensível jamais é enviada a provedores de IA externos.
4. **Organização Lógica de Espaços de Trabalho:** Agrupamento de diretórios dispersos (`enem` e `iffar`) lado a lado em uma janela unificada.
5. **Controle Centralizado de Mídia:** Spotify controlado diretamente via barramento D-Bus sem exigir chaves de API web.
6. **Reversibilidade Determinística (Safe Undo):** Qualquer ação de movimentação ou remoção opera via lixeira segura e gera manifestos JSON para reversão total em 1 comando (`orquidea undo`).

---

## **2. Design System: Identidade Visual "Orquídea Negra" (PyQt6 QSS)**

A interface gráfica é construída em **PyQt6** com estilização via **QSS (Qt Style Sheets)** baseada na paleta de cores da identidade visual da banda **Orquídea Negra**:

### **2.1 Paleta de Cores e Tokens**
| Token | Cor Hex | Uso na Interface |
| :--- | :--- | :--- |
| `BG_MAIN` | `#0A060E` | Fundo principal da aplicação (Preto Obsidiana Profundo) |
| `BG_SIDEBAR` | `#110816` | Fundo da barra lateral de navegação |
| `BG_CARD` | `#190C22` | Cartões de conteúdo e colunas de pastas (Veludo Violeta) |
| `BG_CARD_HOVER` | `#231030` | Efeito hover em cartões e itens de listas |
| `ACCENT_PRIMARY`| `#C026D3` | Destaque principal, botões ativos e sliders (Magenta Orquídea) |
| `ACCENT_HOVER`  | `#E879F9` | Brilho / hover de botões e bordas de foco |
| `ACCENT_GLOW`   | `rgba(192, 38, 211, 0.25)` | Sombra externa suave nos cards ativos |
| `BORDER_SUBTLE` | `#3A1448` | Linhas divisórias e contornos sutis de cards |
| `TEXT_PRIMARY`  | `#F5E8FF` | Títulos e texto principal (Lavanda Claro / Quase Branco) |
| `TEXT_MUTED`    | `#A892B5` | Metadados de arquivos, caminhos e legendas |
| `STATUS_SUCCESS`| `#10B981` | Permissões seguras (`0600`) e serviços online |
| `STATUS_WARNING`| `#F59E0B` | Permissões vulneráveis e atenção de armazenamento |

---

## **3. O Módulo de Overlay Flutuante & Guia Rápido (HUD)**

O **Overlay Flutuante** (`ui/overlay.py`) é uma peça central da experiência do **Orquídea OS**:

```
 [ MESA DO LINUX ]
                                    (Mini-Flor Orquídea Flutuante)
                                               🌸
                                               │ (Clique ou Atalho)
                                               ▼
     ┌─────────────────────────────────────────────────────────────┐
     │ 🌸 GUIA RÁPIDO DO ORQUÍDEA OS                               │
     ├─────────────────────────────────────────────────────────────┤
     │  [🪟 Abrir Orquídea OS Completo]                            │
     │  [⚡ Chat Rápido com o AGY (Antigravity)]                   │
     │  [📊 Monitor de Recursos (CPU / RAM / Disco)]               │
     │  [🎵 Controles do Spotify]                                  │
     │  [📸 Tirar Print com Análise de IA]                         │
     └─────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┴────────────────────────┐
        ▼                                                ▼
┌───────────────────────────────┐        ┌───────────────────────────────┐
│ ⚡ CHAT RÁPIDO AGY (Pop-up)   │        │ 📊 MONITOR RÁPIDO DE RECURSOS │
├───────────────────────────────┤        ├───────────────────────────────┤
│ "organizar downloads de ontem"│        │ CPU: [██████░░░░] 58% (3.6GHz)│
│                               │        │ RAM: [████░░░░░░] 38% (6.1GB) │
│ [AGY]: Mapeei 4 arquivos.     │        │ DISCO (/): [███░░░░░░░] 32%   │
│ Deseja mover p/ Lixeira? [S/N]│        │ SWAP: 0%                      │
└───────────────────────────────┘        └───────────────────────────────┘
```

### **3.1 Os 3 Modos do Guia Rápido:**
1. **🌸 Abrir Orquídea OS (Janela Principal):** Transiciona suavemente para a janela principal com abas completas (Pastas `enem` e `iffar` lado a lado, cofre de chaves SSH, dashboard analítico e player).
2. **⚡ Chat Rápido com o AGY:** Um prompt flutuante com foco automático no teclado para disparar tarefas em linguagem natural ou perguntas diretas à IA, sem precisar carregar a tela completa.
3. **📊 Mini-Janela de Recursos (CPU, Memória e Disco):** Leituras instantâneas e precisas direto de `/proc/stat`, `/proc/meminfo` e `statvfs` em barras compactas com a paleta magenta.

---

## **4. Arquitetura do Sistema**

```
┌────────────────────────────────────────────────────────────────────────┐
│                   INTERFACES VISUAIS PYQT6                             │
│  ┌──────────────────────────────┐    ┌──────────────────────────────┐  │
│  │   JANELA PRINCIPAL COMPLETA  │    │  OVERLAY FLUTUANTE & GUIA    │  │
│  │ - Sidebar & Abas Temáticas   │    │ - Flor Orquídea Flutuante    │  │
│  │ - Pastas Lado a Lado         │    │ - Menu Guia Rápido (HUD)     │  │
│  │ - Mini-Player Spotify Rodapé │    │ - Chat AGY & Monitor CPU/RAM │  │
│  └──────────────────────────────┘    └──────────────────────────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    BARRAMENTO IPC & PERSISTÊNCIA                       │
│   - Unix Domain Socket: `/run/orquidea.sock` (JSON-RPC)                │
│   - SQLite WAL: Métricas, Incidentes, Grupos, Lembretes e Manifestos   │
└───────────────▲───────────────────────────────────▲────────────────────┘
                │                                   │
┌───────────────┴───────────────────┐   ┌───────────┴────────────────────┐
│     DAEMON ORQUÍDEA (REATIVO)     │   │  ORQUESTRADOR DE AGENTE (CLI)  │
│ - Monitor de /proc e statvfs      │   │ - Task Planner (Etapas)        │
│ - Listener D-Bus (systemd)        │   │ - Sanitizador de Egress        │
│ - Listener MPRIS2 (Spotify/Mídia) │   │ - Interface Antigravity CLI    │
│ - Timers e Motor de Lembretes     │   └───────────┬────────────────────┘
└───────────────────────────────────┘               │
                                                    │
        ┌───────────────────────────────────────────┴───────────────────────────────────────────┐
        │                                                                                       │
        ▼                                                                                       ▼
┌─────────────────────────┐                                                 ┌─────────────────────────────────────────┐
│    GATEWAY DE NUVEM     │                                                 │             EXECUÇÃO LOCAL              │
│  - Google AI Studio API │                                                 │  - Antigravity CLI (Tarefas & Automação)│
│  - OpenRouter / Omni    │                                                 │  - Vault & SSH Key Manager (Local Safe) │
│  - Gemini Multimodal    │                                                 │  - Workspace Hub (Pastas Lado a Lado)   │
│  (Análise de tela/logs) │                                                 │  - Media Controller (Spotify / MPRIS2)  │
└─────────────────────────┘                                                 │  - Quick HUD (CPU/RAM/Chat AGY)         │
                                                                            │  - Screen Capture & Lixeira Segura      │
                                                                            └─────────────────────────────────────────┘
```

---

## **5. Especificação dos Módulos**

### **5.1 Interface Gráfica, Guia Rápido e Overlay (`ui/`)**
* **Janela Principal (`ui/app.py`):** Interface completa em PyQt6 com sidebar e abas (`WorkspaceView` lado a lado, `VaultView`, `DashboardView` e `MediaBar`).
* **Overlay Flutuante & Menu Rápido (`ui/overlay.py`):**
  * Mini-janela frameless e translúcida (`Qt.WidgetAttribute.WA_TranslucentBackground`) posicionada no canto do monitor.
  * Animação idle da flor da Orquídea Negra.
  * Menu popover HUD acionado por clique ou atalho global (`Ctrl + Shift + O`).
* **Chat Rápido AGY (`ui/widgets/quick_chat.py`):** Caixa de prompt compacta estilo Spotlight / Raycast que envia solicitações ao orquestrador do Antigravity CLI.
* **Mini-Monitor de Recursos (`ui/widgets/quick_stats.py`):** Painel pop-up com medidores em tempo real de CPU, Memória RAM e Armazenamento.

### **5.2 Módulo de Interação: Voz, Áudio e Lembretes**
* **Entrada por Voz (`agent/tools/voice.py`):** Captura de fala via microfone.
* **Feedback Sonoro (`agent/tools/audio_feedback.py`):** Efeitos de som chiptune/blips e voz sintetizada.
* **Lembretes e Pomodoro (`agent/tools/reminders.py`):** Timers integrados ao modo estudo das pastas `enem` e `iffar`.
* **Captura de Tela Multimodal (`agent/tools/screenshot.py`):** Captura instantânea e análise visual via Gemini 2.0 Flash.

### **5.3 Módulo de Mídia & Áudio (Media Hub)**
* Conexão nativa com Spotify (`org.mpris.MediaPlayer2.spotify`) via D-Bus.
* Controle de volume granular do player via PipeWire (`wpctl`).
* "Modo Foco": playlist e pastas de estudo acionadas em conjunto.

### **5.4 Daemon Orquídea (Engine de Monitoramento)**
* Monitoramento de `/proc/meminfo`, `/proc/stat`, `/proc/diskstats`, `statvfs` e eventos do `systemd`.
* Consumo alvo: < 25 MB RAM e < 0.3% CPU.

### **5.5 Gestão de Credenciais e Segredos (Orquídea Vault)**
* Auditor de chaves SSH (`~/.ssh`), organizador de `~/.ssh/config` e cofre local criptografado com AES-256-GCM.
* Isolamento total contra envio para APIs de nuvem.

### **5.6 Grupos Virtuais de Pastas (Workspace Hub)**
* Mapeamento de pastas dispersas exibidas lado a lado em colunas independentes sem mover arquivos físicos.

---

## **6. Matriz de Ferramentas e Níveis de Permissão**

| Nível | Categoria | Permissão | Exemplos de Ferramentas / Ações |
| :---- | :---- | :---- | :---- |
| **Tier 1** | **Read-Only, Mídia & Assistência** | Autônomo (Execução Imediata) | `journalctl`, `df -h`, ler status de CPU/RAM, ler Spotify, Play/Pause/Volume, criar lembretes, tirar screenshot, ouvir comando de voz |
| **Tier 2** | **Mutating / Modificação** | Requer Confirmação Humana (HitL) | `trash-put <arquivos>`, mover arquivos em lote, organizar pastas, corrigir `chmod 600 ~/.ssh/id_*`, reiniciar serviços, fechar processos |
| **Tier 3** | **Blacklist Estrita** | Bloqueado Incondicionalmente | `rm -rf /`, `mkfs.*`, escrita direta em chaves privadas SSH, modificação em `/etc/sudoers` |

---

## **7. Roadmap de Implementação**

### **Fase 1: Fundação & Observabilidade (Sprints 1 e 2)**
* Estrutura de diretórios, banco SQLite (`state.db`) e daemon `/proc` + D-Bus.
* Servidor IPC via Unix Domain Socket (`/run/orquidea.sock`) com JSON-RPC.

### **Fase 2: Gestão de Segredos & Mídia Spotify (Sprint 3)**
* Módulo `vault.py`: auditoria de chaves SSH e cofre local de senhas/chaves de API.
* Módulo `media.py`: integração com Spotify via D-Bus MPRIS2 e PipeWire.

### **Fase 3: Interface Gráfica PyQt6 - Tema "Orquídea Negra" (Sprint 4)**
* Motor de estilo QSS (`ui/theme.py` e `ui/styles.qss`).
* Janela principal com pastas lado a lado (`enem` e `iffar`) e mini-player Spotify.

### **Fase 4: Overlay Flutuante & Guia Rápido HUD (Sprint 5)**
* Flor flutuante no desktop com animação idle e transparência real (`ui/overlay.py`).
* Menu HUD do Guia Rápido: Abertura da janela principal, Chat Rápido do AGY e Mini-Monitor de CPU/RAM/Disco.
* Lembretes Pomodoro e captura de tela para IA multimodal.

### **Fase 5: Orquestração Agêntica, Rollback & Empacotamento (Sprint 6)**
* Integração com Antigravity CLI para execução de tarefas sob demanda.
* Lixeira segura (`send2trash`) e comando `orquidea undo`.
* Bot de Telegram e serviço de sistema (`orquidea.service`).

---

## **8. Estrutura do Repositório do Projeto**

```
orquidea-os/
├── config/
│   ├── orquidea.conf            # Limiares de alerta e preferências
│   ├── antigravity.yaml         # Políticas de sandbox do Antigravity CLI
│   └── sudoers.d/orquidea       # Regras granulares de sudo
├── daemon/
│   ├── __init__.py
│   ├── core.py                  # Loop de monitoramento do daemon
│   ├── collectors/              # Parsers de /proc, statvfs, D-Bus e MPRIS
│   ├── ipc_server.py            # Servidor Unix Domain Socket
│   └── storage.py               # Manipulação do SQLite e retenção
├── agent/
│   ├── __init__.py
│   ├── orchestrator.py          # Planejador de tarefas e bridge Antigravity
│   ├── cloud_client.py          # Conectores Google AI Studio / OpenRouter
│   ├── sanitizer.py             # Filtros de mascaramento de dados sensíveis
│   └── tools/                   # Ferramentas locais especializadas
│       ├── files.py             # Lixeira segura, organizador e manifestos
│       ├── workspaces.py        # Mapeamento e gestão de grupos de pastas
│       ├── vault.py             # Auditor SSH, scanner de segredos e cofre
│       ├── media.py             # Controlador do Spotify, MPRIS2 e PipeWire
│       ├── voice.py             # Reconhecimento de voz (microfone)
│       ├── audio_feedback.py    # Efeitos de som chiptune/blips e TTS
│       ├── reminders.py         # Motor de timers e lembretes de estudo
│       ├── screenshot.py        # Captura de tela para IA multimodal
│       └── system.py            # Inspeção de processos e journalctl
├── ui/
│   ├── __init__.py
│   ├── app.py                  # Janela principal PyQt6 (Frameless, Sidebar)
│   ├── overlay.py              # Mini-widget flutuante "Orquídea" (Always-on-top)
│   ├── theme.py                # Constantes e tokens de cor "Orquídea Negra"
│   ├── styles.qss              # Folha de estilos Qt (Preto, Violeta e Magenta)
│   ├── assets/                 # Ícones SVG e logo da Orquídea Negra
│   ├── views/
│   │   ├── dashboard_view.py   # Gráficos de hardware e serviços
│   │   ├── workspace_view.py   # Visualizador de pastas lado a lado
│   │   ├── vault_view.py       # Tabela de chaves SSH e senhas
│   │   └── ai_chat_view.py     # Prompt do operador e histórico de ações
│   ├── widgets/
│   │   ├── media_bar.py        # Mini-player do Spotify no rodapé
│   │   ├── quick_hud.py        # Menu do Guia Rápido de funções
│   │   ├── quick_chat.py       # Pop-up de chat rápido com o AGY
│   │   ├── quick_stats.py      # Mini-painel de CPU, RAM e Disco
│   │   └── speech_bubble.py    # Balão de fala flutuante estilizado
│   └── telegram_bot.py         # Bot de aprovação remota
├── cli/
│   └── main.py                  # Ponto de entrada do comando `orquidea`
├── systemd/
│   └── orquidea.service         # Definição do serviço do daemon
├── tests/                       # Testes unitários e de integração
├── README.md
└── requirements.txt
```

---

## **9. Configuração Inicial do Ambiente**

Para iniciar o desenvolvimento prático no ambiente Linux:

1. **Instalação de Dependências de Sistema:**
   ```bash
   sudo apt update && sudo apt install -y python3-venv trash-cli sqlite3 libdbus-1-dev playerctl libegl1 portaudio19-dev libasound2-dev
   ```

2. **Configuração do Ambiente Virtual Python:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install PyQt6 qtawesome rich send2trash cryptography dbus-python google-genai SpeechRecognition pyttsx3 Pillow
   ```

3. **Criação do Grupo Administrativo:**
   ```bash
   sudo groupadd -f orquidea-admin
   sudo usermod -aG orquidea-admin $USER
   ```
