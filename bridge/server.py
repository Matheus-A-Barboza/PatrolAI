"""PatrolAI local bridge v0.1. Binds exclusively to 127.0.0.1."""
import ctypes
import json
import logging
import os
from pathlib import Path
import subprocess
import threading
import time
import uuid
from time import perf_counter
from typing import Literal
import re
from dispatch_records import extract_query, resolve
from backup_intent import parse_backup_request, backup_reply
from service_intent import parse_service, service_reply, unavailable_reply

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
CONFIG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
LOG = logging.getLogger("patrolai")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = FastAPI(title="PatrolAI local bridge", version="0.5.5")
lock = threading.Lock()
jobs = {}
active_job = None
histories = {}
_whisper = None
_whisper_lock = threading.Lock()

def load_whisper():
    """Carrega o modelo uma vez, antes da primeira transmissao."""
    global _whisper
    if _whisper is None:
        with _whisper_lock:
            if _whisper is None:
                from faster_whisper import WhisperModel
                _whisper = WhisperModel(CONFIG["whisper_model"], device=CONFIG["whisper_device"],
                                        compute_type=CONFIG["whisper_compute_type"])
    return _whisper


@app.on_event("startup")
def prewarm_transcriber():
    # Thread separada: API fica responsiva durante o carregamento do Whisper.
    def warm():
        started = perf_counter()
        try:
            load_whisper()
            LOG.info("PatrolAI pronto: Whisper carregado em %.2fs", perf_counter() - started)
        except Exception:
            LOG.exception("Falha ao pre-carregar Whisper; tentaremos novamente na primeira transmissao")
    threading.Thread(target=warm, daemon=True).start()

class StartRequest(BaseModel):
    mode: Literal["npc", "copom"]
    identity: str = Field(default="civil", max_length=80)
    location: str = Field(default="Los Santos", max_length=200)
    distance: float = Field(default=0, ge=0, le=10000)
    text: str | None = Field(default=None, max_length=700)
    vehicle: dict | None = Field(default=None)


def transcribe():
    """Microfone com detecção simples de silêncio (RMS). Mantém limite máximo."""
    import numpy as np
    import sounddevice as sd
    model = load_whisper()
    sr = int(CONFIG["sample_rate"])
    use_vad = bool(CONFIG.get("auto_stop_silence", True))
    max_seconds = float(CONFIG.get("max_listen_seconds", CONFIG.get("listen_seconds", 15)))
    if not use_vad:
        audio = sd.rec(int(sr * max_seconds), samplerate=sr, channels=1, dtype="float32")
        sd.wait()
        samples = np.asarray(audio).reshape(-1)
    else:
        chunk_seconds = 0.1
        frames_per_chunk = int(sr * chunk_seconds)
        silence_seconds = float(CONFIG.get("silence_seconds", 1.8))
        min_speech_seconds = float(CONFIG.get("min_speech_seconds", 0.5))
        threshold = float(CONFIG.get("vad_rms_threshold", 0.013))
        # A fala precisa começar; interrompemos após silêncio contínuo.
        spoke = False
        speech_time = 0.0
        quiet_time = 0.0
        collected = []
        LOG.info("Aguardando fala (limite %.1fs, silencio %.1fs, limiar %.4f)", max_seconds, silence_seconds, threshold)
        with sd.InputStream(samplerate=sr, channels=1, dtype="float32", blocksize=frames_per_chunk) as stream:
            while len(collected) * chunk_seconds < max_seconds:
                block, overflowed = stream.read(frames_per_chunk)
                if overflowed:
                    LOG.warning("Overflow de audio detectado")
                chunk = np.array(block[:,0], copy=True)
                collected.append(chunk)
                level = float(np.sqrt(np.mean(np.square(chunk.astype(np.float64)))))
                if level >= threshold:
                    spoke = True
                    speech_time += chunk_seconds
                    quiet_time = 0.0
                elif spoke:
                    quiet_time += chunk_seconds
                    if speech_time >= min_speech_seconds and quiet_time >= silence_seconds:
                        break
        samples = np.concatenate(collected) if collected else np.empty(0, dtype="float32")
    if len(samples) == 0:
        return ""
    segments, _ = model.transcribe(samples, language="pt", vad_filter=True,
        initial_prompt="Comunicações policiais em português brasileiro. QAP, QSL, QRV, QTC, COPOM, prefixo 111.")
    return " ".join(seg.text.strip() for seg in segments).strip()


from vehicle_context import wants_near_vehicle, vehicle_response, explicit_plate, plate_spoken_response

