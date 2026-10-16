# Projeto 05 — Controle de servo motor por PWM

**Placa:** Raspberry Pi Pico (RP2040) · **Linguagem:** MicroPython · **Esforço estimado:** 3 h

## Contexto

Você vai controlar a abertura de uma persiana didática. O potenciômetro indica
a abertura desejada, de 0% a 100%; um servo representa seu mecanismo. Uma mudança
brusca no controle deve resultar em movimento gradual. Pequenas oscilações não
devem provocar novos comandos continuamente.

Ao encerrar, o atuador precisa receber o comando para uma posição segura antes
que os pulsos sejam desligados. Não é suficiente simplesmente interromper o laço.

## Antes de começar: PWM de servo

A informação de posição é transmitida pela **largura do pulso**, repetido
periodicamente. Neste projeto, mantenha 50 Hz, equivalente a 20 ms por período.
A faixa de referência da ficha é aproximadamente 0,5–2,5 ms para 0°–180°;
confirme e registre os extremos na simulação. Não use esses números como
especificação universal de qualquer servo físico.

`machine.PWM` oferece `freq()`, `duty_u16()` e `deinit()`. A escala de duty vai
de 0 a 65535 e expressa a fração do período em nível alto. Para um servo, não
basta copiar diretamente o valor do ADC para o duty: isso poderia comandar
pulsos incompatíveis com o atuador.

Há três conversões a elaborar: ADC → percentual; percentual → ângulo-alvo;
ângulo → largura do pulso → duty. Documente as fórmulas e suas unidades.

## Antes de começar: alvo, comando e posição real

O alvo é a posição solicitada pelo usuário. O ângulo comandado é o que o
programa envia naquele ciclo. Durante a rampa, eles serão diferentes.
Já a posição real é uma grandeza mecânica: este servo não possui um fio de
feedback para o programa medi-la. Identifique corretamente os campos do log.

## Antes de começar: rampa e deadband

**Slew rate** limita a variação de ângulo por ciclo. Implemente o movimento nos
dois sentidos, sem ultrapassar o alvo nem o curso permitido. Relacione o passo
máximo e o período com a velocidade máxima de comando em graus por segundo.

**Deadband** é uma zona de insensibilidade. Defina uma referência de comparação
e mantenha-a coerente: compare com a última referência aceita, para que pequenas
variações acumuladas possam resultar em movimento. A rampa deve continuar até
o alvo aceito mesmo que as novas leituras não ultrapassem a deadband.
Explique sua decisão para os extremos de 0% e 100% e para a primeira leitura.

## Antes de começar: encerrar de forma controlada

Declare uma posição segura adequada à persiana didática e retorne a ela antes
de desligar o PWM. Reserve tempo para o movimento/acomodação. Use `try/finally`
para liberar o periférico, incluindo na interrupção recebida pelo programa.

Use o botão ENCERRAR para demonstrar esse comportamento no simulador. Clicar
Stop desliga a simulação imediatamente e não permite executar o retorno.
Sem feedback e sem energia, o software não garante a posição física do eixo.

## O que montar

Obrigatório:

- Raspberry Pi Pico original (`wokwi-pi-pico`).
- Servo de posição (`wokwi-servo`).
- Potenciômetro (`wokwi-potentiometer`).

A montagem fornecida também inclui um botão vermelho (`wokwi-pushbutton`)
para encerramento. Consulte a tabela de pinagem do README: potenciômetro a
3,3 V, servo a 5 V, terra comum e sinal PWM separado da alimentação.

Extensões opcionais, fora do gabarito básico: display OLED para mostrar ângulo
e dois botões como modo alternativo de abertura/fechamento.

## Requisitos funcionais

1. Mapear linearmente a posição do potenciômetro, 0%–100%, no ângulo do servo.
2. Calibrar os extremos de largura de pulso na simulação e registrar resultados
   e evidências no README.
3. Limitar a variação do ângulo comandado a um passo máximo por ciclo, permitindo
   deslocamento gradual mesmo com uma mudança brusca no potenciômetro.
