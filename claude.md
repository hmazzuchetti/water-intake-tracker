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
- Seguir a arquitetura existente (main.py, detector.py, ui.py, storage.py)
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

## Estrutura do Projeto

```
main.py              - Entry point, coordena tudo
detector.py          - Detecção via MediaPipe (mãos + face + objetos)
ui.py                - Barra de progresso visual animada
storage.py           - Persistência de dados (JSON)
config.py            - Configurações padrão
settings_ui.py       - Interface de settings
user_config.json     - Config do usuário (não versionar mudanças)
```

## Features Atualmente Funcionando

- Detecção de bebida com garrafa (funciona muito bem!)
- Barra de progresso com água animada
- Sistema de lembretes visual
- Detecção de ausência (away mode)
- Configurações ajustáveis
- Sons e feedback visual
- Histórico diário

## Próximas Features Planejadas

Consultar `docs/DESENVOLVIMENTO.md` seção "Features Planejadas/Backlog"

## Notas Importantes

1. **Detecção funciona melhor com garrafa** - copos não funcionam tão bem, e está OK assim
2. **Garrafa de 500ml é o ideal** - força movimento mas não excessivamente
3. **App em uso diário** - qualquer mudança precisa ser estável
4. **Projeto pessoal** - foco em diversão + utilidade real

## Comandos Úteis

```bash
# Rodar o app
python main.py

# Testar só a detecção (com visualização debug)
python detector.py

# Testar só a UI
python ui.py

# Build do executável
python build_exe.py
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
