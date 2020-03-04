from ecc import PrivateKey, S256Point, Signature
from script import p2pkh_script, p2sh_script, Script
from helper import decode_base58, SIGHASH_ALL, h160_to_p2pkh_address, hash160, h160_to_p2sh_address
from tx import TxIn, TxOut, Tx, TxFetcher

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
       
        
class Build_TX():
    @classmethod
    def get_index(cls,outs_list, address):
        """
        Supporting method.
        receives the list of outputs from transaction and find the index of 
        particular output of interest.
        outs_list: is the list of outputs of previous transaction where the UTXO is.
        address: the address trying to spend the UTXO.
        """
        for index,out in enumerate(outs_list):
            if out.script_pubkey.cmds[2] == decode_base58(address) or out.script_pubkey.cmds[1] == decode_base58(address):
                return index
        raise Expection( "output index not found")

    @classmethod
    def get_amount_utxo(cls,outs_list, index):
        """
        Supporting method.
        receives the list of outputs from transaction and the index of 
        particular output of interest and returns the amount of the UTXO.
        outs_list: is the list of outputs of previous transaction where the UTXO is.
        index: the index of the UTXO in the list of all the outputs.
        """
        return outs_list[index].amount

    @classmethod
    def get_tx_ins_utxo(cls,prev_tx_id_list, receiving_address, testnet=True):
        """
        Receives a list of transaction ids where the UTXOs to spend are, and 
        also the receiving address to return a valid tx_in list to create
        a transaction.
        prev_tx_id_list: list of the transaction ids where the UTXOs are.
        receiving_address: the address trying to spend the UTXO (String).
        testnet: if the transaction is in testnet or not (boolean).
        """
        tx_ins = []

        for prev_tx_id in prev_tx_id_list:
            prev_tx = TxFetcher.fetch(prev_tx_id, testnet)
            prev_index = cls.get_index(prev_tx.tx_outs, receiving_address)
            tx_in = TxIn(bytes.fromhex(prev_tx_id),prev_index)
            utxo = cls.get_amount_utxo(prev_tx.tx_outs, prev_index)
            #print(f"index 1: {prev_index}, amount: {utxo}")
            tx_ins.append({"tx_in": tx_in, "utxo": utxo})

        return tx_ins

    @classmethod
    def calculate_fee(cls,version, tx_ins, tx_outs, locktime, privkey, redeem_script, 
                      testnet=True, multisig =False, fee_per_byte = 8 ):
        """
        privkey: can be just one or a list of private keys in the case of multisignature.
        """
        my_tx = Tx(1, tx_ins, tx_outs, 0, testnet=True)
        print(my_tx)

        # sign the inputs in the transaction object using the private key
        if multisig:
            for tx_input in range(len(tx_ins)):
                print(my_multisig_tx.sign_input_multisig(tx_input, privkey, redeem_script))
        else:
            for tx_input in range(len(tx_ins)):
                print(my_tx.sign_input(tx_input, privkey))
            # print the transaction's serialization in hex

        #Let's calculate the fee and the change:
        tx_size = len(my_tx.serialize().hex())
        #fee_per_byte = 8 # I changed from 2 to 10 after sending this transaction because it had really low appeal to miners.
        fee = tx_size * fee_per_byte
        print(f"fee: {fee}")
        return fee
    
    @classmethod
    def calculate_change(cls, utxo_list, fee, amountTx):
        """
        utxo_list: the list of the amounts of every utxo.
        amountTx: the list of the ammounts of every transaction output.
        fee: the fee of the transaction.
        Returns the respective amount of the change.
        """
        total_utxo = sum(utxo_list)
        total_out = sum(amountTx)
        change = total_utxo - fee - total_out
        print(f"change {change}")
        if change < 0:
            raise Exception( f"Not enough utxos: total_utxo {total_utxo} and total_out {total_out} meaning change = {change}")
        #Let's make sure that we are actually spending the exact amount of the UTXO
        total_send=fee+total_out+change
        diff = total_utxo-total_send
        print(f"total {total_send}, diff: {diff}")

        return change

    @classmethod
    def build_tx(cls, utxo_tx_id_list, outputAddress_amount_list, account, testnet = True, fee=None):
        """
        utxo_tx_id_list: the list of the transaction ids where the UTXOs are.
        outputAddress_amount_list: a list of tuples (to_address:amount) specifying
        the amount to send to each address.
        account: must be an Account object.
        If fee is specifyed, then the custom fee will be applied.
        
        Returns the hex of the raw transaction.
        """
        #Validation process:
        if testnet:
            for addr in outputAddress_amount_list:
                if addr[0][0] not in "2mn":
                    raise Exception (f"{addr[0]} not a testnet address. Funds will be lost!")
                if addr[1] < 1:
                    raise Exception (f"{addr[1]} not a valid amount. It should be greater than 1 satoshis")
        else:
            for addr in outputAddress_amount_list:
                if addr[0][0] not in "13":
                    raise Exception (f"{addr[0]} not a mainnet bitcoin address. Funds will be lost!")
                if addr[1] < 1:
                    raise Exception (f"{addr[1]} not a valid amount. It should be greater than 1 satoshis")
              
        # initializing variables
        tx_outs =[]
        tx_ins =[]
        change = int(0.01 * 100000000)# we are going to fix this later
        #amountTx= int(0.01 * 100000000)
        
        #https://en.bitcoin.it/wiki/List_of_address_prefixes
        #We create the tx outputs based on the kind of address (multisig or normal)
        for output in outputAddress_amount_list:
            if output[0][0] in "1mn" :
                tx_outs.append( TxOut(output[1], p2pkh_script(decode_base58(output[0]))))
            elif output[0][0] in "23" :
                tx_outs.append( TxOut(output[1], p2sh_script(decode_base58(output[0]))))
        
        #Let's return the fake change to our same address. 
        #This will change later when BIP32 is implemented.
        if testnet:
            if account.testnet_address in "mn":
                tx_outs.append( TxOut(change, p2pkh_script(decode_base58(account.testnet_address))))
            elif account.testnet_address == "2":
                tx_outs.append( TxOut(change, p2sh_script(decode_base58(account.testnet_address))))
        else:
            if account.address == "1":
                tx_outs.append( TxOut(change, p2pkh_script(decode_base58(account.address))))
            elif account.address == "3":
                tx_outs.append( TxOut(change, p2sh_script(decode_base58(account.address))))
                
        #Creating the Tx_In list:
        if testnet: tx_ins_utxo = cls.get_tx_ins_utxo(utxo_tx_id_list, account.testnet_address, testnet)
        else:  tx_ins_utxo = cls.get_tx_ins_utxo(utxo_tx_id_list, account.address, testnet)
            
        tx_ins = [x["tx_in"] for x in tx_ins_utxo]
        utxos = [x["utxo"] for x in tx_ins_utxo]
        
        my_tx = Tx(1, tx_ins, tx_outs, 0, testnet=testnet)
        
        fee = cls.calculate_fee(1, tx_ins, tx_outs, 0, privkey=account.privkey, redeem_script=None, testnet=True)
        change = cls.calculate_change(utxos, fee, [x[1] for x in outputAddress_amount_list])
        
        my_tx.tx_outs[-1].amount = change
        
        for tx_input in range(len(tx_ins)):
            if not my_tx.sign_input(tx_input, account.privkey):
                raise Exception("Signature failed")
        
        return my_tx.serialize().hex()
        