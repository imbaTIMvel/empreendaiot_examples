# 04 — Painel de dados em display OLED (I2C)

## Objetivo

Mostrar temperatura e umidade de um DHT22 num display OLED SSD1306 ligado ao
barramento I2C. O projeto ensina endereçamento e scan de I2C, dois fios
compartilhados entre dispositivos, e o projeto de uma interface legível numa
área de 16 caracteres por 8 linhas.

## Ambiente

- **Placa:** ESP32 DevKit V1 (`board-esp32-devkit-v1`). Mantida a placa dos
  projetos anteriores da trilha; o I2C0 nativo em D21/D22 dispensa configuração
  extra. O projeto roda em Raspberry Pi Pico trocando os pinos do barramento.
- **Firmware / versão do MicroPython:** `micropython-20231227-v1.22.0`
  (declarado em `attrs.env` no `diagram.json`).
- **Link da simulação publicada:** <https://wokwi.com/projects/475065722959566849>

## Componentes

| Componente (nome no Wokwi) | Qtd | Obrigatório / Opcional | Observação |
|---|---|---|---|
| `board-esp32-devkit-v1` | 1 | Obrigatório | Placa da simulação |
| `board-ssd1306` | 1 | Obrigatório | OLED 128×64 I2C |
| `wokwi-dht22` | 1 | Obrigatório | Fonte de dados |
| `wokwi-pushbutton` | 1 | Opcional | Alterna dados / diagnóstico |

> O part do DHT22 precisa dos atributos `temperature` e `humidity` no
> `diagram.json`. Sem eles o sensor simulado não responde ao protocolo e toda
> leitura volta `ETIMEDOUT` — ver Limitações.

## Pinagem

| Componente | Pino do componente | Pino da placa | Observação |
|---|---|---|---|
| OLED SSD1306 | VCC | 3V3 | — |
| OLED SSD1306 | GND | GND | — |
| OLED SSD1306 | SDA | D21 (GPIO21) | I2C0 nativo do ESP32 |
| OLED SSD1306 | SCL | D22 (GPIO22) | I2C0 nativo do ESP32 |
| DHT22 | VCC | 3V3 | — |
| DHT22 | GND | GND | — |
| DHT22 | SDA (dados) | D4 (GPIO4) | GPIO comum; evita os strapping pins |
| Push-button | 1.l | D14 (GPIO14) | Pull-up interno; pressionado lê 0 |
| Push-button | 2.l | GND | — |

Por que **D4** e não D15: o GPIO15 é *strapping pin* do ESP32 (MTDO), com
pull-up interno no boot. Funcionaria, mas não é pino para material didático.

## Grade de posicionamento (requisito 5)

Área útil de 128 × 64 px, fonte de 8 × 8 px por caractere: **16 colunas × 8
linhas**. As linhas 1 e 6 ficam reservadas para os traços separadores, e por
isso não recebem texto.

| Linha | `y` (px) | Constante | Conteúdo |
|---|---|---|---|
| 0 | 0 | `Y_HEADER` | Identificação do painel + indicador de atividade |
| 1 | 10 | `Y_TRACO_TOPO` | Traço horizontal (não é texto) |
| 2 | 16 | `Y_CAMPO_1` | Campo de dados 1 |
| 3 | 24 | `Y_CAMPO_2` | Campo de dados 2 |
| 4 | 32 | `Y_CAMPO_3` | Campo de dados 3 |
| 5 | 40 | — | Livre |
| 6 | 52 | `Y_TRACO_BASE` | Traço horizontal (não é texto) |
| 7 | 56 | `Y_RODAPE` | Endereço I2C descoberto + uptime |

As três telas, na grade:

```
      TELA DE DADOS       TELA DE DIAGNOSTICO      TELA DE ERRO
     +----------------+   +----------------+   +----------------+
   0 |PAINEL 04      /|   |DIAGNOSTICO    /|   |** FALHA **    /|   <- invertida
   1 |----------------|   |----------------|   |----------------|
   2 |Temp      23.4 C|   |Falhas         2|   |DHT22 sem       |
   3 |Umid      59.0 %|   |Seguidas       2|   |resposta        |
   4 |Leituras      37|   |Refresh    500ms|   |Seguidas       2|
   5 |                |   |                |   |                |
   6 |----------------|   |----------------|   |----------------|
   7 |I2C 0x3C     12s|   |botao: dados    |   |ok ha        7s |
     +----------------+   +----------------+   +----------------+
```

**Como o requisito 5 é garantido.** Nenhum campo conta caracteres na mão. Toda
linha passa por `montar_linha(esquerda, direita)`, que corta o que não couber e
reserva ao menos um espaço entre rótulo e valor. A garantia vale para os campos
que ainda não existem. O `formatar_uptime()` reforça o mesmo: troca de unidade
(`s` → `m` → `h`) em vez de deixar o número crescer.

