import pyramid_caching_api

class FakeRequest(object):
    request = None
    cachingApi = None

sample_data = {}
for i in range(1,27):
    sample_data[i] = chr(96 + i )


class CachedObject( pyramid_caching_api.utils.CachedData ):
    region_name= 'objects'
    keys = {\
        ## cached
        'id_to_name' : 'CachedObject:id_to_name:%s' ,

        ## NOT cached
        'ids_to_names' : 'CachedObject:ids_to_names:%s' ,
    }

    def id_to_name__set( self , id , value ):
        key = self.keys['id_to_name'] % id
        self.regions_manager.regions[self.region_name].set( key , value )

    def _id_to_name( self ):
        ( id , ) = self.query_args
        print "CachedObject._id_to_name || A VERY EXPENSIVE FUNCTION || id = %s" % id
        if id in sample_data :
            return sample_data[id]
        return pyramid_caching_api.api.NO_VALUE

    def id_to_name( self , id , get_only=False ):
        self.query_args = ( id , )
        key = self.keys['id_to_name'] % id
        if get_only :
            return self.regions_manager.regions[self.region_name].get( key )
        return self.regions_manager.regions[self.region_name].get_or_create( key , self._id_to_name )

    def ids_to_names( self , ids ):
        api_results = dict( [(id,None) for id in ids] )
        for id in ids:
            api_results[id] = self.id_to_name( id , get_only=True )
        check_ids = [ i for i in api_results.keys() if ( api_results[i] in pyramid_caching_api.api.CACHE_FAILS ) ]
        if len(check_ids):
            print "CachedObject.ids_to_names || A VERY EXPENSIVE FUNCTION || ids = %s" % check_ids
            db_results = dict( (i,sample_data[i]) if i in sample_data else (i,False) for i in check_ids )
            for id in db_results.keys():
                name = db_results[id]
                api_results[id] = name
                self.id_to_name__set( id , name )
        return api_results



class AdvancedCachedObject( pyramid_caching_api.utils.CachedData ):
    region_name= 'objects'
    keys = {\
        ## cached
        'get_by_id' : 'AdvancedCachedObject::get_by_id::%s' ,
    }

    def _standardize_object_precache( self , object ):
        """this is a precache, because we might eagerload extra data"""
        if object:
            store= object.copy()
            store['extra_data'] = "more stuff to be dropped into the cache"
            return pyramid_caching_api.utils.ObjectifiedDict(store)
        return pyramid_caching_api.api.NO_VALUE
        
    def _standardize_object_postcache( self , object ):
        if object:
            if object.id != 1:
                object._lazyload( 'original_version' , 
                                    self.request.cachingApi.get ,
                                    AdvancedCachedObject, 'get_by_id', (1,) ,
                                )
            return object
        return pyramid_caching_api.api.NO_VALUE

    def _get_by_id( self ):
        ( id , ) = self.query_args
        print "AdvancedCachedObject._get_by_id || A VERY EXPENSIVE FUNCTION || id = %s" % id
        object = { 'id':id , 'title':'This is an Example Program' , 'original_version':None }
        return self._standardize_object_precache( object )

    def get_by_id( self , id , create=True ):
        self.query_args = ( id , ) 
        key = self.keys['get_by_id'] % self.query_args
        if create:
            cached = self.regions_manager.regions[self.region_name].get_or_create( key , self._get_by_id )
        else:
            cached = self.regions_manager.regions[self.region_name].get( key )
        return self._standardize_object_postcache( cached )
    


pyramid_config = {
    'cache.objects.backend' : 'dogpile.cache.dbm' ,
}
pyramid_settings = { 
    'data_dir' : 'data' ,
}
region_config = { 'objects':{} }

## only one is needed at app startup
regions_manager = pyramid_caching_api.api.CachingManager( pyramid_config , pyramid_settings , region_config )

## this would happen on every request
r = FakeRequest()
r.cachingApi = pyramid_caching_api.api.CachingApi( r , regions_manager=regions_manager , dbSessionReaderFetch=lambda: True )

if True :
    # some sample gets
    print r.cachingApi.get(  CachedObject , 'id_to_name' , (1,) )
    print r.cachingApi.get(  CachedObject , 'id_to_name' , (2,) )
    print r.cachingApi.get(  CachedObject , 'id_to_name' , (100,) )
    print r.cachingApi.get(  CachedObject , 'ids_to_names' , ((1,2,3,100,200,300),) )

    # sample deletes
    for i in range(1,100):
        r.cachingApi.delete(  CachedObject , 'id_to_name' , (i,)  )

if True :
    # advanced example
    #
    # we use a postcache and precache method to lazyload additional attibutes
    advanced_a = r.cachingApi.get(  AdvancedCachedObject , 'get_by_id' , (1,) )
    print advanced_a
    print advanced_a.original_version

    advanced_b = r.cachingApi.get(  AdvancedCachedObject , 'get_by_id' , (2,) )
    print advanced_b
    print advanced_b.original_version
