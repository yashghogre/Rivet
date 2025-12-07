import asyncio
import io
import tarfile
import time
from typing import Dict, Tuple

import docker


def _create_tar_stream(file_map: Dict[str, str]) -> io.BytesIO:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        for filename, content in file_map.items():
            encoded = content.encode("utf-8")
            info = tarfile.TarInfo(name=filename)
            info.size = len(encoded)
            info.mtime = time.time()
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(encoded))
    stream.seek(0)
    return stream


def _run_sync_test(sdk_code: str, test_code: str) -> Tuple[int, str]:
    client = docker.from_env()
    container = None
    try:
        container = client.containers.run(
            "python:3.11-slim",
            command="tail -f /dev/null",
            detach=True,
            working_dir="/app",
        )

        files = {
            "client.py": sdk_code,
            "test_client.py": test_code,
        }
        tar_stream = _create_tar_stream(files)
        container.put_archive("/app", tar_stream)

        # NOTE: For installing dependencies, we'll later set it up
        # to scan imports and install. Keeping it simple for now.
        install_res = container.exec_run(
            "pip install requests pydantic pytest httpx pytest-asyncio"
        )
        if install_res.exit_code != 0:
            return 1, f"Dependency installation failed:\n{install_res.output.decode()}"

        test_res = container.exec_run(
            "python -m pytest test_client.py -v -p asyncio --asyncio-mode=auto"
        )
        return test_res.exit_code, test_res.output.decode("utf-8")

    except Exception as e:
        return 1, f"Docker Infrastructure Error: {str(e)}"

    finally:
        if container:
            try:
                container.stop(timeout=1)
                container.remove()
            except Exception:
                pass


async def run_safe_test(sdk_code: str, test_code: str) -> Tuple[bool, str]:
    exit_code, logs = await asyncio.to_thread(_run_sync_test, sdk_code, test_code)
    return (exit_code == 0), logs