**A tela de erro** usa **inversão de fundo** — `fill(1)` e texto na cor 0. É o
recurso mais forte disponível num display monocromático: dá para perceber a
falha do outro lado da sala, sem ler o texto. Ela se sobrepõe às outras duas:
não é uma terceira opção do botão, e sim um estado que toma a tela.

## Parâmetros ajustáveis (arbitrários)

| Constante | Valor adotado | Faixa aceitável | Por que esse valor |
|---|---|---|---|
| `PERIODO_REFRESH_MS` | 500 | 100 a 2000 | 4 refreshes por leitura tornam visível que as duas taxas são independentes |
| `PERIODO_LEITURA_MS` | 2500 | ≥ 2000 | Margem sobre o mínimo do DHT22; ver Limites |
| `DEBOUNCE_MS` | 50 | 20 a 80 | Janela reiniciada a cada borda do contato |
| `FALHAS_PARA_TELA_ERRO` | 2 | 1 a 5 | Uma falha isolada não deve piscar a tela de erro |
| `SPINNER` | `\|/-\\` | qualquer sequência | Indicador de atividade do requisito 3 |
| `NOME_PAINEL` | `PAINEL 04` | até 15 caracteres | Identificador neutro, sem dado pessoal |
| Pinos | 21/22/4/14 | qualquer GPIO válido | Ver Pinagem |

## Limites determinados (não arbitrários)

| Constante | Valor | Fonte (datasheet / especificação / placa) | Verificado em |
|---|---|---|---|
| `LARGURA_PX` / `ALTURA_PX` | 128 / 64 | Área útil do módulo SSD1306 (datasheet) | 13.09 |
| `LARGURA_FONTE_PX` / `ALTURA_FONTE_PX` | 8 / 8 | Fonte embutida do `framebuf` | 13.09 |
| `COLUNAS` / `LINHAS` | 16 / 8 | Consequência: 128÷8 e 64÷8 | — |
| `ENDERECOS_SSD1306` | `0x3C`, `0x3D` | Endereços possíveis do módulo; descobertos por scan | Confirmado por scan: respondeu em `0x3C` |
| `I2C_FREQ_HZ` | 400000 | Modo *fast* da especificação I2C | 13.09 |
| `DHT22_INTERVALO_MIN_MS` | 2000 | Intervalo mínimo entre leituras (datasheet DHT22) | 13.09 |
| Faixa do DHT22 | −40 a 80 °C, 0 a 100 % | Faixa de medição (datasheet DHT22) | 13.09 |



### Por que 400 kHz e não 100 kHz

Cada `show()` envia o framebuffer inteiro — 1024 bytes, mais o byte de controle,
mais o ACK de cada byte. São cerca de 9200 bits por refresh:

| Clock | Tempo por `show()` | Fração do ciclo de 500 ms |
|---|---|---|
| 100 kHz (*standard*) | ≈ 92 ms | 18 % |
| 400 kHz (*fast*) | ≈ 23 ms | 5 % |

O loop fica **parado** durante esse envio, sem ler o botão. A 100 kHz isso
produzia toques perdidos; o modo *fast* reduz a janela cega em quatro vezes.

## Dependências

| Módulo | Origem (embarcado no firmware / arquivo no projeto) | Verificado em |
|---|---|---|
| `machine` (`Pin`, `I2C`) | Embarcado no firmware MicroPython | 13.09 |
| `time` (`ticks_ms`, `ticks_diff`, `ticks_add`) | Embarcado no firmware MicroPython | 13.09 |
| `dht` | Embarcado no firmware MicroPython | Confirmado: `import dht` funcionou na simulação |
| `framebuf` | Embarcado no firmware MicroPython | Confirmado: usado pelo driver, sem erro de import |
| `ssd1306` | **Arquivo no projeto** (`gabarito/ssd1306.py`) — não vem embarcado neste firmware | 13.09.2026 |

> **Conferido em 13.09.2026**, no firmware `micropython-20231227-v1.22.0`: o
> módulo `ssd1306` **não vem embarcado**. O `import ssd1306` só funciona depois
> de adicionar `ssd1306.py` como arquivo do projeto no editor do Wokwi. Refazer
> esta conferência a cada troca de versão de firmware.

## Como executar

1. Abrir <https://wokwi.com> e criar um novo projeto **MicroPython — ESP32**.
2. Substituir o `diagram.json` pelo de `gabarito/diagram.json`.
3. Substituir o `main.py` pelo de `gabarito/main.py`.
4. Adicionar `gabarito/ssd1306.py` como arquivo novo do projeto (botão de novo
   arquivo no editor). Sem ele o `import ssd1306` falha: o módulo não vem
   embarcado nesta versão de firmware.
