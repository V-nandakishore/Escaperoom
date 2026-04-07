import serial  # type: ignore
import serial.tools.list_ports  # type: ignore


class Talker:
    TERMINATOR = "\r".encode("utf-8")

    def __init__(self, port=None, baudrate=115200, timeout=1):
        self.port = port or self.find_pico_port()
        if not self.port:
            raise RuntimeError("Pico serial port not found.")
        self.serial = serial.Serial(self.port, baudrate, timeout=timeout)

    @staticmethod
    def find_pico_port():
        for p in serial.tools.list_ports.comports():
            hwid = (p.hwid or "").lower()
            desc = (p.description or "").lower()
            if "2e8a" in hwid or "pico" in desc or "circuitpython" in desc:
                return p.device
        return None

    def send(self, text: str):
        line = f"{text}\r\f"
        self.serial.write(line.encode("utf-8"))
        reply = self.receive().replace("--> ", "")
        if reply and reply != text:
            raise ValueError(f"expected {text} got {reply}")
        return True

    def change_code(self, code: str):
        safe = code.replace("\\", "\\\\").replace('"', '\\"')
        return self.send(f'change_code("{safe}")')

    def change_input(self, key: str):
        safe = key.replace("\\", "\\\\").replace('"', '\\"')
        return self.send(f'change_input("{safe}")')

    def receive(self) -> str:
        line = self.serial.read_until(self.TERMINATOR)
        return line.decode("utf-8", errors="ignore").strip()

    def close(self):
        self.serial.close()
