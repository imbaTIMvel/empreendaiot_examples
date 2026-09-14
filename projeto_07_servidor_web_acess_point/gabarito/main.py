"""
Projeto 07 - Servidor web no ESP32 (modo Access Point)
EmpreendAIoT / Instituto Hardware BR - Monitoria, Trilha IoT

O ESP32 sobe a propria rede Wi-Fi e atende HTTP na porta 80. Serve uma pagina
com a leitura do DHT22 e botoes para ligar e desligar o LED, uma rota de dados
em JSON, e devolve 404 em rota inexistente. O HTTP e montado byte a byte:
nao ha framework nenhum aqui.
"""

import gc
import time
import random
import socket
import network
from machine import Pin
import dht

# --- parametros ajustaveis (valores de referencia, podem ser calibrados) ---
SSID_AP = "EmpreendAIoT-P07"
# PLACEHOLDER: nunca comite uma senha real. Troque no editor do Wokwi antes de
# usar, e veja no README como o valor real deve ser combinado com a monitoria.
SENHA_AP = "SUBSTITUA_AQUI"
REFRESH_S = 2                    # auto-refresh da pagina (requisito 3)
ROTA_RAIZ = "/"
ROTA_LIGAR = "/ligar"
ROTA_DESLIGAR = "/desligar"
ROTA_DADOS = "/dados"
MAX_BYTES_REQUEST = 1024         # teto de leitura do socket (requisito 7)
REQUESTS_TESTE_ESTABILIDADE = 50
TIMEOUT_CLIENTE_S = 5            # cliente que emudece nao trava o servidor
PIN_LED = 23
PIN_DHT = 4
PERIODO_LEITURA_MS = 2500        # margem sobre o minimo do DHT22
AUTOTESTE = True                 # bateria de testes no boot; ver autoteste()
TESTE_VARIACAO = True            # varia temp/umidade e confere as respostas
RODADAS_VARIACAO = 20            # 4 casos de borda + sorteados
CICLOS_VISUAIS_CARGA = 3         # quantas vezes o LED acende e apaga no teste
PAUSA_VISUAL_CARGA_MS = 1000     # tempo em cada estado: longo o bastante para ver

# --- limites determinados: NAO alterar sem consultar a fonte citada ---
# Porta padrao do HTTP (definida pelo protocolo).
PORTA_HTTP = 80
# Senha WPA2: de 8 a 63 caracteres ASCII, sendo 8 o minimo do padrao.
# Nao e escolha do monitor - abaixo disso o AP nao sobe protegido.
SENHA_MIN_CARACTERES = 8
SENHA_MAX_CARACTERES = 63
# O requisito pede rede protegida por senha WPA2. O modo de autenticacao
# precisa ser informado explicitamente na configuracao do AP (ver subir_ap).
AUTH_EXIGIDO = network.AUTH_WPA2_PSK
# A resposta HTTP exige status line, headers e UMA LINHA EM BRANCO antes do
# body. Omitir essa linha deixa o navegador esperando indefinidamente.
FIM_DOS_HEADERS = "\r\n\r\n"
# A rota de dados exige este content type para o cliente interpretar o body.
TIPO_JSON = "application/json"
TIPO_HTML = "text/html; charset=utf-8"
TIPO_TEXTO = "text/plain; charset=utf-8"
# Faixa de medicao do DHT22 (datasheet). O teste de variacao sorteia dentro
# dela, para nunca gerar um valor que o sensor real nao conseguiria entregar.
DHT22_TEMP_MIN_C = -40.0
DHT22_TEMP_MAX_C = 80.0
DHT22_UMID_MIN_PCT = 0.0
DHT22_UMID_MAX_PCT = 100.0
# Semantica dos status usados, definida pelo HTTP.
STATUS_OK = "200 OK"
STATUS_NAO_ENCONTRADO = "404 Not Found"
STATUS_REQUEST_INVALIDO = "400 Bad Request"
# Rota que existe, chamada com metodo nao suportado. O HTTP exige que o 405
# traga o header Allow com os metodos aceitos (RFC 9110, secao 15.5.6).
STATUS_METODO_NAO_PERMITIDO = "405 Method Not Allowed"

