# Wokwi - Estufa Inteligente

Projeto de estufa inteligente simples, desenvolvido com um ESP32 no ambiente simulado Wokwi.

## Funcionamento

O projeto funciona da seguinte forma:
- Ao iniciar a simulação no Wokwi, o usuário tem a possibilidade de digitar o nome de uma planta no terminal;
- Ao pressionar "Enter", o programa envia o nome da planta (via API) a um modelo de Inteligência Artificial;
- A IA, então, define quais são as condições ideais (de temperatura, umidade e luminosidade) para aquela planta específica;
- Definidos os parâmtros, a API retorna essas informações para que o programa atualize seus thresholds;
- Com base nos novos thresholds, o microcontrolador ativará os atuadores binários - ventilador, lâmpada e umidificador, representados pelos LEDs verde, vermelho e azul, respectivamente -, a depender dos valores medidos pelos sensores;
  - Caso a temperatura esteja acima do ideal, o ventilador (LED verde) será acionado;
  - Caso a luminosidade esteja abaixo do ideal, a lâmpada (LED vermelho) será acionada;
  - Caso a umidade esteja abaixo do ideal, o umidificador (LED azul) será acionado.

## Interfaces

### Simulação no Wokwi

#### Código principal

> Para ver o código (raw file), acesse: [main.py](https://github.com/imbaTIMvel/empreendaiot_examples/tree/main/esp32_wokwi_smart_greenhouse/main.py)

O código principal exerce a função de:
- Receber entrada do usuário (input() ou valor fixo)
- Fazer requisição HTTP pra API
- Realizar a leitura dos sensores:
  - LDR (fotorresistor via ADC)
  - DHT22 (temperatura + umidade)
- Comparar com thresholds
- Controlar os LEDs (p/ representar atuadores binários):
  - LED verde (ventilador)
  - LED vermelho (luz)
  - LED azul (água/umidificador)

#### Diagrama

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

![Diagrama de conexões no Wokwi](images/diagram.png)

### Servidor local

> Para ver o código (raw file), acesse: [greenhouse_server.py](https://github.com/imbaTIMvel/empreendaiot_examples/tree/main/esp32_wokwi_smart_greenhouse/server/greenhouse_server.py)

O servidor local exerce a função de:
- Receber o nome da planta a partir da entrada fornecida pelo usuário (via terminal Wokwi)
- Consultar a IA (modelo: llama-3.1-8b-instant) da Groq
- Receber e retornar JSON com thresholds

## Configuração

Segue, abaixo, o passo a passo para configurar e executar o programa no ambiente simulado Wokwi:
1. No site [Wokwi](https://wokwi.com), selecione a aba "My Projects" no seu perfil e clique no botão "New Project"
2. Selecione o microcontrolador ESP32 padrão (1ª opção), optando pelo "Beginner template" em Micropython
3. Na aba "main.py", substitua o template pelo código Python disponível em: [main.py](https://github.com/imbaTIMvel/empreendaiot_examples/tree/main/esp32_wokwi_smart_greenhouse/main.py)
   - A
4. Na aba "diagram.json", substitua o template pelo JSON disponível em: [diagram.json](https://github.com/imbaTIMvel/empreendaiot_examples/tree/main/esp32_wokwi_smart_greenhouse/diagram.json)
