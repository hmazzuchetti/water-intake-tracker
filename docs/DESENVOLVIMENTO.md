# Filosofia de Desenvolvimento - AI Drink Water

## Visão Geral

Este projeto é um aplicativo pessoal de hidratação que usa visão computacional para detectar quando você toma água. O objetivo é **crescimento contínuo e incremental**, sempre adicionando features novas de forma divertida e funcional.

## Princípios

### 1. Desenvolvimento Incremental
- **Uma feature de cada vez** - Implementar, testar e deixar redondo antes de partir para a próxima
- **Simplicidade primeiro** - Priorizar features simples e práticas sobre complexidade
- **Testes reais** - Usar o app diariamente para validar cada feature

### 2. Foco na Experiência do Usuário
- Features devem ser **úteis** ou **divertidas**
- Interface deve permanecer **limpa e não intrusiva**
- Cada adição deve melhorar a experiência, não complicar

### 3. Qualidade sobre Quantidade
- Melhor ter poucas features bem feitas do que muitas mal implementadas
- Refinar e polir cada adição
- Manter o código limpo e documentado

## Features Planejadas/Backlog

### GATE (council 2026-08): 14 dias de uso real antes de QUALQUER item abaixo
A v2.1/v2.2 shipou gamificação inteira com 0 dias de uso real — e o bug
do achievement impossível passou 3 meses despercebido porque ninguém
jogava. Regra nova: `data/game.json` (days_played, last_active_date) é o
juiz. Sem ~14 dias de uso genuíno, o backlog fica congelado.

### Depois do gate — priorizado pelo council
- [ ] **Sparkline 7 dias** no StatsDialog (history.jsonl já alimenta)
- [ ] **Streak freeze** estilo Duolingo (1 "gota de gelo" a cada 7 dias de streak, máx 2)
- [ ] **XP proporcional ao volume** (1 XP / 10ml) — mata o exploit de fragmentar registros
- [ ] **Gole dourado** (~10% de chance, 3x XP) — reward variável
- [ ] **Dica de descoberta dos satélites** no primeiro uso (auto-expand 2s)
- [ ] **QSS dark comum** pros 3 dialogs (Stats/Settings/NoteEdit)
- [ ] **Bug do tray icon** não aparecer ao lado do relógio
- [ ] **Registrar refills, não goles** (ideia Brian): clique no momento de encher a garrafa, fora do flow
- [ ] **Windows AppBar** — snippet pronto no [`REFORMULACAO.md`](REFORMULACAO.md)

### Polish sticky notes (TODOs conscientemente adiados na Fase 3)
- [ ] Edit inline (clica no card e edita ali mesmo, sem dialog)
- [ ] Drag-and-drop pra reordenar manualmente
- [ ] Animação de reordenação quando nota muda de prioridade
- [ ] Notificação Windows quando deadline <24h
- [ ] Recurring notes (semanal, mensal)
- [ ] Tela de notas completadas (histórico)

### Ideias para o Futuro
- [ ] **Estatísticas semanal/mensal** — Resumo de consumo
- [ ] **Temas visuais** — Dark/light, cores customizáveis
- [ ] **Exportar dados** — CSV pra análise (history.jsonl já é semi-exportável)
- [ ] **Meta adaptativa** — Ajustar baseado em peso/altura/atividade

## Log de Desenvolvimento

### 2026-08-05 — v2.3.0: Fundação + Cue (pós-council de 5 agentes)
**Status:** ✅ COMPLETO

**Contexto:** council multi-agente (produto, UX, engenharia, gamificação,
advogado do diabo) diagnosticou por que o app parou de ser usado em
13/05: settings modal bloqueante a cada boot, loop de hábito sem gatilho
(a purga 2.0 removeu lembretes E webcam sem substituto), e dados sem
memória histórica.

**Fase 0 — Fundação:**
- ✅ Settings dialog só no first run — startup silencioso (era o assassino nº 1)
- ✅ Fix crítico notes_ui.py: `add_btn` + `refresh()` estavam DENTRO de
  `_on_width_anim_tick` (bug de indentação) — coluna de notas nascia
  vazia e era reconstruída ~17x por hover
- ✅ `storage.get_progress()` sem cap de 100% — achievement "Camelo de
  Volta" (200%) era matematicamente impossível
- ✅ `_ensure_today()` único (eram 5 checks duplicados) + arquivamento
  append-only em `data/history.jsonl` antes do reset diário
- ✅ Dados no .exe migram pra `%APPDATA%\WaterIntakeTracker` (one-shot);
  installer não shippa mais `data/*` nem apaga dados no uninstall;
  spec não embute mais dados pessoais no bundle
