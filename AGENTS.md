# **REGRAS E DIRETIVAS DE DESENVOLVIMENTO AGÊNTICO (ORQUÍDEA OS)**

Este arquivo atua como o conjunto de regras primárias para agentes de IA neste repositório.  
Para o guia técnico e arquitetural completo com tokens de QSS e contratos de interface, consulte o documento oficial: [INSTRUCOES_IA.md](file:///home/rodnei/%C3%81rea%20de%20trabalho/proj%20sen/INSTRUCOES_IA.md).

---

## **DIRETIVAS RÁPIDAS OBRIGATÓRIAS (RESUMO EXECUTIVO):**

1. **Stack & Ambiente:** Python 3.12+, Linux (X11/Wayland), PyQt6, D-Bus, SQLite (modo WAL), Unix Domain Socket (`/run/orquidea.sock`).
2. **Concorrência PyQt6:** NUNCA execute chamadas bloqueantes (rede, I/O síncrono, D-Bus, `time.sleep`) na thread principal da GUI. Use sempre `QThread` com `pyqtSignal`.
3. **Consumo Máximo do Daemon (< 25 MB RAM e < 0.3% CPU):** Proibido usar subprocessos (`ps`, `top`, `free`) para coletar métricas. Parse direto de `/proc/stat`, `/proc/meminfo` e `os.statvfs('/')`.
4. **Segurança & Reversibilidade:**
   - Proibido `rm -rf` ou `os.remove()` em arquivos de usuário. Use `send2trash`.
   - Gere manifestos JSON em `~/.cache/orquidea/undo/` antes de operações em lote para permitir `orquidea undo`.
   - Zero-Trust Egress: Nunca envie chaves privadas SSH (`~/.ssh/id_*`) ou credenciais para APIs de IA em nuvem.
5. **Estilização "Orquídea Negra":** Paleta Dark/Magenta estrita (`#0A060E`, `#190C22`, `#C026D3`, `#F5E8FF`).
6. **Overlay Flutuante:** Flags `FramelessWindowHint | WindowStaysOnTopHint | SubWindow` com `WA_TranslucentBackground`.
7. **Código Completo:** Proibidos placeholders (`# TODO`, `# restante do código aqui`). Entregue arquivos funcionais e completos.
