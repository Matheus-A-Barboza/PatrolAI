# PatrolAI v0.1 — MVP local (GTA V Legacy + RAGE Plugin Hook)

## Escopo desta versão
- F6: identifica um pedestre até 4m e inicia gravação de 5s; conversa em português com LLM local e resposta por voz do Windows.
- F7: mesmo fluxo para o COPOM fictício.
- Histórico curto separado por NPC (handle de sessão) ou COPOM.
- Nenhuma ação física no jogo, consulta real de placas, detenção ou integração com dados internos do LSPDFR **nesta versão**.
- Localização ainda fixa em `Los Santos` no plugin. Voz depende da voz instalada no Windows; não é garantida uma voz brasileira.

## Pré-requisitos
1. Windows, GTA V Legacy e LSPDFR/RAGE Plugin Hook já funcionais.
2. Python 3.11 (incluindo Python Launcher `py`).
3. Ollama instalado: https://ollama.com/download/windows
4. Visual Studio 2022 ou Build Tools com suporte .NET Framework 4.8 e targeting pack, para compilar a DLL.
5. Espaço para baixar modelo de linguagem + modelo Whisper na primeira execução.

## Instalação e primeira execução
1. Abra PowerShell, execute `ollama pull llama3.2:3b` (Ollama precisa estar em execução).
2. Abra `bridge/start.bat`; na primeira vez instala as dependências. Aguarde `Uvicorn running on http://127.0.0.1:8765`.
3. Abra `http://127.0.0.1:8765/docs` e teste `GET /health`.
4. Abra outro terminal na pasta bridge, ative `.venv\Scripts\activate`, execute `python test_text.py`. O COPOM deve responder pelo terminal (e opcionalmente por voz).
5. Copie o caminho da pasta onde está `RagePluginHook.dll` (geralmente a pasta principal do GTA V).
6. No PowerShell na pasta `plugin`, compile definindo a variável:
   ```powershell
   $env:RPH_DIR = 'C:\CAMINHO\PARA\Grand Theft Auto V'
   dotnet build .\PatrolAI.csproj -c Release
   ```
   Se usar Visual Studio, configure a variável de ambiente `RPH_DIR` antes de iniciar o VS, ou edite `HintPath` no `.csproj`.
7. Copie `plugin\bin\Release\net48\PatrolAI.dll` para `Grand Theft Auto V\Plugins\PatrolAI.dll`.
8. Mantenha o serviço Python rodando; inicie o GTA via RAGE Plugin Hook e, no console F4, execute `LoadPlugin PatrolAI.dll` (não execute duas vezes).
9. F6 perto de um civil; F7 para COPOM. Certifique-se de que seu microfone padrão está selecionado nas configurações de som do Windows.

## Configuração
Edite `bridge/config.json` **antes de iniciar** o servidor. `tts_enabled=false` desliga a fala; `whisper_model=tiny` reduz custo de CPU com menor precisão; `listen_seconds=5` controla duração; `copom_*` personaliza a identificação. O modelo padrão é `llama3.2:3b`; experimente outro modelo somente após `ollama pull`.

## Limites de segurança/estabilidade
- API só em `127.0.0.1`; não exponha a porta 8765 para rede/internet.
- Um diálogo por vez, para evitar gravação dupla e sobrecarga.
- O jogo nunca faz chamadas Ollama diretamente.
- Não use GTA Online, FiveM, ou sistemas de anticheat com este plugin: somente Story Mode/LSPDFR.
- O serviço usa scripts de voz SAPI do Windows; se não houver voz adequada, mantenha texto ou instale uma voz pt-BR confiável.
- Transcrição Whisper em CPU, por padrão. GTX 1660 pode auxiliar modelos, mas configuração CUDA no Windows requer componentes adicionais.
- A IA não controla peds, nem altera ocorrências. O histórico é apenas em memória e perde-se ao reiniciar o bridge.
- A seleção por handle não garante identidade persistente após despawn/reuso.
- A DLL ainda exige compilação/testes reais com a versão de RAGE Plugin Hook instalada no PC. APIs e assinaturas podem variar.

## Resolução de problemas
- `Unable to connect`: servidor local não iniciado / porta 8765 ocupada.
- `404` em Ollama: modelo não baixado; `ollama list`.
- Microfone silencioso: selecione dispositivo de entrada padrão do Windows e permita acesso ao microfone para apps desktop.
- Python instala mas Whisper não executa: confirme Python 64-bit 3.11 e pacotes atualizados; teste `whisper_model=tiny`.
- Erro na compilação `RagePluginHook`: confirme `RPH_DIR` e arquivo RagePluginHook.dll.
- Verifique `RagePluginHook.log` e console do Python para detalhes.
