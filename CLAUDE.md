# **CLAUDE.md - DIRETIVAS DO ORQUÍDEA OS PARA O OPEN-CLAUDE**

Este arquivo é lido automaticamente pelo **Open-Claude** ao iniciar qualquer sessão neste repositório.

---

## **1. Gateway de Inferência & Modelos (Omnirouter + Dual-Tier)**
* **Gateway de Roteamento:** **Omnirouter** (Ativo localmente para unificação de endpoints e aliases).
* **Geração Inicial / Código Bruto:** **GPT-6 Luna** (`--model gpt-6-luna` roteado via Omnirouter).
  * Use para: Scaffolding, classes, lógica dos coletores, UI em PyQt6, estilização QSS e testes.
* **Depuração Estrutural & Bug-Hunting:** **GPT-6 Sol** (`--model gpt-6-sol` roteado via Omnirouter).
  * Acione quando: Houver travamentos de GUI (`QThread`), problemas de concorrência com D-Bus, locks em socket Unix ou falhas complexas que o Luna não resolver em 2 tentativas.

---

## **2. Regras Rígidas de Desenvolvimento (Invioláveis)**

1. **Anti-Placeholder:** NUNCA gere código incompleto, com `# TODO`, `# lógica restante aqui` ou classes vazias. O código gerado deve ser 100% funcional.
2. **Concorrência PyQt6 (UI Nunca Trava):**
   * A thread principal do PyQt6 é exclusiva para renderização.
   * Proibido `time.sleep()`, chamadas de rede ou I/O síncrono na thread da GUI.
   * Use sempre `QThread` com `pyqtSignal` para tarefas em segundo plano.
3. **Consumo Máximo do Daemon (< 25 MB RAM / < 0.3% CPU):**
   * Proibido usar subprocessos (`ps`, `top`, `free`) para coletar métricas.
   * Use parse direto de `/proc/stat`, `/proc/meminfo` e `os.statvfs('/')`.
4. **Segurança e Reversibilidade:**
   * NUNCA use `rm -rf` ou `os.remove()` em arquivos de usuário. Use `send2trash`.
   * Gere manifestos JSON em `~/.cache/orquidea/undo/<timestamp>.json` antes de qualquer movimentação/exclusão em lote para permitir `orquidea undo`.
   * Zero-Trust Egress: Nunca serialize ou envie chaves privadas SSH (`~/.ssh/id_*`) ou senhas para APIs de nuvem.
5. **Paleta "Orquídea Negra" (QSS):**
   * `BG_MAIN`: `#0A060E` | `BG_CARD`: `#190C22` | `ACCENT_PRIMARY`: `#C026D3` | `ACCENT_HOVER`: `#E879F9`
   * `BORDER_SUBTLE`: `#3A1448` | `TEXT_PRIMARY`: `#F5E8FF` | `TEXT_MUTED`: `#A892B5`
6. **Overlay Flutuante (`ui/overlay.py`):**
   * Flags obrigatórias: `FramelessWindowHint | WindowStaysOnTopHint | SubWindow` com `setAttribute(WA_TranslucentBackground, True)`.

---

## **3. Comandos de Validação e Testes Locais**

Após gerar ou alterar arquivos, execute sempre a checagem de sintaxe:
```bash
python3 -m py_compile caminho/do/arquivo.py
pytest tests/ -v
```

Para referências de arquitetura e contratos completos, consulte:
- [plano inicial .md](file:///home/rodnei/%C3%81rea%20de%20trabalho/proj%20sen/plano%20inicial%20.md)
- [INSTRUCOES_IA.md](file:///home/rodnei/%C3%81rea%20de%20trabalho/proj%20sen/INSTRUCOES_IA.md)
- [estrategia_desenvolvimento_ia.md](file:///home/rodnei/%C3%81rea%20de%20trabalho/proj%20sen/estrategia_desenvolvimento_ia.md)
