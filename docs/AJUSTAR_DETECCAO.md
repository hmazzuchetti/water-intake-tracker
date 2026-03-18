# Como Ajustar a Detecção de Goles

Se a detecção estiver **muito difícil** ou **muito fácil** (muitos falsos positivos), você pode ajustar!

## Configurações Principais (config.py)

### 1. Sensibilidade de Detecção

**O mais importante!** Define quantos critérios precisam ser atendidos:

```python
"detection_sensitivity": "easy",  # "easy", "medium", ou "strict"
```

- **"easy"** (2 de 4 critérios) ✅ **RECOMENDADO para começar**
  - Mais fácil detectar goles
  - Pode ter alguns falsos positivos (raros)
  - Bom para testar e validar o app

- **"medium"** (3 de 4 critérios) - Padrão
  - Equilíbrio entre precisão e facilidade
  - Menos falsos positivos
  - Pode perder alguns goles reais

- **"strict"** (4 de 4 critérios) - Muito restritivo
  - Quase impossível ter falso positivo
  - Vai perder muitos goles reais
  - Não recomendado para uso normal

### 2. Distância Mão-Boca (proximity_threshold)

Quão perto a mão precisa estar da boca:

```python
"proximity_threshold": 0.20,  # 0.20 = mais longe OK, 0.12 = precisa estar bem perto
```

- **0.20-0.25** - Mais tolerante (recomendado para garrafa)
- **0.15** - Médio
- **0.10-0.12** - Muito restrito (bom para copos pequenos)

### 3. Frames para Confirmar (frames_to_confirm)

Quantos frames consecutivos precisa para confirmar:

```python
"frames_to_confirm": 1,  # 1 = detecta rápido, 3 = mais robusto
```

- **1** - Detecta no primeiro frame que atende critérios (mais sensível) ✅ **RECOMENDADO**
- **2** - Precisa de 2 frames consecutivos (padrão)
- **3+** - Muito restrito, pode perder goles rápidos

### 4. Cooldown (cooldown_seconds)

Tempo mínimo entre detecções:

```python
"cooldown_seconds": 10,  # segundos
```

- **5-8s** - Se você bebe rápido em sequência
- **10s** - Padrão, bom para maioria
- **15-20s** - Se quer evitar múltiplas detecções do mesmo gole

### 5. Threshold de Garrafa (detector.py)

Já está em 0.25 (25% de certeza). Se ainda não detectar sua garrafa:

```python
score_threshold=0.20  # Linha 148 em detector.py
```

## Configuração Recomendada para Garrafas 🍾

Esta configuração facilita bastante a detecção:

```python
# No config.py:
"detection_sensitivity": "easy",      # 2 de 4 critérios
"proximity_threshold": 0.20,          # Mão pode estar mais longe
"frames_to_confirm": 1,               # Detecta no primeiro frame
"cooldown_seconds": 10,               # Padrão
"require_cup": True,                  # Exige garrafa detectada
```

## Os 4 Critérios de Detecção

O detector verifica:

1. ✅ **is_close** - Mão perto da boca (obrigatório)
2. ✅ **is_holding** - Mão em pose de segurar algo
3. ✅ **is_drinking** - Mão inclinada (posição de beber)
4. ✅ **upward_motion** - Mão se movendo para cima

Com **"easy"**: Precisa de `is_close` + 1 outro critério
Com **"medium"**: Precisa de `is_close` + 2 outros critérios
Com **"strict"**: Precisa de todos os 4 critérios

## Testando Suas Configurações

### Modo Debug Visual:

```bash
python detector.py
```

Vai mostrar:
- Critérios atendidos em tempo real
- Frames consecutivos
- Distância da mão à boca
- Se garrafa foi detectada

### App Normal:

```bash
python main.py
```

Olhe o console para ver quando detecta:
```
[GULP DETECTED] {
  'is_close': True,
  'is_holding': True,
  'is_drinking': False,
  'upward_motion': True,
  'criteria_met': 3,
  'criteria_required': 2
}
```

## Troubleshooting

### "Não detecta mesmo quando bebo"

Tente:
1. `"detection_sensitivity": "easy"`
2. `"proximity_threshold": 0.22`
3. `"frames_to_confirm": 1`
4. Verifique se garrafa está sendo detectada (modo debug)

### "Detecta quando não estou bebendo"

Tente:
1. `"detection_sensitivity": "medium"`
2. `"proximity_threshold": 0.15`
3. `"frames_to_confirm": 2`
4. `"cooldown_seconds": 15`

### "Garrafa não é reconhecida"

1. No `detector.py` linha 148, reduza:
   ```python
   score_threshold=0.20  # Era 0.25
   ```
2. Rode `python detector.py` para ver % de confiança
3. Use garrafa com rótulo claro (ajuda o detector)

---

**Comece com "easy" e vá ajustando conforme necessário!** 🎯💧
