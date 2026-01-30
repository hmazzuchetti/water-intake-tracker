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

### Próxima Feature
- [ ] (Escolher próxima feature)

### Em Refinamento
- [✅] **System Tray** - COMPLETO!
- [✅] **Sistema de mensagens com IA** - COMPLETO!
  - ✅ Mensagens geradas por Ollama ou fallback
  - ✅ Balão de texto flutuante com mascote
  - ✅ Personalidade configurável
  - ✅ Contexto de progresso
  - ✅ Editor de personalidade no menu de configurações
  - ✅ Galeria de mascotes pré-prontos (7 mascotes)
  - ✅ 6 personalidades diferentes
  - ✅ Sons diferentes por tipo de mensagem

### Ideias para o Futuro
- [ ] **Histórico visual** - Gráfico dos últimos 7 dias de consumo
- [ ] **Notificações de milestone** - Alertas do Windows ao atingir 25%, 50%, 75%, 100% da meta
- [ ] **Sons customizáveis** - Diferentes sons para diferentes conquistas
- [ ] **Estatísticas** - Resumo semanal/mensal de consumo
- [ ] **Ajuste de meta inteligente** - Sugerir beber mais em dias quentes (integração com API de clima)
- [ ] **Temas visuais** - Modo escuro/claro, cores customizáveis para a água
- [ ] **Sistema de conquistas** - Gamificação com badges e streaks
- [ ] **Exportar dados** - Salvar histórico em CSV para análise
- [ ] **Estatísticas detalhadas** - Horários de pico, padrões de consumo
- [ ] **Meta adaptativa** - Ajustar meta baseado em peso/altura/atividade física
- [ ] **Integração com wearables** - Conectar com apps de saúde

## Log de Desenvolvimento

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
