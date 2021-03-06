===============
Getting Started
===============

This guide is current as of version 0.18.0. See the :ref:`Upgrade Guide` if
you're running an older version.

The code matching this guide is `here
<https://github.com/uber/tchannel-python/tree/master/examples/guide>`_.


-------------
Initial Setup
-------------

Create a directory called ``keyvalue`` to work inside of:

.. code-block:: bash

    $ mkdir ~/keyvalue
    $ cd ~/keyvalue

Inside of this directory we're also going to create a ``keyvalue`` module, which
requires an ``__init__.py`` and a ``setup.py`` at the root:

.. code-block:: bash

    $ mkdir keyvalue
    $ touch keyvalue/__init__.py

Setup a `virtual environment <https://virtualenv.pypa.io/en/latest/>`_ for your
service and install the Tornado and Tchannel packages:

.. code-block:: bash

    $ virtualenv env
    $ source env/bin/activate
    $ pip install 'tchannel<0.19'


---------------------------
Thrift Interface Definition
---------------------------

Create a `Thrift <https://thrift.apache.org/>`_ file under
``thrift/keyvalue.thrift`` that defines an interface for your service:

.. code-block:: bash

    $ mkdir thrift
    $ vim thrift/keyvalue.thrift
    $ cat thrift/keyvalue.thrift


.. code-block:: idl

    exception NotFoundError {
        1: required string key,
    }

    service KeyValue {
        string getValue(
            1: string key,
        ) throws (
            1: NotFoundError notFound,
        )

        void setValue(
            1: string key,
            2: string value,
        )
    }

\
This defines a service named ``KeyValue`` with two functions:

``getValue``
    a function which takes one string parameter, and returns a string.
``setValue``
    a void function that takes in two parameters.


------------
Thrift Types
------------

TChannel has some custom behavior so it can't use the code generated by the
Apache Thrift code generator. Instead we’re going to dynamically generate our
Thrift types.

Open up ``keyvalue/thrift.py``:

.. code-block:: bash

    $ cat > keyvalue/thrift.py
    from tchannel import thrift

    service = thrift.load(path='thrift/keyvalue.thrift', service='keyvalue')

Let’s make sure everything is working:

.. code-block:: bash

    $ python -m keyvalue.thrift

You shouldn’t see any errors. A lot of magic just happened :)


-------------
Python Server
-------------

To serve an application we need to instantiate a TChannel instance, which we
will register handlers against. Open up ``keyvalue/server.py`` and write
something like this:

.. code-block:: python

    from __future__ import absolute_import

    from tornado import ioloop
    from tornado import gen

    from tchannel import TChannel

    from keyvalue.thrift import service


    tchannel = TChannel('keyvalue-server')


    @tchannel.thrift.register(service.KeyValue)
    def getValue(request):
        pass


    @tchannel.thrift.register(service.KeyValue)
    def setValue(request):
        pass


    def run():
        tchannel.listen()
        print('Listening on %s' % tchannel.hostport)


    if __name__ == '__main__':
        run()
        ioloop.IOLoop.current().start()

Here we have created a TChannel instance and registered two no-op handlers with
it. The name of these handlers map directly to the Thrift service we defined
earlier.

A TChannel server only has one requirement: a name for itself. By default an
ephemeral port will be chosen to listen on (although an explicit port can be
provided).

(As your application becomes more complex, you won't want to put everything in
a single file like this. Good code structure is beyond the scope of this
guide.)

Let's make sure this server is in a working state:

.. code-block:: bash

    python -m keyvalue.server
    Listening on localhost:8889
    ^C

The process should hang until you kill it, since it's listening for requests to
handle. You shouldn't get any exceptions.


--------
Handlers
--------

To implement our service's endpoints let's create an in-memory dictionary that
our endpoints will manipulate:

.. code-block:: python

    values = {}


    @tchannel.thrift.register(service.KeyValue)
    def getValue(request):
        key = request.body.key
        value = values.get(key)

        if value is None:
            raise service.NotFoundError(key)

        return value


    @tchannel.thrift.register(service.KeyValue)
    def setValue(request):
        key = request.body.key
        value = request.body.value
        values[key] = value