# Rotas validas. Serve para o roteamento E para a mensagem do 404 - que lista
# o que existe, em vez de repetir o que o cliente pediu (ver requisito 7).
ROTAS_VALIDAS = (ROTA_RAIZ, ROTA_LIGAR, ROTA_DESLIGAR, ROTA_DADOS)
# Metodos que as rotas aceitam. Vai no header Allow das respostas 405.
METODOS_PERMITIDOS = ("GET",)


# --------------------------------------------------------------------------
# Funcoes puras: nao tocam em socket, sensor nem LED.
# Todas testaveis isoladamente, fora da placa.
# --------------------------------------------------------------------------
def senha_valida(senha):
    """True se a senha respeita o tamanho exigido pelo WPA2."""
    return SENHA_MIN_CARACTERES <= len(senha) <= SENHA_MAX_CARACTERES


def extrair_rota(bruto):
    """Le a request line e devolve (metodo, rota).

    Entrada nao confiavel (requisito 7): qualquer coisa pode chegar aqui.
    Devolve (None, None) quando o request nao da para interpretar, e o
    chamador responde 400 - nunca estoura excecao.
    """
    if not bruto:
        return None, None
    # So a primeira linha interessa para o roteamento.
    fim_linha = bruto.find(b"\r\n")
    if fim_linha < 0:
        fim_linha = len(bruto)
    try:
        linha = bruto[:fim_linha].decode("utf-8")
    except UnicodeError:
        return None, None          # bytes que nao sao texto: descarta

    partes = linha.split(" ")
    if len(partes) != 3:
        return None, None          # nao e "METODO alvo HTTP/x.y"

    metodo, alvo = partes[0], partes[1]
    if not alvo.startswith("/"):
        return None, None
    # Descarta a query string: este projeto nao usa parametros.
    corte = alvo.find("?")
    if corte >= 0:
        alvo = alvo[:corte]
    return metodo, alvo


def montar_resposta(status, tipo_conteudo, corpo, allow=None):
    """Monta a resposta HTTP completa, em bytes.

    Ordem imposta pelo protocolo: status line, headers, LINHA EM BRANCO, body.
    O Content-Length evita que o cliente fique esperando mais dados.
    'allow', quando informado, vira o header Allow - obrigatorio no 405.
    """
    corpo_bytes = corpo.encode("utf-8")
    cabecalho = "HTTP/1.1 " + status + "\r\n"
    if allow is not None:
        cabecalho += "Allow: " + allow + "\r\n"
    # Repare que a ULTIMA linha de header NAO termina em \r\n aqui. Quem fecha
    # ela e o primeiro \r\n de FIM_DOS_HEADERS; o segundo \r\n e a linha em
    # branco propriamente dita. Terminar a ultima linha E concatenar os dois
    # produz uma linha em branco a mais, e o body sai deslocado do que o
    # Content-Length anuncia - o cliente le o corpo truncado.
    cabecalho += (
        "Content-Type: " + tipo_conteudo + "\r\n"
        "Content-Length: " + str(len(corpo_bytes)) + "\r\n"
        "Connection: close"
    )
    return (cabecalho + FIM_DOS_HEADERS).encode("utf-8") + corpo_bytes


def montar_json(dados):
    """JSON da rota de dados, montado a mao para nao carregar o modulo json."""
    if dados["temp_c"] is None:
        temp = "null"
        umid = "null"
    else:
        temp = "{:.1f}".format(dados["temp_c"])
        umid = "{:.1f}".format(dados["umid_pct"])
    return (
        "{"
        '"dispositivo":"' + SSID_AP + '",'
        '"temp_c":' + temp + ","
        '"umid_pct":' + umid + ","
        '"led":' + ("true" if dados["led"] else "false") + ","
        '"uptime_s":' + str(dados["uptime_s"]) + ","
        '"requests":' + str(dados["requests"]) + ","
        '"memoria_livre_b":' + str(dados["memoria_livre"]) +
        "}"
    )