5. Clicar em **Play**. O log serial mostra o scan do barramento e o endereço
   encontrado; o painel aparece na tela em seguida.
6. Clicar no sensor DHT22 para ajustar temperatura e umidade; clicar no botão
   para alternar entre o painel e a tela de diagnóstico.

## Roteiro de teste

| # | Ação | Resultado esperado | Resultado obtido |
|---|---|---|---|
| 1 | Rodar a simulação | O log lista os endereços do scan e identifica o SSD1306 | Correto |
| 2 | Remover o fio SDA e rodar | Diagnóstico no log e encerramento controlado, sem traceback |Correto |
| 3 | Observar o painel em regime | Header fixo, campos atualizando, traços nos lugares | sim  |
| 4 | Observar 30 s sem tocar em nada | O indicador de atividade nunca para de girar | sim |
| 5 | Provocar falha no DHT22 | Tela invertida de erro após 2 falhas seguidas | sim |
| 6 | Restaurar o sensor | O painel volta sozinho, e o log registra a recuperação | Correto |
| 7 | Forçar extremos (−40 °C, 100 %, contadores grandes) | Nenhum texto cortado, em nenhuma das três telas | Correto |
| 8 | Clicar o botão várias vezes seguidas | A tela troca em todo toque, no instante do clique | Há a chance haver um pequeno bug ou de não trocar a tela insta ou de demorar pra trocar. Isso ocorre, pois o clique em botão simulado de um mouse é rápido demais para os padrões de click FÍSICOS de um botão. Mas isso não compromete a funcionalidade. |

Um item por requisito funcional. Evidências em `evidencias/`:
`tela-log.PNG` (circuito montado e início do log), `semsda.PNG` (item 2: scan
vazio, diagnóstico e encerramento controlado) e `max.PNG` (item 7: extremos de
−40 °C e 100 % sem texto cortado).

## Limitações da simulação

- **O DHT22 do Wokwi exige atributos iniciais.** Sem `temperature` e `humidity`
  no `diagram.json`, o sensor não responde ao handshake e toda leitura volta
  `ETIMEDOUT`. Em hardware real isso não existe: o sensor responde assim que
  energizado. Foi a causa da primeira falha durante o desenvolvimento.
- **O intervalo mínimo do sensor é aplicado com rigidez.** Pedir exatamente
  2000 ms fica na fronteira e produz erros intermitentes; daí os 2500 ms
  adotados. Em bancada a margem costuma ser mais tolerante.
- **O display não tem inércia.** No Wokwi a troca de framebuffer é instantânea
  e perfeita. Um OLED real tem tempo de resposta do pixel e brilho desigual
  entre regiões.
- **O barramento é ideal.** Não há capacitância de linha, ruído, nem necessidade
  de resistores de pull-up externos em SDA e SCL — que em hardware real são
  obrigatórios e costumam ser a causa de metade dos problemas de I2C.
- **O botão não tem repique real.** O debounce implementado é indispensável em
  bancada, mas na simulação quase não tem o que filtrar.
- **O uptime depende de `ticks_diff()`**, que só devolve resultado correto
  enquanto a diferença couber em metade do período do contador de
  milissegundos. Em execução muito longa o valor exibido deixa de ser
  confiável — `formatar_uptime()` trata o negativo como zero para não mostrar
  lixo, mas o número deixa de valer.

## Referências

- MicroPython — `machine.I2C` (`scan()`, `writeto`, frequência):
  <https://docs.micropython.org/en/latest/library/machine.I2C.html> — acesso em 13.09
- MicroPython — `framebuf` (fonte embutida, `MONO_VLSB`, `text()`):
  <https://docs.micropython.org/en/latest/library/framebuf.html> — acesso em 13.09
- MicroPython — módulo `dht`:
  <https://docs.micropython.org/en/latest/esp32/quickref.html> — acesso em 13.09
- Solomon Systech — SSD1306 datasheet (comandos e inicialização):
  <https://cdn-shop.adafruit.com/datasheets/SSD1306.pdf> — acesso em 13.09
- NXP — I2C-bus specification (modos standard e fast):
  <https://www.nxp.com/docs/en/user-guide/UM10204.pdf> — acesso em 13.09
- Wokwi — documentação do SSD1306:
  <https://docs.wokwi.com/parts/board-ssd1306> — acesso em 13.09

## Controle

- Elaboração (função): Monitoria — Trilha IoT
- Revisão por par (função): `PENDENTE` — Data: `PENDENTE`
- Aprovação (coordenação): `PENDENTE` — Data: `PENDENTE`
