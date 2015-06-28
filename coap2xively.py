#!/usr/bin/env python

#
# Simple CoAP -> Xively Gateway
#
# Posting to this server will insert the data into a xively account
#

import sys

from twisted.internet import defer
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.python import log

import txthings.resource as resource
import txthings.coap as coap
import datetime, time
import xively

import json


class Coap2Xively:
    class xivelyGatewayResource (resource.CoAPResource):
        def __init__(self):
            resource.CoAPResource.__init__(self)
            self.visible = True
            self.addParam(resource.LinkParam("title", "CoAP -> Xively gateway"))
            self.directory = {}
            self.eid = 0

        """
        Use get resource as help
        """
        def render_GET(self, request):
            payload = "To use this resource, POST a json string like \"" + \
                    "{'value': <myValue>, 'xively_api_key': '<myApiKey>'," +\
                    "'xively_feed_id': '<myFeedId>'," + \
                    "'xively_channel_id':'<myChannelId>'}\" to this resource."
            response = coap.Message(code=coap.CONTENT, payload=payload)
            return defer.succeed(response)

        """
        Post resource for translation between services / protocols

        TODO: Support other formats: XML?
        """
        def render_POST(self, request):
            if request.opt.content_format == coap.media_types_rev['application/json']:
                pl = None
                try:
                    pl = json.loads(request.payload)
                except:
                    print "Cannot decode json!"#, request.payload
                    return defer.succeed(coap.Message(code=coap.UNSUPPORTED_CONTENT_FORMAT, payload='Wrong payload format'))
                # Extend dict by some meta data
                pl["srv_receive_timestamp"] = time.time()
                pl["srv_remote_ipaddress"] = unicode(request.remote[0])
                pl["srv_remote_port"] = int(request.remote[1])
                print "Try to insert into xively"
                if "xively_api_key" in pl and \
                        "xively_feed_id" in pl and \
                        "xively_channel_id" in pl:
                    try:
                        xivelyApi = xively.XivelyAPIClient(pl["xively_api_key"])
                        xivelyFeed = xivelyApi.feeds.get(pl["xively_feed_id"])
                        xivelyFeed.datastreams = [
                                xively.Datastream(id=pl["xively_channel_id"],
                                    current_value=pl["value"]),
                                ]
                        xivelyFeed.update()
                        del(xivelyFeed)
                        del(xivelyApi)
                    except Exception, e:
                        print "Error: cannot insert into xively:", e
                        return defer.succeed(coap.Message(code=coap.PRECONDITION_FAILED, payload="xively error: " + str(e)))
                    print "Successfully inserted data to database"
                else:
                    # General error: Not found xively related keys
                    defer.succeed(coap.Message(code=coap.UNSUPPORTED_CONTENT_FORMAT, payload='xively-specific keys missing'))
                return defer.succeed(coap.Message(code=coap.CREATED, payload=''))

            else:
                # Extend other content formats
                return defer.succeed(coap.Message(code=coap.UNSUPPORTED_CONTENT_FORMAT, payload=''))

    class CoreResource(resource.CoAPResource):
        """
        Example Resource that provides list of links hosted by a server.
        Normally it should be hosted at /.well-known/core

        Resource should be initialized with "root" resource, which can be used
        to generate the list of links.

        For the response, an option "Content-Format" is set to value 40,
        meaning "application/link-format". Without it most clients won't
        be able to automatically interpret the link format.

        Notice that self.visible is not set - that means that resource won't
        be listed in the link format it hosts.
        """

        def __init__(self, root):
            resource.CoAPResource.__init__(self)
            self.root = root

        def render_GET(self, request):
            data = []
            self.root.generateResourceList(data, "")
            payload = ",".join(data)
            response = coap.Message(code=coap.CONTENT, payload=payload)
            response.opt.content_format = coap.media_types_rev['application/link-format']
            return defer.succeed(response)

    def start(self):
        # Resource tree creation
        log.startLogging(sys.stdout)
        root = resource.CoAPResource()

        well_known = resource.CoAPResource()
        root.putChild('.well-known', well_known)
        core = Coap2Xively.CoreResource(root)
        well_known.putChild('core', core)

        post = Coap2Xively.xivelyGatewayResource()
        root.putChild('postSensorData', post)

        endpoint = resource.Endpoint(root)
        reactor.listenUDP(coap.COAP_PORT, coap.Coap(endpoint))#, interface="::")
        reactor.run()
        print "DONE"

if __name__ == "__main__":
    res = Coap2Xively()
    res.start()
