import requests

BASE_URL = 'https://raw.githubusercontent.com/Alpha-Stochastic-Research/asr-quant/71b52097f9bfb3c923deab7b3a441c161fc33f3f/dinav-qf-kaggle-cli/dinav_qf_125m_pilot.py'

base = requests.get(BASE_URL, timeout=60)
base.raise_for_status()
source = base.text

marker = "env = os.environ.copy()\nenv['PYTHONUNBUFFERED'] = '1'\nstart = time.time()\nproc = subprocess.Popen("
if marker not in source:
    raise RuntimeError('Unable to patch base launcher: process marker not found')

injection = r'''import threading

def _disk_gb(path):
    usage = shutil.disk_usage(path)
    return usage.total / (1024 ** 3), usage.used / (1024 ** 3), usage.free / (1024 ** 3)


def _prune_checkpoints_once():
    if not CHECKPOINT_DIR.exists():
        return
    now = time.time()
    checkpoints = sorted(
        CHECKPOINT_DIR.glob('DINAV-QF-125M-*.pt'),
        key=lambda p: p.stat().st_mtime,
    )
    stable = [p for p in checkpoints if now - p.stat().st_mtime > 30]
    # Keep only the newest stable checkpoint. The newest file overall may still be writing.
    for path in stable[:-1]:
        try:
            size_gb = path.stat().st_size / (1024 ** 3)
            path.unlink()
            print('DISK_GUARD_PRUNED', str(path), f'{size_gb:.3f}GB', flush=True)
        except FileNotFoundError:
            pass
    # Remove abandoned temporary checkpoint files only when clearly stale.
    for path in CHECKPOINT_DIR.glob('*.tmp'):
        try:
            if now - path.stat().st_mtime > 180:
                path.unlink()
                print('DISK_GUARD_REMOVED_STALE_TMP', str(path), flush=True)
        except FileNotFoundError:
            pass


def _disk_guard(stop_event):
    while not stop_event.wait(10):
        try:
            _prune_checkpoints_once()
            total, used, free = _disk_gb(WORK)
            print('DISK_GUARD', f'total={total:.2f}GB', f'used={used:.2f}GB', f'free={free:.2f}GB', flush=True)
            if free < 4.0:
                # Extra cleanup of reproducible intermediates. Never delete the newest checkpoint.
                for candidate in [ZIP_PATH, OPEN_CORPUS]:
                    try:
                        if candidate.exists():
                            size_gb = candidate.stat().st_size / (1024 ** 3)
                            candidate.unlink()
                            print('DISK_GUARD_REMOVED_REPRODUCIBLE', str(candidate), f'{size_gb:.3f}GB', flush=True)
                    except FileNotFoundError:
                        pass
                _prune_checkpoints_once()
        except Exception as exc:
            print('DISK_GUARD_WARNING', repr(exc), flush=True)


env = os.environ.copy()
env['PYTHONUNBUFFERED'] = '1'
stop_disk_guard = threading.Event()
disk_guard_thread = threading.Thread(target=_disk_guard, args=(stop_disk_guard,), daemon=True)
disk_guard_thread.start()
start = time.time()
proc = subprocess.Popen('''
source = source.replace(marker, injection, 1)

wait_marker = "exit_code = proc.wait()\nelapsed = time.time() - start"
if wait_marker not in source:
    raise RuntimeError('Unable to patch base launcher: completion marker not found')
source = source.replace(
    wait_marker,
    "exit_code = proc.wait()\nstop_disk_guard.set()\ndisk_guard_thread.join(timeout=15)\n_prune_checkpoints_once()\ntotal_gb, used_gb, free_gb = _disk_gb(WORK)\nprint('DISK_GUARD_FINAL', f'total={total_gb:.2f}GB', f'used={used_gb:.2f}GB', f'free={free_gb:.2f}GB', flush=True)\nelapsed = time.time() - start",
    1,
)

exec(compile(source, BASE_URL, 'exec'), globals(), globals())
