# 02 — Leitura de potenciômetro (ADC)

## Objetivo

Ler um potenciômetro pelo conversor A/D e transformar o valor *raw* em grandezas
físicas — tensão e percentual de nível de um reservatório. O projeto ensina
resolução, tensão de referência, ruído de leitura e, principalmente, a diferença
entre o número que o ADC devolve e a grandeza que ele representa.

## Ambiente

- **Placa:** ESP32 DevKit V1 (`board-esp32-devkit-v1`). Escolhida por ser a placa
  usada nos projetos 7 a 9 e 12 desta trilha, o que evita trocar de hardware no
  meio do percurso; o projeto roda igualmente em Raspberry Pi Pico trocando o
  pino do ADC e removendo a chamada de atenuação (`atten()`), que é específica
  do ESP32.
- **Firmware / versão do MicroPython:** `micropython-20231227-v1.22.0` (declarado
  em `attrs.env` no `diagram.json`).
- **Link da simulação publicada:** <https://wokwi.com/projects/474831894996008961>

## Componentes

| Componente (nome no Wokwi) | Qtd | Obrigatório / Opcional | Observação |
|---|---|---|---|
| `board-esp32-devkit-v1` | 1 | Obrigatório | Placa da simulação |
| `wokwi-potentiometer` | 1 | Obrigatório | Representa a boia do reservatório |
| `wokwi-led` | 1 | Opcional | Brilho proporcional à leitura (PWM) |
| `wokwi-resistor` | 1 | Opcional | 220 Ω, em série com o LED |
| `wokwi-slide-potentiometer` | — | Opcional | Alternativa mais intuitiva de "nível" |

## Pinagem

| Componente | Pino do componente | Pino da placa | Observação |
|---|---|---|---|
| Potenciômetro | VCC | 3V3 | Extremo superior do divisor |
| Potenciômetro | GND | GND | Extremo inferior do divisor |
| Potenciômetro | SIG | D34 (GPIO34) | ADC1_CH6; GPIO34 é entrada apenas |
| LED (opcional) | A (ânodo) | D23 via resistor 220 Ω | Saída PWM |
| LED (opcional) | C (cátodo) | GND | — |

Por que **ADC1**: no ESP32, os canais do ADC2 são usados pelo rádio e ficam
indisponíveis com o Wi-Fi ativo. Neste projeto não há Wi-Fi, mas a convenção
vale para toda a trilha.

## Parâmetros ajustáveis (arbitrários)

| Constante | Valor adotado | Faixa aceitável | Por que esse valor |
|---|---|---|---|
| `PERIODO_AMOSTRA_MS` | 50 | 20 a 1000 | 20 amostras/s: o LED acompanha o giro sem atraso perceptível |
| `N_MEDIA_MOVEL` | 5 | 4 a 32 | 5 × 50 ms = 250 ms de janela: suaviza sem atrasar a resposta (ver nota abaixo) |
| `THRESHOLD_REPORTE_PCT` | 1.0 | 0,5 a 5,0 | 1 % ≈ 33 mV, acima da flutuação observada com o eixo parado |
| `PERIODO_HEARTBEAT_MS` | 5000 | 0 (desliga) ou 2000 a 30000 | Prova que o loop não travou quando nada varia |
| `PWM_FREQ_HZ` | 1000 | 200 a 5000 | Acima da frequência de cintilação perceptível |
| `PIN_POT` / `PIN_LED` | 34 / 23 | qualquer pino ADC1 / qualquer GPIO de saída | Livres, respeitada a restrição do ADC1 |

## Limites determinados (não arbitrários)

| Constante | Valor | Fonte (datasheet / especificação / placa) | Verificado em |
|---|---|---|---|
| `ADC_MAX_U16` | 65535 | API do MicroPython: `machine.ADC.read_u16()` reescala qualquer ADC para 0–65535 | 11.09.2026 |
| `ADC_BITS_NATIVOS` | 12 | Resolução nativa do SAR ADC do ESP32 (0–4095); idem no RP2040 | 11.09.2026 |
| `V_REF_V` | 3,3 V | Tensão de alimentação / referência da placa ESP32 DevKit V1 | 11.09.2026 |
| `PWM_MAX_U16` | 65535 | API do MicroPython: escala de `PWM.duty_u16()` | 11.09.2026 |
| Atenuação de entrada | `ATTN_11DB` | Única atenuação do ESP32 que cobre a faixa até ~3,3 V; com 0 dB a leitura satura por volta de 1,0 V | 11.09.2026 |

> **Latência do filtro.** O atraso entre girar o eixo e ver o valor final é o
> produto `PERIODO_AMOSTRA_MS × N_MEDIA_MOVEL` — com os valores adotados, 250 ms.
> Os valores sugeridos na especificação (200 ms × 10 = 2 s) foram calibrados para
> baixo após teste no Wokwi: a resposta do LED ficava visivelmente lenta. A
> especificação trata esses dois valores como sugestão inicial, não requisito.



### As duas escalas não se misturam

O erro clássico deste projeto é converter com a escala errada. São duas:

| Escala | Faixa | De onde vem |
|---|---|---|
| Nativa | 0 a 4095 | Resolução física do ADC (12 bits) |
| `read_u16()` | 0 a 65535 | Reescalonamento imposto pela API do MicroPython |

Este código trabalha **inteiramente** na escala `u16`. Como o conversor é de 12
bits, o valor lido não anda de 1 em 1: ele pula degraus. Isso é quantização, não
ruído — nenhum filtro cria precisão que o conversor não tem.

