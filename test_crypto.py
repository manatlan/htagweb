from htagweb import crypto
def test_crypto():
    phrase="htagweb seems ready"
    key="12313545664"

    blob=crypto.encrypt(phrase.encode(),key)
    assert isinstance(blob,str) # base64

    assert crypto.decrypt(blob.encode(),key).decode() == phrase
