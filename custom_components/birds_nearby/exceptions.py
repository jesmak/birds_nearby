"""Errors from eBird."""


class EbirdError(Exception):
    """eBird couldn't be reached, or it answered with something unexpected."""


class EbirdAuthError(EbirdError):
    """eBird refused the API key."""