- ✅ `git rm --cached data/progress.json` + data/ no .gitignore
- ✅ Streak stale zerada no load (StatsDialog não mente mais)
- ✅ Undo desfaz XP (`revert_gulp`) — farm add→undo fechado
- ✅ Versão única: build_installer.py injeta `/DMyAppVersion` no ISCC

**Fase 1 — Cue ambiente + feedback no lugar certo:**
- ✅ **Botão que seca**: dessatura de azul vivo a cinza-seco entre 45min
  e 2h sem gole (lerp no paintEvent). Sem gole hoje = seco; meta batida
  = vivo o resto do dia. Hover/press mantêm cor viva. Zero popup/som.
- ✅ **EffectsLayer**: camada transparente POR CIMA dos widgets (ripples
  antigos eram pintados atrás do botão — invisíveis). Ripple + texto
  flutuante "+Nml" + celebrações ("Meta batida!", "Nível N!", conquistas)
  escalonadas no próprio overlay. Tray toast virou fallback (overlay
  escondido).
- ✅ Tooltip no botão principal: "700 / 3000 ml — 23%"
- ✅ Help tab reescrito pra UI real (descrevia a barra removida na 2.0)
- ✅ Idioma unificado pt-BR (menu contexto, settings, dialogs)
- ✅ Preview de som ao soltar o slider de volume

**Fase 2 — A prova (agora é com o Henrique):**
14 dias de uso real, zero features novas. O game.json decide o que vem
depois.

---

### 2026-05-11 — Reformulação 2.0 (limpeza + sticky notes)
**Status:** ✅ COMPLETO — branch `refactor/cleanup-and-sticky-notes`

Reformulação iniciada porque o app, após meses de uso diário, estava
atrapalhando mais do que ajudando: mascote + IA quebrando foco com
pop-up + som, webcam falhando e alugando a câmera, sub-barra vermelha
de lembrete poluindo a tela.

Plano e decisões consolidadas em [`REFORMULACAO.md`](REFORMULACAO.md).
Council multi-agente (UX × 3, arquitetura × 2, produto, research) foi
usado pra alinhar decisões antes de tocar em código. Padrão a repetir
em reformulações grandes.

**Commits da branch:**
- `7101529` docs: Plano de reformulação
- `12d9e2f` feat: Fase 1 — botão manual de gole + microinteração
- `87637f4` feat: Fase 2 — purga total de IA, mascote, webcam, lembrete
- `ca0981e` feat: Fase 3 — sticky notes embutidos com hover-expand
- `ecf82bd` fix: polish da Fase 3 — hover-flicker + chip-only collapsed cards

**Diff agregado:** ~5000 linhas deletadas, ~1100 inseridas. Bundle do
.exe deve cair de ~400MB → ~60MB.

**O que entra:**
- Botão "gordo" de gole com microinteração (ripple, splash, bolhas, plop)
- Coluna de sticky notes embutida ao lado da barra, hover-expand
- 3 níveis de prioridade (Agora / Hoje / Depois) em vez de P0–P5
- Persistência separada em `data/notes.json`
- Debounce de 180ms no collapse → fim do flicker quando mouse roça borda

**O que sai:**
- `detector.py`, `vision_detector.py` (MediaPipe + Ollama vision)
- `ai_messages.py`, `message_bubble.py` (IA + mascote)
- `personalities/`, `mascots/`, `models/` (pastas)
- Sons de mascote (mantém só `gulp.wav`)
- Sub-barra vermelha de lembrete
- Tabs Detection/Reminder/Mascote no settings (sobra só General + Help)
- `mediapipe`, `opencv-python`, `ollama` do `requirements.txt`

**Investigação adiada:**
- **Windows AppBar (`SHAppBarMessage`)** — viável via ctypes/PyQt5,
  snippet pronto. Vira sessão dedicada.

**Lição meta-aprendida:**
> "App em uso diário tem feedback honesto que protótipo não tem."

Tudo que foi adicionado entre jan-mar/2026 (mascote/IA/AI Vision) era
tecnicamente impressionante mas o uso real corrigiu — o ciclo "usar →
tirar o que incomoda" é mais saudável que adicionar incremental sem
auditar.

---

### 2026-03-18 - Deteccao por AI Vision (Ollama)
**Status:** ✅ COMPLETO!

**Problema Resolvido:**
- Deteccao MediaPipe falhava com ambiente claro e gerava falsos positivos
- 3 modelos rodando a cada 300ms era pesado (impactava jogos como BF6)
- Heuristicas de gesto (holding pose, upward motion) eram frageis

