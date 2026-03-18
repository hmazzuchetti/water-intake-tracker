# Issues & Melhorias - Tracking

Arquivo para acompanhar problemas conhecidos e melhorias planejadas.
Atacamos **um por vez**, testamos, e marcamos como resolvido.

---

## Issue #1: Duas instancias abrem ao ligar o PC
**Status:** PENDENTE
**Prioridade:** Alta (afeta uso diario)

**Problema:**
Ao ligar o PC, duas instancias do Water Intake Tracker abrem simultaneamente.

**Causa provavel:**
Existem **dois mecanismos de autostart** configurados ao mesmo tempo:

1. **Atalho na pasta Startup do Windows** - Criado pelo instalador Inno Setup (`installer.iss` linha 98):
   ```
   {userstartup}\Water Intake Tracker -> {app}\WaterIntakeTracker.exe
   ```

2. **Entrada no Registro do Windows** - Criada pelo settings_ui.py (`set_startup_with_windows()` linha 128):
   ```
   HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run\WaterIntakeTracker
   ```

Se o usuario marcou "iniciar com Windows" no instalador E tambem nas Settings do app, ambos disparam na inicializacao.

**Solucao proposta:**
- Adicionar um **mutex/single-instance lock** no `main.py` (usando `QSharedMemory` ou named mutex do Windows)
- Se ja existe uma instancia rodando, a segunda simplesmente fecha
- Bonus: unificar o mecanismo de autostart para evitar duplicatas

**Arquivos envolvidos:**
- `main.py` (entry point - adicionar single-instance check)
- `settings_ui.py` (mecanismo de registry)
- `installer.iss` (mecanismo de startup shortcut)

---

## Issue #2: Compatibilidade com macOS
**Status:** PENDENTE
**Prioridade:** Baixa (feature futura)

**Problema:**
O app e 100% Windows-only. Para rodar em Mac, varias partes precisam mudar.

**O que e cross-platform (ja funciona):**
- Deteccao via MediaPipe/OpenCV
- Interface PyQt5
- Storage JSON
- Ollama/AI messaging

**O que e Windows-only (precisa adaptar):**
1. **Som:** Usa `winsound` (main.py, message_bubble.py) - trocar por `pygame.mixer` ou `playsound`
2. **Autostart:** Usa `winreg` (settings_ui.py) - Mac usa `~/Library/LaunchAgents/` com plist
3. **Instalador:** Inno Setup e Windows-only - Mac precisa de `.dmg` ou `.app` bundle
4. **Caminhos:** Backslashes hardcoded em alguns lugares

**Nao tem deteccao de plataforma:** Zero uso de `sys.platform` ou `platform.system()` no codigo.

**Solucao proposta:**
- Criar uma camada de abstracao `platform_utils.py` com funcoes tipo `play_sound()`, `set_autostart()`, etc.
- Cada funcao checa o OS e usa a implementacao correta
- Criar build script separado para Mac (py2app ou PyInstaller Mac)

**Arquivos envolvidos:**
- `main.py` (winsound import)
- `message_bubble.py` (winsound import)
- `settings_ui.py` (winreg import, startup functions)
- `build_installer.py` / `installer.iss` (Windows-only build)

---

