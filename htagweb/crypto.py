# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################
from Cryptodome.Cipher import AES # pip3 install pycryptodomex
import hashlib
import base64,os
# https://hackernoon.com/how-to-use-aes-256-cipher-python-cryptography-examples-6tbh37cr

def decrypt(b64:bytes,key:str) -> bytes:   # text
    data=base64.b64decode(b64)
    key = hashlib.sha256(key.encode()).digest()
    cipher = AES.new(key, AES.MODE_GCM, data[:12]) # nonce
    return cipher.decrypt_and_verify(data[12:-16], data[-16:]) # ciphertext, tag

def encrypt(data:bytes,key:str) -> str:   # b64 cypĥertext
    key = hashlib.sha256(key.encode()).digest()
    iv = os.urandom(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    cyphertext,tag = cipher.encrypt_and_digest(data) # ciphertext, tag
    return base64.b64encode(iv + cyphertext + tag).decode()

JSCRYPTO="""

async function encrypt(plaintext, password) {
    const pwUtf8 = new TextEncoder().encode(password);
    const pwHash = await crypto.subtle.digest('SHA-256', pwUtf8);
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ivStr = Array.from(iv).map(b => String.fromCharCode(b)).join('');
    const alg = { name: 'AES-GCM', iv: iv };
    const key = await crypto.subtle.importKey('raw', pwHash, alg, false, ['encrypt']);
    const ptUint8 = new TextEncoder().encode(plaintext);
    const ctBuffer = await crypto.subtle.encrypt(alg, key, ptUint8);
    const ctArray = Array.from(new Uint8Array(ctBuffer));
    const ctStr = ctArray.map(byte => String.fromCharCode(byte)).join('');
    return btoa(ivStr+ctStr);
}
async function decrypt(ciphertext, password) {
    const pwUtf8 = new TextEncoder().encode(password);
    const pwHash = await crypto.subtle.digest('SHA-256', pwUtf8);
    const ivStr = atob(ciphertext).slice(0,12);
    const iv = new Uint8Array(Array.from(ivStr).map(ch => ch.charCodeAt(0)));
    const alg = { name: 'AES-GCM', iv: iv };
    const key = await crypto.subtle.importKey('raw', pwHash, alg, false, ['decrypt']);
    const ctStr = atob(ciphertext).slice(12);
    const ctUint8 = new Uint8Array(Array.from(ctStr).map(ch => ch.charCodeAt(0)));
    const plainBuffer = await crypto.subtle.decrypt(alg, key, ctUint8);
    const plaintext = new TextDecoder().decode(plainBuffer);
    return plaintext;
}

"""
