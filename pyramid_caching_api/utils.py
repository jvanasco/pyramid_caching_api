import logging

log = logging.getLogger(__name__)

from dogpile.cache import make_region
from dogpile.cache.api import NO_VALUE

import os, errno

CACHE_FAILS = (NO_VALUE,)


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise


class CachedData(object):
    keys = None
    request = None
    dbSession = None
    query_args = None
    regions_manager = None
    keyed_multiples = None


class LazyloadedFunction(object):
    """a deferred function"""

    def __init__(
        self,
        object,
        object_attribute,
        cache_function,
        *cache_function_args,
        **cache_function_kwargs
    ):
        self.object = object
        self.object_attribute = object_attribute
        self.cache_function = cache_function
        self.cache_function_args = cache_function_args
        self.cache_function_kwargs = cache_function_kwargs
        try:
            self.__doc__ = function.__doc__
        except:  # pragma: no cover
            pass

    def execute(self):
        val = self.cache_function(
            *self.cache_function_args, **self.cache_function_kwargs
        )
        return val


class ObjectifiedDict(dict):
    """Dict that allows for .dotted access"""

    def __getitem__(self, attr):
        if attr in self:
            item = dict.__getitem__(self, attr)
            if isinstance(item, LazyloadedFunction):
                item = item.execute()
                dict.__setitem__(self, attr, item)
            return item

    def __getattr__(self, attr):
        if attr in self:
            if isinstance(self[attr], LazyloadedFunction):
                value = self[attr].execute()
                self[attr] = value
            return self[attr]
        return self.__getattribute__(attr)

    def _lazyload(self, attr, function, *args, **kwargs):
        self[attr] = LazyloadedFunction(self, attr, function, *args, **kwargs)

    def _expand(self):
        for k, v in self.iteritems():
            if isinstance(v, LazyloadedFunction):
                v = v.execute()
                dict.__setitem__(self, k, v)

    def _cacheable(self, exclude=None):
        copied = self.copy()
        for k, v in copied.iteritems():
            if isinstance(v, LazyloadedFunction):
                del copied[k]
        if exclude:
            for k in exclude:
                if k in copied:
                    del copied[k]
        return copied


class AttributeSafeObject(object):
    """
    Object with lax attribute access. Returns an empty string ('') when the
    attribute does not exist; good for templating). Based on Pylons.
    """

    def __init__(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def __getattr__(self, name):
        try:
            ## note that we're using the object class directly
            return object.__getattribute__(self, name)
        except AttributeError:
            if name[:2] == "__":
                raise
            if DEBUG_ATTRIB_SAFE:
                log.debug(
                    "No attribute `%s` found in AttributeSafeObject instance,"
                    "returning empty string",
                    name,
                )
            return ""

    def keys(self):
        return self.__dict__.keys()


class AttributeSafeObject_set(AttributeSafeObject):
    """An AttributeSafeObject that sets & gets `set({})` on misses"""

    def __getattr__(self, k):
        try:
            return object.__getattribute__(self, k)
        except AttributeError:
            if k[:2] == "__":
                raise
            setattr(self, k, set())
            return object.__getattribute__(self, k)


class AttributeSafeObject_dict(AttributeSafeObject):
    """An AttributeSafeObject that sets & gets dict `{}` on misses"""

    def __getattr__(self, k):
        try:
            return object.__getattribute__(self, k)
        except AttributeError:
            if k[:2] == "__":
                raise
            setattr(self, k, {})
            return object.__getattribute__(self, k)


class AttributeSafeObject_dict_ids(AttributeSafeObject_dict):
    """An AttributeSafeObject_dict_ids used to manage ids"""

    def add_unknown(self, key, items_to_update, v=None):
        store = getattr(self, key)
        for k in items_to_update:
            if k not in store:
                store[k] = v

    def update(self, key, items_to_update, v=None):
        store = getattr(self, key)
        for k in items_to_update:
            store[k] = v

    def get_true(self, key):
        store = getattr(self, key)
        rval = [k for k in store.keys() if store[k]]
        return rval

    def get_false(self, key):
        store = getattr(self, key)
        rval = [k for k in store.keys() if not store[k]]
        return rval
