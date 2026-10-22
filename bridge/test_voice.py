import json
from pathlib import Path
from tts_radio import speak_text
base=Path(__file__).resolve().parent
cfg=json.loads((base/'config.json').read_text(encoding='utf-8'))
print('Testando voz do COPOM. Aguarde...')
speak_text('QSL, prefixo cento e onze. COPOM ciente. Patrulhamento iniciado na região de Davis. Sem alterações no momento.',cfg,base)
print('Áudio reproduzido com sucesso.')
