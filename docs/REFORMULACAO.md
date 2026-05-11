# Reformulação 2026-05 — Limpeza + Sticky Notes

**Branch:** `refactor/cleanup-and-sticky-notes`
**Sessão:** 2026-05-01 (planejamento)
**Status:** Em planejamento — execução nas próximas sessões

## Por que

App está em uso diário, mas três coisas estavam atrapalhando o foco do Henrique:

1. **Mascote + IA** — mensagens repetitivas e sem noção; pop-up + som tirando concentração.
2. **Webcam para detectar gole** — aluga a câmera, falha com frequência, exige posicionamento. Mais atrito do que valor.
3. **Sub-barra vermelha de lembrete** — ruído visual constante, desnecessária quando o registro vira manual.

Ao mesmo tempo, falta uma feature que ele realmente usaria: **sticky notes priorizados por urgência e prazo**, sempre visíveis ao lado da barra de água.

## O que esta sessão entrega (planejamento)

- Branch criada
- Investigação completa de viabilidade (Windows AppBar, arquitetura, UX)
- Este documento com decisões e task list
- Registro no brain repo

A **execução** (código) acontece nas próximas sessões, fase por fase.

---

## Decisões consolidadas (síntese do council multi-agente)

### Arquitetura

- **Refactor em duas fases**, não tudo num único PR. Fase 1 = purga. Fase 2 = sticky notes.
- **Notas EMBUTIDAS na barra**, não em janela separada (decisão Henrique 2026-05-01). Estado padrão = colapsado/discreto; **hover na coluna abre** para ver detalhes. Filosofia: o que matou o app antes foi pop-up interruptivo; embutido + hover é minimalista, fica fora do caminho até você precisar. Se a hipótese não validar com uso real, descartamos e testamos janela separada.
- **JSON separado** (`data/notes.json`) para notas — ciclo de vida diferente do progresso diário (notas não resetam à meia-noite).
- **Não inventar SQLite, event bus, ou abstração de storage** — JSON simples + signal/slot Qt já bastam.

### UX — Botão de gole (microinteração com dopamina)

1. Ripple radial 250ms a partir do clique (`QGraphicsDropShadowEffect` animado)
2. Onda de água sobe com `QEasingCurve.OutBack` (overshoot 8%)
3. 5–8 bolhas sobem com trajetória senoidal por 600ms
4. Som "plop" curto (~80ms, `QSoundEffect`) — som de matéria, não de UI
5. Streak counter pulsa ao bater meta diária; 3 dias seguidos = glow dourado sutil

### UX — Sticky Notes

**3 níveis de prioridade confirmados** (Henrique 2026-05-01) — descarta P0–P5 do esboço original. Razão: 6 níveis paralisam decisão pessoal e na prática vira tudo P3.

- **Agora** — `#E74C3C` (vermelho)
- **Hoje** — `#F39C12` (amarelo)
- **Depois** — `#95A5A6` (cinza)

**Layout (embutido na barra de água):**
- Indicador = borda esquerda 4px. Fundo sempre amarelo sticky `#FFF4A3`.
- **Estado padrão = colapsado** (36px, só título truncado + borda colorida).
- **Hover na coluna inteira expande** os cards para 90px revelando deadline e botão "✓ feito". Mouse sai = volta a colapsar suavemente.
- **Máximo 3 cards visíveis**, restantes em chip "+N" clicável que expande.
- **Reordenação animada**: `QPropertyAnimation` em `pos()`, `InOutCubic`, 350ms. Saída → entrada (sequencial).
- **Criação inline** (botão "+" no rodapé empurra cards pra baixo). Sem modal pra criar.
- Badge de deadline só aparece se `< 24h`.

### Windows AppBar — viabilidade

**Veredito:** viável. Win32 `SHAppBarMessage` (shell32.dll) acessível via `ctypes` direto do `winId()` do PyQt5.

- Sequência canônica: `ABM_NEW` → `ABM_QUERYPOS` → `ABM_SETPOS`.
- Notificações via `nativeEvent()` — tratar `ABN_POSCHANGED`, `ABN_FULLSCREENAPP`, `ABN_STATECHANGE`.
- `ABM_REMOVE` obrigatório no `closeEvent` (senão o espaço fica reservado até logoff).
- **Não usar** `SPI_SETWORKAREA` — Windows 10/11 sobrescreve.
- Edge cases conhecidos: multi-monitor (registrar por monitor), DPI awareness (manifesto Per-Monitor V2), fullscreen exclusivo (mover para `HWND_BOTTOM`), borderless fake-fullscreen (não dispara `ABN_FULLSCREENAPP`).

