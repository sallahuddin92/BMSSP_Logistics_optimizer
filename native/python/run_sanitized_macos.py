"""Run a sanitized extension with CLT ASan and a Homebrew framework virtualenv.

The small Homebrew bin launcher discards the preload before framework exec.
This helper starts the framework executable directly, preserving the venv prefix.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', required=True)
    parser.add_argument('python_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.python_args
    if command[:1] == ['--']:
        command = command[1:]
    if sys.platform != 'darwin' or sys.prefix == sys.base_prefix or not command:
        parser.error('Requires macOS, an active virtualenv, and Python arguments after --')
    interpreter = Path(sys.base_prefix) / 'Resources/Python.app/Contents/MacOS/Python'
    resource = subprocess.check_output([args.compiler, '-print-resource-dir'], text=True).strip()
    runtime = Path(resource) / 'lib/darwin/libclang_rt.asan_osx_dynamic.dylib'
    if not interpreter.is_file() or not runtime.is_file():
        parser.error('This helper requires a framework Python and a matching Clang ASan runtime')
    environment = {**os.environ, 'DYLD_INSERT_LIBRARIES': str(runtime),
                   '__PYVENV_LAUNCHER__': sys.executable,
                   'ASAN_OPTIONS': 'detect_leaks=0',
                   'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'}
    print(f'Framework interpreter: {interpreter}; ASan runtime: {runtime}; venv: {sys.prefix}', flush=True)
    sys.exit(subprocess.run([str(interpreter), *command], env=environment).returncode)


if __name__ == '__main__':
    main()
