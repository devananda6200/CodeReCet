import psutil


def get_system_cpu_percent() -> float:
    return float(psutil.cpu_percent(interval=None))


def get_process_memory_mb() -> float:
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)

