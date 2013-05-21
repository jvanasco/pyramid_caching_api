import logging
log = logging.getLogger(__name__)

from dogpile.cache import make_region
from dogpile.cache.api import NO_VALUE

import os , errno

CACHE_FAILS = ( NO_VALUE , )


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else: raise



class CachedData(object):
    keys = None
    request = None
    dbSession = None
    query_args = None
    regions_manager = None





class LazyloadedFunction(object):
    """ a deferred function """
    def __init__(self, object , object_attribute, function , *args , **kwargs ):
        self.object = object
        self.object_attribute = object_attribute
        self.function = function
        self.args = args
        self.kwargs = kwargs
        try:
            self.__doc__ = function.__doc__
        except: # pragma: no cover
            pass
    def execute(self):
        val = self.function(*self.args,**self.kwargs)
        return val



class ObjectifiedDict(dict):
    """Dict that allows for .dotted access"""

    def __getitem__(self,attr):
        if attr in self:
            item = dict.__getitem__(self,attr)
            if isinstance( item , LazyloadedFunction ):
                item = item.execute()
                dict.__setitem__( self , attr , item )
            return item

    def __getattr__(self,attr):
        if attr in self:
            if isinstance( self[attr] , LazyloadedFunction ):
                self[attr] = self[attr].execute()
            return self[attr]
        return self.__getattribute__(attr)


    def _lazyload( self, attr , function , *args , **kwargs ):
        self[attr] = LazyloadedFunction(self,attr,function,*args,**kwargs)
        

    def _expand(self):
        for k,v in self.iteritems():
            if isinstance( v , LazyloadedFunction ) :
                v = v.execute()
                dict.__setitem__( self , k , v )


    def _cacheable( self , exclude=None ):
        copied = self.copy()
        for k,v in copied.iteritems():
            if isinstance( v , LazyloadedFunction ) :
                del copied[k]
        if exclude :
            for k in exclude :
                if k in copied :
                    del copied[k]
        return copied
        