**Solucao Implementada (AI Vision):**
- ✅ Novo modo de deteccao: envia foto da webcam para modelo de visao (Ollama)
- ✅ Modelo descreve o que ve, codigo checa keywords ("drinking", "sipping", etc)
- ✅ 1 check a cada ~10s vs 3 modelos a cada 300ms - muito mais leve
- ✅ Robusto com iluminacao, menos falso positivo
- ✅ Seletor de modo nas Settings (Classic MediaPipe / AI Vision)
- ✅ Dropdown de modelo de visao (llava, moondream, minicpm-v, etc)
- ✅ Intervalo de analise configuravel
- ✅ Modo classic mantido como fallback
- ✅ Script de debug: `test_vision.py`

**Decisoes:**
- `llava` como modelo padrao (moondream muito fraco, respostas YES/NO nao confiaveis)
- Abordagem "describe + keyword match" em vez de YES/NO direto (modelos pequenos tem vies em respostas binarias)
- Intervalo de 2s no thread mas check real a cada 10s (configurable)

**Arquivos Criados:**
- `vision_detector.py` - VisionGulpDetector (mesma interface que WaterGulpDetector)
- `test_vision.py` - Script de debug standalone

**Arquivos Modificados:**
- `config.py` - detection_mode, ai_vision_model, ai_vision_interval_seconds
- `main.py` - create_detector() escolhe detector por config, intervalo adaptativo
- `settings_ui.py` - Grupo "Modo de Deteccao" no tab Detection

---

### 2026-01-30 - Cache Temporal de Garrafa + System Tray

#### Indicadores de ML + Melhorias na Barra de Lembrete
**Status:** ✅ COMPLETO!

**Indicadores de ML:**
- ✅ Labels rotacionados a cada 500ml na barra de água
- ✅ Formato inteligente: "500", "1k", "1.5k", "2k", etc.
- ✅ Semi-transparentes para não poluir a visualização

**Melhorias na barra de lembrete:**
- ✅ Removido o tremor/shake (era feio)
- ✅ Barras coladas (sem gap entre elas)
- ✅ Título "Lembrete" rotacionado no topo da barra

**Arquivos modificados:**
- `ui.py` - Labels de ML e melhorias visuais
- `config.py` - Removido `reminder_shake_threshold`

---

#### Instalador Profissional (Inno Setup)
**Status:** ✅ COMPLETO!

**O que foi criado:**
- ✅ Script Inno Setup (`installer.iss`) - Instalador profissional Windows
- ✅ Script de build automatizado (`build_installer.py`)
- ✅ Documentação completa (`BUILD_INSTRUCTIONS.md`)

**Funcionalidades do instalador:**
- ✅ Instalação em Program Files (ou AppData se não for admin)
- ✅ Entrada no Menu Iniciar com ícone
- ✅ Ícone opcional na Área de Trabalho
- ✅ Opção de iniciar com o Windows (startup)
- ✅ Desinstalador pelo Painel de Controle
- ✅ Preserva configurações do usuário em atualizações
- ✅ Detecta se o app está rodando antes de instalar/desinstalar
- ✅ Suporte a Português e Inglês

**Como usar:**
```bash
# Instalar Inno Setup primeiro: https://jrsoftware.org/isdl.php
python build_installer.py    # Cria tudo automaticamente
```

**Arquivos criados:**
- `installer.iss` - Script do Inno Setup
- `build_installer.py` - Automatiza todo o processo de build
- `BUILD_INSTRUCTIONS.md` - Documentação detalhada

**Próximos passos (profissionalização futura):**
- [ ] Assinatura de código (Code Signing) para evitar avisos do Windows
- [ ] Auto-updater integrado
- [ ] Preparação para Steam

---

#### Cache Temporal de Garrafa
**Status:** ✅ COMPLETO!

**Problema Resolvido:**
- Quando o usuário virava a garrafa para beber, ela não era mais reconhecida pelo detector
- A garrafa virada não parece uma "bottle" para o modelo de IA
- Isso causava falha na detecção de goles legítimos

**Solução Implementada (Persistence Buffer):**
- ✅ Ao detectar garrafa sendo segurada, salva em "cache" por 5 segundos (configurável)
- ✅ Durante esse período, se detectar gesto de beber, conta como gole válido
- ✅ Também salva a posição da garrafa e verifica se a mão ainda está na região
- ✅ Visualização no modo debug: mostra "CACHE: BOTTLE (Xs)" em amarelo
- ✅ Nova configuração: `bottle_cache_seconds` no config.py

