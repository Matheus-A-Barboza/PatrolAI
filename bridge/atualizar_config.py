"""Adiciona opções v0.2 sem sobrescrever voz, Piper ou ajustes atuais."""
import json
from pathlib import Path
p = Path(__file__).with_name('config.json')
if not p.exists():
    raise SystemExit('config.json não encontrado na pasta bridge')
d = json.loads(p.read_text(encoding='utf-8-sig'))
for name, value in {
    'auto_stop_silence': True,
    'max_listen_seconds': 25,
    'silence_seconds': 1.8,
    'min_speech_seconds': 0.5,
    'vad_rms_threshold': 0.013,
}.items():
    d.setdefault(name, value)
p.with_name('config.json.bak-v02').write_bytes(p.read_bytes())
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('Configuração atualizada. Voz e rádio foram preservados.')
