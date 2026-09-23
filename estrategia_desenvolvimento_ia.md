# **GUIA DE ENGENHARIA: CONSTRUÇÃO COM OPEN-CLAUDE & IA DUAL-TIER**
# **PROJETO: ORQUÍDEA OS & ASSISTENTE AGÊNTICO LINUX**

**Documento de Metodologia, Orquestração com Open-Claude e Ciclo Luna/Sol**  
**Versão:** 2.0  
**Ferramenta de Codificação:** **Open-Claude** (CLI Agent)  
**Modelos:** **GPT-6 Luna** (Drafting & Construção) + **GPT-6 Sol** (Resolução de Bugs Críticos)  

---

## **1. A Dinâmica do Open-Claude com a Estratégia Dual-Tier**

O **Open-Claude** é um agente autônomo de terminal que lê o repositório, edita arquivos e executa comandos bash diretamente no seu Linux. Para extrair o máximo dele sem estourar custos nem criar bugs acumulados, adotamos a divisão estrita:

```
┌────────────────────────────────────────────────────────────────────────┐
│               FLUXO DE TRABALHO COM OPEN-CLAUDE & DUAL-TIER            │
├──────────────────────────────────┬─────────────────────────────────────┤
│   🚀 OPEN-CLAUDE + GPT-6 LUNA    │     🧠 OPEN-CLAUDE + GPT-6 SOL      │
├──────────────────────────────────┼─────────────────────────────────────┤
│ • Construção modular arquivo a   │ • Depuração de bugs estruturais     │
│   arquivo (85% do projeto)       │ • Concorrência de threads PyQt6     │
│ • Criação de scaffolding e QSS   │ • Travamentos de D-Bus / Socket IPC │
│ • Parsers de /proc e SQLite      │ • Auditoria final de segurança      │
│ • Custo ultrabaixo (~$0.10 / 1M) │ • Custo seletivo (~$2.00 / 1M)      │
│ • Comando:                       │ • Comando:                          │
│   open-claude --model gpt-6-luna │   open-claude --model gpt-6-sol     │
└──────────────────────────────────┴─────────────────────────────────────┘
```