def generate(req, phrase):
    role = "COPOM, central de operações policiais brasileira, objetiva, usa linguagem de rádio e códigos Q apenas quando adequado" if req.mode == "copom" else "civil abordado por policial, personagem comum, não sabe o que não testemunhou"
    system = (f"Você interpreta {role} no universo fictício de GTA V. Fale sempre português brasileiro, "
              "em resposta curta de no máximo 2 frases. Não invente acesso a bancos de placas, ocorrências ou "
              "ações reais do jogo. Não declare que uma viatura foi enviada ou que uma placa foi consultada. "
              "Se pedirem ação não integrada, explique que está indisponível. "
              "A localização atual enviada pelo jogo é a única fonte válida de localização. Jamais reuse ruas de mensagens passadas; "
              "se a localização disser não identificada, informe que não sabe a rua. Não confunda distância com posição. "
              f"LOCALIZAÇÃO ATUAL DESTA TRANSMISSÃO: {req.location}; id={req.identity}; distância ao interlocutor={req.distance:.1f}m; "
              f"prefixo policial={CONFIG['copom_prefix']}; operador={CONFIG['copom_operator']}; número={CONFIG['copom_number']}.")
    key = f"{req.mode}:{req.identity}"
    # Não enviar mensagens antigas com ruas que poderiam confundir o COPOM.
    history = [] if req.mode == "copom" else histories.get(key, [])[-8:]
    messages = [{"role":"system","content":system}] + history + [{"role":"user","content":phrase}]
    prompt = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages) + "\nASSISTANT:"
    try:
        res = requests.post(CONFIG["ollama_url"], json={"model":CONFIG["model"], "prompt":prompt, "stream":False,
              "options":{"temperature":0.5,"num_predict":64}, "keep_alive":"15m"}, timeout=(5, 40))
        res.raise_for_status()
        answer = res.json().get("response", "").strip() or "Não compreendi, repita por gentileza."
    except requests.exceptions.Timeout:
        LOG.warning("Ollama demorou mais que 40s para gerar resposta; usando resposta de contingencia")
        answer = "QSL, prefixo. Central com instabilidade de comunicação. Repita a última mensagem, por gentileza."
    except requests.exceptions.RequestException as exc:
        LOG.warning("Falha de comunicacao com Ollama: %s", exc)
        answer = "QSL, prefixo. Comunicação com a central temporariamente indisponível."

    histories[key] = (history + [{"role":"user","content":phrase}, {"role":"assistant","content":answer}])[-10:]
    return answer


def speak(text):
    if not CONFIG.get("tts_enabled"):
        return
    from tts_radio import speak_text
    speak_text(text, CONFIG, BASE)


def process(jid, req):
    global active_job
    started = perf_counter()
    try:
        with lock:
            jobs[jid]["state"] = "listening" if req.text is None else "thinking"
        LOG.info("Job %s: iniciando modo=%s local=%s", jid, req.mode, req.location)
        phrase = req.text if req.text is not None else transcribe()
        heard_at = perf_counter()
        LOG.info("Job %s: captura+transcricao=%.2fs", jid, heard_at - started)
        if not phrase:
            raise ValueError("Não detectei fala. Confira o microfone e tente novamente.")
        with lock:
            jobs[jid].update(state="thinking", heard=phrase)
        LOG.info("Job %s: ouvi=%r", jid, phrase[:200])
        # Serviços precisam ser avaliados antes do pedido generico de reforco.
        service = parse_service(phrase) if req.mode == "copom" else None
        if service:
            chosen = service["service"]
            LOG.info("Job %s: servico_operacional=%s", jid, chosen)
            if chosen in ("tow", "coroner"):
                reply = unavailable_reply(chosen)
            else:
                with lock:
                    jobs[jid].update(state="action_pending", action=service)
                    signal = threading.Event()
                    jobs[jid]["_event"] = signal
                queued_at = perf_counter()
                if not signal.wait(timeout=18):
                    raise TimeoutError("Sem confirmacao do adaptador; serviço não confirmado")
                with lock:
                    result = jobs[jid].get("_result", {})
                LOG.info("Job %s: servico_resultado=%s tempo=%.2fs", jid, result.get("success"), perf_counter()-queued_at)
                reply = service_reply(chosen, bool(result.get("success")))
            with lock:
                jobs[jid].update(state="speaking", reply=reply)
            try:
                speak(reply)
            except Exception as exc:
                LOG.warning("Erro de voz: %s", exc)
            with lock:
                jobs[jid]["state"] = "done"
            return
        backup = parse_backup_request(phrase) if req.mode == "copom" else None
        if req.mode == "copom":
            LOG.info("Job %s: reconheceu_pedido_apoio=%s", jid, bool(backup))
        if backup:
            with lock:
                jobs[jid].update(state="action_pending", action=backup)
                signal = threading.Event()
                jobs[jid]["_event"] = signal
            LOG.info("Job %s: pedido de apoio aguardando execucao no GTA: %s", jid, backup)
            queued_at = perf_counter()
            if not signal.wait(timeout=18):
                raise TimeoutError("Sem retorno do plugin do GTA; apoio não confirmado")
            with lock:
                result = jobs[jid].get("_result", {})
            LOG.info("Job %s: adaptador_respondeu_em=%.2fs", jid, perf_counter() - queued_at)
            reply = backup_reply(result.get("success", False), backup["code"])
            with lock:
                jobs[jid].update(state="speaking", reply=reply)
            tts_start = perf_counter()
            try:
                speak(reply)
            except Exception as exc:
                LOG.warning("TTS indisponível: %s", exc)
            LOG.info("Job %s: resposta_falada=%.2fs; total=%.2fs", jid, perf_counter() - tts_start, perf_counter() - started)
            with lock:
                jobs[jid]["state"] = "done"
            LOG.info("Job %s: apoio confirmado=%s", jid, result.get("success", False))
            return
        query = extract_query(phrase) if req.mode == "copom" else None
        spoken_plate = explicit_plate(phrase) if req.mode == "copom" else None
        if spoken_plate:
            reply = plate_spoken_response(spoken_plate, req.vehicle, BASE, resolve)
            LOG.info("Job %s: placa falada=%s; veiculo_proximo=%s", jid, spoken_plate, req.vehicle)
        elif req.mode == "copom" and wants_near_vehicle(phrase):
            reply = vehicle_response(req.vehicle)
            LOG.info("Job %s: consulta de veiculo fisico snapshot=%s", jid, req.vehicle)
        elif query:
            reply = resolve(BASE, *query)
            LOG.info("Job %s: consulta simulada tipo=%s termo=%s", jid, query[0], query[1])
        else:
            reply = generate(req, phrase)
        LOG.info("Job %s: texto_resposta_pronto_em=%.2fs apos fala", jid, perf_counter() - heard_at)
        with lock:
            jobs[jid].update(state="speaking", reply=reply)
        tts_start = perf_counter()
        try:
            speak(reply)
        except Exception as exc:
            LOG.warning("TTS indisponível: %s", exc)
        LOG.info("Job %s: resposta_falada=%.2fs; total=%.2fs", jid, perf_counter() - tts_start, perf_counter() - started)
        with lock:
            jobs[jid]["state"] = "done"
        LOG.info("Job %s: concluido", jid)
    except Exception as exc:
        LOG.exception("Falha no job")
        with lock:
            jobs[jid].update(state="error", error=str(exc)[:250])
    finally:
        with lock:
            if active_job == jid:
                active_job = None


@app.get("/health")
def health():
    return {"ok":True, "version":"0.6.0", "model":CONFIG["model"], "auto_stop_silence": CONFIG.get("auto_stop_silence", True), "simulated_queries": True}


@app.post("/start")
def start(req: StartRequest):
    global active_job
    with lock:
        if active_job is not None:
            LOG.warning("409: pedido novo recusado porque job %s esta ativo; modo=%s local=%s", active_job, req.mode, req.location)
            raise HTTPException(409, f"Transmissao ativa: {active_job}")
        jid = str(uuid.uuid4())
        active_job = jid
        jobs[jid] = {"id":jid,"state":"queued", "heard":"", "reply":"", "error":"", "location":req.location}
        LOG.info("POST /start aceito job=%s modo=%s local=%s", jid, req.mode, req.location)
        if len(jobs) > 50:
            for old in list(jobs.keys())[:-50]:
                if old != jid:
                    jobs.pop(old, None)
    threading.Thread(target=process, args=(jid,req), daemon=True).start()
    return {"id":jid}


@app.get("/status/{jid}")
def status(jid: str):
    with lock:
        if jid not in jobs:
            raise HTTPException(404, "Interação desconhecida")
        return {k: v for k,v in jobs[jid].items() if not k.startswith("_")}

class ActionResult(BaseModel):
    success: bool
    error: str = Field(default="", max_length=250)

@app.post("/action-result/{jid}")
def action_result(jid: str, result: ActionResult):
    with lock:
        job = jobs.get(jid)
        if not job or job.get("state") != "action_pending" or "_event" not in job:
            raise HTTPException(409, "Ação não está aguardando resultado")
        if "_result" in job:
            raise HTTPException(409, "Resultado já informado")
        job["_result"] = result.model_dump()
        job["_event"].set()
    return {"ok": True}

@app.get("/adapter/next")
def adapter_next():
    """Retorna uma única ação ao adaptador LSPDFR carregado em serviço."""
    from fastapi import Response
    with lock:
        for jid, job in jobs.items():
            if (job.get("state") == "action_pending" and
                job.get("action", {}).get("type") in ("request_backup", "request_service") and
                not job.get("_claimed", False)):
                job["_claimed"] = True
                action = job["action"]
                LOG.info("Adapter recebeu acao %s: %s", jid, action)
                return {"id": jid, "type": action["type"],
                        "service": action.get("service", ""),
                        "code": int(action.get("code", 2))}
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
