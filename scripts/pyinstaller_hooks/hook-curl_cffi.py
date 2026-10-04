"""Keep the Windows wheel's native DLL layout; do not collect unrelated package data."""
from PyInstaller.utils.hooks import collect_delvewheel_libs_directory

datas, binaries = collect_delvewheel_libs_directory("curl_cffi")
