This Package is EOL and unsupported.
====================================

`pyramid_caching_api` was an attempt to abstract out a production system's
caching layer. The production system drastically changed, and work on this
ceased MANY years ago.


pyramid_caching_api
===================

`pyramid_caching_api` offers lightweight support for managing cached data under
`dogpile.cache``.

It is designed to help you optimize cache access under certain situations.

This is a work in progress.  Contributions are greatly appreciated.
A version of this strategy is used on a production site, but this is a total
rewrite.

Cached Info is generated from 3 places, in this priority:

1. The Request ( via an internal data store )
2. The Cloud ( via dogpile.cache )
3. The Database ( via a failover )

It is important to note this package is designed to optimize cache access and
traffic. This library has little to do with the actual caching, and just offers
a framework to better integrate well established caching libaries.

1. Items stashed into a "per request cache" do not have an expiry.
  They sit there until the request is destroyed.
  This is designed so that you don't query a cache server for the same object
  twice.

2. A framework is provided to quickly write functions for pulling multiple keys
   at once in a two-pass phase:

* Phase 1 - Split keys into cache-hits and cache-misses.
* Phase 2 - Group cache-misses into a single parallel select:

	"SELECT WHERE id IN (1...100)"
	
  is faster than 100

	"SELECT WHERE id = ?"

  statements.

The package proxies caching info as such:

Create a regions manager on application startup:

	region_config = { 'objects':{} } # which regions are being managed ?
    regions_manager = pyramid_caching_api.api.CachingManager(
    	pyramid_config, pyramid_settings, region_config
    )

Attach a new api instance to your request:

	request.cachingApi = pyramid_caching_api.api.CachingApi(
		request, regions_manager=regions_manager, dbSessionReader=dbSession
	)

Ask it to get the useraccount from mapping:

	useraccount = request.cachingApi.get(
		CachedUseraccountObject, 'get_by_id', (1,)
	)

if you need relationships between your data, you can set "lazyloaded functions":

	useraccount._lazyload(
		'photo', request.cachingApi.get, CachedPhotoObject, 'get_by_id',
		(useraccount.photo_id,)
	)

The file `demo.py` shows some sample usage. In the demo, objects are defined with pre-cache and post-cache hooks to optimize data handling.

A benefit of the approach with lazyloads is that you can load multiple objects, record all the needed ids, and then cache them into the request.

The demo also shows an example of optimizing multiple selects to parallel from serial ( see `get_by_id` vs `get_by_ids` )


# To Do

1. The customized implementation of this strategy pairs the multiple-select functions with corresponding single-select functions.  This allows for local (request) cache data to address info first, and also allows for the multiple-select functions to populate the local cache.  This feature didn't make it into the current rewrite in a decent manner. The implementation is messy:

* An object needs to have a `keyed_multiples` attribute to map the selection:

	keyed_multiples = {
		'ids_to_names': 'id_to_name',
	}

* This only works for items that have a single argument