4. Implementar deadband configurável: variações abaixo do limiar não produzem
   uma nova referência de comando.
5. Exibir percentual e ângulo no log serial a cada mudança efetiva; incluir
   unidades e distinguir alvo de comando.
6. Ao encerrar, retornar à posição segura antes de desligar o PWM. Não comandar
   ângulos nem pulsos fora da faixa validada para o atuador.

## Parâmetros e limites

Separe os dois blocos no topo do arquivo e justifique as escolhas.

### Ajustáveis (arbitrários)

| Parâmetro | Referência inicial | O que investigar |
|---|---|---|
| `PASSO_MAX_GRAUS` | 2° por ciclo | Suavidade e tempo de deslocamento |
| `DEADBAND_PCT` | 1,5 ponto percentual | Estabilidade e sensibilidade |
| `ANGULO_SEGURO` | 0° | Por que essa posição é segura no contexto didático |
| `PERIODO_COMANDO_MS` | 20 ms | Relação com a velocidade de comando |
| `TEMPO_ACOMODACAO_MS` | 500 ms | Tempo de manutenção dos pulsos no encerramento |

Os limites de pulso são resultados de calibração: partir da referência nominal
não substitui medir e registrar. Não os escolha para acelerar o servo.

### Determinados (não arbitrários)

- Frequência adotada para este projeto: **50 Hz**, período de **20 ms**.
- Curso do servo simulado: **0° a 180°**.
- Faixa nominal de referência: **aproximadamente 0,5–2,5 ms**, sujeita à calibração.
- Relação matemática: **duty cycle = largura de pulso / período**.
- APIs `read_u16()` e `duty_u16()`: escala **0 a 65535**; essa escala não informa,
  por si só, a resolução física do periférico.

## O que entregar

- `aluno/main.py` com os TODOs resolvidos, validações e encerramento controlado.
- Circuito coerente com os pinos do programa.
- README no formato fornecido, com parâmetros justificados, tabela de calibração
  preenchida e resultados **realmente observados**.
- Capturas e log serial em `evidencias/`, incluindo extremos, rampa, deadband e
  retorno seguro. Inclua medição de pulsos quando disponível.

As instruções para executar no navegador e no VS Code estão no README. No
VS Code, Play precisa ser seguido do envio de `main.py` com `mpremote`.

## Roteiro de teste

| # | Ação | O que verificar |
|---|---|---|
| 1 | Levar o controle a 0%, aproximadamente 50% e 100% | Linearidade, alvo e curso permitido |
| 2 | Observar e medir cada ponto de calibração | Correspondência entre pulso e ângulo |
| 3 | Mudar bruscamente de um extremo ao outro e voltar | Passo máximo, continuidade e ausência de ultrapassagem |
| 4 | Oscilar abaixo da deadband e depois ultrapassá-la | Ausência de novo alvo abaixo do limiar e reação à mudança acumulada |
| 5 | Observar o log em movimento e em repouso | Percentual, ângulo, unidades e ausência de linhas repetidas |
| 6 | Pressionar ENCERRAR com o servo distante da posição segura | Retorno, acomodação e desligamento, nessa ordem |

## Perguntas para o relatório

Responda no README, em uma ou duas frases cada:

1. Qual é a diferença entre largura de pulso e duty cycle? Por que não aplicar
   diretamente o valor do ADC ao PWM do servo?
2. Como passo máximo e período determinam a velocidade máxima de comando?
3. Por que comparar a deadband somente com a amostra imediatamente anterior
   pode impedir a reação a uma mudança lenta?
4. Por que os extremos de pulso precisam de calibração? Que valores você observou?
5. O log informa posição desejada, comandada ou medida? Qual informação falta
   para confirmar que o eixo chegou à posição?
6. Qual é a diferença entre pressionar ENCERRAR e clicar Stop? O que acontece
   com a capacidade de manter posição após desligar o sinal?