### **1.1 Carregamento Automático de Contexto (`CLAUDE.md`)**
Ao iniciar o Open-Claude no diretório do projeto, ele lê automaticamente o arquivo [CLAUDE.md](file:///home/rodnei/%C3%81rea%20de%20trabalho/proj%20sen/CLAUDE.md). Isso garante que o **GPT-6 Luna** já comece ciente de:
* Regra Anti-Placeholder (código completo, sem `# TODO`).
* Uso obrigatório de `QThread` no PyQt6 (sem travar a GUI).
* Consumo `< 25 MB RAM` no Daemon (parse direto de `/proc`).
* Segurança com `send2trash` e paleta *Orquídea Negra*.

---

## **2. Ciclo de Execução no Open-Claude: "Construa, Teste e Avance"**

O maior risco em ferramentas autônomas como o Open-Claude é pedir muito de uma vez só e ele gerar 10 arquivos interdependentes com pequenas falhas.

O ciclo correto no Open-Claude é **uma unidade funcional por prompt**:

```
 ┌──────────────────────┐
 │ 1. Iniciar Sessão    │ open-claude --model gpt-6-luna
 └──────────┬───────────┘
            │
            ▼
 ┌──────────────────────┐
 │ 2. Prompt Específico │ "Implemente apenas o arquivo daemon/collectors/proc_collector.py..."
 └──────────┬───────────┘
            │
            ▼
 ┌──────────────────────┐
 │ 3. Validação Bash    │ O Open-Claude executa `python3 -m py_compile ...`
 └──────────┬───────────┘
            │
     ┌──────┴──────┐
     ▼             ▼
  [Sucesso]     [Erro]
     │             │
     │             ├─► Erro simples? Luna corrige no mesmo prompt.
     │             └─► Travou / Bug de thread? Troca para:
     │                 open-claude --model gpt-6-sol "Corrija o bug em..."
     ▼
 ┌──────────────────────┐
 │ 4. Commit Local      │ git add . && git commit -m "feat: proc_collector implementado"
 └──────────────────────┘
```

---

## **3. Roteiro Passo a Passo de Construção com o Open-Claude**

Abaixo estão as 5 fases estruturadas, com a **sequência exata de prompts** para você colar no Open-Claude:

---

### **Fase 1: Fundação & Daemon (Headless - Sem Interface Gráfica)**
*Modelo no Open-Claude:* `gpt-6-luna`

#### **Passo 1.1: Estrutura e Banco SQLite**
> **Prompt para o Open-Claude:**  
> *"Crie o arquivo `daemon/storage.py` com a classe `StorageManager` usando SQLite em modo WAL (`PRAGMA journal_mode=WAL;`). Crie as tabelas `metricas_sistema` (timestamp, cpu, ram, disk), `incidentes_log` e `grupos_virtuais` conforme o plano. Crie testes unitários em `tests/test_storage.py` e execute os testes para validar."*

#### **Passo 1.2: Coletor de Métricas `/proc` (Consumo < 25 MB)**
> **Prompt para o Open-Claude:**  
> *"Implemente `daemon/collectors/proc_collector.py`. Faça o parse direto de `/proc/stat` para CPU, `/proc/meminfo` para RAM (MemTotal vs MemAvailable) e `os.statvfs('/')` para disco. É estritamente proibido usar subprocessos (`ps`, `free`, `top`). Crie métodos tipados e teste o arquivo com `python3 -m py_compile`."*

#### **Passo 1.3: Servidor IPC Socket Unix**
> **Prompt para o Open-Claude:**  
> *"Crie `daemon/ipc_server.py`. O servidor deve escutar em `/run/orquidea.sock` usando protocolo JSON-RPC não-bloqueante. Deve definir permissões `chmod 0660` e responder a comandos como `get_metrics` e `ping`. Inclua tratamento seguro de encerramento removendo o arquivo de socket."*

#### **Passo 1.4: Loop do Daemon Principal**
> **Prompt para o Open-Claude:**  
> *"Crie `daemon/core.py` unindo `proc_collector.py`, `storage.py` e `ipc_server.py`. O loop deve coletar métricas a cada 2 segundos e gravar no SQLite. O consumo total de memória deve permanecer abaixo de 25 MB."*

---

### **Fase 2: Ferramentas Locais & Mídia (Python)**
*Modelo no Open-Claude:* `gpt-6-luna`

#### **Passo 2.1: Módulo de Mídia (Spotify D-Bus & PipeWire)**
> **Prompt para o Open-Claude:**  
> *"Crie `agent/tools/media.py` com a classe `MediaController`. Use `dbus` para se conectar a `org.mpris.MediaPlayer2.spotify` e implementar `play_pause()`, `next()`, `previous()` e `get_metadata()`. Use `subprocess.run(['wpctl', ...])` para controle de volume do PipeWire com validação de limites."*

#### **Passo 2.2: Cofre de Chaves e Auditor SSH**
> **Prompt para o Open-Claude:**  
> *"Implemente `agent/tools/vault.py`. Crie a função de auditar `~/.ssh/` verificando permissões `0600` em chaves privadas e `0700` no diretório. Crie a classe `LocalVault` com criptografia AES-256-GCM (usando a biblioteca `cryptography`) para salvar senhas locais sob chave mestre."*

#### **Passo 2.3: Hub de Grupos Virtuais & Lixeira Segura**
> **Prompt para o Open-Claude:**  
> *"Implemente `agent/tools/workspaces.py` para mapear pastas dispersas (ex: `enem` e `iffar`) no SQLite. E implemente `agent/tools/files.py` usando `send2trash` para qualquer exclusão e gerando manifesto JSON em `~/.cache/orquidea/undo/` antes de mover arquivos."*

---

### **Fase 3: Design System & Interface Gráfica PyQt6**
*Modelo no Open-Claude:* `gpt-6-luna`

#### **Passo 3.1: Design Tokens & QSS "Orquídea Negra"**
> **Prompt para o Open-Claude:**  
> *"Crie `ui/theme.py` e `ui/styles.qss`. Implemente o tema 'Orquídea Negra' com as cores: `#0A060E` (fundo principal), `#190C22` (cards), `#C026D3` (magenta de destaque), `#E879F9` (hover) e `#F5E8FF` (texto). Estilize botões, barras de progresso, listas e scrollbars."*

#### **Passo 3.2: Mini-Player Spotify no Rodapé**
> **Prompt para o Open-Claude:**  
> *"Implemente `ui/widgets/media_bar.py` em PyQt6. Crie um widget horizontal com: thumbnail do álbum, nome da faixa, botões de mídia (Play/Pause/Next) em magenta e barra de progresso. Conecte com `agent/tools/media.py` de forma não-bloqueante usando `QTimer` para atualizar o status a cada 1 segundo."*

#### **Passo 3.3: Visualizador de Pastas Lado a Lado**
> **Prompt para o Open-Claude:**  
> *"Implemente `ui/views/workspace_view.py`. O componente deve usar `QSplitter` para renderizar as pastas de estudo (ex: `enem` em Área de Trabalho e `iffar` em Documentos) lado a lado em colunas independentes, listando arquivos e permitindo abrir itens com o aplicativo padrão do Linux."*

#### **Passo 3.4: Janela Principal Integrada**
> **Prompt para o Open-Claude:**  
> *"Crie `ui/app.py` com a janela principal (`MainWindow`) unindo a sidebar de navegação, a visualização de pastas lado a lado e o mini-player de mídia no rodapé. A janela deve ser frameless com controles customizados e aplicar a folha de estilos `styles.qss`."*

---

### **Fase 4: Overlay Flutuante & Guia Rápido (HUD)**
*Modelo no Open-Claude:* `gpt-6-luna`

#### **Passo 4.1: Flor Flutuante com Transparência Real**
> **Prompt para o Open-Claude:**  
> *"Implemente `ui/overlay.py`. Crie uma janela flutuante com a flor da Orquídea Negra usando `FramelessWindowHint`, `WindowStaysOnTopHint`, `SubWindow` e `WA_TranslucentBackground`. Implemente o arraste com o mouse (`mousePressEvent` e `mouseMoveEvent`) e animação suave de idle."*

#### **Passo 4.2: O Guia Rápido HUD**
> **Prompt para o Open-Claude:**  
> *"Crie `ui/widgets/quick_hud.py`. Ao clicar na flor do overlay, deve abrir um popover com bordas em magenta contendo: 1. Botão 'Abrir Orquídea OS'; 2. 'Chat Rápido com o AGY'; 3. 'Monitor de Recursos' com barras de CPU, RAM e Disco em tempo real lendo do daemon."*

---

### **Fase 5: Bug-Hunting & Polimento com GPT-6 Sol**
*Modelo no Open-Claude:* `gpt-6-sol`

Quando todos os módulos estiverem criados, **inicie o Open-Claude com o GPT-6 Sol** para uma auditoria cirúrgica:

```bash
open-claude --model gpt-6-sol
```

> **Prompt de Auditoria para o GPT-6 Sol:**  
> *"Você é o Arquiteto Sênior do Orquídea OS. Faça uma auditoria rigorosa em todos os arquivos de `daemon/`, `ui/` e `agent/tools/`. Verifique especificamente:  
> 1. Alguma thread do PyQt6 está bloqueando a interface principal?  
> 2. Há algum vazamento de memória ou descritor de arquivo aberto no `proc_collector.py` ou `ipc_server.py`?  
> 3. O `media.py` trata corretamente quando o Spotify está fechado sem lançar exceções não tratadas?  
> 4. O `sanitizer.py` mascara 100% de qualquer chave privada antes de conexões de IA?  
> Corrija qualquer inconformidade encontrada diretamente nos arquivos."*

---

## **4. Dicas de Ouro para o Open-Claude**

1. **Reinicie o Open-Claude entre Fases (`/clear` ou novo terminal):**  
   Não deixe o histórico acumular o código de todas as fases. Limpe a sessão ao terminar uma fase para que o Luna continue focado e rápido.
2. **Deixe o Open-Claude Executar os Testes:**  
   Como o Open-Claude tem acesso ao bash, sempre termine o prompt com: *"Valide a sintaxe do arquivo gerado executando `python3 -m py_compile <caminho>`"*.
3. **Não Insista com o Luna em Travamentos:**  
   Se o Luna tentar corrigir um problema de thread/interface 2 vezes e a GUI continuar travando, troque na hora para `open-claude --model gpt-6-sol`. O Sol resolverá o erro de concorrência em uma única resposta.
