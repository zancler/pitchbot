import os

MEMORY_PATH = "/data/memory.txt"


def load_memory() -> str:
    """Load persistent memory from disk."""
    try:
        with open(MEMORY_PATH) as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def save_memory(content: str) -> str:
    """Overwrite persistent memory with updated content."""
    try:
        os.makedirs("/data", exist_ok=True)
        with open(MEMORY_PATH, "w") as f:
            f.write(content)
        return "Memory saved — I'll remember this across restarts."
    except Exception as e:
        return f"Error saving memory: {e}"