You can see that the return value of ``getValue`` will be coerced into the
expected Thrift shape. If we needed to return an additional field, we could
accomplish this by returning a dictionary.

This example service doesn't do any network IO work. If we wanted to take
advantage of Tornado's `asynchronous
<http://tornado.readthedocs.org/en/latest/gen.html>`_ capabilities, we could
define our handlers as coroutines and yield to IO operations:

.. code-block:: python

    @tchannel.register(service.KeyValue)
    @gen.coroutine
    def setValue(request):
        key = request.body.key
        value = request.body.value

        # Simulate some non-blocking IO work.
        yield gen.sleep(1.0)

        values[key] = value


~~~~~~~~~~~~~~~~~
Transport Headers
~~~~~~~~~~~~~~~~~

In addition to the call arguments and headers, the ``request`` object also
provides some additional information about the current request under the
``request.transport`` object:

``transport.flags``
    Request flags used by the protocol for fragmentation and streaming.
``transport.ttl``
    The time (in milliseconds) within which the caller expects a response.
``transport.headers``
    Protocol level headers for the request. For more information on transport
    headers check the
    `Transport Headers <https://github.com/uber/tchannel/blob/master/docs/protocol.md#transport-headers>`_
    section of the protocol document.


---------
Hyperbahn
---------

As mentioned earlier, our service is listening on an ephemeral port, so we are
going to register it with the Hyperbahn routing mesh. Clients will use this
Hyperbahn mesh to determine how to communicate with your service.

Let's change our `run` method to advertise our service with a local Hyperbahn
instance:

.. code-block:: python

    import json
    import os

    @gen.coroutine
    def run():

        tchannel.listen()
        print('Listening on %s' % tchannel.hostport)

        if os.path.exists('/path/to/hyperbahn_hostlist.json'):
            with open('/path/to/hyperbahn_hostlist.json', 'r') as f:
                hyperbahn_hostlist = json.load(f)
            yield tchannel.advertise(routers=hyperbahn_hostlist)

The `advertise` method takes a seed list of Hyperbahn routers and the name of
the service that clients will call into. After advertising, the Hyperbahn will
connect to your process and establish peers for service-to-service
communication.

Consult the Hyperbahn documentation for instructions on how to start a process
locally.


---------
Debugging
---------

Let's spin up the service and make a request to it through Hyperbahn. Python
provides ``tcurl.py`` script, but we need to use the `Node
version <https://github.com/uber/tcurl>`_ for now since it has Thrift support.

.. code-block:: bash

    $ python keyvalue/server.py &
    $ tcurl -H /path/to/hyperbahn_host_list.json -t ~/keyvalue/thrift/keyvalue.thrift keyvalue-server KeyValue::setValue -3 '{"key": "hello", "value": "world"}'
    $ tcurl -H /path/to/hyperbahn_host_list.json -t ~/keyvalue/thrift/keyvalue.thrift keyvalue-server KeyValue::getValue -3 '{"key": "hello"}'
    $ tcurl -H /path/to/hyperbahn_host_list.json -t ~/keyvalue/thrift/keyvalue.thrift keyvalue-server KeyValue::getValue -3 '{"key": "hi"}'

Your service can now be accessed from any language over Hyperbahn + TChannel!


-------------
Python Client
-------------

Let's make a client call from Python in ``keyvalue/client.py``:

.. code-block:: python

    from tornado import gen, ioloop
    from tchannel import TChannel, thrift

    tchannel = TChannel('keyvalue-consumer')
    service = thrift.load(
        path='examples/guide/keyvalue/service.thrift',
        service='keyvalue-server',
        hostport='localhost:8889',
    )


    @gen.coroutine
    def run():

        yield tchannel.thrift(
            service.KeyValue.setValue("foo", "Hello, world!"),
        )

        response = yield tchannel.thrift(
            service.KeyValue.getValue("foo"),
        )

        print response.body


    if __name__ == '__main__':
        ioloop.IOLoop.current().run_sync(run)
