# 07 — Servidor web no ESP32 (modo Access Point)

## Objetivo

O ESP32 sobe a própria rede Wi-Fi e atende HTTP na porta 80, servindo uma
página com a leitura de um DHT22, controles para uma carga e uma rota de dados
em JSON. O projeto mostra que o microcontrolador pode ser o servidor, e
apresenta o HTTP na forma crua: request line, headers, linha em branco, body e
status code, montados byte a byte, sem framework.

## Ambiente

- **Placa:** ESP32 DevKit V1 (`board-esp32-devkit-v1`). Obrigatória pela
  especificação para os projetos com conectividade; é a placa com rádio Wi-Fi da
  trilha.
- **Firmware / versão do MicroPython:** `micropython-20231227-v1.22.0`
  (declarado em `attrs.env` no `diagram.json`). A execução registrada em
  `evidencias/log-autoteste.txt` não imprime a linha de versão, porque o
  programa não termina; a versão foi **inferida pela assinatura do
  bootloader** (`len:4728/14888/3368`, `entry 0x400805cc`), idêntica à de
  execuções que imprimiram `v1.22.0`. Projetos novos no Wokwi, sem este
  `diagram.json`, sobem na `v1.28.0`.
- **Link da simulação publicada:** <https://wokwi.com/projects/475082925554620417>

## Componentes

| Componente (nome no Wokwi) | Qtd | Obrigatório / Opcional | Observação |
|---|---|---|---|
| `board-esp32-devkit-v1` | 1 | Obrigatório | Placa com Wi-Fi |
| `wokwi-dht22` | 1 | Obrigatório | Fonte de dados |
| `wokwi-led` | 1 | Obrigatório | Carga controlável remotamente |
| `wokwi-resistor` | 1 | Obrigatório | 220 Ω, em série com o LED |

> O part do DHT22 precisa dos atributos `temperature` e `humidity` no
> `diagram.json`. Sem eles, o sensor simulado não responde e toda leitura volta
> `ETIMEDOUT`.

## Pinagem

| Componente | Pino do componente | Pino da placa | Observação |
|---|---|---|---|
| DHT22 | VCC | 3V3 | — |
| DHT22 | GND | GND | — |
| DHT22 | SDA (dados) | D4 (GPIO4) | GPIO comum; evita os strapping pins |
| LED | A (ânodo) | D23 via resistor 220 Ω | Saída digital |
| LED | C (cátodo) | GND | — |

## Parâmetros ajustáveis (arbitrários)

| Constante | Valor adotado | Faixa aceitável | Por que esse valor |
|---|---|---|---|
| `SSID_AP` | `EmpreendAIoT-P07` | até 32 caracteres | Identificador neutro do projeto |
| `SENHA_AP` | `SUBSTITUA_AQUI` | 8 a 63 caracteres | **Placeholder** — ver abaixo |
| `REFRESH_S` | 2 | 1 a 30 | Atualização perceptível sem sobrecarregar o servidor |
| `MAX_BYTES_REQUEST` | 1024 | 512 a 4096 | Cabe a request line e os headers usuais de um navegador |
| `REQUESTS_TESTE_ESTABILIDADE` | 50 | ≥ 50 | Valor sugerido pela especificação |
| `TIMEOUT_CLIENTE_S` | 5 | 1 a 30 | Cliente que emudece não prende o servidor |
| `PERIODO_LEITURA_MS` | 2500 | ≥ 2000 | Margem sobre o mínimo do DHT22 |
| `AUTOTESTE` | `True` | `True` / `False` | Bateria de testes dos requisitos no boot |
| `TESTE_VARIACAO` | `True` | `True` / `False` | Varia a leitura e confere as respostas |
| `RODADAS_VARIACAO` | 20 | ≥ 4 | 4 casos de borda + sorteados |
| `CICLOS_VISUAIS_CARGA` | 3 | 1 a 10 | Piscadas do LED no teste da carga |
| `PAUSA_VISUAL_CARGA_MS` | 1000 | ≥ 300 | Tempo em cada estado; abaixo disso o olho não acompanha |
| Pinos | 4 / 23 | GPIO válido | Ver Pinagem |

### Senha do Access Point (requisito 1)

