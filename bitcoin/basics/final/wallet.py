from ecc import PrivateKey, S256Point, Signature
from script import p2pkh_script, Script
from helper import decode_base58, SIGHASH_ALL, h160_to_p2pkh_address, hash160, h160_to_p2sh_address


class Account():
    
    def __init__(self, _privkey):
        """
        Initialize the account with a private key in Integer form.
        """
        self.privkey = PrivateKey(_privkey)
        self.testnet_address = self.privkey.point.address(testnet = True)
        self.address = self.privkey.point.address(testnet = False)
        
    def __repr__(self):
        return f"Private Key Hex: {self.privkey.hex()}"
        
    
    @classmethod
    def from_phrase(cls,phrase, endian="big"):
        """
        phrase must be in bytes.
        endian can be either "big" or "little"
        Returns an account using the phrase chosen which is converted to an Integer
        """
        if endian not in ["big","little"]:
            raise Exception( f'endian can be either "big" or "little" not "{endian}"')
            
        if isinstance(phrase, str):
            phrase = phrase.encode('utf-8')
            
        elif isinstance(phrase, bytes):
            return cls(int.from_bytes(phrase,endian))
        
        else:
            raise Exception( f"The phrase must be a string or bytes, not {type(phrase)}" )


class MultSigAccount():
    
    def __init__(self,m, n,  _privkeys):
        """
        Initialize the account with a private key in Integer form.
        """
        if n != len(_privkeys):
            raise Exception("m must be equal to the amount of private keys")
        if m < 1 or m > 16 or n < 1 or n > 16:
            raise Exception("m and n must be between 1 and 16")
        if m > n:
            raise Exception("m must be always less or equal than n")
            
            
        self.privkeys = [PrivateKey(privkey) for privkey in _privkeys]
        self.m = m
        self.n = n
        pubkeys = [x.point.sec() for x in self.privkeys]
        self.redeem_script = Script([m+80, *pubkeys, n + 80, 174])
        serialized_redeem = self.redeem_script.raw_serialize()
        self.testnet_address = h160_to_p2sh_address(hash160(serialized_redeem), testnet=True)
        self.address = h160_to_p2sh_address(hash160(serialized_redeem), testnet=False)
        
    def __repr__(self):
        return f"Private Key Hex: {self.privkey.hex()}"
        
    
    @classmethod
    def from_phrases(cls, m , n , phrases):
        """
        phrase: must be a list of tuples of (bytes, endian) or (string, endian). i.e:
            [(b"my secret","little"),("my other secret","big")]
            
        endian: can be either "big" or "little"
        Returns a multisignature account using the phrases chosen which are converted to Integers
        """
        keys = [int.from_bytes(key[0],key[1]) for key in phrases]
        return cls(m,n,keys)
       

    
    