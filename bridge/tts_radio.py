"""PatrolAI speech backend. No network or commercial API required at runtime."""
from pathlib import Path
import os
import subprocess
import tempfile
import wave
import numpy as np
import sounddevice as sd


def _path(base, value):
    p = Path(value)
    return p if p.is_absolute() else base / p


def _sapi(text, cfg):
    # Optional Windows female SAPI voice fallback, not Piper.
    ps = r'''Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = 1
$match = $env:PATROLAI_VOICE
if ($match) {
  $v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Name -like "*$match*" } | Select-Object -First 1
  if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }
}
$s.Speak([Console]::In.ReadToEnd())'''
    env=os.environ.copy(); env['PATROLAI_VOICE']=cfg.get('tts_voice_contains','')
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],input=text,text=True,encoding='utf-8',errors='replace',check=True,timeout=60,env=env)


def _filter(audio, sr, cfg):
    # Radio-like bandpass using scipy's stable 4th order SOS filters.
    from scipy.signal import butter, sosfilt
    lo = float(cfg.get('radio_highpass_hz',350))
    hi = min(float(cfg.get('radio_lowpass_hz',3100)),sr*.45)
    if not (0 < lo < hi): raise ValueError('Frequências de rádio inválidas')
    sos = butter(4,[lo,hi],btype='bandpass',fs=sr,output='sos')
    audio = sosfilt(sos,audio)
    drive = float(cfg.get('radio_drive',1.5))
    audio = np.tanh(audio * drive) / np.tanh(max(drive,0.1))
    noise = float(cfg.get('radio_noise_level',0.002))
    noise = max(0,min(noise,0.02))
    audio = audio + np.random.default_rng().normal(0,noise,len(audio))
    return np.clip(audio,-.95,.95)


def _beep(sr):
    t=np.arange(int(sr*.085),dtype=np.float32)/sr
    tone=.11*np.sin(2*np.pi*950*t)*np.sin(np.pi*np.arange(len(t))/max(len(t)-1,1))
    return np.concatenate((tone,np.zeros(int(sr*.08),dtype=np.float32)))


def speak_text(text,cfg,base):
    if cfg.get('tts_engine','piper') == 'sapi':
        if os.name!='nt': raise RuntimeError('SAPI requer Windows')
        return _sapi(text,cfg)
    exe=_path(base,cfg.get('piper_exe','piper/piper.exe'))
    model=_path(base,cfg.get('piper_model','piper/voices/pt_BR-faber-medium.onnx'))
    if not exe.is_file(): raise FileNotFoundError(f'Piper executável não encontrado: {exe}')
    if not model.is_file(): raise FileNotFoundError(f'Modelo Piper ausente: {model}')
    if not Path(str(model)+'.json').is_file(): raise FileNotFoundError(f'Configuração do modelo ausente: {model}.json')
    with tempfile.TemporaryDirectory(prefix='patrolai_') as folder:
        output=Path(folder)/'speech.wav'
        result=subprocess.run([str(exe),'--model',str(model),'--output_file',str(output)],input=text+'\n',text=True,encoding='utf-8',errors='replace',capture_output=True,timeout=90,cwd=str(exe.parent))
        if result.returncode!=0 or not output.exists(): raise RuntimeError('Piper falhou: '+result.stderr[-500:])
        with wave.open(str(output),'rb') as wf:
            sr=wf.getframerate(); channels=wf.getnchannels(); width=wf.getsampwidth(); raw=wf.readframes(wf.getnframes())
        if width!=2:raise ValueError('WAV não é PCM 16 bits')
        audio=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
        if channels>1:audio=audio.reshape(-1,channels).mean(axis=1)
        if cfg.get('radio_enabled',True):audio=_filter(audio,sr,cfg)
        if cfg.get('radio_beep',True):audio=np.concatenate((_beep(sr),audio,_beep(sr)))
        sd.play(audio.astype(np.float32),sr); sd.wait()
