"""3D visualization plugins.

Each file in this package that defines a Shape subclass is automatically
discovered and added to the shape list.  See shape.py for the base class.
"""

import importlib
import inspect
import pkgutil

from .shape import Shape


_shapes = []
_shape_names = []


def _discover():
    global _shapes, _shape_names
    _shapes = []
    _shape_names = []
    for mod_info in pkgutil.iter_modules(__path__):
        if mod_info.name in ('shape',):
            continue
        try:
            mod = importlib.import_module(f'.{mod_info.name}', __package__)
        except Exception:
            continue
        for _, cls in inspect.getmembers(mod, inspect.isclass):
            if cls is not Shape and issubclass(cls, Shape):
                inst = cls()
                _shapes.append(inst)
                _shape_names.append(inst.name)


def get_shapes():
    if not _shapes:
        _discover()
    return _shapes


def get_shape_names():
    if not _shape_names:
        _discover()
    return _shape_names


def get_shape(name):
    for s in get_shapes():
        if s.name == name:
            return s
    return None
