# Copyright 2012 the rootpy developers
# distributed under the terms of the GNU General Public License
from __future__ import absolute_import

import os
import re
import inspect
import warnings

from .context import preserve_current_directory
from .extern.decorator import decorator
import ROOT

__all__ = [
    'requires_ROOT',
    'method_file_check',
    'method_file_cd',
    'chainable',
    'camel_to_snake',
    'snake_case_methods',
    'sync',
    'cached_property',
]


CONVERT_SNAKE_CASE = os.getenv('NO_ROOTPY_SNAKE_CASE', False) is False

def _get_qualified_name(thing):
    if inspect.ismodule(thing):
        return thing.__file__
    if inspect.isclass(thing):
        return '{0}.{1}'.format(thing.__module__, thing.__name__)
    if inspect.ismethod(thing):
        return '{0}.{1}'.format(thing.im_class.__name__, thing.__name__)
    if inspect.isfunction(thing):
        return thing.__name__
    return repr(thing)


@decorator
def method_file_check(f, self, *args, **kwargs):
    """
    A decorator to check that a TFile as been created before f is called.
    This function can decorate methods.
    """
    # This requires special treatment since in Python 3 unbound methods are
    # just functions: http://stackoverflow.com/a/3589335/1002176 but to get
    # consistent access to the class in both 2.x and 3.x, we need self.
    curr_dir = ROOT.gDirectory.func()
    if isinstance(curr_dir, ROOT.TROOT):
        raise RuntimeError(
            "You must first create a File before calling {0}.{1}".format(
                self.__class__.__name__, _get_qualified_name(f)))
    if not curr_dir.IsWritable():
        raise RuntimeError(
            "Calling {0}.{1} requires that the "
            "current File is writable".format(
                self.__class__.__name__, _get_qualified_name(f)))
    return f(self, *args, **kwargs)


@decorator
def method_file_cd(f, self, *args, **kwargs):
    """
    A decorator to cd back to the original directory where this object was
    created (useful for any calls to TObject.Write).
    This function can decorate methods.
    """
    with preserve_current_directory():
        self.GetDirectory().cd()
        return f(self, *args, **kwargs)


@decorator
def chainable(f, self, *args, **kwargs):
    """
    Decorator which causes a 'void' function to return self

    Allows chaining of multiple modifier class methods.
    """
    # perform action
    f(self, *args, **kwargs)
    # return reference to class.
    return self


FIRST_CAP_RE = re.compile('(.)([A-Z][a-z]+)')
ALL_CAP_RE = re.compile('([a-z0-9])([A-Z])')


def camel_to_snake(name):
    """
    http://stackoverflow.com/questions/1175208/
    elegant-python-function-to-convert-camelcase-to-camel-case
    """
    s1 = FIRST_CAP_RE.sub(r'\1_\2', name)
    return ALL_CAP_RE.sub(r'\1_\2', s1).lower()


def snake_case_methods(cls, debug=False):
    """
    A class decorator adding snake_case methods
    that alias capitalized ROOT methods. cls must subclass
    a ROOT class and define the _ROOT class variable.
    """
    if not CONVERT_SNAKE_CASE:
        return cls
    # get the ROOT base class
    root_base = cls._ROOT
    members = inspect.getmembers(root_base)
    # filter out any methods that already exist in lower and uppercase forms
    # i.e. TDirectory::cd and Cd...
    names = {}
    for name, member in members:
        lower_name = name.lower()
        if lower_name in names:
            del names[lower_name]
        else:
            names[lower_name] = None

    for name, member in members:
        if name.lower() not in names:
            continue
        # Don't touch special methods or methods without cap letters
        if name[0] == '_' or name.islower():
            continue
        # Is this a method of the ROOT base class?
        if not inspect.ismethod(member) and not inspect.isfunction(member):
            continue
        # convert CamelCase to snake_case
        new_name = camel_to_snake(name)
        # Use a __dict__ lookup rather than getattr because we _want_ to
        # obtain the _descriptor_, and not what the descriptor gives us
        # when it is `getattr`'d.
        value = None
        skip = False
        for c in cls.mro():
            # skip methods that are already overridden
            if new_name in c.__dict__:
                skip = True
                break
            if name in c.__dict__:
                value = c.__dict__[name]
                break
        # <neo>Woah, a use for for-else</neo>
        else:
            # Weird. Maybe the item lives somewhere else, such as on the
            # metaclass?
            value = getattr(cls, name)
        if skip:
            continue
        setattr(cls, new_name, value)
    return cls


def sync(lock):
    """
    A synchronization decorator
    """
    @decorator
    def sync(f):
        def new_function(*args, **kw):
            lock.acquire()
            try:
                return f(*args, **kw)
            finally:
                lock.release()
        return new_function
    return sync


class cached_property(object):
    """
    Computes attribute value and caches it in the instance.
    Written by Denis Otkidach and published in the Python Cookbook.
    This decorator allows you to create a property which can be computed once
    and accessed many times. Sort of like memoization.
    """
    def __init__(self, method, name=None):
        # record the unbound-method and the name
        self.method = method
        self.name = name or method.__name__
        self.__doc__ = method.__doc__

    def __get__(self, inst, cls):
        # self: <__main__.cache object at 0xb781340c>
        # inst: <__main__.Foo object at 0xb781348c>
        # cls: <class '__main__.Foo'>
        if inst is None:
            # instance attribute accessed on class, return self
            # You get here if you write `Foo.bar`
            return self
        # compute, cache and return the instance's attribute value
        result = self.method(inst)
        # setattr redefines the instance's attribute so this doesn't get called again
        setattr(inst, self.name, result)
        return result

