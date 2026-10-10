import yaml

class RobotFileOps:
    def load(self, filepath: str) -> list:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data

    def save(self, steps: list, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(steps, f, sort_keys=False)