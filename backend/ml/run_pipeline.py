"""Pipeline completo: features -> train -> predict."""
import subprocess
import sys
from pathlib import Path

STEPS = [
    ("Gerando features do banco...", "ml/features.py"),
    ("Treinando modelo...", "ml/train.py"),
    ("Gerando predicoes...", "ml/predict.py"),
]

def main():
    print("=== Pipeline ML PharmaPredict ===\n")
    backend_dir = Path(__file__).parent.parent

    for msg, script in STEPS:
        print(f">>> {msg}")
        result = subprocess.run(
            [sys.executable, script],
            cwd=str(backend_dir),
        )
        if result.returncode != 0:
            print(f"\nErro ao executar {script}")
            sys.exit(1)
        print()

    print("=== Pipeline concluido com sucesso ===")

if __name__ == "__main__":
    main()