def montar_pagina(dados):
    """Pagina HTML da raiz.

    Sem CDN, sem fonte remota, sem JavaScript (requisito 2): o cliente esta
    numa rede isolada, sem internet - qualquer recurso externo nao carregaria.
    O auto-refresh sai do meta refresh, que e HTML puro (requisito 3).
    """
    if dados["temp_c"] is None:
        temp = "--.-"
        umid = "--.-"
    else:
        temp = "{:.1f}".format(dados["temp_c"])
        umid = "{:.1f}".format(dados["umid_pct"])
    estado_led = "LIGADO" if dados["led"] else "DESLIGADO"
    return (
        "<!DOCTYPE html><html lang=\"pt-BR\"><head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<meta http-equiv=\"refresh\" content=\"" + str(REFRESH_S) + "\">"
        "<title>" + SSID_AP + "</title>"
        "<style>"
        "body{font-family:sans-serif;margin:2em;background:#111;color:#eee}"
        "h1{font-size:1.2em}"
        ".v{font-size:2em;font-weight:bold}"
        "a{display:inline-block;padding:.6em 1.2em;margin-right:.5em;"
        "border-radius:.4em;text-decoration:none;background:#333;color:#eee}"
        ".on{background:#2a7}"
        "small{color:#888}"
        "</style></head><body>"
        "<h1>" + SSID_AP + "</h1>"
        "<p>Temperatura<br><span class=\"v\">" + temp + " &deg;C</span></p>"
        "<p>Umidade<br><span class=\"v\">" + umid + " %</span></p>"
        "<p>Carga: <b>" + estado_led + "</b></p>"
        "<p><a class=\"on\" href=\"" + ROTA_LIGAR + "\">LIGAR</a>"
        "<a href=\"" + ROTA_DESLIGAR + "\">DESLIGAR</a></p>"
        "<p><small>atualiza a cada " + str(REFRESH_S) + " s &middot; "
        "requests: " + str(dados["requests"]) + " &middot; "
        "memoria livre: " + str(dados["memoria_livre"]) + " B &middot; "
        "<a href=\"" + ROTA_DADOS + "\">JSON</a></small></p>"
        "</body></html>"
    )


def montar_404():
    """Body do 404.

    Requisito 7: a mensagem lista as rotas que EXISTEM. Repetir aqui o caminho
    que o cliente pediu seria refletir entrada nao confiavel na resposta.
    """
    return ("404 - rota inexistente.\n\n"
            "Rotas disponiveis:\n  " + "\n  ".join(ROTAS_VALIDAS) + "\n")


def montar_405():
    """Body do 405.

    Mesma regra do 404 (requisito 7): informa o que a rota ACEITA, em vez de
    repetir o metodo que o cliente mandou.
    """
    return ("405 - metodo nao permitido nesta rota.\n\n"
            "Metodos aceitos: " + ", ".join(METODOS_PERMITIDOS) + "\n")


def responder(metodo, rota, dados):
    """Roteamento. Devolve (resposta_em_bytes, acao).

    'acao' diz ao chamador o que fazer com o hardware: "ligar", "desligar" ou
    None. Assim esta funcao continua pura - ela decide, mas nao aciona.
    """
    if metodo is None:
        return montar_resposta(STATUS_REQUEST_INVALIDO, TIPO_TEXTO,
                               "400 - request malformado.\n"), None
    # A ORDEM destes dois testes importa. Rota inexistente e 404 com QUALQUER
    # metodo: o recurso nao existe. So uma rota que existe, chamada com o
    # metodo errado, e 405 - e esse nunca aciona a carga.
    if rota not in ROTAS_VALIDAS:
        return montar_resposta(STATUS_NAO_ENCONTRADO, TIPO_TEXTO,
                               montar_404()), None
    if metodo not in METODOS_PERMITIDOS:
        return montar_resposta(STATUS_METODO_NAO_PERMITIDO, TIPO_TEXTO,
                               montar_405(),
                               allow=", ".join(METODOS_PERMITIDOS)), None

    if rota == ROTA_RAIZ:
        return montar_resposta(STATUS_OK, TIPO_HTML, montar_pagina(dados)), None
    if rota == ROTA_DADOS:
        return montar_resposta(STATUS_OK, TIPO_JSON, montar_json(dados)), None
    if rota == ROTA_LIGAR:
        dados = dict(dados)
        dados["led"] = True
        return montar_resposta(STATUS_OK, TIPO_HTML, montar_pagina(dados)), "ligar"
    if rota == ROTA_DESLIGAR:
        dados = dict(dados)
        dados["led"] = False
        return montar_resposta(STATUS_OK, TIPO_HTML, montar_pagina(dados)), "desligar"

    return montar_resposta(STATUS_NAO_ENCONTRADO, TIPO_TEXTO, montar_404()), None


