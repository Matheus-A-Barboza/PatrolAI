"""Registros FICTÍCIOS para testes offline do PatrolAI.
Nenhuma informação vem de bancos policiais ou do LSPDFR.
"""
import hashlib
import re
import sqlite3
import unicodedata
from pathlib import Path
from contextlib import closing

PLATE_RE = re.compile(r'(?<![A-Z0-9])([A-Z]{3})[\s\-]?([0-9][A-Z0-9][0-9]{2})(?![A-Z0-9])')
# Captura o nome depois de um marcador de pessoa. Exige contexto de consulta
# para não confundir diálogos comuns com pesquisas de cadastro.
PERSON_RE = re.compile(
    r"\b(?:nome\s+(?:completo\s+)?(?:de|do|da)?|indiv[ií]duo|pessoa|cidad[aã]o|suspeito|senhor|senhora)\s*[:,-]?\s*(?:chamad[oa]\s+)?(?:de\s+)?([A-Za-zÀ-ÿ]+(?:\s+(?:[A-Za-zÀ-ÿ]+)){0,7})",
    re.I,
)
DIRECT_RE = re.compile(
    r"\b(?:consult(?:ar|a|e|o)?|verific(?:ar|a|que|o)?|pesquis(?:ar|a|e|o)?|chec(?:ar|a|que|o)?)\s+(?:o\s+cadastro\s+(?:de|do|da)\s+|(?:os\s+)?antecedentes\s+(?:de|do|da)\s+|(?:o|a|de|do|da)\s+)?([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+){0,7})",
    re.I,
)
TAIL = re.compile(r"\b(?:por\s+favor|pra\s+mim|para\s+mim|no\s+sistema|qsl|qap|qrv|qtc|copom|obrigad[oa]|por\s+gentileza|tem\s+mandado|possui\s+mandado|tem\s+antecedentes|possui\s+antecedentes)\b.*$",re.I)
NOISE = {"consulta", "consultar", "consulto", "verifica", "verificar", "pesquisa", "pesquisar", "checar", "checa", "antecedentes", "cadastro", "individuo", "indivíduo", "pessoa", "cidadão", "cidadao", "suspeito", "nome", "placa", "a", "o", "de", "do", "da", "em", "por"}

def normalize(s):
    return ''.join(x for x in unicodedata.normalize('NFKD',s) if not unicodedata.combining(x)).lower()

def extract_query(text):
    raw = text.upper().replace('.', ' ').replace(',', ' ')
    match = PLATE_RE.search(raw)
    normalized = normalize(text)
    intent = any(word in normalized for word in ('consult','verific','pesquis','chec','placa','cadastro','antecedent','mandado','individuo','cidadao','suspeito'))
    if match and intent:
        return ('plate',match.group(1)+match.group(2))
    if not any(word in normalized for word in ('consult','verific','pesquis','chec','antecedent','cadastro','mandado')):
        return None
    candidate = PERSON_RE.search(text) or DIRECT_RE.search(text)
    if not candidate:
        return None
    name = TAIL.sub('', candidate.group(1)).strip(' .,;:!?-')
    words = name.split()
    while words and normalize(words[0]) in NOISE:
        words.pop(0)
    while words and normalize(words[-1]) in NOISE:
        words.pop()
    name = ' '.join(words)
    # Exigir pelo menos 2 palavras; uma transcrição incompleta não gera um cadastro.
    if len(words) >= 2 and all(len(w) >= 2 or normalize(w) in ('de','da','do') for w in words):
        return ('person', name)
    return None


def db_connection(base: Path):
    db=base/'patrolai_simulated_records.sqlite3'
    conn=sqlite3.connect(db,timeout=5)
    conn.execute('CREATE TABLE IF NOT EXISTS plate_queries(plate TEXT PRIMARY KEY, model TEXT, color TEXT, flag TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS person_queries(name_key TEXT PRIMARY KEY, name TEXT, status TEXT)')
    conn.commit()
    return conn


def resolve(base:Path,kind:str,term:str):
    # Deterministic simulation. Values do not imply actual game-world data.
    with closing(db_connection(base)) as con, con:
        if kind=='plate':
            key=term.upper()
            row=con.execute('SELECT model,color,flag FROM plate_queries WHERE plate=?',(key,)).fetchone()
            if not row:
                h=int(hashlib.sha256(('plate:'+key).encode()).hexdigest()[:8],16)
                models=['Sedan','SUV','Compacto','Picape','Coupe']
                colors=['preto','branco','prata','vermelho','azul']
                flags=['sem apontamentos na base fictícia','registro de atenção simulado','sem apontamentos na base fictícia']
                row=(models[h%len(models)],colors[(h//7)%len(colors)],flags[(h//11)%len(flags)])
                con.execute('INSERT OR IGNORE INTO plate_queries VALUES(?,?,?,?)',(key,*row))
        elif kind=='person':
            key=normalize(term).strip()
            row=con.execute('SELECT name,status FROM person_queries WHERE name_key=?',(key,)).fetchone()
            if not row:
                # Never invent real arrest warrants/criminal histories for arbitrary names.
                row=(term.title(),'sem dados policiais reais; cadastro de treinamento apenas')
                con.execute('INSERT OR IGNORE INTO person_queries VALUES(?,?,?)',(key,*row))
        else:
            raise ValueError('tipo de consulta desconhecido')
        con.commit()
    if kind=='plate':
        return (f'QSL. Consulta de treinamento, placa {term}: veículo fictício tipo {row[0]}, '
                f'cor {row[1]}; {row[2]}. Dados simulados, não representam o veículo do jogo.')
    return (f'QSL. Pesquisa de treinamento para {row[0]}: {row[1]}. '
            'Não há acesso a registros oficiais ou dados pessoais do cidadão.')
