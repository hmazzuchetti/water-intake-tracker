# Como Criar o Instalador do Water Intake Tracker

Este guia explica como criar um instalador profissional do Windows para o Water Intake Tracker.

## Pré-requisitos

### 1. Python e Dependências
```bash
pip install pyinstaller pillow
```

### 2. Inno Setup (para criar o instalador)

1. Baixe o Inno Setup 6: https://jrsoftware.org/isdl.php
2. Execute o instalador e siga as instruções
3. **IMPORTANTE**: Na instalação, marque a opção "Install Inno Setup Preprocessor"

## Build Rápido (Tudo de Uma Vez)

```bash
python build_installer.py
```

Este comando:
1. Compila o executável com PyInstaller (~5-10 min)
2. Sincroniza os arquivos de recursos
3. Cria o instalador com Inno Setup

O instalador será criado em: `installer_output/WaterIntakeTracker_Setup_1.0.0.exe`

## Build Passo a Passo

### Apenas o Executável
```bash
python build_installer.py --exe
```

### Apenas Sincronizar Recursos
```bash
python build_installer.py --sync
```

### Apenas o Instalador (requer exe já existente)
```bash
python build_installer.py --iss
```

## Build Manual (Alternativa)

### 1. Compilar o Executável
```bash
python build_exe.py
```

### 2. Compilar o Instalador
Abra o `installer.iss` no Inno Setup Compiler e pressione F9 para compilar.

Ou via linha de comando:
```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

## O Que o Instalador Faz

- ✅ Instala em `C:\Program Files\Water Intake Tracker` (ou AppData se não for admin)
- ✅ Cria entrada no Menu Iniciar
- ✅ Cria ícone opcional na Área de Trabalho
- ✅ Opção de iniciar com o Windows
- ✅ Desinstalador pelo Painel de Controle
- ✅ Preserva configurações do usuário em atualizações
- ✅ Detecta se o app está rodando antes de instalar/desinstalar

## Estrutura do Instalador

```
C:\Program Files\Water Intake Tracker\
├── WaterIntakeTracker.exe    # Aplicativo principal
├── icon.ico                   # Ícone
├── user_config.json          # Configurações (preservado em updates)
├── sounds\                   # Sons do app
├── mascots\                  # Imagens dos mascotes
├── personalities\            # Arquivos de personalidade da IA
├── models\                   # Modelos de ML (MediaPipe)
└── data\                     # Dados do usuário (progresso)
```

## Testando o Instalador

1. Crie uma VM do Windows ou use outro PC
2. Execute o instalador
3. Verifique:
   - [ ] Instalação completa sem erros
   - [ ] Ícone no Menu Iniciar funciona
   - [ ] Ícone na Área de Trabalho funciona (se selecionado)
   - [ ] App inicia e funciona corretamente
   - [ ] Desinstalação remove todos os arquivos
   - [ ] Painel de Controle > Programas mostra o app

## Próximos Passos (Futuro)

- [ ] Assinatura de código (Code Signing Certificate) para evitar avisos do Windows
- [ ] Auto-updater integrado
- [ ] Preparação para distribuição na Steam

## Troubleshooting

### "Inno Setup não encontrado"
Instale o Inno Setup 6 de: https://jrsoftware.org/isdl.php

### "Executável não encontrado"
Execute primeiro: `python build_installer.py --exe`

### O instalador é muito grande
O exe tem ~130MB porque inclui todo o runtime do Python e MediaPipe.
Isso é normal para apps Python empacotados.

### Windows Defender bloqueia o instalador
Isso acontece porque o exe não está assinado. Para uso pessoal, clique em
"Mais informações" > "Executar assim mesmo". Para distribuição pública,
considere comprar um certificado de assinatura de código.
