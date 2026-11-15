"""The Station API's error codes and ApiError. They are the protocol's own (station_protocol/errors.py); the app
imports them from here."""

from station_protocol.errors import ApiError, ErrorCode

__all__ = ["ApiError", "ErrorCode"]
