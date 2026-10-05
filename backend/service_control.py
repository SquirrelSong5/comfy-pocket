"""Track and stop only the Pocket server owned by a particular data directory."""
import json
from pathlib import Path
import sys

import psutil


def record_server(home):
    process = psutil.Process()
    record = {'pid': process.pid, 'created': process.create_time(), 'cwd': process.cwd()}
    path = Path(home) / 'pocket-process.json'
    path.write_text(json.dumps(record), encoding='utf-8')
    return record


def clear_record(home, record):
    path = Path(home) / 'pocket-process.json'
    try:
        if json.loads(path.read_text(encoding='utf-8')) == record:
            path.unlink()
    except (FileNotFoundError, ValueError):
        pass


def stop_server(home):
    home = Path(home).resolve()
    path = home / 'pocket-process.json'
    if not path.exists():
        return 'No managed Pocket process found / 未找到此配置目录的 Pocket 进程；旧版或手动启动请在原终端按 Ctrl+C。'
    record = json.loads(path.read_text(encoding='utf-8'))
    try:
        process = psutil.Process(record['pid'])
        if process.create_time() != record['created']:
            clear_record(home, record)
            return 'Pocket has already stopped / Pocket 已停止。'
        command = process.cmdline()
        cwd = Path(process.cwd()).resolve()
        process_home = Path(process.environ().get('COMFY_POCKET_HOME', str(cwd))).resolve()
        if command[-2:] != ['-m', 'backend.server'] or cwd != Path(record['cwd']).resolve() or process_home != home:
            raise ValueError('Process identity mismatch; nothing stopped / 进程身份不匹配，未停止任何进程。')
        process.terminate()
        try:
            process.wait(timeout=8)
        except psutil.TimeoutExpired as exc:
            raise ValueError('Pocket has not exited yet / Pocket 尚未退出，请检查原终端。') from exc
    except psutil.NoSuchProcess:
        pass
    clear_record(home, record)
    return 'Pocket stopped. ComfyUI was not stopped. / Pocket 已关闭，ComfyUI 未停止。'


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3 or sys.argv[1] != 'stop':
            raise ValueError('Usage: python -m backend.service_control stop HOME')
        print(stop_server(sys.argv[2]))
    except (ValueError, KeyError, OSError, psutil.Error) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
