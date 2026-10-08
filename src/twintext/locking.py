"""Advisory file locks shared by native Windows and Linux processes."""

import errno
import sys
import time
from contextlib import contextmanager


def acquire_lock(path, blocking=True, timeout=30):
    stream = path.open("a+b")
    try:
        if sys.platform == "win32":
            import msvcrt

            if path.stat().st_size == 0:
                stream.write(b"\0")
                stream.flush()
            deadline = time.monotonic() + timeout
            while True:
                stream.seek(0)
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                        raise
                    if not blocking:
                        stream.close()
                        return None
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"Timed out waiting for {path.name}") from exc
                    time.sleep(0.05)
        else:
            import fcntl

            try:
                flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
                fcntl.flock(stream, flags)
            except BlockingIOError:
                stream.close()
                return None
        return stream  # Closing the descriptor releases its OS lock.
    except BaseException:
        stream.close()
        raise


@contextmanager
def file_lock(path):
    stream = acquire_lock(path)
    try:
        yield stream
    finally:
        stream.close()
