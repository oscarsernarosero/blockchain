"""
This code makes use of the code written by Jimmy Song in the book Programming Bitcoin.
This code only tries to build on top of Jimmi Song's code and take it to the next step as 
suggested by him in chapter 14 of his book.
This module is coded entirely by Oscar Serna.

This is just an educational-purpose code. The author does not take any responsibility
on any losses caused by the use of this code.
"""
from constants import *
from ecc import PrivateKey, S256Point, Signature
from script import p2pkh_script, p2sh_script, Script, p2wpkh_script,p2wsh_script
from helper import (
    decode_base58, SIGHASH_ALL, h160_to_p2pkh_address, hash160, 
    h160_to_p2sh_address, encode_varint)
from tx import TxIn, TxOut, Tx, TxFetcher
import hashlib
from bip32 import Xtended_privkey, Xtended_pubkey
from bip39 import Mnemonic
import segwit_addr
from accounts import Account, MasterAccount


class Transact:
    
    @classmethod
    def get_index(self,outs_list, address):    
        """
        For later: implement looking for multiple indexes in the same tx.
        """
       
        print(f"Address: {address}")
        if address[:2] in ["tb","bc"]:
            address = self.decode_p2wpkh_addr(address)
            for index,out in enumerate(outs_list):
                if out.script_pubkey.cmds[1] == address or out.script_pubkey.cmds[0] == address:
                    return index
        else:
            address = decode_base58(address)
            for index,out in enumerate(outs_list):
                if out.script_pubkey.cmds[2] == address or out.script_pubkey.cmds[1] == address:
                    return index
        
        
        raise Exception( "output index not found")

    @classmethod
    def get_amount_utxo(self,outs_list, index):
        """
        Supporting method.
        receives the list of outputs from transaction and the index of 
        particular output of interest and returns the amount of the UTXO.
        outs_list: is the list of outputs of previous transaction where the UTXO is.
        index: the index of the UTXO in the list of all the outputs.
        """
        return outs_list[index].amount

    @classmethod
    def get_tx_ins_utxo(self,prev_tx_id_list, receiving_address, testnet=True):
        """
        deprecated. Use get_inputs instead.
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
            prev_index = self.get_index(prev_tx.tx_outs, receiving_address)
            tx_in = TxIn(bytes.fromhex(prev_tx_id),prev_index)
            utxo = self.get_amount_utxo(prev_tx.tx_outs, prev_index)
            #print(f"index 1: {prev_index}, amount: {utxo}")
            tx_ins.append({"tx_in": tx_in, "utxo": utxo})

        return tx_ins

    @classmethod
    def calculate_fee(cls,version, tx_ins, tx_outs, locktime, privkey, redeem_script, 
                      testnet=True, multisig =False, fee_per_byte = 12, segwit = False ):
        """
        privkey: can be just one or a list of private keys in the case of multisignature.
        """
        my_tx = Tx(1, tx_ins, tx_outs, 0, testnet=True)
        print(my_tx)

        # sign the inputs in the transaction object using the private key
        if multisig:
            #for tx_input in range(len(tx_ins)):
             #   print(my_tx.sign_input_multisig(tx_input, privkey, redeem_script))
                pass
        else:
            for tx_input in range(len(tx_ins)):
                print(my_tx.sign_input(tx_input, privkey, segwit = segwit))
            # print the transaction's serialization in hex

        #Let's calculate the fee and the change:
        tx_size = len(my_tx.serialize().hex())
        if multisig: tx_size*=2
        fee = tx_size * fee_per_byte
        print(f"fee: {fee}")
        return fee
    
    @classmethod
    def calculate_fee_w_master(self,utxo_list, my_tx, fee_per_byte = 3, segwit = False):
        """
        privkey: can be just one or a list of private keys in the case of multisignature.
        """
        #tx = self.sign_w_master(utxo_list, my_tx, master_account, segwit)

        #Let's calculate the fee and the change:
        if segwit: tx_size = len(my_tx.serialize().hex())+5
        else: tx_size = len(my_tx.serialize().hex())+len(utxo_list)*64
        print(f"size of transaction without signatures: {tx_size}")
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
    def decode_p2wpkh_addr(self,address):
        decoded = segwit_addr.bech32_decode(address)
        str_pubkeyhash = ""
        for char in decoded[1][1:]:
            str_pubkeyhash += "{0:05b}".format(char)
    
        try: 
            addr_bytes = int(str_pubkeyhash,2).to_bytes(20,"big")
        except: 
            print("trying P2WSH")
            addr_bytes = int(str_pubkeyhash[:256],2).to_bytes(32,"big")
        return addr_bytes
    
class Transaction(Transact):
      
    def __init__(self,transaction,sender_account,tx_ins,utxos ,tx_outs, fee, change, testnet, segwit):
        """
        utxo_tx_id_list: the list of the transaction ids where the UTXOs are.
        receivingAddress_w_amount_list: a list of tuples (to_address,amount) specifying
        the amount to send to each address.
        sender_account: must be an Account object.
        If fee is specifyed, then the custom fee will be applied.
        """
        self.transaction = transaction
        self.sender_account = sender_account
        self.tx_ins = tx_ins
        self.utxos = utxos
        self.fee = fee
        self.segwit = segwit
        self.tx_outs = tx_outs
        self.testnet = testnet
        self.change = change
        
    @classmethod
    def validate_data(self,sender_account_address,outputAddress_amount_list ):
        if sender_account_address[0] in "2mnt":
            testnet = True
            for addr in outputAddress_amount_list:
                if addr[0][0] not in "2mnt":
                    raise Exception (f"{addr[0]} not a valid testnet address. Funds will be lost!")
                if addr[1] < 1:
                    raise Exception (f"{addr[1]} not a valid amount. It should be greater than 1 satoshis")
        else:
            testnet  = False
            for addr in outputAddress_amount_list:
                if addr[0][0] not in "13b":
                    raise Exception (f"{addr[0]} not a valid mainnet bitcoin address. Funds will be lost!")
                if addr[1] < 1:
                    raise Exception (f"{addr[1]} not a valid amount. It should be greater than 1 satoshis")
              
        return testnet
    
    @classmethod
    def get_outputs(self, receivingAddress_w_amount_list, account=None, send_all=False):
        """
        receivingAddress_w_amount_list: ('receiving_address',amount_in_satoshi)
        account: can be an Account object or an address (String)
        send_all: if you want to send all the funds set this to True. You don't need an account if you set send_all to True.
        """
        
        #https://en.bitcoin.it/wiki/List_of_address_prefixes
        #We create the tx outputs based on the kind of address
        
        if send_all == False and account is None: raise Exception("A change account must be provided if send_all is False. If not, this would result in a lost of funds.")
        
        tx_outs = []
        for output in receivingAddress_w_amount_list:
            
            if output[0][0] in "1mn" :
                tx_outs.append( TxOut(output[1], p2pkh_script(decode_base58(output[0]))))
            #For multidignature p2sh
            elif output[0][0] in "23" :
                tx_outs.append( TxOut(output[1], p2sh_script(decode_base58(output[0]))))
            elif output[0][:2] in ["bc","tb"] :
                tx_outs.append( TxOut(output[1], p2wpkh_script(self.decode_p2wpkh_addr(output[0]))))#Needs to be tested
            else:raise Exception ("Not supported address.")
        
        #Let's return the fake change to our change-account address. 
        if not send_all:
            #we check if we received an address or an account as an argument and convert it if necessary.
                
            if account.addr_type == "p2pkh":tx_outs.append( TxOut(1000000, p2pkh_script(decode_base58(account.address))))
            elif account.addr_type in ["p2wpkh","p2wsh"]:
                tx_outs.append( TxOut(1000000, p2wpkh_script(self.decode_p2wpkh_addr(account.address))))
            elif account.addr_type in  ["p2sh","p2sh_p2wpkh","p2sh_p2wsh"]:
                tx_outs.append( TxOut(1000000, p2sh_script(decode_base58(account.address))))
            else: raise Exception ("Not supported address.")
            
        return tx_outs
                
    @classmethod
    def get_inputs(self,utxo_list):
        print(f"utxo_list: {utxo_list}")
        
        tx_ins = []

        for _utxo in utxo_list:
            tx_in = TxIn(bytes.fromhex(_utxo[0]) , _utxo[1])
            tx_ins.append({"tx_in": tx_in, "utxo": _utxo[2]})

        return tx_ins
         
    
    @classmethod
    def unsigned_tx(self,tx_ins, tx_outs, testnet, segwit, change_account, utxos,receivingAddress_w_amount_list):
        """
        This method is overwritten in the MultiSigTransaction class for the multi-signature case.
        """
        
        my_tx = Tx(1, tx_ins, tx_outs, 0, testnet=testnet, segwit=segwit)#check for segwit later!!!!
        
        #CHECK THE FOLLOWING LINE LATER!! 
        if change_account.addr_type not in  ["p2sh","p2wsh","p2sh_p2wsh"]:
            fee = self.calculate_fee(1, tx_ins, tx_outs, 0, privkey=change_account.privkey, 
                                         redeem_script=None, testnet=testnet, segwit = segwit)
            
            
            change = self.calculate_change(utxos, fee, [x[1] for x in receivingAddress_w_amount_list])

        else: raise Exception ("This is a multisignature transaction. Use MultiSigTransaction instead of Transaction.")
        
        my_tx.tx_outs[-1].amount = change
        return fee, change, my_tx
    
    
    @classmethod
    def unsigned_tx_w_master(self,tx_ins, tx_outs, testnet, segwit, 
                             utxos,receivingAddress_w_amount_list, utxo_list):
        
        my_tx = Tx(1, tx_ins, tx_outs, 0, testnet=testnet, segwit=segwit)#check for segwit later!!!!
       
        fee = self.calculate_fee_w_master(utxo_list, my_tx, segwit=segwit)
            
        change = self.calculate_change(utxos, fee, [x[1] for x in receivingAddress_w_amount_list])
        
        my_tx.tx_outs[-1].amount = change
        return fee, change, my_tx
        
        
    @classmethod
    def sign_tx(self, tx_ins, transaction, sender_account, segwit):
        p2sh = False
        if sender_account.addr_type in ["p2sh","p2sh_p2wpkh"]: p2sh = True
        for tx_input in range(len(tx_ins)):
            if not transaction.sign_input(tx_input, sender_account.privkey, segwit = segwit, p2sh = p2sh):
                return False
        return True
    
    @classmethod
    def sign_w_master(self, utxo_list, transaction, master_account, segwit):
        
        for tx_input in range(len(utxo_list)):
            
            addr_index = utxo_list[tx_input][4]
            print(f"Address trying to spend from: {utxo_list[tx_input][5]}, path {utxo_list[tx_input][3]}{addr_index}")
            #if utxo_list[tx_input]["address.type"] == "change": change_addr = True
            #else: change_addr = False
            signing_master_account = master_account.get_child_from_path(f"{utxo_list[tx_input][3]}{addr_index}")
            #type doesn't really matter here because the private key doesn't depend on it. So, a simple p2wpkh is Ok.
            signing_account = Account(int.from_bytes(signing_master_account.private_key,"big"), "p2wpkh",
                                      signing_master_account.testnet)
            print(signing_account.address)
            
            if utxo_list[tx_input][6] == P2WPKH or utxo_list[tx_input][6] == P2WSH or utxo_list[tx_input][6] == P2SH_P2WPKH:
                print(f"from Transactions: sending from a SegWit Address")
                segwit=True
            else:
                print(f"from Transactions: sending from a NOT SegWit Address")
                segwit=False
                
            if utxo_list[tx_input][6] == P2SH_P2WPKH:
                print(f"from Transactions: sending from a P2SH Address")
                p2sh=True
            else:
                print(f"from Transactions: sending NOT from a P2SH Address")
                p2sh=False
                
            if not transaction.sign_input(tx_input, signing_account.privkey, segwit=segwit, p2sh=p2sh):
                print("SIGNATURE FAILED")
        return transaction
    
    @classmethod
    def create(self, utxo_tx_id_list, receivingAddress_w_amount_list, sender_account, fee=None, #Modify code to allow manual fee!!!
                 segwit=False):
        """
        utxo_tx_id_list: the list of the transaction ids where the UTXOs are.
        receivingAddress_w_amount_list: a list of tuples (to_address,amount) specifying
        the amount to send to each address.
        sender_account: must be an Account object.
        If fee is specifyed, then the custom fee will be applied.
        """
        testnet = self.validate_data(sender_account.address,receivingAddress_w_amount_list)
        tx_outs = self.get_outputs(receivingAddress_w_amount_list, sender_account)
        tx_ins_utxo = self.get_tx_ins_utxo(utxo_tx_id_list, sender_account.address, testnet)
        tx_ins = [x["tx_in"] for x in tx_ins_utxo]
        utxos = [x["utxo"] for x in tx_ins_utxo]
        fee, change, transaction = self.unsigned_tx(tx_ins, tx_outs, testnet, segwit, sender_account, utxos,receivingAddress_w_amount_list)
        if self.sign_tx( tx_ins, transaction, sender_account, segwit):
            return Transaction(transaction, sender_account, tx_ins,utxos ,tx_outs, fee, change, testnet, segwit)
        else:
            raise Exception("Signature faliled") 
            
    @classmethod
    def create_from_master(self, utxo_list, receivingAddress_w_amount_list, master_account,change_account,
                           fee=None, #Modify code to allow manual fee!!!
                 segwit=False):
        """
        utxo_list: the list of touples with all the UTXOs information. Likethis:
        [(tx_id, out_index, amount, path, account_index, address, type), ... ].
        receivingAddress_w_amount_list: a list of tuples (to_address,amount) specifying
        the amount to send to each address.
        master_account: must be a MasterAccount object.
        change_account: must be an Account object. This will contain the address to which
        the change of the transaction will be sent to.
        If fee is specifyed, then the custom fee will be applied.
        """
        testnet = master_account.testnet
        tx_outs = self.get_outputs(receivingAddress_w_amount_list, change_account)
        tx_ins_utxo = self.get_inputs(utxo_list)
        tx_ins = [x["tx_in"] for x in tx_ins_utxo]
        utxos = [x["utxo"] for x in tx_ins_utxo]
        fee, change, transaction = self.unsigned_tx_w_master(tx_ins, tx_outs, testnet, segwit, utxos,receivingAddress_w_amount_list, utxo_list)
        if self.sign_w_master( utxo_list, transaction, master_account, segwit):
            return Transaction(transaction, master_account, tx_ins,utxos ,tx_outs, fee, change, testnet, segwit)
        else:
            raise Exception("Signature faliled") 
     
               
class MultiSigTransaction(Transaction):
    
    @classmethod
    def unsigned_tx(self,tx_ins, tx_outs, testnet, segwit, sender_account, utxos,receivingAddress_w_amount_list,send_all):
        
        my_tx = Tx(1, tx_ins, tx_outs, 0, testnet=testnet, segwit=segwit)
        
        fee = self.calculate_fee(1, tx_ins, tx_outs, 0, privkey=sender_account.privkey,
                                redeem_script=sender_account.redeem_script,testnet=testnet, 
                                segwit = segwit, multisig =True)
        
        if send_all: 
            my_tx.tx_outs[0].amount -= fee
            change = 0
        else:
            change = self.calculate_change(utxos, fee, [x[1] for x in receivingAddress_w_amount_list])
            my_tx.tx_outs[-1].amount = change
            
        return fee, change, my_tx

    @classmethod
    def unsigned_tx_from_wallet(self,tx_ins, tx_outs, testnet, segwit,utxos,receivingAddress_w_amount_list, utxo_list, send_all):
        
        my_tx = Tx(1, tx_ins, tx_outs, 0, testnet=testnet, segwit=segwit)
        
        fee = self.calculate_fee_w_master(utxo_list, my_tx, segwit=segwit)
        
        if send_all: 
            my_tx.tx_outs[0].amount -= fee
            change = 0
        else:
            change = self.calculate_change(utxos, fee, [x[1] for x in receivingAddress_w_amount_list])
            my_tx.tx_outs[-1].amount = change
            
        return fee, change, my_tx

    @classmethod
    def sign1by1(self, transaction, sender_account):
        """
        transaction: must be Tx object.
        sender account: must be Multisignature object.
        """
        p2sh_p2wsh=False
        if sender_account.addr_type == "p2sh_p2wsh": p2sh_p2wsh = True
            
        for tx_input in range(len(transaction.tx_ins)):
            transaction.sign_input_multisig_1by1(tx_input, sender_account.privkey,sender_account.privkey_index,
                                                 sender_account.redeem_script, sender_account.n,
                                                 sender_account.m,transaction.segwit,p2sh_p2wsh)
        return transaction
    
    @classmethod
    def sign1by1_with_wallet(self, utxo_list, transaction, account):
        """
        transaction: must be Tx object.
        sender account: must be Multisignature object.
        """
        
        for tx_input in range(len(transaction.tx_ins)):
            
            p2sh_p2wsh=False
            
            addr_index = utxo_list[tx_input][4]
            print(f"Address trying to spend from: {utxo_list[tx_input][5]}, path {utxo_list[tx_input][3]}{addr_index}")
            
            if utxo_list[tx_input][3] == "m/1/": 
                print(f"change account index {addr_index}")
                signing_account = account.get_change_account(index=addr_index) 
            else: 
                print(f"Deposit account index {addr_index}")
                signing_account =  account.get_deposit_account(index=addr_index)
                
            print(signing_account.address)
            
            if utxo_list[tx_input][6] == P2SH_P2WPKH:
                print(f"from Transactions: sending from a p2sh_p2wsh Address")
                p2sh_p2wsh = True
            
            transaction.sign_input_multisig_1by1(tx_input, signing_account.privkey,signing_account.privkey_index,
                                                 signing_account.redeem_script, signing_account.n,
                                                 signing_account.m,signing_account.segwit,p2sh_p2wsh)
        return transaction
        
    
    @classmethod
    def verify_signatures(self, transaction, sender_account):
        p2sh_p2wsh=False
        if sender_account.addr_type == "p2sh_p2wsh": p2sh_p2wsh = True
        if transaction.verify_signatures( sender_account.m, transaction.segwit,p2sh_p2wsh):
            return transaction
        else:
            return False
        
    @classmethod    
    def verify_signatures_with_wallet(self, transaction, account):
        if transaction.verify_signatures( account.m, transaction.segwit):
            return transaction
        else:
            return False
    
    @classmethod
    def create(self, utxo_tx_id_list, receivingAddress_w_amount_list, 
               sender_account, 
               change_address, 
               fee=None, #Modify code to allow manual fee!!!
                 segwit=False, send_all=False):
        """
        Currently only works with simple multisignature accounts. HD Multisignature accounts is next step!!
        utxo_tx_id_list: the list of the transaction ids where the UTXOs are.
        receivingAddress_w_amount_list: a list of tuples (to_address,amount) specifying
        the amount to send to each address.
        sender_account: must be a MultSigAccount object. 
        change_address: String. The address to receive the change.
        If fee is specifyed, then the custom fee will be applied.
        """
        #testnet = self.validate_data(sender_account.address,receivingAddress_w_amount_list)
        testnet = sender_account.testnet
        if send_all:  tx_outs = self.get_outputs(receivingAddress_w_amount_list, send_all = send_all)
        else:         tx_outs = self.get_outputs(receivingAddress_w_amount_list, account = change_address)
        #tx_ins_utxo = self.get_tx_ins_utxo(utxo_tx_id_list, sender_account.address, testnet)
        tx_ins_utxo = self.get_inputs(utxo_tx_id_list)#change name of variable from utxo_tx_id_list to utxo_list
        tx_ins = [x["tx_in"] for x in tx_ins_utxo]
        utxos = [x["utxo"] for x in tx_ins_utxo]
        fee, change, transaction = self.unsigned_tx(tx_ins, tx_outs, testnet, segwit, sender_account,
                                                    utxos,receivingAddress_w_amount_list,send_all)
        transaction = self.sign1by1(transaction, sender_account)
        final_tx =  self.verify_signatures(transaction, sender_account)
        if isinstance(final_tx,bool):
            print("transaction not ready to broadcast")
            return (MultiSigTransaction(transaction, sender_account, tx_ins,utxos ,tx_outs, fee, change, testnet, segwit),False)
        else:
            print("transaction ready!")
            return (final_tx,True)
    
    @classmethod
    def create_from_wallet(self, utxo_list, receivingAddress_w_amount_list, 
               multi_sig_account, 
               change_address, 
               fee=None, #Modify code to allow manual fee!!!
                 segwit=False, send_all=False, no_change=False):
        """
        Currently only works with simple multisignature accounts. HD Multisignature accounts is next step!!
        utxo_list: the list of touples with all the UTXOs information. Likethis:
        [(tx_id, out_index, amount, path, account_index, address, type), ... ].
        receivingAddress_w_amount_list: a list of tuples (to_address,amount) specifying
        the amount to send to each address.
        multi_sig_account: must be a multi-signature account such as SHMAccount or an FHMAccount object. 
        change_address: String. The address to receive the change.
        If fee is specifyed, then the custom fee will be applied.
        """
        #testnet = self.validate_data(sender_account.address,receivingAddress_w_amount_list)
        testnet = multi_sig_account.testnet
        #Maybe, we can create the change account inside this method instead of receiving it through the arguments.
        if send_all:  tx_outs = self.get_outputs(receivingAddress_w_amount_list, send_all = send_all)
        else:         tx_outs = self.get_outputs(receivingAddress_w_amount_list, account = change_address)
        #tx_ins_utxo = self.get_tx_ins_utxo(utxo_tx_id_list, sender_account.address, testnet)
        tx_ins_utxo = self.get_inputs(utxo_list)
        tx_ins = [x["tx_in"] for x in tx_ins_utxo]
        utxos = [x["utxo"] for x in tx_ins_utxo]
        
        fee, change, transaction = self.unsigned_tx_from_wallet(tx_ins, tx_outs, testnet, segwit,
                                                                utxos,receivingAddress_w_amount_list, 
                                                                utxo_list, send_all)
        
        transaction = self.sign1by1_with_wallet(utxo_list, transaction, multi_sig_account)
        final_tx =  self.verify_signatures_with_wallet(transaction, multi_sig_account)
        if isinstance(final_tx,bool):
            print("transaction not ready to broadcast")
            return (MultiSigTransaction(transaction, None, tx_ins,utxos ,tx_outs, fee, change, testnet, segwit),False)
        else:
            print("transaction ready!")
            return (final_tx,True)
        
    
    @classmethod
    def sign_received_tx(self,multisig_transaction,sender_account):
        """
        multisig_transaction: must be a MultiSigTransaction object.
        sender_account: must be a MultSigAccount object.
        """
        signed_tx = self.sign1by1(multisig_transaction.transaction,sender_account)
        final_tx =  self.verify_signatures(signed_tx, sender_account)
        if isinstance(final_tx,bool):
            print("transaction not ready to broadcast")
            return MultiSigTransaction(signed_tx, sender_account, multisig_transaction.tx_ins,multisig_transaction.utxos ,
                                       multisig_transaction.tx_outs, multisig_transaction.fee, multisig_transaction.change,
                                       multisig_transaction.testnet, multisig_transaction.segwit), False
        else:
            print("TRANSACTION READY!\nRun serialize().hex() to get the raw transaction.")
            return final_tx, True
        
        
    @classmethod
    def sign_received_tx_with_wallet(self,utxo_list, multisig_transaction, multi_sig_account):
        """
        multisig_transaction: must be a MultiSigTransaction object.
        sender_account: must be a MultSigAccount object.
        """
        signed_tx = self.sign1by1_with_wallet(utxo_list, multisig_transaction.transaction, multi_sig_account)
        final_tx =  self.verify_signatures_with_wallet(signed_tx, multi_sig_account)
        if isinstance(final_tx,bool):
            print("transaction not ready to broadcast")
            return MultiSigTransaction(signed_tx, None, multisig_transaction.tx_ins,multisig_transaction.utxos ,
                                       multisig_transaction.tx_outs, multisig_transaction.fee, multisig_transaction.change,
                                       multisig_transaction.testnet, multisig_transaction.segwit), False
        else:
            print("TRANSACTION READY!\nRun serialize().hex() to get the raw transaction.")
            return MultiSigTransaction(final_tx, None, multisig_transaction.tx_ins,multisig_transaction.utxos ,
                                       multisig_transaction.tx_outs, multisig_transaction.fee, multisig_transaction.change,
                                       multisig_transaction.testnet, multisig_transaction.segwit), True
        
    @classmethod
    def sign_tx():
        raise Exception ("Unsupported for multisignature transactions. Use sign1by1() method instead." )
    