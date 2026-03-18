# Como Trocar o Modelo de IA

## Modelos Disponíveis no Seu Sistema:

Para ver quais modelos você tem instalados:

```bash
ollama list
```

Resultado no seu caso:
```
llama3.2:1b    - Modelo leve (1.3GB)
llama3.1:latest - Modelo melhor (4.9GB)
```

## Como Trocar:

### Opção 1: Editar config.py

Abra `config.py` e mude:

```python
"ai_ollama_model": "llama3.1:latest",  # Era llama3.2:1b
```

### Opção 2: Editar user_config.json

Abra `user_config.json` e adicione/mude:

```json
{
  "ai_ollama_model": "llama3.1:latest",
  ...
}
```

## Modelos Recomendados:

### Para Frases Curtas e Rápidas:
- `llama3.2:1b` - Mais rápido, mais leve (1GB)
- `llama3.2:3b` - Bom equilíbrio

### Para Mensagens Mais Criativas e Inteligentes:
- `llama3.1:latest` (8B) - Melhor qualidade (5GB)
- `llama3.1:8b` - Mesmo modelo
- `llama3:8b` - Versão anterior

### Para Máxima Qualidade (se tiver GPU/RAM):
- `llama3.1:70b` - Qualidade incrível, mas pesado
- `llama3:70b`

## Como Instalar Novos Modelos:

```bash
ollama pull llama3.1:8b
```

Ou qualquer outro modelo do catalogo: https://ollama.com/library

## Performance:

| Modelo | Tamanho | Velocidade | Qualidade | Uso |
|--------|---------|------------|-----------|-----|
| llama3.2:1b | 1.3GB | ⚡⚡⚡ Muito rápido | ⭐⭐ Básica | Frases simples |
| llama3.2:3b | 2GB | ⚡⚡ Rápido | ⭐⭐⭐ Boa | Recomendado |
| llama3.1:8b | 4.9GB | ⚡ Normal | ⭐⭐⭐⭐ Ótima | Mensagens criativas |
| llama3.1:70b | 40GB+ | 🐢 Lento | ⭐⭐⭐⭐⭐ Perfeita | Apenas se tiver GPU potente |

## Testando:

Depois de mudar, teste:

```bash
python ai_messages.py
```

Vai mostrar qual modelo está sendo usado:
```
[AI] Gerando mensagem com modelo: llama3.1:latest
```

---

**Dica:** O modelo `llama3.1:latest` (8B) é um ótimo equilíbrio entre qualidade e velocidade! 🚀
