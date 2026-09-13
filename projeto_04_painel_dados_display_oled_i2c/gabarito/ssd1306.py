"""
Driver minimo para o display OLED SSD1306 128x64 no barramento I2C.
EmpreendAIoT / Instituto Hardware BR - Monitoria, Trilha IoT

Este arquivo e uma DEPENDENCIA, nao material didatico: o aluno importa e usa,
nao precisa ler linha a linha. Ele existe porque o modulo `ssd1306` pode nao
vir embarcado no firmware MicroPython em uso - confira no editor do Wokwi e
registre o resultado, com data, na secao Dependencias do README.

A sequencia de inicializacao abaixo segue o datasheet do SSD1306 (secao 10,
tabela de comandos). A classe herda de framebuf.FrameBuffer, e e dai que vem
todo o desenho: text(), fill(), pixel(), hline(), rect(). O framebuffer vive
na memoria da placa; nada aparece na tela ate show() ser chamado.
"""

import framebuf

# --- limites determinados pelo componente: NAO alterar ---
LARGURA = 128          # pixels (datasheet SSD1306)
ALTURA = 64            # pixels
PAGINAS = ALTURA // 8  # o controlador organiza a memoria em paginas de 8 linhas

# Comandos do datasheet usados na inicializacao.
_DISPLAY_OFF = 0xAE
_DISPLAY_ON = 0xAF
_MEM_ADDR_MODE = 0x20
_COL_ADDR = 0x21
_PAGE_ADDR = 0x22
_START_LINE = 0x40
_SEG_REMAP = 0xA1
_MUX_RATIO = 0xA8
_COM_SCAN_DEC = 0xC8
_DISP_OFFSET = 0xD3
_COM_PIN_CFG = 0xDA
_DISP_CLK_DIV = 0xD5
_PRECHARGE = 0xD9
_VCOM_DESEL = 0xDB
_CONTRASTE = 0x81
_ENTIRE_ON = 0xA4
_NORMAL = 0xA6
_CHARGE_PUMP = 0x8D


class SSD1306_I2C(framebuf.FrameBuffer):
    def __init__(self, i2c, endereco):
        self.i2c = i2c
        self.endereco = endereco
        self.buffer = bytearray(PAGINAS * LARGURA)
        super().__init__(self.buffer, LARGURA, ALTURA, framebuf.MONO_VLSB)
        self.init_display()

    def comando(self, valor):
        # 0x80 no primeiro byte = "o proximo byte e comando, nao dado"
        self.i2c.writeto(self.endereco, bytes([0x80, valor]))

    def init_display(self):
        sequencia = (
            _DISPLAY_OFF,
            _MEM_ADDR_MODE, 0x00,    # enderecamento horizontal
            _START_LINE | 0x00,
            _SEG_REMAP,              # espelha as colunas
            _MUX_RATIO, ALTURA - 1,
            _COM_SCAN_DEC,           # varre as linhas de baixo para cima
            _DISP_OFFSET, 0x00,
            _COM_PIN_CFG, 0x12,      # 0x12 para paineis 128x64
            _DISP_CLK_DIV, 0x80,
            _PRECHARGE, 0xF1,
            _VCOM_DESEL, 0x30,
            _CONTRASTE, 0xFF,
            _ENTIRE_ON,              # mostra o conteudo da RAM, nao tudo aceso
            _NORMAL,                 # sem inversao global
            _CHARGE_PUMP, 0x14,      # bomba de carga interna ligada
            _DISPLAY_ON,
        )
        for valor in sequencia:
            self.comando(valor)
        self.fill(0)
        self.show()

    def show(self):
        # Sem esta chamada o desenho fica so no framebuffer da placa.
        self.comando(_COL_ADDR)
        self.comando(0)
        self.comando(LARGURA - 1)
        self.comando(_PAGE_ADDR)
        self.comando(0)
        self.comando(PAGINAS - 1)
        # 0x40 no primeiro byte = "o que vem depois e dado para a GDDRAM"
        self.i2c.writeto(self.endereco, b"\x40" + self.buffer)

    def contraste(self, valor):
        self.comando(_CONTRASTE)
        self.comando(valor)