`SENHA_AP` é um **placeholder**, e nunca deve receber uma senha real no
repositório — nem em código, comentário, log ou captura de tela.

- **Na simulação**, o placeholder funciona como está: tem 14 caracteres, dentro
  da faixa exigida pelo WPA2.
- **Em hardware real**, a senha deve ser combinada com a monitoria e digitada
  apenas na cópia local do `main.py`, sem commit. Uma senha que já passou pelo
  Git continua no histórico mesmo depois de apagada do arquivo.

A rede sobe com **WPA2-PSK explícito**, e o modo é lido de volta e impresso no
log. Se o firmware subir o Access Point aberto, o programa recusa abrir o
servidor.

### Rotas (requisito 4)

| Rota | Método | Resposta | `Content-Type` | Efeito |
|---|---|---|---|---|
| `/` | GET | `200` — página HTML | `text/html; charset=utf-8` | — |
| `/ligar` | GET | `200` — página HTML | `text/html; charset=utf-8` | Liga a carga |
| `/desligar` | GET | `200` — página HTML | `text/html; charset=utf-8` | Desliga a carga |
| `/dados` | GET | `200` — JSON | `application/json` | — |
| rota válida | outro método | `405` — texto com os métodos aceitos, header `Allow: GET` | `text/plain; charset=utf-8` | Nenhum: não aciona a carga |
| rota inexistente | qualquer método | `404` — texto com as rotas válidas | `text/plain; charset=utf-8` | — |
| request ininteligível | — | `400` — texto | `text/plain; charset=utf-8` | — |

A rota é avaliada **antes** do método: um `POST` numa rota inexistente recebe
`404`, porque o recurso não existe, e só uma rota válida com método errado
recebe `405`. A query string é descartada antes do roteamento. Toda resposta
leva `Content-Length` e `Connection: close`; nenhum body repete a rota ou o
método enviados pelo cliente.

### Chaves do JSON de `/dados`

| Chave | Tipo | Conteúdo |
|---|---|---|
| `dispositivo` | string | Identificador neutro (o SSID) |
| `temp_c` | número ou `null` | Temperatura em °C, uma casa; `null` se o sensor falhou |
| `umid_pct` | número ou `null` | Umidade relativa em %, uma casa; `null` se o sensor falhou |
| `led` | booleano | Estado da carga |
| `uptime_s` | inteiro | Segundos desde o boot |
| `requests` | inteiro | Requests atendidos |
| `memoria_livre_b` | inteiro | `gc.mem_free()` no momento da resposta |

Exemplo:

```json
{"dispositivo":"EmpreendAIoT-P07","temp_c":21.4,"umid_pct":59.0,"led":false,"uptime_s":142,"requests":7,"memoria_livre_b":91520}
```

## Limites determinados (não arbitrários)

| Constante | Valor | Fonte (datasheet / especificação / placa) | Verificado em |
|---|---|---|---|
| `PORTA_HTTP` | 80 | Porta padrão do esquema `http` — RFC 9110 | `13.09` |
| `SENHA_MIN_CARACTERES` / `SENHA_MAX_CARACTERES` | 8 / 63 | Passphrase WPA2 de 8 a 63 caracteres ASCII — IEEE 802.11 | `13.09` |
| `AUTH_EXIGIDO` | `network.AUTH_WPA2_PSK` | Requisito 1 (rede protegida por senha WPA2) | `13.09` |
| `FIM_DOS_HEADERS` | `\r\n\r\n` | Linha em branco entre headers e body — RFC 9112, seção 2.1 | `13.09` |
| `TIPO_JSON` | `application/json` | Media type do JSON — RFC 8259, seção 11 | `13.09` |
| `STATUS_OK` / `STATUS_NAO_ENCONTRADO` / `STATUS_REQUEST_INVALIDO` | 200 / 404 / 400 | Semântica dos status — RFC 9110, seção 15 | `13.09` |
| `STATUS_METODO_NAO_PERMITIDO` | 405, com header `Allow` obrigatório | RFC 9110, seção 15.5.6 | `PENDENTE` |
| `DHT22_TEMP_MIN_C` / `DHT22_TEMP_MAX_C` | −40 / 80 °C | Faixa de medição (datasheet DHT22) | `13.09` |
| `DHT22_UMID_MIN_PCT` / `DHT22_UMID_MAX_PCT` | 0 / 100 % | Faixa de medição (datasheet DHT22) | `13.09` |
| Intervalo mínimo do DHT22 | ≈ 2 s | Datasheet DHT22 | `13.09` |

