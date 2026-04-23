# Wokwi - Estufa Inteligente

Projeto de estufa inteligente simples, desenvolvido com um ESP32 no ambiente simulado Wokwi.

## Simulação no Wokwi

### Código principal

> Para ver o código (raw file), acesse: [main.py](https://github.com/imbaTIMvel/empreendaiot_examples/tree/main/esp32_wokwi_smart_greenhouse/main.py)

O fluxo de controle exerce a função de:
- Entrada do usuário (input() ou valor fixo)
- Requisição HTTP pra API
- Leitura dos sensores:
  - LDR (fotorresistor via ADC)
  - DHT22 (temperatura + umidade)
- Comparação com thresholds
- Controle dos LEDs (p/ representar atuadores binários):
  - LED verde (ventilador)
  - LED vermelho (luz)
  - LED azul (água/umidificador)

### Diagrama

> Para ver o diagrama (raw file), acesse: [diagram.json](https://github.com/imbaTIMvel/empreendaiot_examples/tree/main/esp32_wokwi_smart_greenhouse/diagram.json)

O diagrama faz uso dos seguintes componentes:
- 1 ESP32
- 1 Módulo sensor fotorresistor (LDR)
- 1 Sensor digital de temperatura e umidade (DHT22)
- 3 LEDs 5mm padrão:
  - 1 verde
  - 1 vermelho
  - 1 azul
- 3 resistores de 220 Ω

Seguindo o seguinte esquema de conexões:

| ESP32 | Intermediário | LDR | DHT22 | LED verde | LED vermelho | LED azul |
| ----- | ------------- | --- | ----- | --------- | ------------ | -------- |
|  3V3  |      ---      | VCC |  VCC  |    ---    |      ---     |    ---   |
|  GND  |      ---      | GND |  GND  |     C     |       C      |     C    |
|   4   |      ---      | --- |  SDA  |    ---    |      ---     |    ---   |
|   16  | Resistor 220Ω | --- |  ---  |     A     |      ---     |    ---   |
|   17  | Resistor 220Ω | --- |  ---  |    ---    |       A      |    ---   |
|   18  | Resistor 220Ω | --- |  ---  |    ---    |      ---     |     A    |
|   34  |      ---      |  AO |  ---  |    ---    |      ---     |    ---   |

Como pode ser visto na imagem a seguir:

![Alt Text](https://github.com/imbaTIMvel/empreendaiot_examples/tree/main/esp32_wokwi_smart_greenhouse/images/diagram.png)

## Servidor local

> Para ver o código (raw file), acesse: [greenhouse_server.py](https://github.com/imbaTIMvel/empreendaiot_examples/tree/main/esp32_wokwi_smart_greenhouse/greenhouse_server.py)
