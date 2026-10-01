"""Ligação celular <-> micro:bit via Bluetooth (serviço UART do micro:bit).

Protocolo: uma mensagem de texto por linha, terminando em "\\n", igual nos dois sentidos.
    SL  seta esquerda ligada
    SR  seta direita ligada
    S0  setas desligadas
    B1  freio aceso
    B0  freio apagado

Celular -> micro:bit: setas (tela ou automáticas) e o freio detectado pelo celular.
micro:bit -> celular: só as setas dos botões A/B (usados para teste).
O micro:bit fica na traseira da bike; a matriz de LEDs é a luz (quadrado cheio = freio).

A conexão Bluetooth (BLE) ainda não foi implementada. Por enquanto, conectar()
devolve False e enviar() não faz nada, e o app funciona normalmente sem o micro:bit.
"""


class MicrobitLink:
    # UUIDs do serviço UART do micro:bit (Nordic UART)
    UART_SERVICE = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
    UART_TX = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'   # micro:bit -> celular (indicate)
    UART_RX = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'   # celular -> micro:bit (write)

    def __init__(self, on_message):
        self.on_message = on_message
        self.conectado = False

    def conectar(self):
        # TODO: procurar o micro:bit e assinar UART_TX (BLE no Android via pyjnius)
        return False

    def desconectar(self):
        self.conectado = False

    def enviar(self, msg):
        if not self.conectado:
            return
        # TODO: escrever (msg + '\n').encode() em UART_RX

    def _ao_receber(self, linha):
        msg = linha.strip()
        if msg:
            self.on_message(msg)
