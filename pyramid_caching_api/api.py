import logging
log = logging.getLogger(__name__)

import types
from dogpile.cache import make_region

from . import utils
from .utils import CACHE_FAILS
from .utils import NO_VALUE              # actually `dogpile.cache.api::NO_VALUE`


class CachingManager(object):
    """CachingManager provides a base class to configure regions
    
        You only need this ONCE , during applicaiton setup.
    """
    regions = None
    
    def __init__( self , config , settings , region_config ):
        """
        initializes the dogpile cache.
    
        params
        ------
            `config` - pyramid's config
            `settings` - pyarmid's settings
                must contain:
                    `data_dir` - the directory we'll store cached data in.  all data will be in `"%s/pyramid_caching_api" % data_dir`

            `region_config` - a dict of region names to be managed.  values can be overrides
        """
        regions = {}
        customized= { 'data_dir' : settings['data_dir'] }

        ## make the data dir
        utils.mkdir_p( "%(data_dir)s/pyramid_caching_api" % customized )

        for region_name in region_config.keys() : 
        
            customized['region_name'] = region_name

            #  STEP 1 - make the region
            #       pyramid uses unicode, that fucks up the dogpile cache keys , which need to be ascii for certain backends
            key_mangler = str
            if 'key_mangler' in region_config : 
                key_mangler = region_config['key_mangler']
            regions[region_name] = make_region(key_mangler=key_mangler)
            
            # STEP 2 - do we have to massage any data from the config file or set defaults ?
            region_backend_key = 'cache.%s.backend' % region_name
            if region_backend_key not in config :
                config[region_backend_key] = 'dogpile.cache.dbm'

            region_backend = config[region_backend_key]
            if region_backend == 'dogpile.cache.dbm' :
                filename_key = 'cache.%s.arguments.filename' % region_name
                if filename_key not in config :
                    config[filename_key] = '%(data_dir)s/pyramid_caching_api/%(region_name)s' % ( customized )

            
            # STEP 3 - configure the region
            regions[region_name].configure_from_config( config , 'cache.%s.' % region_name )
            
        self.regions = regions
        


        


