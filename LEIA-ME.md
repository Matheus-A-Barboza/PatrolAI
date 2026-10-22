# PatrolAI — Piper + rádio v0.1.1

Atualização do Bridge v0.1 **sem modificar os endpoints**. Foram mantidos `POST /start`, `GET /status/{jid}` e `/health`.

## ATENÇÃO: voz feminina
O catálogo oficial Piper pt-BR atualmente não dispõe de voz feminina comprovada. O instalador opcional abaixo oferece **Faber, masculino**, apenas para validar Piper e o efeito de rádio. Para uma voz feminina brasileira real, informe em `piper_model` o caminho de um modelo Piper feminino pt-BR obtido de outra fonte confiável (com seu arquivo `.onnx.json`). Como solução provisória use `tts_engine: sapi` e `tts_voice_contains: Maria` se esta voz existir em seu Windows (nesse modo não há filtro de rádio).

## Instalação (Windows, Python 3.13)
1. Faça backup da pasta `bridge` atual. Pare o `start.bat` com Ctrl+C.
2. Copie **os arquivos dentro de `bridge/`** deste pacote para sua pasta `D:\PatrolAI-v0.1\PatrolAI-v0.1\bridge`, mesclando as pastas e substituindo `server.py`, `requirements.txt` e `config.json`. **Se personalizou `listen_seconds`, reconfigure no novo config.json**, pois este pacote usa o original.
3. Baixe [Piper para Windows amd64](https://github.com/rhasspy/piper/releases) (`piper_windows_amd64.zip`). Extraia os arquivos para `bridge/piper/` de modo que `bridge/piper/piper.exe` exista, junto das DLLs.
4. Para teste provisório com a voz **masculina Faber**, baixe os dois arquivos oficiais:
   - https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx
   - https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json
   Salve ambos em `bridge/piper/voices/`.
5. Execute `start.bat` (use o seu arquivo atual, já ajustado para Python 3.13, se for diferente do original). Ele instalará também `scipy`.
6. Para testar sem Ollama e sem GTA V, em outro terminal execute `bridge\test_voice.bat`. Para validar o circuito completo, teste `POST /start` no Swagger.

## Configurações
Em `bridge/config.json`:
- `tts_engine`: `piper` ou `sapi`.
- `piper_model`: caminho para o `.onnx` escolhido (é possível usar modelo feminino de terceiros).
- `radio_enabled`: true/false.
- `radio_highpass_hz`: 350; `radio_lowpass_hz`: 3100 (rádio estreito).
- `radio_noise_level`: 0.002 (ruído suave; pode zerar).
- `radio_drive`: 1.5 (saturação controlada).
- `radio_beep`: true (tom simples no começo e fim, não uma gravação oficial).

## Observações
- Testes de sintaxe realizados; síntese Piper real depende dos binários/modelos baixados no Windows.
- Os erros de síntese são registrados no terminal do Bridge sem derrubar a API.
- Para manter 15 segundos de gravação, configure novamente `listen_seconds: 15`.
- A pasta contém **somente atualização do Bridge**; plugin C# permanece inalterado.
