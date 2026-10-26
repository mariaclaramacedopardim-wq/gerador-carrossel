# Fichário (site instalável)

Planner e bullet journal digital, em formato de fichário. Funciona como app no iPhone, **sem conta, sem login e sem nuvem**:
todos os dados ficam no próprio aparelho (localStorage e IndexedDB). Nada do que você escreve é enviado a servidor algum.

O código aqui não contém nenhum dado pessoal. Os dados vêm de um arquivo de backup que só você tem.

## Instalar no iPhone

1. Abra o endereço do site no **Safari**.
2. Toque em **Compartilhar** e em **Adicionar à Tela de Início**.
3. Abra pelo ícone. Instalado assim, o iPhone não apaga os dados por falta de uso e o app abre sem internet.

## Trazer os dados de outro lugar (restaurar backup)

Botão **dados** (no topo) > **restaurar backup** > escolha o arquivo `fichario-backup-….json` (no app Arquivos).

## Backup

Como não há nuvem, o backup é a sua segurança. Botão **dados** > **salvar backup**, e guarde o arquivo no iCloud Drive.
O app avisa quando passam 14 dias sem backup.

## Lembretes na Agenda do iPhone

Botão **dados** > **gerar lembretes (.ics)**. Gera as próximas 4 semanas com alarmes (no máximo 5 por dia):
medicação, treino (15 min antes), estudo, hora de desacelerar na véspera de treino cedo, e revisão do dia.
Crie antes um calendário chamado "Fichário" para escolher ao adicionar. Refazer atualiza os mesmos compromissos.
Dias marcados como "dia leve" ficam só com medicação e revisão.

## O que mudou em relação à versão do Claude

- Dados e fotos do vision board ficam no aparelho (antes ficavam no banco do artefato).
- Medicação aparece no topo do Hoje, com o horário em que foi tomada.
- Ritual de domingo guiado (escala, treinos, estudo, marmitas e compras, 3 prioridades), na página Planner > Semana.
- Corpo funciona sem prova marcada.
- O instrutor de estudos (IA) só existe dentro do Claude, então fica desligado aqui.

## Desenvolvimento

É um site estático: `index.html` (todo o código), `sw.js` (offline), `manifest.webmanifest`, `img/` e `icons/`.

```
cd fichario && python3 -m http.server 8000      # abrir http://localhost:8000
pip install pytest playwright && pytest tests/test_fichario_e2e.py
```

A publicação é automática pelo GitHub Pages (`.github/workflows/fichario-pages.yml`) a cada mudança na pasta `fichario/` da branch principal.
Ao mudar arquivos do site, aumente `VERSAO` em `sw.js` para forçar a atualização do cache.
