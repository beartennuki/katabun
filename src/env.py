from pathlib import Path

from dotenv import load_dotenv


def load_katabun_env():
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_path)
    return env_path