**Decisão:** investigação OK, **não implementar nesta reformulação**. Vira sessão dedicada própria depois que sticky notes estiverem rodando.

### O que NÃO mexer

- Padrão Qt Signal/Slot do `main.py`
- Animação de água da `ui.py` (coração visual)
- System tray e ciclo de vida do `QApplication`
- `storage.py` JSON simples para o progresso diário

---

## Task list (sem estimativas)

### Fase 1 — Webcam → botão manual (caminho crítico)

- [ ] Adicionar botão de "+1 gole" na `ProgressBarOverlay` (clique registra gole via `storage.add_gulp()`)
- [ ] Implementar microinteração do botão: ripple, overshoot na onda, bolhas, som plop
- [ ] Remover `DetectorThread`, `create_detector()`, `_on_gulp_detected` ligado à webcam, `_on_detector_error`
- [ ] Remover `meeting_detection` (auto-pause de webcam não faz mais sentido)
- [ ] Remover `_on_calibration_event` e qualquer hook do "easter egg" do detector
- [ ] Smoke test: app abre, botão funciona, gole persiste, abrir/fechar mantém estado

### Fase 2 — Purga de IA, mascote, sub-barra de lembrete

- [ ] Deletar `detector.py`
- [ ] Deletar `vision_detector.py`
- [ ] Deletar `ai_messages.py`
- [ ] Deletar `message_bubble.py`
- [ ] Deletar pasta `personalities/`
- [ ] Deletar pasta `mascots/`
- [ ] Deletar pasta `models/`
- [ ] Deletar `test_ai_system.py` e `test_vision.py`
- [ ] Avaliar pasta `sounds/` — manter só os sons que ainda serão usados (plop, gulp, milestone). Deletar celebration/funny/reminder/achievement se não houver uso planejado.
- [ ] Deletar arquivos de geração não mais usados: `generate_mascots.py`, `generate_pop_sound.py`, `generate_sound.py`, `generate_sounds.py`
- [ ] `main.py`: remover `_init_ai_messages`, `_show_ai_message`, `_on_message_timer`, `_init_meeting_detection`, `_check_meeting_processes`, `_on_meeting_started`, `_on_meeting_ended`, todos os imports de AI/mascote/meeting
- [ ] `ui.py`: remover `_draw_reminder_bar`, `_get_reminder_color`, `_get_reminder_percentage`, `last_gulp_time`, `reminder_interval`, `reminder_bar_width`. Ajustar `_setup_geometry` para não reservar espaço da reminder bar.
- [ ] `settings_ui.py`: remover tabs "Detection", "Reminder", "Mascote & IA". Manter "General" + "Help" (atualizar tutorial). Adicionar tab nova "Notes" se necessário.
- [ ] `config.py`: remover todas as chaves de detector/vision/ollama/mascote/AI/calibration/meeting/reminder. Manter `goal_ml`, `ml_per_gulp`, `bar_position`, `bar_width`, `bar_margin`, `hover_opacity`, `sound_enabled`, `data_dir`, `progress_file`, `gulp_sound`.
- [ ] `requirements.txt`: remover `mediapipe`, `opencv-python`, `ollama`. Avaliar `Pillow` (só ainda necessário para `convert_icon` no build).
- [ ] `WaterIntakeTracker.spec`: remover `collect_data_files('mediapipe')`, hidden imports mortos, datas de `mascots/personalities/models`.
- [ ] `installer.iss`: remover linhas `Source: "mascots/*"`, `personalities/*`, `models/*`.
- [ ] `build_exe.py` e `build_installer.py`: limpar referências mortas.
- [ ] Smoke test pós-purga: app ainda abre, barra ainda aparece, botão funciona, persistência intacta. .exe builda. Tamanho deve cair drasticamente (~400MB → ~60MB esperado).

### Fase 3 — Sticky Notes (MVP)

