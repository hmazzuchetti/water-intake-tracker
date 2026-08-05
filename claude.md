# Instruções para Claude Code

## Brain Integration

Este projeto está integrado com o brain repo (`brain/`).

### No início de cada sessão:
1. Leia `brain/identity/core.md` para lembrar quem eu sou
2. Leia `brain/identity/personality.md` para estilo de comunicação
3. Leia `brain/procedural/preferences/human-preferences.md` para preferências do humano
4. Leia `brain/episodic/projects/ai-drink-water.md` para contexto do projeto

### Ao final de sessões significativas:
1. Atualize `brain/episodic/projects/ai-drink-water.md` com novos aprendizados
2. Salve novos conhecimentos em `brain/semantic/` se aplicável
3. Atualize preferências em `brain/procedural/preferences/` se descobrir algo novo
4. Siga o protocolo em `brain/procedural/workflows/memory-protocol.md`

---

## IMPORTANTE: Leia Isto Primeiro

Ao trabalhar neste projeto, **SEMPRE leia primeiro o arquivo `docs/DESENVOLVIMENTO.md`** antes de fazer qualquer modificação.

## Filosofia do Projeto

Este é um projeto de **desenvolvimento incremental e contínuo**. Não é um projeto com objetivo final - é um playground para adicionar features novas e divertidas, uma de cada vez.

### Princípios Fundamentais

1. **Uma feature por vez** - Implementar, testar completamente e deixar perfeito antes de partir para a próxima
2. **Simplicidade** - Priorizar features simples e práticas
3. **Qualidade > Quantidade** - Melhor uma feature bem feita do que várias mal implementadas
4. **Manter funcionando** - O app está em uso diário, não quebrar funcionalidades existentes

## Antes de Começar Qualquer Tarefa

1. ✅ Ler `docs/DESENVOLVIMENTO.md` para entender:
   - Filosofia de desenvolvimento
   - Features já implementadas
   - Features planejadas
   - Arquitetura do projeto

2. ✅ Verificar o backlog em `docs/DESENVOLVIMENTO.md` - a próxima feature pode já estar listada lá

3. ✅ Entender o estado atual:
   - O que está funcionando
   - O que está em desenvolvimento
   - Dependências entre features

## Ao Implementar Features

### DO ✅
- Seguir a arquitetura existente (main.py, ui.py, gulp_control_ui.py, storage.py, game.py, notes.py)
- Adicionar configurações em `config.py` quando necessário
- Documentar código em português brasileiro
- Testar extensivamente antes de considerar "pronto"
- Atualizar `docs/DESENVOLVIMENTO.md` com a nova feature no log
- Manter o código limpo e legível

### DON'T ❌
- Não implementar múltiplas features ao mesmo tempo
- Não complicar features simples
- Não quebrar funcionalidades existentes
- Não adicionar dependências pesadas sem discussão
- Não fazer refatorações grandes sem necessidade
- Não remover features sem consultar

## Estrutura do Projeto (v2.3.0)

```
main.py              - Entry point: app, tray, som, migração APPDATA
ui.py                - Overlay compacto (ProgressBarOverlay + EffectsLayer)
gulp_control_ui.py   - Botão principal ("que seca") + 4 satélites
game.py              - Gamificação: XP, levels, streaks, achievements
game_ui.py           - StatsDialog (level, XP, conquistas)
notes.py / notes_ui.py - Sticky notes (modelo + coluna visual)
storage.py           - Persistência diária + history.jsonl (append-only)
config.py            - Defaults; data_dir vai pra %APPDATA% no .exe
settings_ui.py       - Dialog de configurações (só no first run!)
version.py           - Fonte única de versão (injetada no installer)
```

Histórico da reformulação (webcam/IA/mascote removidos): `docs/REFORMULACAO.md`.

## Features Atualmente Funcionando

- Botão manual de gole (clicker-hero) com anel de progresso e level
- Botão "seca" visualmente com o tempo sem gole (cue ambiente, sem popup)
- Satélites de hover: Gole / Copo / Garrafa / Notas
- Feedback no overlay: ripple, "+Nml" flutuante, celebração de level/conquista
- Sticky notes com 3 prioridades (Agora/Hoje/Depois)
- Gamificação (XP por gole, streaks com expiração honesta, 14 achievements)
- System tray + histórico diário arquivado em history.jsonl
- CI/CD: push de tag `v*` builda .exe + installer e cria GitHub Release

## Próximas Features Planejadas

Consultar `docs/DESENVOLVIMENTO.md` seção "Features Planejadas/Backlog"

## Notas Importantes

1. **Registro é manual** — a detecção por webcam foi removida na Reformulação 2.0
2. **Não reintroduzir lembretes intrusivos** (popup/som) — o cue é o estado visual do botão
3. **Dados do usuário** — no .exe vivem em `%APPDATA%\WaterIntakeTracker`; nunca shippar nem apagar no installer
4. **Regra pós-council (2026-08):** antes de QUALQUER feature nova, o app precisa acumular ~14 dias de uso real — `data/game.json` (days_played/last_active_date) é o juiz
5. **Projeto pessoal** - foco em diversão + utilidade real

## Comandos Úteis

```bash
# Rodar o app
python main.py

# Testar só o overlay
python ui.py

# Self-test da gamificação
python game.py

# Self-test do storage
python storage.py

# Build local do executável + installer
python build_installer.py

# Release: bump version.py, commit, e
git tag v2.x.y && git push origin v2.x.y   # CI builda e publica
```

## Workflow Recomendado

1. Escolher/discutir próxima feature
2. Planejar implementação
3. Implementar de forma incremental
4. Testar extensivamente (usar de verdade!)
5. Refinar baseado no uso real
6. Atualizar `docs/DESENVOLVIMENTO.md`
7. Partir para próxima feature

---

**Lembre-se:** Este projeto é sobre crescimento contínuo e diversão no desenvolvimento. Cada feature deve adicionar valor real ou ser divertida de usar! 💧