## Issue #3: Disponibilizar na Steam
**Status:** PENDENTE
**Prioridade:** Baixa (feature futura, depende de #2 parcialmente)

**Problema:**
Preparar o app para distribuicao via Steam.

**O que seria necessario:**
1. **Conta Steamworks** - Registro como desenvolvedor ($100 taxa unica)
2. **Steam App ID** - Registrar o app na Steam
3. **Steamworks SDK Integration** - Wrapper Python (`steamworks-py` ou similar)
4. **Features Steam:**
   - Achievements (ex: "Hidracao Master - 7 dias seguidos", "Primeiro Litro", etc.)
   - Steam Cloud saves (sincronizar `user_config.json` e `data/`)
   - Steam Overlay compatibilidade
   - Stats/leaderboards (ranking de hidratacao entre amigos)
5. **Assets da Store:**
   - Capsule images (header, hero, etc.)
   - Screenshots
   - Descricao, tags, trailer (opcional)
6. **Review da Steam** - Submeter para aprovacao
7. **Code Signing** - Certificado digital para evitar avisos de seguranca

**Pre-requisitos:**
- Issue #2 resolvida (pelo menos parcialmente, se quiser vender pra Mac tambem)
- Sistema de achievements implementado (ja esta no backlog do DESENVOLVIMENTO.md)

**Estimativa de esforco:** Significativo - envolve burocracia, assets graficos, e integracao tecnica.

---

## Issue #4: Bugs no seletor de imagem do mascote
**Status:** PENDENTE
**Prioridade:** Media

**Problema:**
O seletor de mascote nas Settings tem comportamentos bugados.

**Bugs identificados na analise do codigo:**

### Bug 4a: Path separator mismatch ao carregar config
Em `_load_values()` (linha 870-874), ao comparar o mascot_file salvo no config com os items do combo:
- `user_config.json` salva com backslash: `"mascots\\bolsonaro...png"`
- `_populate_mascots()` usa `glob.glob("mascots/*.png")` que retorna com forward slash: `"mascots/bolsonaro...png"`
- A comparacao `itemData(i) == mascot_file` **falha** por causa do separador diferente
- **Resultado:** O dropdown nao seleciona o mascote correto ao abrir Settings (mas o preview funciona porque `_update_mascot_preview` usa `os.path.exists` que aceita ambos)

Mesmo bug existe para o seletor de personalidade (linha 862-866).

### Bug 4b: Verificacao fragil de path no browse
Em `_browse_mascot()` (linha 695):
```python
if not filepath.startswith("mascots"):
```
Isso pode falhar se:
- O path absoluto e retornado pelo dialog (ex: `D:\AI-drink-water\mascots\foto.png`)
- O path usa backslashes

### Bug 4c: Nomes de arquivo longos no dropdown
Arquivos com nome muito grande (como o bolsonaro meme com 80+ chars) ficam cortados/ilegíveis no ComboBox.

**Solucao proposta:**
- Normalizar paths com `os.path.normpath()` antes de comparar
- Usar `os.path.abspath()` ou comparar apenas o `basename`
- Truncar nomes longos no display do combo

**Arquivos envolvidos:**
- `settings_ui.py` (funcoes `_populate_mascots`, `_load_values`, `_browse_mascot`)

---

## Issue #5: Botao manual de conexao com Ollama nas Settings
**Status:** PENDENTE
**Prioridade:** Alta (afeta uso diario)

**Problema:**
Quando o PC liga, o Ollama nao abre automaticamente. O Water Intake Tracker inicia, tenta conectar ao Ollama no `__init__` do `AIMessageGenerator` (ai_messages.py linha 24-76), falha, e seta `ollama_available = False`. Depois disso, mesmo que o usuario abra o Ollama manualmente, o app **nunca mais tenta reconectar** - fica sem IA a sessao inteira.

**Comportamento atual:**
1. PC liga -> Water Intake Tracker inicia -> Ollama nao esta rodando ainda
2. `AIMessageGenerator.__init__()` tenta `ollama.list()` -> falha -> `ollama_available = False`
3. App roda o dia inteiro usando mensagens de fallback (pre-escritas)
4. Mesmo que o usuario abra o Ollama depois, o app nao reconecta

**Solucao proposta:**
- Adicionar botao "Conectar com Ollama" na aba "Mascote & IA" das Settings
- Ao clicar, tenta conectar com `ollama.list()`
- Feedback visual claro:
  - Sucesso: "Conectado! Modelo X disponivel" (verde)
  - Erro: "Ollama nao esta rodando. Abra o Ollama e tente novamente." (vermelho)
  - Erro: "Biblioteca ollama nao instalada." (vermelho)
- Se conectar com sucesso, atualiza `ollama_available = True` na instancia do `AIMessageGenerator`
- Bonus: tentar reconectar automaticamente a cada X minutos em background

**Arquivos envolvidos:**
- `settings_ui.py` (adicionar botao e logica de teste de conexao)
- `ai_messages.py` (expor metodo `try_reconnect()` ou similar)
- `main.py` (passar referencia do AIMessageGenerator para o Settings)

---

## Ordem sugerida de ataque

| # | Issue | Justificativa |
|---|-------|---------------|
| 1 | **#1 - Dupla instancia** | Bug critico, afeta todo dia |
| 2 | **#5 - Botao Ollama** | QoL importante, afeta uso diario da IA |
| 3 | **#4 - Bugs mascote** | Bugs de UI irritantes |
| 4 | **#2 - Mac support** | Feature grande, planejamento |
| 5 | **#3 - Steam** | Mais distante, depende de outras |

---

*Atualizar este arquivo conforme formos resolvendo cada issue.*
