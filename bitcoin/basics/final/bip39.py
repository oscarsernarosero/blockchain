from os import urandom
import hashlib
import unicodedata
import hmac

class Mnemonic:
    
    def __init__(self,entropy = 128, words=None, random_number=None, passphrase="", seed=None):
        self.entropy = entropy
        self.words = words
        self.random_number = random_number
        self.passphrase = passphrase
        self.seed= seed
        self.MS = None
        
    def __repr__(self):
        return self.words.decode("utf-8") 
    
    @classmethod
    def generate_random(self,entropy = 128,  passphrase=""):
        
        ENT = entropy
        
        ENTsie = ENT//8
     

        random_number = urandom(ENTsie)
        
        return self.generate_from_number(number = random_number, entropy=entropy, passphrase = passphrase)
      
        
    @classmethod
    def generate_from_number(self,number = None, entropy = 128,  passphrase=""):
        
        ENT = entropy

        CSsize = ENT//32

        MS = (ENT+CSsize)//11
        
        return self.get_seed(ENT = entropy, random_number = number, passphrase = passphrase,MS=MS)
    
    @classmethod
    def recover_from_words(self,mnemonic_list = None, entropy = 128,  passphrase=""):
        
        return self.get_seed(mnemonic_list = mnemonic_list, passphrase = passphrase)
      
        
    @classmethod
    def get_seed(cls,ENT = 128, mnemonic_list=None, random_number=None,passphrase="",MS=None):
        
        words = []
        with open("english_word.txt", "r", encoding="utf-8") as f:
            for w in f.readlines():
                words.append(w.strip())

        if random_number is not None:

            if ENT not in [128,160,192,224,256]:
                raise Exception( "not a valid entropy." )                
            if isinstance(random_number,str):
                size = len(random_number)//2
                random_number = int(random_number,16).to_bytes(size,"big")
            elif isinstance(random_number,int):
                random_number.to_bytes(ENT//8,"big")
            elif isinstance(random_number,bytes):
                if len(random_number)*8 != ENT:
                    raise Exception( "Length of random number must match entropy")
            else:
                raise Exception( f"NOT a valid format for random number. Must be hex_string, int, or bytes. Not {type(random_number)}")
            
            CSsize = ENT//32
            CS = hashlib.sha256(random_number).digest()
            CSstring = "{0:0256b}".format(int.from_bytes(CS,"big"),16)[:CSsize]

            #This is a string binary representation
            format_string = "{0:0"+str(ENT)+"b}"
            pre_binary_seed =  format_string.format(int.from_bytes(random_number,"big"),16) + CSstring

            binary_seed_list = [pre_binary_seed[i*11:(i+1)*11] for i in range(MS) ]

            mnemonic_words = []
            for i in range(MS):
                mnemonic_words.append(words[int(binary_seed_list[i],2)])


        elif mnemonic_list is not None:
            if len(mnemonic_list) not in [12,15,18,21,24]:
                raise Exception( "Not a valid amount of words. Must be 12, 15, 18, 21, or 24 word list.")

            random_number_list = ["{0:016b}".format(words.index(x))[-11:] for x in mnemonic_list]
            random_number = "".join(random_number_list)
            size = len(random_number)//2
            random_number = int(random_number[:-(size//32)],2).to_bytes(size,"big")
            mnemonic_words = mnemonic_list

        salt = (unicodedata.normalize("NFKD","mnemonic" + passphrase)).encode("utf-8")

        mnemonic = " ".join(mnemonic_words)
        mnemonic = unicodedata.normalize("NFKD", mnemonic).encode("utf-8")

        seed = hashlib.pbkdf2_hmac("sha512", mnemonic, salt, 2048)

        return cls( entropy = ENT, words=mnemonic, random_number=random_number, 
                   passphrase=passphrase,seed=seed)