**Por que essa solução:**
- Simples e eficaz
- Não depende de detecção contínua durante o movimento
- Evita falsos positivos (precisa da garrafa + mão na região + gesto)
- Configurável (pode ajustar o tempo conforme necessário)

**Arquivos Modificados:**
- `config.py` - Adicionado `bottle_cache_seconds`
- `detector.py` - Implementado sistema de cache com verificação de região

---

### 2026-01-30 - System Tray (App "de verdade")
**Status:** ✅ COMPLETO!

**Problema Resolvido:**
- App não aparecia na barra de tarefas nem na bandeja do sistema
- Não parecia um "programa de verdade" do Windows
- Erro ao iniciar com Windows (PermissionError no diretório personalities)

**System Tray Implementado:**
- ✅ Ícone na bandeja do sistema (ao lado do relógio)
- ✅ Tooltip com status atual (copos, ml, % da meta)
- ✅ Menu de contexto com:
  - Status atual (copos e %)
  - Pausar/Continuar detecção
  - Esconder/Mostrar barra de progresso
  - Abrir Configurações
  - Sair
- ✅ Clique simples: mostra/esconde a barra
- ✅ Duplo clique: abre configurações
- ✅ Notificação ao iniciar mostrando progresso
- ✅ App continua rodando mesmo com janelas fechadas

**Correção de Bug:**
- ✅ Corrigido erro de inicialização com Windows (os.chdir para diretório do app)

**Arquivos Modificados:**
- `main.py` - Adicionado QSystemTrayIcon com menu e interações

**Próximos Passos (Profissionalização):**
- [ ] Instalador com Inno Setup
- [ ] Entrada no Menu Iniciar
- [ ] Desinstalador pelo Painel de Controle
- [ ] Preparação para Steam (futuro)

---

### 2026-01-28 - Finalização do Sistema de Mascote e IA
**Status:** ✅ COMPLETO!

**Editor de Personalidade:**
- ✅ Nova aba "Mascote & IA" no menu de configurações
- ✅ Editor de texto para personalidade
- ✅ Seletor de personalidade existente
- ✅ Criar novas personalidades pelo menu
- ✅ Configuração de modelo Ollama
- ✅ Toggle de mascote on/off
- ✅ Seletor visual de mascote
- ✅ Preview do mascote

**Galeria de Mascotes:**
- ✅ 7 mascotes pré-prontos disponíveis:
  - gotinha.png - Gotinha d'água fofa
  - sapo.png - Sapo simpático
  - robo.png - Robô amigável
  - sol.png - Sol feliz
  - nuvem.png - Nuvem fofa
  - cacto.png - Cacto com flor
  - default.png - Mascote original

**Personalidades Pré-prontas:**
- ✅ 6 personalidades diferentes:
  - default.txt - Sarcástico e provocativo (original)
  - amigavel.txt - Gentil e carinhoso
  - coach.txt - Personal trainer motivador
  - cientifico.txt - Curiosidades científicas
  - zen.txt - Calmo e filosófico
  - gamer.txt - Linguagem de games

**Sons por Tipo de Mensagem:**
- ✅ Sistema de tipos de mensagem (celebration, achievement, reminder, normal, funny)
- ✅ 7 sons diferentes:
  - pop.wav - Aparição do mascote
  - celebration.wav - Meta atingida (fanfarra)
  - achievement.wav - Conquistas/milestones
  - reminder.wav - Lembrete suave
  - water_drop.wav - Som de gota
  - funny.wav - Som engraçado (boing)
  - gulp.wav - Detecção de gole

**Arquivos Criados:**
- `generate_mascots.py` - Gerador de mascotes PNG
- `generate_sounds.py` - Gerador de sons WAV
- `personalities/amigavel.txt`
- `personalities/coach.txt`
- `personalities/cientifico.txt`
- `personalities/zen.txt`
- `personalities/gamer.txt`
- `mascots/gotinha.png`, `sapo.png`, `robo.png`, `sol.png`, `nuvem.png`, `cacto.png`
- `sounds/celebration.wav`, `reminder.wav`, `achievement.wav`, `water_drop.wav`, `funny.wav`

---

### 2026-01-27 (Tarde) - Sistema de Mensagens com IA + Mascote Animado
**Status:** ✅ COMPLETO e funcional!

