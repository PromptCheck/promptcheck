from importlib.metadata import version as _v, PackageNotFoundError as _PackageNotFoundError

__version__: str

try:
    __version__ = _v("evalloop")
except _PackageNotFoundError:
    # Package is not installed, so we fall back to a dev version.
    # This is useful for local development when the package might not be installed in editable mode yet.
    __version__ = "0.0.0-dev"