- [ ] Criar `notes.py`:
  - `@dataclass Note` com campos: `id` (uuid4 str), `title`, `body`, `priority` (`Literal["now", "today", "later"]`), `deadline` (ISO 8601 ou `None`), `created_at`, `completed_at` (`None` = aberta)
  - `class NotesStore` com: `load()`, `save()`, `add(note)`, `update(id, **fields)`, `delete(id)`, `complete(id)`, `list_active()` (sorted por prioridade `now < today < later` → deadline asc → created_at asc)
  - Persistência em `data/notes.json` (separado de `progress.json`, sem reset diário)
- [ ] Criar `notes_ui.py`:
  - `NotesColumn(QWidget)` — coluna lateral embutida ao lado da barra de água. Detecta hover (`enterEvent`/`leaveEvent`) e propaga para os cards. Anima reordenação.
  - `NoteCard(QWidget)` — card colapsado (36px) ↔ expandido (90px) com `QPropertyAnimation` de altura. Borda esquerda colorida por prioridade. Badge de deadline `<24h`.
  - `NoteEditDialog(QDialog)` — criação/edição (title, body, priority radio, deadline picker)
  - Botão "+" no rodapé com criação inline
- [ ] Integrar `NotesColumn` à `ProgressBarOverlay`: largura total da janela cresce para acomodar coluna ao lado da barra de água. Ajustar `_setup_geometry`. Coluna pode ser togglada via menu de contexto.
- [ ] `storage.py` ou novo `notes_storage.py`: NUNCA aplicar lógica de "reset diário" às notas
- [ ] Smoke test: criar 3 notas com prioridades diferentes, verificar ordenação. Marcar uma como completa, verificar que sai da lista. Fechar e reabrir, verificar persistência.

### Fase 4 — Validação final

- [ ] Uso real por pelo menos 1 dia inteiro antes de mergear na `main`
- [ ] Conferir que nenhum import morto sobrou (`grep -r "mediapipe\|ollama\|mascot\|message_bubble"` retorna vazio)
- [ ] Atualizar `docs/DESENVOLVIMENTO.md` com a reformulação (log entry novo)
- [ ] Atualizar `README.md` removendo menções a webcam/IA/mascote
- [ ] Bumpar versão no `installer.iss` (1.0.0 → 2.0.0 — quebra de paradigma)

---

## Critério "pronto" (definition of done desta reformulação)

- App abre sem webcam, sem Ollama, sem mascote
- Botão de gole funciona e é prazeroso de clicar
- Sticky notes: criar + listar ordenado + marcar como completa + persistir entre sessões
- Edit inline e drag-and-drop = TODO conhecido (não bloqueia merge)
- .exe builda com tamanho reduzido
- Henrique usou por 1+ dia sem quebrar

## TODOs conscientemente adiados

- **Edit inline de notas** — botão de edit abre `NoteEditDialog`; edit direto no card vira fase 5
- **Drag-and-drop** para reordenação manual — auto-ordenação por prioridade + deadline já cobre o uso
- **Notificação de prazo** quando deadline `<24h` se aproxima
- **Recurring notes** (semanal, mensal)
- **Migração da câmera para botão para usuários antigos** — `user_config.json` antigo continua sendo lido, chaves mortas serão ignoradas

---

## Backlog próximas sessões (após esta reformulação)

Ordem sugerida pelo council:

1. **CI/CD do .exe** — GitHub Actions que builda + zipa o `WaterIntakeTracker.exe` ao push de tag `v*`. Investimento de infra que paga juros compostos: toda mudança futura testada no .exe real sem rodar `build_installer.py` na mão.
2. **Bug do tray icon não aparecer** ao lado do relógio — impacta uso diário, mas só vale arrumar com .exe builds rápidos disponíveis.
3. **Reformular menu inteiro** — cosmético, vem por último, depende de iteração rápida (que a CI/CD habilita).
4. **Windows AppBar** — investigação completa, snippet pronto, vira sessão dedicada com smoke test em multi-monitor.

---

## Referências

- [Microsoft Learn — Application Desktop Toolbars](https://learn.microsoft.com/en-us/windows/win32/shell/application-desktop-toolbars)
- [SHAppBarMessage function](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shappbarmessage)
- Council multi-agente desta sessão: arquitetos (kill-it-with-fire vs cuidado-com-escopo), UX (cético + encantador + pragmático visual), product strategist