**Novo Sistema de Mensagens:**
- ✅ Gerador de mensagens com Ollama (IA local) + fallback para mensagens pré-escritas
- ✅ Balão de texto flutuante elegante com animações
- ✅ Mensagens contextualizadas (progresso, tempo desde última bebida)
- ✅ Personalidade configurável via arquivo de texto
- ✅ Funciona COM ou SEM Ollama instalado
- ✅ Mensagens aparecem em milestones (50%, 100%) e aleatoriamente
- ✅ Respeita modo "away" (não mostra quando ausente)
- ✅ Modelos de IA trocáveis facilmente

**Mascote Animado:**
- ✅ Suporte para PNG customizável (até 200x200px)
- ✅ Animação de slide in/out (desliza da tela)
- ✅ Som de "pop" ao aparecer
- ✅ Ponteiro do balão aponta para o mascote
- ✅ Efeito bouncy (OutBack) na entrada

**Melhorias Técnicas:**
- ✅ Threshold de detecção de garrafa reduzido (30% → 25%) - reconhece melhor
- ✅ Parsing correto dos modelos do Ollama
- ✅ Configuração de modelo via config.py
- ✅ **Sistema de sensibilidade configurável** ("easy", "medium", "strict")
- ✅ Proximity threshold aumentado (0.15 → 0.20) - mão pode estar mais longe
- ✅ Frames para confirmar reduzido (2 → 1) - detecção mais rápida
- ✅ Modo "easy": apenas 2 de 4 critérios necessários (muito mais fácil!)

**Arquivos Criados:**
- `ai_messages.py` - Sistema de geração de mensagens
- `message_bubble.py` - Widget visual do balão com mascote
- `generate_pop_sound.py` - Gerador do som de "pop"
- `personalities/default.txt` - Personalidade padrão da IA
- `mascots/README.md` - Guia para adicionar mascotes
- `sounds/pop.wav` - Som de aparição do mascote
- `AI_MESSAGES_SETUP.md` - Documentação completa de setup
- `TROCAR_MODELO_IA.md` - Como trocar modelos do Ollama
- `AJUSTAR_DETECCAO.md` - Guia completo para ajustar sensibilidade

**Próximos Passos Dessa Feature:**
- ✅ Editor de personalidade no menu de configurações
- ✅ Galeria de mascotes pré-prontos
- ✅ Mais personalidades pré-prontas
- ✅ Sons diferentes por tipo de mensagem

**Feature COMPLETA!** Sistema de mascote totalmente funcional.

### 2026-01-27 (Manhã) - Estrutura Atual
**Status:** Funcional e em uso diário

**Features Implementadas:**
- ✅ Detecção de bebida usando MediaPipe (mãos + face + objetos)
- ✅ Detecção específica de garrafa d'água (funciona muito melhor que copos)
- ✅ Barra de progresso visual com animação de água
- ✅ Sistema de lembretes com barra gradiente (verde → amarelo → laranja → vermelho)
- ✅ Detecção de ausência (pausa quando usuário não está presente)
- ✅ Configurações ajustáveis (câmera, meta diária, mão preferida, etc)
- ✅ Som ao detectar bebida
- ✅ Histórico diário de gulps com timestamps
- ✅ Opacidade reduzida ao passar mouse (hover)
- ✅ Menu de contexto (adicionar/remover gulps manualmente, reset, etc)
- ✅ Undo de última detecção (duplo clique)
- ✅ Persistência de dados diária

**Tecnologias:**
- Python 3.x
- PyQt5 (interface gráfica)
- MediaPipe (detecção de mãos, rosto e objetos)
- OpenCV (processamento de imagem)
- JSON (armazenamento de dados)

**Arquitetura:**
```
main.py           - Aplicação principal, coordena componentes
detector.py       - Detecção de gestos e garrafa (MediaPipe + OpenCV)
ui.py             - Interface visual (barra de progresso com água animada)
storage.py        - Persistência de dados diários
config.py         - Configurações padrão
settings_ui.py    - Interface de configurações
user_config.json  - Configurações do usuário
```

---

## Como Contribuir (Futuro)

Quando o projeto for público, este será o guia:

1. **Escolha uma feature** do backlog ou sugira uma nova
2. **Discuta a ideia** antes de implementar
3. **Mantenha o código simples** e bem comentado
4. **Teste extensivamente** antes de submeter
5. **Uma feature por PR** - não misture múltiplas mudanças

---

## Notas

- Este é um projeto pessoal que está ajudando no dia a dia
- O foco é **funcionalidade real** e **diversão** no desenvolvimento
- Garrafa de 500ml é o formato ideal (evita ter que levantar muito, mas força movimento)
- A detecção funciona muito bem com garrafas, menos com copos (e está tudo bem!)
