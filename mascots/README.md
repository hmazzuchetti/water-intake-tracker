# Mascotes

Coloque aqui imagens PNG para usar como mascote!

## Como usar:

1. **Adicione sua imagem PNG** nesta pasta
   - Formato: PNG (com transparência de preferência)
   - Tamanho recomendado: até 200x200 pixels
   - Nome: qualquer nome (ex: `dog.png`, `cat.png`, `robot.png`)

2. **Configure no arquivo `config.py`:**
   ```python
   "mascot_file": "mascots/seu_mascote.png",
   ```

3. **Ou crie `mascots/default.png`** - será usado automaticamente!

## Recomendações:

### Tamanho:
- Máximo: 200x200 pixels (configurável em `mascot_size`)
- Ideal: 100-150 pixels
- Pequeno o suficiente para não atrapalhar

### Estilo:
- PNG com fundo transparente fica melhor
- Personagens cartoon/chibi funcionam bem
- Emojis grandes também
- Ícones bonitos

### Exemplos de ideias:
- 🐶 Cachorrinho
- 🤖 Robô
- 💧 Gotinha d'água
- 🦈 Tubarão (porque você precisa se manter em movimento na água!)
- ☕ Caneca (irônico, mas engraçado)
- 🐸 Sapo
- 🌊 Onda

## Onde encontrar mascotes:

- **Flaticon** (https://flaticon.com) - ícones grátis
- **Icons8** (https://icons8.com) - mascotes fofos
- **OpenMoji** (https://openmoji.org) - emojis open source
- **Fazer o seu próprio** no Canva, Figma, etc

## Som do mascote:

O mascote toca um som ao aparecer! Configure em `config.py`:

```python
"mascot_sound": "pop.wav",  # Nome do arquivo em sounds/
```

Você pode trocar por outro som divertido (coloque na pasta `sounds/`)

---

**Dica:** Se não colocar nenhum mascote, o app funciona normalmente sem ele! 😊
