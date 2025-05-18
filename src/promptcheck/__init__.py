from importlib.metadata import version as _v, PackageNotFoundError as _PackageNotFoundError

__version__: str

try:
    __version__ = _v("promptcheck") # RENAMED package name for lookup
except _PackageNotFoundError:
    __version__ = "0.0.0-dev" 