Para observar o degrau bruto, rodar com `N_MEDIA_MOVEL = 1` (item 7 do roteiro
de teste): com o filtro ligado, a coluna `raw` mostra a média da janela, que não
cai exatamente sobre os degraus.

## Dependências

| Módulo | Origem (embarcado no firmware / arquivo no projeto) | Verificado em |
|---|---|---|
| `machine` (`Pin`, `ADC`, `PWM`) | Embarcado no firmware MicroPython |  11.09.2026 |
| `time` (`ticks_ms`, `ticks_diff`, `ticks_add`) | Embarcado no firmware MicroPython | 11.09.2026 |

Nenhuma biblioteca auxiliar precisa ser adicionada ao projeto.

## Como executar

1. Abrir <https://wokwi.com> e criar um novo projeto **MicroPython — ESP32**.
2. Substituir o conteúdo de `diagram.json` pelo arquivo de `gabarito/diagram.json`.
3. Substituir o conteúdo de `main.py` pelo arquivo de `gabarito/main.py`.
4. Clicar em **Play**. O monitor serial exibe o cabeçalho e a primeira linha de
   dados quando a janela da média enche (≈ 250 ms com os valores adotados).
5. Girar o eixo do potenciômetro com o mouse e acompanhar as colunas.
6. Para rodar pela extensão do VS Code, usar o `gabarito/wokwi.toml` incluído.

## Roteiro de teste

| # | Ação | Resultado esperado | Resultado obtido |
|---|---|---|---|
| 1 | Rodar a simulação sem tocar no potenciômetro | Uma linha `inicial` e, depois, apenas linhas `periodico` a cada 5 s | linhas "inicial" e "periodico" atingidas corretamente |
| 2 | Girar o potenciômetro até o mínimo | raw ≈ 0 · 0,00 V · 0,0 % | atingido com sucesso o esperado |
| 3 | Girar até o máximo | raw ≈ 65535 · 3,30 V · 100,0 % | atingido com sucesso o esperado |
| 4 | Parar no meio do curso | ≈ 50 % · ≈ 1,65 V | Atingido com sucesso o esperado |
| 5 | Girar lentamente de ponta a ponta | Uma linha `delta` por variação ≥ 1 %, sem repetição | Resultado esperado obtido. Cada giro lento imprimia um novo número pelo menos 1% maior |
| 6 | Deixar parado 1 min após o giro | Nenhuma linha `delta`; colunas seguem alinhadas | Nenhuma linha delta imprimida, somente periódicas. Resultado esperado obtido. |
| 7 | Rodar com `N_MEDIA_MOVEL = 1` (filtro desligado) e conferir o passo do valor raw | O valor pula degraus fixos, não anda de 1 em 1 (quantização de 12 bits) | Todos os valores de raw são múltiplos de 16 (704 = 16×44, 1472 = 16×92, 2176 = 16×136). Trecho de `evidencias/log-n1-quantizacao.txt`:<br>`550 0 0.00 0.0% delta`<br>`4150 704 0.04 1.1% delta`<br>`5500 1472 0.07 2.2% delta`<br>`7450 2176 0.11 3.3% delta` |
| 8 | Observar o LED opcional ao longo do curso | Brilho cresce junto com o percentual | Resultado Esperado Obtido. |

Um item por requisito funcional; evidência correspondente em `evidencias/`
(screenshot do circuito em execução + captura do log serial).



## Limitações da simulação

- **Não há ruído analógico real.** No Wokwi a leitura é limpa e estável; em
  hardware, o mesmo potenciômetro oscila alguns LSBs mesmo parado. A média móvel
  parece quase desnecessária na simulação — em bancada, não é.
- **A não linearidade do ADC do ESP32 não é reproduzida.** No silício real a
  curva se achata perto de 0 V e perto de 3,3 V, e os extremos exatos costumam
  ser inatingíveis (a leitura satura antes). O simulador entrega uma reta de
  ponta a ponta. Esse efeito deve ser **documentado**, nunca compensado com um
  fator mágico no código.
- **A tensão de referência é ideal.** Não há queda no regulador, ruído de fonte
  nem deriva térmica.
- **O potenciômetro simulado é perfeitamente linear** e não tem zona morta,
  desgaste de pista nem repique de contato.
- **O tempo do simulador não é tempo real garantido:** o período de amostragem
  observado pode variar conforme a carga da máquina do usuário.

## Referências

- MicroPython — `machine.ADC` (classe, `read_u16()`, atenuação no ESP32):
  <https://docs.micropython.org/en/latest/library/machine.ADC.html> — acesso em 11.09.2026
- MicroPython — porta ESP32, notas de ADC e pinagem:
  <https://docs.micropython.org/en/latest/esp32/quickref.html> — acesso em 11.09.2026
- MicroPython — `time.ticks_ms()` / `time.ticks_diff()` (overflow do contador):
  <https://docs.micropython.org/en/latest/library/time.html> — acesso em 11.09.2026
- Espressif — ESP32 Technical Reference Manual, capítulo do SAR ADC:
  <https://www.espressif.com/sites/default/files/documentation/esp32_technical_reference_manual_en.pdf> — acesso em 11.09.2026
- Wokwi — documentação do potenciômetro:
  <https://docs.wokwi.com/parts/wokwi-potentiometer> — acesso em 11.09.2026

## Controle

- Elaboração (função): Monitoria — Trilha IoT
- Revisão por par (função): `PENDENTE` — Data: `PENDENTE`
- Aprovação (coordenação): `PENDENTE` — Data: `PENDENTE`