# --------------------------------------------------------------------------
# Hardware e rede
# --------------------------------------------------------------------------
def nome_seguranca(modo):
    """Traduz o authmode lido do Wi-Fi para um texto legivel no log."""
    if modo is None:
        return "nao informada pelo firmware"
    if modo == network.AUTH_OPEN:
        return "ABERTA (sem senha)"
    if modo == network.AUTH_WPA2_PSK:
        return "WPA2-PSK"
    if modo == network.AUTH_WPA_WPA2_PSK:
        return "WPA/WPA2-PSK"
    return "codigo {}".format(modo)


def subir_ap():
    """Sobe o Access Point protegido e devolve o IP, ou None se algo impedir."""
    if not senha_valida(SENHA_AP):
        print("# FALHA: a senha do AP precisa ter de {} a {} caracteres.".format(
            SENHA_MIN_CARACTERES, SENHA_MAX_CARACTERES))
        print("#   o valor atual tem {}.".format(len(SENHA_AP)))
        return None

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    # O modo de autenticacao vai EXPLICITO. Passar so a senha nao garante uma
    # rede protegida: conforme a versao do firmware, o AP sobe aberto e a senha
    # e simplesmente ignorada - sem erro nenhum.
    ap.config(essid=SSID_AP, password=SENHA_AP, authmode=AUTH_EXIGIDO)
    espera = 0
    while not ap.active() and espera < 50:
        time.sleep_ms(100)
        espera += 1
    if not ap.active():
        print("# FALHA: o Access Point nao subiu.")
        return None

    # Le o modo DE VOLTA: assim o log prova que a rede esta protegida, em vez
    # de presumir que a configuracao pegou (requisito 1).
    try:
        modo = ap.config("authmode")
    except (OSError, ValueError) as erro:
        modo = None
        print("# AVISO: este firmware nao deixa ler o authmode ({})".format(erro))
    if modo == network.AUTH_OPEN:
        print("# FALHA: o Access Point subiu ABERTO, sem protecao.")
        print("#   o servidor nao sera aberto numa rede desprotegida.")
        ap.active(False)
        return None

    ip = ap.ifconfig()[0]
    print("# Access Point no ar")
    print("#   SSID:      {}".format(SSID_AP))
    print("#   seguranca: {}".format(nome_seguranca(modo)))
    print("#   IP:        {}".format(ip))
    print("#   URL:       http://{}/".format(ip))
    return ip


def abrir_servidor():
    srv = socket.socket()
    # SO_REUSEADDR evita "address in use" ao reiniciar a simulacao.
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORTA_HTTP))
    srv.listen(2)
    print("# servidor HTTP escutando na porta {}".format(PORTA_HTTP))
    return srv


def ler_sensor(sensor):
    """Devolve (temp_c, umid_pct) ou (None, None) se a leitura falhar."""
    try:
        sensor.measure()
        return sensor.temperature(), sensor.humidity()
    except OSError as erro:
        print("# AVISO: falha na leitura do DHT22 ({})".format(erro))
        return None, None


def atender(srv, led, dados, registrar=True):
    """Aceita UM cliente, responde e fecha. Devolve a acao pedida pela rota.

    Nunca propaga excecao: cliente que desaparece no meio do request e
    ocorrencia normal, nao defeito (requisito 6).
    'registrar' desliga a linha de log por request - usado no teste de
    estabilidade, para os 50 requests nao soterrarem o resultado.
    """
    cliente = None
    acao = None
    try:
        cliente, endereco = srv.accept()
        cliente.settimeout(TIMEOUT_CLIENTE_S)
        # Teto de leitura: o cliente nao dita quanta memoria vamos usar.
        bruto = cliente.recv(MAX_BYTES_REQUEST)
        metodo, rota = extrair_rota(bruto)
        resposta, acao = responder(metodo, rota, dados)
        cliente.send(resposta)
        if registrar:
            print("# servidor: {} {} -> {}".format(
                metodo if metodo else "?",
                rota if rota else "?",
                resposta[9:12].decode("utf-8")))
        if acao == "ligar":
            led.value(1)
        elif acao == "desligar":
            led.value(0)
    except OSError as erro:
        # Cliente fechou antes da hora, ou estourou o timeout.
        print("# AVISO: request interrompido ({})".format(erro))
    finally:
        # O fechamento vai no finally: sem isto, cada request perdido deixa um
        # socket aberto e a memoria livre cai ate a placa parar (requisito 6).
        if cliente is not None:
            cliente.close()
    return acao


