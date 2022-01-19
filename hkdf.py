# hkdf hash function

from binascii import unhexlify
import hashlib
import hmac
import math

def hkdf_extract(input_key_material,salt, hash=hashlib.sha512):
    hash_len = hash().digest_size
    if salt == None or len(salt) == 0:
        salt = chr(0) * hash_len
        salt = bytes(salt, 'utf-8')
    return hmac.new(input_key_material,salt, hash).digest()

def hkdf_expand(pseudo_random_key, info="", length=32, hash=hashlib.sha512):
    if info != "":
        info = str(info)
    hash_len = hash().digest_size
    length = int(length)
    if length > 255 * hash_len:
        raise Exception("Cannot expand to more than 255 * %d = %d bytes using the specified hash function" % (hash_len, 255 * hash_len))
    blocks_needed = length / hash_len + (0 if length % hash_len == 0 else 1  ) # ceil
    blocks_needed = math.ceil(blocks_needed)
    okm = ""
    output_block = ""
    for counter in range(blocks_needed):
        output_block_par2 = output_block + info + chr(counter + 1)
        output_block_par2 = bytes(output_block_par2, 'utf-8')
        output_block = hmac.new(pseudo_random_key, output_block_par2, hash).digest()
        output_block = output_block.decode('latin1') ##임시처방!!!
        okm += output_block
    return okm[:length]

def HKDF(input_key_material,salt, info="",length=12 ):
    prk = hkdf_extract(input_key_material,salt)
    key = hkdf_expand(prk,info, length=length)
    # print(f"prk is {prk} \n key is {key}")
    return key

class Hkdf(object):
    '''
    Wrapper class for HKDF extract and expand functions
    '''
    def __init__(self, input_key_material,salt, hash=hashlib.sha256):

        self._hash = hash
        self._prk = hkdf_extract(salt, input_key_material, self._hash)
    def expand(self, info="", length=32):

        return hkdf_expand(self._prk, info, length, self._hash)


# kdf = Hkdf(unhexlify(b"8e94ef805b93e683ff18"), b"asecretpassword", hash=hashlib.sha512)
# key = kdf.expand(b"context1", 16)
# print(key)

# salt = unhexlify(b"8e94ef805b93e683ff18")
# input_key_material = b"asecretpassword"
# key=HKDF(salt,input_key_material)
# print(key.encode('utf-16'))