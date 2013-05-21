pyramid_caching_api gives lightweight support for managing cached data in dogpile.cache.

It's designed to help you optimize cache access under certain situations.

This is a work in progress.  Contributions are greatly appreciated.  A version of this strategy is used on a production site, but this is a total rewrite.

Cached Info is generated from 3 places , in this priority :

	1. The Cloud
	2. The Request
	3. The Database

The CachingApi package proxies caching info as such...


create a regions manager on application startup

	region_config = { 'objects':{} } # which regions are being managed ?
    regions_manager = pyramid_caching_api.api.CachingManager( pyramid_config , pyramid_settings , region_config )

attach a new api instance to your request

	# dbSessionReaderFetch is a lazyloaded function to return a database connection.  this way you don't open a database unless you need data
	request.cachingApi = pyramid_caching_api.api.CachingApi( request , regions_manager=regions_manager , dbSessionReaderFetch=lambda: True )

ask it to get the useraccount from mapping

	useraccount = request.cachingApi.get(  CachedUseraccountObject , 'get_by_id' , (1,) )

if you need relationships between your data, you can set "lazyloaded functions"

	useraccount._lazyload( 'photo' ,
						request.cachingApi.get ,
						CachedPhotoObject, 'get_by_id', (useraccount.photo_id,) ,
					)

the file `demo.py` shows some sample usage.  in the demo, objects are defined with pre-cache and post-cache hooks to optimize data handling.

a benefit of the approach with lazyloads is that you can load multiple objects , record all the needed ids, and then cache them into the request.

the demo also shows an example of optimizing multiple selects to parallel from serial ( see `get_by_id` vs `get_by_ids` )
