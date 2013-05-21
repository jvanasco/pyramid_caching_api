pyramid_caching_api gives lightweight support for managing cached data.

Cached Info is generated from 3 places:
	1. The Cloud
	2. The Request
	3. The Database

The CachingApi package proxies caching info as such:

	# create a new api instance
	cachingApi = CachingApi( request , dbSession )

	# ask it to get the useraccount from mapping
	cachingApi.get( 'mapping' , 'Useraccount' , 'get_by_id' , 1 )

	# transparently , it does this:
	#   a. what is the key that mapping.Useraccount( request , dbSession ).get_by_id(1) would access ?
	#   b. check self.cached for that key
	#   c. if we don't have that key , then call the function

	# the function then does this:
	#   a. generate the key.
	#   b. if it exists in the cloud, serve it
	#   c. if it doesn't, set it
