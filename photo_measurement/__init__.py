import os

try:  # python.org macOS builds ship without a CA bundle; urllib/torch.hub need one
    import certifi

    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass
