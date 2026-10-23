"""Reconhecimento deterministico de servicos operacionais — sem executar GTA aqui."""
import re
import unicodedata

def normalize(text):
    s = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()

def parse_service(text):
    s = normalize(text)
    # Restrito a comandos de despacho: evita ativar em conversa informativa.
    requesting = bool(re.search(r"\b(solicit|acion|envie|manda|mande|precis|requer|cham|despach|enviem|quero|pe[cç]o)\w*\b", s))
    if not requesting:
        return None
    if re.search(r"\b(ambulancia|samu|resgate medico|socorro medico|equipe medica|paramedico|ems)\b", s):
        return {"type":"request_service","service":"ambulance"}
    if re.search(r"\b(guincho|reboque|remocao do veiculo|remover o veiculo|caminhao plataforma)\b", s):
        return {"type":"request_service","service":"tow"}
    if re.search(r"\b(iml|coroner|legista|recolhimento do corpo|remocao do corpo|pericia cadaverica)\b", s):
        return {"type":"request_service","service":"coroner"}
    if re.search(r"\b(transporte de (preso|detido|custodiado)|conducao do (preso|detido|individuo)|conduzir (o |um )?(preso|detido|individuo)|viatura para (conducao|transporte)|camburao)\b", s):
        return {"type":"request_service","service":"prisoner_transport"}
    return None

def service_reply(service, success):
    label={"ambulance":"equipe médica", "prisoner_transport":"viatura para condução do detido", "tow":"guincho", "coroner":"equipe de recolhimento"}.get(service,"serviço")
    if success:
        return f"QSL, prefixo. Solicitação de {label} encaminhada à unidade responsável. Aguarde confirmação de chegada."
    return f"QSL, prefixo. Não foi possível acionar {label} neste momento. Utilize o menu operacional da viatura."

def unavailable_reply(service):
    label={"tow":"guincho", "coroner":"equipe de recolhimento"}.get(service,"serviço")
    return f"QSL, prefixo. Acionamento de {label} indisponível por esta central. Solicite pelo menu operacional."