## Dependências

| Módulo | Origem (embarcado no firmware / arquivo no projeto) | Verificado em |
|---|---|---|
| `network` (`WLAN`, `AP_IF`, constantes `AUTH_*`) | Embarcado no firmware MicroPython | `13.09` |
| `socket` | Embarcado no firmware MicroPython | `13.09` |
| `gc` | Embarcado no firmware MicroPython | `13.09` |
| `time` (`ticks_ms`, `ticks_diff`, `ticks_add`, `sleep_ms`) | Embarcado no firmware MicroPython | `13.09` |
| `random` (`getrandbits`) | Embarcado no firmware MicroPython | `13.09` |
| `machine` (`Pin`) | Embarcado no firmware MicroPython | `13.09` |
| `dht` | Embarcado no firmware MicroPython | `13.09` |

Nenhum arquivo auxiliar é necessário. O JSON é montado à mão, sem o módulo
`json`, para não carregá-lo na memória.

## Como executar

1. Abrir <https://wokwi.com> e criar um novo projeto **MicroPython — ESP32**.
2. Substituir o `diagram.json` pelo de `gabarito/diagram.json`.
3. Substituir o `main.py` pelo de `gabarito/main.py`.
4. Clicar em **Play**. O log serial mostra, em ordem: o Access Point no ar com o
   modo de segurança lido de volta, uma pausa de ~2,5 s para o DHT22
   estabilizar, o autoteste dos requisitos, o teste da carga — com o LED do
   diagrama piscando três vezes, cerca de 6 s —, o teste de estabilidade de
   memória e o teste de variação.
5. Ao aparecer `pronto. aguardando requests`, o log fica em silêncio. É o
   esperado: o servidor bloqueia à espera de cliente.

O `gabarito/wokwi.toml` traz, comentado, um encaminhamento de porta para a
extensão do Wokwi no VS Code. Não foi verificado — ver Limitações.

## Roteiro de teste

| # | Ação | Resultado esperado | Resultado obtido |
|---|---|---|---|
| 1 | Rodar a simulação | Log com SSID, IP, porta, e segurança `WPA2-PSK` lida de volta | OK |
| 2 | Autoteste: requisitar a raiz | `200 OK` |  OK |
| 3 | Autoteste: requisitar `/dados` | `200 OK` |  OK |
| 4 | Teste da carga: `/ligar` e `/desligar`, 3 ciclos | `200 OK`, pino lido de volta `1` e `0`, e o LED do diagrama pisca visivelmente |  OK |
| 5 | Autoteste: rota inexistente | `404 Not Found` |  OK |
| 6 | Autoteste: request malformado | `400 Bad Request` |  OK |
| 7 | Autoteste: request gigante (4000 bytes) | `400 Bad Request`, ou conexão resetada rotulada como esperada |  OK |
| 8 | Autoteste: cliente fecha antes da resposta | Servidor segue de pé |  OK |
| 9 | 50 requests seguidos | Memória livre estável (sem queda proporcional) |  OK |
| 10 | Teste de variação, 20 rodadas | `20 de 20 rodadas corretas`, inclusive −40 °C, 80 °C, −0,1 °C e falha de leitura |  OK |
| 11 | Trocar `SENHA_AP` por 7 caracteres e rodar | Programa recusa e explica, sem subir o Access Point |  OK |
| 12 | Autoteste: `POST /ligar` | `405 Method Not Allowed` com `Allow: GET`, e a carga não acende | Verificado fora da placa (CPython); ainda não consta no log da placa |

Evidências em `evidencias/`:

- `log-autoteste.txt` — log serial completo de uma execução na placa simulada:
  segurança `WPA2-PSK` lida de volta, autoteste dos requisitos, teste da carga
  com o pino lido de volta nos 3 ciclos, estabilidade de memória (+160 B em 50
  requests) e 20 de 20 rodadas do teste de variação. É **anterior** à inclusão
  do caso `POST em rota valida` (item 12), que por isso não aparece nele.