def montar_dados(led, temp_c, umid_pct, t_boot, requests):
    """Junta num dicionario tudo que as funcoes de resposta precisam."""
    return {
        "temp_c": temp_c,
        "umid_pct": umid_pct,
        "led": led.value() == 1,
        "uptime_s": time.ticks_diff(time.ticks_ms(), t_boot) // 1000,
        "requests": requests,
        "memoria_livre": gc.mem_free(),
    }


# --------------------------------------------------------------------------
# Autoteste: a propria placa vira cliente do proprio servidor.
# Existe porque o Access Point simulado nao e alcancavel de fora do Wokwi -
# ver Limitacoes no README. Cada caso abaixo cobre um requisito.
# --------------------------------------------------------------------------
def enviar_request(ip, bruto):
    """Conecta no proprio servidor e manda os bytes. Devolve o socket ABERTO.

    Esta funcao NAO le a resposta, e isso e o ponto central do autoteste.
    O programa tem uma thread so: o servidor so responde quando atender()
    roda. Se o cliente tentasse ler aqui, ficaria esperando uma resposta que
    so pode existir depois que ele desistir - ate estourar o timeout.
    A ordem certa e: enviar_request -> atender -> ler_resposta.
    """
    cli = socket.socket()
    cli.settimeout(TIMEOUT_CLIENTE_S)
    cli.connect((ip, PORTA_HTTP))
    cli.send(bruto)
    return cli


def ler_resposta(cli):
    """Le a resposta e fecha o cliente. Chamar SEMPRE depois de atender()."""
    try:
        return cli.recv(512)
    except OSError as erro:
        return b"ERRO: " + str(erro).encode("utf-8")
    finally:
        cli.close()


def teste_carga(srv, led, ip, dados):
    """Requisito 4: ligar e desligar precisam mover a carga de verdade.

    Sem pausa, as duas rotas rodam com milissegundos de diferenca e o LED
    acende e apaga rapido demais para o olho. Aqui cada rota e seguida de uma
    pausa, para o LED do diagrama piscar visivelmente, e o nivel do pino e
    lido de volta: o log prova que a carga acompanhou a rota, alem do que da
    para ver na tela.
    """
    print("#")
    print("# ---- carga (req 4): o LED do diagrama deve piscar {} vezes ----".format(
        CICLOS_VISUAIS_CARGA))
    for ciclo in range(CICLOS_VISUAIS_CARGA):
        for rota, nivel_esperado in ((ROTA_LIGAR, 1), (ROTA_DESLIGAR, 0)):
            bruto = ("GET " + rota + " HTTP/1.1\r\nHost: x\r\n\r\n").encode("utf-8")
            cli = enviar_request(ip, bruto)
            atender(srv, led, dados, registrar=False)
            resposta = ler_resposta(cli)
            status = resposta.split(b"\r\n")[0].decode("utf-8")
            nivel = led.value()
            print("#   ciclo {}  {:<10} {}  pino = {}  {}".format(
                ciclo + 1, rota, status, nivel,
                "ok" if nivel == nivel_esperado else "FALHOU"))
            time.sleep_ms(PAUSA_VISUAL_CARGA_MS)


def gerar_leitura_aleatoria():
    """Uma leitura sintetica dentro da faixa do DHT22, com a resolucao dele.

    Usa random.getrandbits(), que existe em qualquer port do MicroPython. O
    random.uniform() seria mais direto, mas so existe se o firmware foi
    compilado com as funcoes extras do modulo.
    """
    fracao_t = random.getrandbits(16) / 65535
    fracao_u = random.getrandbits(16) / 65535
    temp = DHT22_TEMP_MIN_C + fracao_t * (DHT22_TEMP_MAX_C - DHT22_TEMP_MIN_C)
    umid = DHT22_UMID_MIN_PCT + fracao_u * (DHT22_UMID_MAX_PCT - DHT22_UMID_MIN_PCT)
    return round(temp, 1), round(umid, 1)


