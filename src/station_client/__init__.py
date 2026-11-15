"""A client for the Station API that any tool can use: a TCP connection with its requests in flight
(connection.py), and a link that keeps it up (link.py): reconnecting with backoff, holding requests made while
connecting, the sys.hello heartbeat, subscribing again after a reconnect, and spotting lost events.

It depends only on station_protocol, and on nothing of any application (tests/unit/test_architecture.py checks
it). Results come back as raw JSON; a tool checks them against station_protocol's types and builds its own
models from them. It is meant to move to the station's repository with station_protocol.
"""
