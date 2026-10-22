import re

VEHICLE_INTENT = re.compile(r"\b(?:placa|ve[ií]culo|carro|autom[oó]vel|moto|motocicleta)\b", re.I)
NEAR_INTENT = re.compile(r"\b(?:pr[oó]ximo|perto|abordando|abordado|aqui|minha frente|na frente|este|esse|desse|deste|olhando|parado)\b", re.I)
QUERY_INTENT = re.compile(r"\b(?:consult|verific|pesquis|chec|informa|identific|confirma)\w*", re.I)

def wants_near_vehicle(phrase):
    return bool(VEHICLE_INTENT.search(phrase) and QUERY_INTENT.search(phrase) and NEAR_INTENT.search(phrase))

def vehicle_response(snapshot):
    if not isinstance(snapshot, dict) or not snapshot.get('found'):
        return 'QSL. Nenhum veículo selecionado próximo ao policial. Aproxime-se do automóvel e repita a consulta.'
    plate = re.sub(r'[^A-Z0-9]', '', str(snapshot.get('plate','')).upper())[:12]
    model = re.sub(r'[^a-zA-Z0-9 _-]', '', str(snapshot.get('model','')))[:45].strip()
    distance = snapshot.get('distance_m')
    if not plate:
        return 'QSL. Veículo identificado nas proximidades, mas a placa não pôde ser obtida.'
    result = f'QSL. Veículo próximo identificado no jogo. Placa {plate}.'
    if model: result += f' Modelo {model}.'
    if isinstance(distance,(float,int)) and 0 <= distance <= 30: result += f' Aproximadamente {distance:.0f} metros.'
    return result + ' Sem consulta ao cadastro policial do LSPDFR.'




def explicit_plate(text):
    """Extrai apenas placa ditada explicitamente após a palavra 'placa'.

    Formatos aceitos: AAA1234, AAA1A23 e até 8 caracteres para placas
    fictícias do GTA. Não troca O por 0 sem comprovação.
    """
    match = re.search(r"\bplaca\s*(?:de\s*)?(?:n[uú]mero\s*)?[:#-]?\s*([A-Za-z]{3}[- ]?[A-Za-z0-9]{4,5})(?![A-Za-z0-9])", text, re.I)
    if not match:
        return None
    raw = re.sub(r"[^A-Z0-9]", "", match.group(1).upper())
    # Captura encerra ao alcançar sufixo comum de conversação se misturado;
    # a leitura é melhor quando a placa é ditada como um bloco.
    if len(raw) in (7,8) and raw[:3].isalpha() and any(ch.isdigit() for ch in raw[3:]):
        return raw
    return None


def plate_spoken_response(plate, snapshot, base, resolver):
    """Prioriza placa dita e compara com snapshot da entidade GTA.

    Não reivindica acesso ao banco policial do LSPDFR.
    """
    observed = None
    if isinstance(snapshot, dict) and snapshot.get('found'):
        observed = re.sub(r'[^A-Z0-9]', '', str(snapshot.get('plate','')).upper())
    if observed and observed == plate:
        return vehicle_response(snapshot) + ' A placa informada pelo policial confere com a leitura local.'
    result = resolver(base, 'plate', plate)
    if observed:
        return (f'QSL. Placa informada {plate}; veículo próximo apresenta placa {observed}, '
                'que não confere. ' + result)
    return result