def teste_variacao(srv, led, ip, t_boot):
    """Varia temperatura e umidade e confere que o servidor segue respondendo.

    NAO altera o DHT22: o firmware nao consegue mexer no sensor simulado. O
    teste substitui a LEITURA por valores sinteticos e requisita a pagina e o
    JSON a cada rodada. Comeca pelos casos de borda - extremos da faixa,
    negativo perto de zero e falha de leitura -, que e onde a formatacao
    costuma quebrar.
    """
    print("#")
    print("# ---- teste de variacao: {} rodadas ----".format(RODADAS_VARIACAO))
    leituras = [
        (DHT22_TEMP_MIN_C, DHT22_UMID_MIN_PCT),   # extremo inferior
        (DHT22_TEMP_MAX_C, DHT22_UMID_MAX_PCT),   # extremo superior
        (-0.1, 99.9),                              # negativo perto de zero
        (None, None),                              # sensor em falha
    ]
    while len(leituras) < RODADAS_VARIACAO:
        leituras.append(gerar_leitura_aleatoria())

    corretas = 0
    for temp, umid in leituras:
        dados = montar_dados(led, temp, umid, t_boot, 0)

        cli = enviar_request(ip, b"GET / HTTP/1.1\r\nHost: x\r\n\r\n")
        atender(srv, led, dados, registrar=False)
        pagina = ler_resposta(cli)

        cli = enviar_request(ip, b"GET /dados HTTP/1.1\r\nHost: x\r\n\r\n")
        atender(srv, led, dados, registrar=False)
        resposta_json = ler_resposta(cli)

        # O JSON precisa trazer EXATAMENTE o valor desta rodada - nao basta
        # responder 200 com um numero antigo.
        if temp is None:
            esperado = b'"temp_c":null'
        else:
            esperado = ('"temp_c":' + "{:.1f}".format(temp)).encode("utf-8")
        ok_pagina = pagina.startswith(b"HTTP/1.1 200")
        ok_json = resposta_json.startswith(b"HTTP/1.1 200") and esperado in resposta_json
        if ok_pagina and ok_json:
            corretas += 1

        rotulo_t = "falha" if temp is None else "{:.1f} C".format(temp)
        rotulo_u = "falha" if umid is None else "{:.1f} %".format(umid)
        print("#   temp {:>8}  umid {:>7}  pagina {:<6} json {}".format(
            rotulo_t, rotulo_u,
            "ok" if ok_pagina else "FALHOU",
            "ok" if ok_json else "FALHOU"))

    print("#   {} de {} rodadas corretas".format(corretas, len(leituras)))
    print("# ---- fim do teste de variacao ----")


