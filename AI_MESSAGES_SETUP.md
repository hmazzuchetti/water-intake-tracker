# Setup: Sistema de Mensagens com IA

## Visão Geral

O app agora possui um sistema de mensagens aleatórias e contextuais que aparecem durante o dia de trabalho!

**Features:**
- 💬 Mensagens geradas por IA local (Ollama) ou fallback para mensagens pré-escritas
- 🎯 Contextualizadas com seu progresso de hidratação
- ⏰ Aparecem aleatoriamente e em milestones (50%, 100%)
- 🎨 Balão de texto simples e elegante
- 🔧 Personalizável via arquivo de texto

## Instalação

### 1. Instalar Dependências

```bash
pip install ollama
```

### 2. (Opcional) Instalar Ollama

Se quiser usar IA para gerar mensagens:

**Windows:**
1. Baixe Ollama: https://ollama.com/download
2. Instale o executável
3. Abra um terminal e rode:
   ```bash
   ollama pull llama3.2:1b
   ```
   (Este é um modelo leve de ~1GB, perfeito para gerar frases curtas)

**Se não instalar Ollama:**
- O app vai funcionar normalmente!
- Vai usar mensagens pré-escritas divertidas (fallback)
- Sem problemas, ambos funcionam bem

## Como Funciona

### Quando as mensagens aparecem:

1. **Aleatoriamente** - A cada X minutos (configurável, padrão: 45 min)
2. **Nos milestones** - Ao atingir 50% e 100% da meta
3. **Nunca quando você está away** - Respeita seu modo ausente

### Personalização

Edite o arquivo: `personalities/default.txt`

Esse arquivo contém as instruções para a IA sobre:
- Tom das mensagens (sarcástico, encorajador, etc)
- Tamanho das mensagens
- Tipos de conteúdo (curiosidades, piadas, etc)
- Contexto que ela tem disponível

Exemplo de personalidade customizada:

```
Você é um personal trainer de hidratação super motivado.

ESTILO:
- Seja extremamente encorajador e energético
- Use CAPS e emojis de fogo 🔥
- Trate o usuário como "campeão" ou "fera"
- Seja breve mas impactante

EXEMPLOS:
- "ISSO AÍ CAMPEÃO! Mais água nesse corpo! 🔥"
- "VOCÊ É IMPARÁVEL! Continue assim fera! 💪💧"
```

## Configurações

No arquivo `config.py` ou via menu de configurações:

```python
"ai_messages_enabled": True,           # Ligar/desligar mensagens
"ai_message_interval_minutes": 45,    # Intervalo entre mensagens aleatórias
"ai_message_duration_seconds": 8,     # Quanto tempo mostrar cada mensagem
"ai_personality_file": "personalities/default.txt",
```

## Testando

### 1. Testar Gerador de Mensagens:

```bash
python ai_messages.py
```

Isso vai:
- Detectar se Ollama está disponível
- Testar vários cenários (início do dia, progresso médio, meta batida, etc)
- Mostrar as mensagens geradas

### 2. Testar Balão Visual:

```bash
python message_bubble.py
```

Isso vai:
- Mostrar uma sequência de balões de teste
- Você pode clicar no balão para fechá-lo manualmente
- Testa animações de fade in/out

### 3. Testar Integrado:

```bash
python main.py
```

Use o app normalmente. Mensagens vão aparecer:
- Quando você atingir 50% da meta
- Quando você atingir 100% da meta
- Aleatoriamente a cada 45 minutos

## Arquitetura

```
ai_messages.py        - Gerador de mensagens (Ollama + fallback)
message_bubble.py     - Widget visual do balão flutuante
personalities/        - Arquivos de personalidade da IA
  └── default.txt     - Personalidade padrão
```

## Próximos Passos

Essa é a base funcional! Próximas features planejadas:

- [ ] Editor de personalidade no menu de configurações
- [ ] Mascote PNG customizável
- [ ] Galeria de mascotes pré-feitos
- [ ] Múltiplas personalidades para escolher
- [ ] Estatísticas de mensagens mais engraçadas

## Troubleshooting

**Mensagem de erro: "Ollama não disponível"**
- Normal! O app vai funcionar com mensagens pré-escritas
- Se quiser usar IA, instale Ollama (veja seção 2 acima)

**Balão não aparece:**
- Verifique se `ai_messages_enabled` está `True`
- Confira se já não tem um balão ativo
- Veja o console para logs `[AI]`

**Mensagens muito longas:**
- Edite `personalities/default.txt`
- Enfatize "seja breve" e "máximo X caracteres"
- O sistema limita automaticamente a 120 caracteres

**Mensagens não contextualizam bem:**
- Verifique se Ollama está rodando: `ollama list`
- Teste com: `python ai_messages.py`
- Ajuste a personalidade para ser mais específica sobre contexto

## Performance

- **Com Ollama:** ~1-2 segundos para gerar cada mensagem (local, privado)
- **Sem Ollama:** Instantâneo (pega de pool pré-escrito)
- **Memória:** +~30MB com Ollama carregado
- **CPU:** Mínimo, gera mensagens raramente

---

Divirta-se com as mensagens! 💧😄
