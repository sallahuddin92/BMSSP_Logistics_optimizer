"""Build in an external directory using this virtual environment's Python/tooling."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-dir', required=True, type=Path)
    parser.add_argument('--config', choices=['Debug', 'Release'], default='Release')
    parser.add_argument('--compiler', help='Optional C++ compiler path')
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix:
        parser.error('Activate an isolated Python virtual environment first')
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    source = Path(__file__).resolve().parents[2]
    build = args.build_dir.resolve()
    if build == source or source in build.parents:
        parser.error('The build directory must be outside the source checkout')
    pybind_dir = subprocess.check_output([sys.executable, '-m', 'pybind11', '--cmakedir'], text=True).strip()
    command = ['cmake', '-S', str(source), '-B', str(build),
               '-DBMSSP_PYTHON=ON', '-DBUILD_TESTING=ON',
               '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', f'-DCMAKE_BUILD_TYPE={args.config}',
               f'-DPython_EXECUTABLE={sys.executable}', f'-Dpybind11_DIR={pybind_dir}']
    if args.compiler:
        command.append(f'-DCMAKE_CXX_COMPILER={args.compiler}')
    subprocess.run(command, check=True)
    subprocess.run(['cmake', '--build', str(build), '--parallel', str(args.jobs)], check=True)
    subprocess.run(['ctest', '--test-dir', str(build), '-R', 'python_binding_smoke', '--output-on-failure'], check=True)
    print(f'Add {build / "python"} to PYTHONPATH to import bmssp_native')


if __name__ == '__main__':
    main()