class CachingApi(object):
    """CachingApi Provides an interface to Get/Create items from the DogPile cache (external), and manages a per-request caching stash
    
    A single instance of CachingApi() is recommended to be attached to the `request` object

    the `dbSessionReaderFetch` and `dbSessionWriterFetch` attributes should be callables that return a dbSession connection.

    the `dbSessionReader` and `dbSessionWriter` attributes are memoized properties that cache a dbSession connection when first called.
    """
    DEBUG_CACHING_API = False
    cached = None
    _dbSessionReader = None
    _dbSessionWriter = None
    dbSessionReaderFetch = None
    dbSessionWriterFetch = None
    dbPreference = None
    request = None
    regions_manager = None
    

    @property
    def dbSessionReader(self):
        """returns a memoizied _dbSessionReader"""
        if self._dbSessionReader is None and self.dbSessionReaderFetch is not None:
            self._dbSessionReader = self.dbSessionReaderFetch()
        return self._dbSessionReader


    @property
    def dbSessionWriter(self):
        """returns a memoizied _dbSessionWriter"""
        if self._dbSessionWriter is None and self.dbSessionWriterFetch is not None:
            self._dbSessionWriter = self.dbSessionWriterFetch()
        return self._dbSessionWriter


    def __init__( self , request , dbSessionReaderFetch=None , dbSessionWriterFetch=None , dbPreference=None , regions_manager=None ):
        """ __init__ 
        
            Params
            ------
            `request`
                pryramid request object
            `dbSessionReaderFetch`
                callable action that returns a `dbSessionReader`
            `dbSessionWriterFetch`
                callable action that returns a `dbSessionWriterFetch`
            `dbPreference`
                do we prefer the writer to the reader ?
            `regions_manager`
                cache regions config 
        """
        self.request = request
        self.dbSessionReaderFetch = dbSessionReaderFetch
        self.dbSessionWriterFetch = dbSessionWriterFetch
        self.dbPreference = dbPreference
        self.regions_manager = regions_manager
        
        # init the internal cache
        # also create a stashed region for our lightweight request caching
        if self.regions_manager is not None :
            # created a cached attribute for each dogpile region
            self.cached = dict([ (i,{}) for i in self.regions_manager.regions.keys() ])
            self.cached['!stashed'] = {}
        else:
            self.cached = { '!stashed' : {} }
        
    
    def _setup_apiObject(  self , apiObject ):
        """Sets up the apiObject for requesting"""
        # exit early if we set it up already.
        if apiObject.request is not None:
            return
        apiObject.request = self.request
        apiObject.regions_manager = self.regions_manager
        if self.dbSessionWriterFetch and self.dbSessionReaderFetch :
            if   self.dbPreference == 'writer':
                apiObject.dbSession = self.dbSessionWriter
            elif self.dbPreference == 'reader':
                apiObject.dbSession = self.dbSessionReader
            else:
                apiObject.dbSession = self.dbSessionReader
        else :
            if self.dbSessionWriter :
                apiObject.dbSession = self.dbSessionWriter
            elif self.dbSessionReader :
                apiObject.dbSession = self.dbSessionReader
            else:
                raise ValueError("must have a dbSession")



    def get( self , cachedClass , method_name , argstuple , force=False ):
        """
            `get` an item from the cache
            
            this has some aggressive behavior:
            
                it stashes the cached data into the current request, saving a trip to memcached (or other data store )
                if the requested data is a `multiple_fetch` ( as defined above ) it will not stash that data - instead it will stash the individual data
                this is because get_clique_ids(1,2,3,4,5) is very likely to be followed by get_clique_id('any of those ids') and not likely to request the same 'set' of data
                
                some elements, like SharedLink have a secondary argument.  if that's the case -- we append that
            
        """
        if __debug__ and self.DEBUG_CACHING_API: 
            log.debug( "pyramid_caching_api.CachingApi().get() : %s,%s,%s,%s" ,
                    cachedClass , method_name , argstuple )
        try:
            apiObject = cachedClass()
            region_name = apiObject.region_name

            ## this is really dirty and should be redone
            keyed_multiples = getattr( apiObject , 'keyed_multiples' )
            if keyed_multiples and method_name in keyed_multiples :
                method_name_single = keyed_multiples[method_name]
                rval = dict([(argset,NO_VALUE) for argset in argstuple[0]])
                check_argsets = []
                for argset in rval.keys() :
                    argset_pass = argset
                    if not isinstance( argset , types.TupleType ):
                        argset_pass = ( argset , )
                    key_single = apiObject.keys[method_name_single] % argset_pass
                    if key_single not in self.cached[region_name] or force :
                        self._setup_apiObject( apiObject )
                        _rval = getattr( apiObject , method_name_single )( *argset_pass , get_only=True )
                        if _rval == NO_VALUE :
                            check_argsets.append( argset )
                            continue
                        rval[argset] = _rval
                        self.cached[region_name][key_single] = rval[argset]
                if check_argsets:
                    argset_pass = (check_argsets,)
                    key_multiple = apiObject.keys[method_name] % argset_pass
                    self._setup_apiObject( apiObject )
                    _rval = getattr( apiObject , method_name )( *argset_pass )
                    for argset in _rval.keys():
                        argset_pass = (check_argsets,)
                        key_single = apiObject.keys[method_name_single] % argset_pass
                        rval[argset] = _rval[argset]
                        self.cached[region_name][key_single] = _rval[argset]
                return rval

            # else, the single select
            key_single = apiObject.keys[method_name] % argstuple
            if key_single not in self.cached[region_name] or force :
                self._setup_apiObject( apiObject )
                rval = getattr( apiObject , method_name )( *argstuple )
                self.cached[region_name][key_single] = rval
            return self.cached[region_name][key_single]
        except:
            raise
        


    def stashed( self , key , value=NO_VALUE ):
        """this is a quick little kv stash for other data"""
        if value is NO_VALUE :
            if key in self.cached['!stashed'] :
                return self.cached['!stashed'][key]
            return NO_VALUE
        self.cached['!stashed'][key] = value
        return True



    def update( self , cachedClass , method_name , argstuple ):
        if __debug__ and self.DEBUG_CACHING_API: 
            log.debug("pyramid_caching_api.CachingApi().update() : %s,%s,%s" ,
             cachedClass , method_name , argstuple )
        try:
            apiObject = cachedClass()
            self._setup_apiObject( apiObject )
            rval = getattr( apiObject , method_name )( *argstuple )
            return rval
        except:
            raise


    def delete( self , cachedClass , method_name , argstuple ):
        if __debug__ and self.DEBUG_CACHING_API: 
            log.debug("pyramid_caching_api.CachingApi().delete() : %s,%s,%s" , 
                cachedClass , method_name , argstuple )
        try :
            apiObject = cachedClass()
            self._setup_apiObject( apiObject )
            region_name = apiObject.region_name
            key = apiObject.keys[method_name] % argstuple
            self.regions_manager.regions[ region_name ].delete(key)
            if key in self.cached[region_name] :
                del self.cached[region_name][key]
        except:
            log.debug("pyramid_caching_api.CachingApi().delete() -- ERROR RAISED")
            raise
