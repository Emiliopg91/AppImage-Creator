class DesktopParser:
    data = {}

    def __init__(self, file_path) -> None:
        with open(file_path, 'r', encoding='utf-8') as file:
            self.data = {}
            current_section = None

            for line in file:
                line = line.strip()
                # Ignorar comentarios y líneas vacías
                if not line or line.startswith('#'):
                    continue

                # Detectar nueva sección
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                    self.data[current_section] = {}
                elif '=' in line and current_section:
                    # Dividir clave y valor
                    key, value = map(str.strip, line.split('=', 1))
                    self.data[current_section][key] = value
