"""Recognizes explicit radio backup requests. Does not execute game actions."""
import re

BACKUP = re.compile(r'\b(?:apoio|refor[cç]o|backup|viatura\s+(?:de\s+)?apoio|solicito\s+uma\s+unidade)\b', re.I)
REQUEST = re.compile(r'\b(?:solicit\w*|precis\w*|manda\w*|envia\w*|acion\w*|requer\w*|pe[cç]o|urgente|emerg[eê]ncia|ped\w*)\b', re.I)
NEGATE = re.compile(r'\b(?:n[aã]o\s+(?:preciso|quero|solicito)|cancel\w*|dispens\w*|sem\s+necessidade)\b', re.I)
EMERGENCY = re.compile(r'\b(?:c[oó]digo\s*(?:3|tr[eê]s)|code\s*3|urg[eê]ncia|urgente|emerg[eê]ncia|tiroteio|disparos|armad[oa]|sob\s+fogo|socorro)\b', re.I)
CODE2 = re.compile(r'\b(?:c[oó]digo\s*(?:2|dois)|code\s*2|sem\s+(?:sirene|urg[eê]ncia)|sem\s+prioridade)\b', re.I)

def parse_backup_request(text):
    if not isinstance(text, str) or NEGATE.search(text) or not BACKUP.search(text):
        return None
    if not REQUEST.search(text) and not re.search(r'\b(?:qap|copom)\b', text, re.I):
        return None
    if EMERGENCY.search(text):
        code = 3
    elif CODE2.search(text):
        code = 2
    else:
        code = 2  # Safe, no-siren default
    return {"type": "request_backup", "unit": "local", "code": code}


def backup_reply(ok, code, detail=None):
    if ok:
        return ('QSL, prefixo. Solicitação de apoio encaminhada em Código ' + str(code)
                + '. Mantenha contato com a central.')
    return 'QSL, prefixo. Não foi possível acionar o apoio neste momento. Repita a solicitação se necessário.'