- `pagina-servida.html` — o HTML exato que a rota `/` devolve, gerado pela
  mesma `montar_pagina()` do firmware com dados de exemplo. Serve para
  conferência visual; os botões não funcionam fora do dispositivo.

Verificações feitas **fora da placa**, com as mesmas funções do firmware
executadas em CPython: o `Content-Length` bate com os bytes do body em todas as
rotas; `/dados` devolve `application/json` e faz parse; o 404 não repete o
caminho pedido (testado com `/<script>...`); a página não contém `http://`,
`https://` nem `<script`; a falha de leitura vira `null` no JSON; `POST`,
`PUT` e `DELETE` em rota válida devolvem `405` com `Allow: GET` sem acionar a
carga, e `POST` em rota inexistente devolve `404`.

## Limitações da simulação

- **O Access Point não é alcançável do navegador no Wokwi web.** Ele existe só
  dentro da simulação. Por isso a evidência vem do **autoteste**: a própria placa
  abre sockets para o próprio IP e imprime as respostas no log. Isso exercita o
  servidor de ponta a ponta, mas por *loopback*, sem rádio real.
- **O autoteste é cliente único e sequencial.** Não exercita vários clientes
  simultâneos nem comportamentos de navegador real — como o pedido automático de
  `/favicon.ico`, que recebe `404`, ou conexões *keep-alive*.
- **O servidor atende um cliente por vez.** O `accept()` bloqueia, então um
  cliente lento segura os demais por até `TIMEOUT_CLIENTE_S`. E o sensor só é
  lido entre dois requests: sem cliente, a leitura não avança.
- **O resultado do request gigante depende da pilha TCP.** O servidor lê só
  `MAX_BYTES_REQUEST` e fecha com o resto não lido. No ESP32 simulado a resposta
  foi `400`; num PC com Windows, a mesma situação produz *reset* da conexão. As
  duas reações demonstram o teto de leitura.
- **A proteção da rede é comprovada por configuração, não por handshake.** O log
  mostra o modo lido do firmware; nenhum cliente real se autentica na rede
  simulada.
- **O teste de variação não altera o DHT22.** O firmware não controla o sensor
  simulado; o teste substitui a leitura por valores sintéticos dentro da faixa
  do datasheet.
- **A variação de memória é pequena e positiva.** `gc.mem_free()` depois de
  `gc.collect()` recupera um pouco mais no fim do que no início; o sinal de
  vazamento seria queda proporcional ao número de requests.
- **O encaminhamento de porta não foi testado.** O `wokwi.toml` traz, comentado,
  o bloco `[[net.forward]]` da extensão do VS Code. O fluxo de MicroPython na
  extensão pode exigir o binário do firmware no campo `firmware`, em vez do
  `main.py`.

## Referências

- MicroPython — `network.WLAN` (modo AP, `config`, `authmode`):
  <https://docs.micropython.org/en/latest/library/network.WLAN.html> — acesso em `13.09`
- MicroPython — `socket`:
  <https://docs.micropython.org/en/latest/library/socket.html> — acesso em `13.09`
- MicroPython — `random`:
  <https://docs.micropython.org/en/latest/library/random.html> — acesso em `13.09`
- IETF — RFC 9110, *HTTP Semantics* (porta 80, status codes):
  <https://www.rfc-editor.org/rfc/rfc9110> — acesso em `13.09`
- IETF — RFC 9112, *HTTP/1.1* (formato da mensagem, linha em branco):
  <https://www.rfc-editor.org/rfc/rfc9112> — acesso em `13.09`
- IETF — RFC 8259, *The JSON Data Interchange Format* (`application/json`):
  <https://www.rfc-editor.org/rfc/rfc8259> — acesso em `13.09`
- IEEE 802.11 Working Group (padrão Wi-Fi; passphrase WPA2):
  <https://www.ieee802.org/11/> — acesso em `13.09`
- Aosong — DHT22 / AM2302 datasheet:
  <https://www.sparkfun.com/datasheets/Sensors/Temperature/DHT22.pdf> — acesso em `13.09`

## Controle

- Elaboração (função): Monitoria — Trilha IoT
- Revisão por par (função): `PENDENTE` — Data: `PENDENTE`
- Aprovação (coordenação): `PENDENTE` — Data: `PENDENTE`