def autoteste(srv, led, ip, dados):
    print("#")
    print("# ---- autoteste: a placa como cliente dela mesma ----")
    # (rotulo, request cru, cliente some no meio?, reset e resultado esperado?)
    casos = (
        ("req 2/3  pagina na raiz", b"GET / HTTP/1.1\r\nHost: x\r\n\r\n", False, False),
        ("req 4    rota de dados JSON", b"GET /dados HTTP/1.1\r\nHost: x\r\n\r\n", False, False),
        # ligar e desligar tem teste proprio, com pausa visivel: ver teste_carga()
        ("req 5    rota inexistente", b"GET /nao-existe HTTP/1.1\r\nHost: x\r\n\r\n", False, False),
        ("http     POST em rota valida", b"POST /ligar HTTP/1.1\r\nHost: x\r\n\r\n", False, False),
        ("req 7    request malformado", b"isto nao e http\r\n\r\n", False, False),
        # O servidor le so MAX_BYTES_REQUEST e fecha com o resto ainda no buffer.
        # Pelo TCP, fechar com dado nao lido gera RESET em vez de encerramento
        # normal - o cliente pode ver "conexao resetada". E o teto funcionando.
        ("req 7    request gigante", b"GET /" + b"A" * 4000 + b" HTTP/1.1\r\n\r\n", False, True),
        ("req 6    cliente some no meio", b"GET / HTTP/1.1\r\nHost: x\r\n\r\n", True, False),
    )
    for rotulo, bruto, some_no_meio, reset_esperado in casos:
        try:
            cli = enviar_request(ip, bruto)
        except OSError as erro:
            print("#   {:<28} ERRO ao conectar: {}".format(rotulo, erro))
            continue
        if some_no_meio:
            # Requisito 6: o cliente fecha ANTES de o servidor responder.
            cli.close()
            atender(srv, led, dados)
            print("#   {:<28} (cliente fechou; servidor seguiu de pe)".format(rotulo))
            continue
        atender(srv, led, dados)
        resposta = ler_resposta(cli)
        if resposta.startswith(b"ERRO") and reset_esperado:
            print("#   {:<28} conexao resetada - ESPERADO: o servidor".format(rotulo))
            print("#   {:<28} parou de ler no teto de {} bytes".format(
                "", MAX_BYTES_REQUEST))
            continue
        primeira = resposta.split(b"\r\n")[0] if resposta else b"(sem resposta)"
        print("#   {:<28} {}".format(rotulo, primeira.decode("utf-8")))

    teste_carga(srv, led, ip, dados)

    print("#")
    print("# ---- estabilidade de memoria: {} requests ----".format(
        REQUESTS_TESTE_ESTABILIDADE))
    gc.collect()
    antes = gc.mem_free()
    for _ in range(REQUESTS_TESTE_ESTABILIDADE):
        cli = enviar_request(ip, b"GET / HTTP/1.1\r\nHost: x\r\n\r\n")
        atender(srv, led, dados, registrar=False)
        ler_resposta(cli)
    gc.collect()
    depois = gc.mem_free()
    print("#   memoria livre antes:  {} B".format(antes))
    print("#   memoria livre depois: {} B".format(depois))
    print("#   variacao: {:+d} B".format(depois - antes))
    print("# ---- fim do autoteste ----")
    print("#")


def main():
    gc.collect()
    led = Pin(PIN_LED, Pin.OUT)
    led.value(0)
    sensor = dht.DHT22(Pin(PIN_DHT))

    ip = subir_ap()
    if ip is None:
        print("# encerrando sem abrir o servidor.")
        return

    srv = abrir_servidor()
    t_boot = time.ticks_ms()
    requests = 0

    # Primeira leitura antes de atender qualquer um: o DHT22 precisa de um
    # tempo depois de energizado. Esperar aqui, no boot, e aceitavel - ainda
    # nao ha cliente nenhum. Sem isto, o autoteste rodaria com o sensor ainda
    # sem leitura e a evidencia mostraria temperatura nula.
    print("# aguardando o DHT22 estabilizar...")
    time.sleep_ms(PERIODO_LEITURA_MS)
    temp_c, umid_pct = ler_sensor(sensor)
    prox_leitura = time.ticks_add(time.ticks_ms(), PERIODO_LEITURA_MS)

    try:
        if AUTOTESTE:
            autoteste(srv, led, ip,
                      montar_dados(led, temp_c, umid_pct, t_boot, requests))
        if TESTE_VARIACAO:
            teste_variacao(srv, led, ip, t_boot)

        print("# pronto. aguardando requests em http://{}/".format(ip))
        # A partir daqui o log fica em silencio, e isso e o esperado: accept()
        # bloqueia ate chegar cliente, e no Wokwi do navegador nenhum cliente
        # externo alcanca o Access Point simulado (ver Limitacoes no README).
        while True:
            if time.ticks_diff(time.ticks_ms(), prox_leitura) >= 0:
                prox_leitura = time.ticks_add(prox_leitura, PERIODO_LEITURA_MS)
                temp_c, umid_pct = ler_sensor(sensor)

            dados = montar_dados(led, temp_c, umid_pct, t_boot, requests)
            atender(srv, led, dados)
            requests += 1
            if requests % 10 == 0:
                gc.collect()
                print("# {} requests atendidos | memoria livre {} B".format(
                    requests, gc.mem_free()))
    except KeyboardInterrupt:
        print("# encerrado pelo usuario")
    finally:
        srv.close()
        led.value(0)
        print("# servidor fechado, carga desligada.")


main()
