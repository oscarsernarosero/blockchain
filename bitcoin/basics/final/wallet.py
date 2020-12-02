"""
This module is coded entirely by Oscar Serna.
This code makes use of the code written by Jimmy Song in the book Programming Bitcoin.
This code only tries to build on Jimmi Song's code and take it to the next step as 
suggested by him in chapter 14 of his book.

This is just an educational-purpose code. The author does not take any responsibility
on any losses caused by the use of this code.
"""
from constants import *
from accounts import MasterAccount, Account, MultSigAccount
from transactions import Transaction, MultiSigTransaction
from os import urandom
from coin_selector import coin_selector
#from database import WalletDB
from wallet_database_sqlite3 import Sqlite3Wallet, Sqlite3Environment
from blockcypher import get_address_details, get_transaction_details
from blockcypher import pushtx
import threading

import schedule 
import time 
import datetime

class Wallet(MasterAccount):
    
    def __init__(self, depth, fingerprint, index, chain_code, private_key, db_user="neo4j",db_password="wallet", testnet = False):
        
        
        #self.db = WalletDB( "neo4j://localhost:7687" ,db_user ,db_password )
        
        super().__init__( depth, fingerprint, index, chain_code, private_key,testnet)
        
        #if not self.db.exist_wallet(self.get_xtended_key()):
            #self.db.new_wallet(self.get_xtended_key())
        
        #self.start_schedule()
        
    @classmethod
    def start_schedule(self):
        """
        This method starts the process of the scheduled tasks that are in charge of cleaning the database, 
        updating the balace automatically every hour, and update confirmations on new transactions sent or
        received.
        """
        schedule.every().day.do(self.clean_addresses)
        schedule.every().hour.do(self.update_balance)
        #pendind: to update confirmations of incoming and outcoming transactions.
        
    
    #@classmethod
    def clean_addresses(self):
        print("cleaning addresses...")
        self.db.clean_addresses()
    
    def start_conn(self, conn=None):
        if conn:
            self.db= conn
        else:
            self.db = Sqlite3Wallet()
        return True

    def close_conn(self):
        self.db.conn.close()
    
    def close_db(self):
        self.db.close_database()
        
        
    def consult_confirmations(self,tx,BLOCKCYPHER_API_KEY):
    
        tx_details = get_transaction_details(tx,coin_symbol = "btc-testnet",api_key=BLOCKCYPHER_API_KEY)

        try: confirmations = tx_details['confirmations']
        except: confirmations = None

        return confirmations


    def confirm_tx_sent(self,tx,state=0):

        """
        This method consults the blockchain to check on a transaction and its confirmations.
        tx: the transaction hexadecimal to consult. 
        state: only use this for transactions previously consulted. Mostly for internal recursive use.
        """

        env = Sqlite3Environment()
        BLOCKCYPHER_API_KEY = env.get_key("BLOCKCYPHER_API_KEY")[0][0]
        env.close_database()
        
        #initial interval of seconds in which the app will consult the blockchain for changes in the
        #confirmation number. This value will be updated automatically after the first and the third
        #confirmation to gain some efficiency.
        sleeping_time = 90

        initiated = datetime.datetime.now()
        time.sleep(5)

        for i in range(60):
            
            #get confirmations from the blockchain
            confirmations = self.consult_confirmations(tx,BLOCKCYPHER_API_KEY)
            #print(f"confirmations: {confirmations}")
            
            #if a None value is returned, it means that the blockchain doesn't know about the transaction at all.
            #This means that there was an error and the transaction didn't get broadcasted.
            if confirmations is None: 
                
                if   state == 0:
                    if i == 0:  print("Transaction didn't get broadcasted.")
                    else:print("Transaction was refused by the miners.")
                elif state  > 0: print("Transaction was lost in a fork. Try broadcasting again.")#Not sure if this is possible.
                self.start_conn()
                self.db.delete_tx(tx)
                
                self.close_conn()  
                return False

            if confirmations>0 and state==0:
                print(f"got 1 confirmation. Now in state 1 {tx}")
                sleeping_time = (((datetime.datetime.now() - initiated)*3)//5).seconds
                print(f"sleeping time: {sleeping_time}")
                state=1
            elif confirmations>2 and state ==1:
                print(f"got 3 confirmation. Now in state 2 {tx}")
                state=2
            elif confirmations>5 and state == 2:
                state=3
                print("confirmed")
                break
                
            print(f"counter {i}; confirmation {confirmations} for tx {tx} at {datetime.datetime.now()}")
            time.sleep(sleeping_time*(i*2//3 + 1))
            

        print(f"finish {datetime.datetime.now()}")
        
        self.start_conn()
        if state == 0:
            print("transaction not broadcasted")
            self.db.delete_tx(tx)
            self.close_conn()  
            return False
            
        elif state == 1:
            print("transaction disregarded")
            self.db.delete_tx(tx)
            self.close_conn()  
            return False
        
          
        elif state == 2: 
            if confirm_tx_sent(tx,state=2):
                return True
            else: return False
            
        else: 
            print("transaction succesfull")
            self.db.delete_partial_tx(tx)
            return True
    
    def get_i(self,account_path, index,random_index = False):
        if random_index:
            if index is None:
                print(f"get i: {index}")
                i = int.from_bytes(urandom(4),"big")
                i = i & 0x7fffffff
                if i < (2**31-1):print("true")
            elif index is not None:
                if index <= (2**31-1):
                    i = index
                else:
                    raise Exception (f"index must be less than {2**31-1} ")
        else:
            #try: print(f"{self.db} OK.")
            #except: 
            self.start_conn()
                
            last_index = self.db.get_max_index( account_path, self.get_xtended_key())
            print(f"last_index: {last_index}")
            if last_index is None: i = 0
            else: i = last_index + 1
            self.close_conn()
        return i

    def get_unused_addresses_list(self, change_addresses=False, range_of_days=None, last_day_range=None):
        self.start_conn()
        unused_addresses = self.db.get_unused_addresses(wallet = self.get_xtended_key(), 
                                                        days_range = range_of_days, 
                                                        max_days = last_day_range)
        self.close_conn()
        if change_addresses:
            unused_addresses_filtered =  [x for x in unused_addresses if x[1]==1]
        else:
            unused_addresses_filtered =  [x for x in unused_addresses if x[1]==0]
        
        return unused_addresses_filtered
                               
                               
    def create_receiving_address(self, addr_type = "p2pkh",index=None):
        if addr_type.lower()   ==   "p2pkh":     _type  = P2PKH
        elif addr_type.lower() ==  "p2wpkh":     _type  = P2WPKH
        elif addr_type.lower() ==    "p2sh":     _type  = P2SH
        elif addr_type.lower() ==   "p2wsh":     _type  = P2WSH
        elif addr_type.lower() == "p2sh_p2wpkh": _type  = P2SH_P2WPKH
        elif addr_type.lower() == "p2sh_p2wsh":  _type  = P2SH_P2WSH
        else: raise Exception(f"{addr_type} is NOT a valid type of address.")
        receiving_path = "m/44H/0H/0H/"
        i = self.get_i(receiving_path, index)
        path = receiving_path + str(i)
        print(f"Deposit address's Path: {path}")
        receiving_xtended_acc = self.get_child_from_path(path)
        account = Account(int.from_bytes(receiving_xtended_acc.private_key,"big"),addr_type, self.testnet )
        self.start_conn()
        self.db.new_address(account.address,receiving_path,i,FALSE, _type, self.get_xtended_key())
        self.close_conn()
        return account

    
    def create_change_address(self, addr_type = "p2wpkh", index=None):
        change_path = "m/44H/0H/1H/"
        i = self.get_i(change_path, index)
        path = change_path + str(i)
        print(f"Change address's Path: {path}")
        change_xtended_acc = self.get_child_from_path(path)
        account = Account(int.from_bytes(change_xtended_acc.private_key,"big"),addr_type, self.testnet )
        self.start_conn()
        self.db.new_address(account.address,change_path,i,TRUE, P2WPKH, self.get_xtended_key())
        self.close_conn()
        return account
    
    def get_a_change_address(self):
        """
        Returns an Account object containing a change address. It returns an existing unused change
        address account, or creates a new one if necessary.
        """
        unused_addresses = self.get_unused_addresses_list(change_addresses=True)
        
        if len(unused_addresses)>0: 
            #We grab the first unused address always
            #The unused_addresses will be a list of touples. Each touple will be (address, change_addr, path, acc_index)
            change_xtended_acc = self.get_child_from_path(f"{unused_addresses[0][2]}{unused_addresses[0][3]}")
            account = Account(int.from_bytes(change_xtended_acc.private_key,"big"),"p2wpkh", self.testnet )
            if unused_addresses[0][0] == account.address:
                return account
            else:
                raise Exception("Addresses don't match!")
        else: return self.create_change_address()
    
    def get_utxos(self):
        self.start_conn()
        return self.db.look_for_coins(self.get_xtended_key())
    
    def get_coins(self, to_address_amount_list, send_all=None, segwit=True, min_fee_per_byte=70):
        """
        Returns a dictionary with the utxos, fee, and change.
        to_address_amount_list: List of tuples [(address1,amount1),(address2,amount2),...]
        send_all: bool/None: if you are trying to send all of your funds somewhere else, set this to True.
        account_index: if we are trying to spend from a specific account, then spicify the index here.
        total: if we are trying to spend from the wallet and not from a specific account, then set this to True. \
        If True, account_index will be ignored.
        
        """
        
        print(f"From wallet.send(): {to_address_amount_list}")
        #calculate total amount to send from the wallet
        total_amount = sum([x[1] for x in to_address_amount_list])
        
        #We get all of our utxos and calculate our balance by the way.
        all_utxos = self.get_utxos()
        if len(all_utxos) == 0: raise Exception("There is no coins at all here.")
        balance = sum([x[2] for x in all_utxos])
        
        #We calculate the min and max fee for using all of our coins:
        min_fee = (len(all_utxos)*146 + len(to_address_amount_list)*34 + 20)*min_fee_per_byte
        max_fee = min_fee*2 + 546
        
        #If we are trying to send more than what we have minus the minumim fee, but we are not explicitly
        #trying to send all of our money somewhere, then we raise an exception. We don't have enough funds.
        if total_amount>balance-min_fee and not send_all:
            raise Exception(f"Not enough funds in wallet for this transaction.\nOnly {balance} satoshis available for a tx\
            with minimum fee of {min_fee} and a total output of {total_amount}")
        
        #If not, we try to find out if this tx is unawarely trying to spend all of our funds:
        elif total_amount >= balance - max_fee and total_amount <= balance-min_fee and not send_all: send_all = True
            
        #If we are indeed trying to send all the funds, then we choose all the utxos
        if send_all: coins = {"utxos":all_utxos,"fee":min_fee,"change":False}
        #If not, then we have to choose in an efficient manner.
        else: coins = coin_selector(all_utxos, total_amount, len(to_address_amount_list)) 
        
        return coins
        
        
    def get_balance(self):
        coins = self.get_utxos()
        print(coins)
        balance = 0
        if len(coins)>0:
            for coin in coins:
                print(coin)
                "coin will be an array with data [ tx_id, out_index, amount ]"
                balance += coin[2]
        return balance

    def update_balance(self):
        self.start_conn()
        addresses = self.db.get_all_addresses(self.get_xtended_key())
        
        if self.testnet: coin_symbol = "btc-testnet"
        else: coin_symbol = "btc"
            
        for address in addresses:
            "address will be a touple with data (address,)"
            print(f"consulting blockchain for address {address}")
            addr_info = get_address_details(address[0], coin_symbol = coin_symbol, unspent_only=True)
            print(f"res for {address}:\n{addr_info}")
            
            if addr_info["unconfirmed_n_tx"] > 0:
                print("got unconfirmed transactions.")
                for utxo in addr_info["unconfirmed_txrefs"]:
                    if not self.db.exist_utxo( utxo["tx_hash"], utxo["tx_output_n"], 0):
                        print("new unconfirmed UTXO")
                        self.db.new_utxo(utxo["address"],utxo["value"],utxo["tx_hash"],utxo["tx_output_n"],confirmed = 0)
            
            if addr_info["n_tx"] - addr_info["unconfirmed_n_tx"] > 0 :
                print("got transactions.")
                for utxo in addr_info["txrefs"]:
                    if not self.db.exist_utxo( utxo["tx_hash"], utxo["tx_output_n"], 1):
                        print("new confirmed UTXO")
                        self.db.new_utxo(addr_info["address"],utxo["value"],utxo["tx_hash"],utxo["tx_output_n"],confirmed = 1)
                        
        self.close_conn()
        
        return 
    
    #@classmethod
    #def create_multisig_account(m,public_key_list,account,addr_type="p2sh", testnet = False, segwit=True):
    #    n = len(public_key_list)
    #    return MultiSigTransaction(m, n, int.from_bytes(account.private_key,"big"), public_key_list, addr_type, testnet, segwit)

    #@classmethod
    def send(self, to_address_amount_list, segwit=True,send_all=False,min_fee_per_byte=70):
        """
        to_address can be a single address or a list.
        amount can be an integer or a list of integers.
        If they are lists, they must be ordered in the same way. address 1 will e sent amount 1, 
        adrress 2 will be sent amount2.. adress n will be sent amount n.
        """
        print(f"From wallet.send(): {to_address_amount_list}")
        coins = self.get_coins(to_address_amount_list, send_all=send_all,
                                         segwit=segwit,min_fee_per_byte=min_fee_per_byte)
        print(f"coins from coin-selector: {coins}")
        
        
        if coins["change"]: change_account = self.get_a_change_address()
        else: change_account = None
          
        tx = Transaction.create_from_master( coins,to_address_amount_list, self,change_account,
                           fee=coins["fee"], segwit=segwit)
        
        if self.testnet: symbol = "btc-testnet"
        else: symbol= "btc"
        
        env = Sqlite3Environment()
        BLOCKCYPHER_API_KEY = env.get_key("BLOCKCYPHER_API_KEY")[0][0]
        env.close_database()
        push = pushtx(tx_hex= tx.transaction.serialize().hex(), coin_symbol=symbol,api_key=BLOCKCYPHER_API_KEY)
        tx_id = tx.transaction.id()
        print(f"TRANSACTION ID: {tx_id}")
        
        #saving in db
        
        self.start_conn()
        self.db.new_tx(tx_id, [ (x[0],x[1]) for x in coins['utxos']] ,
                       [str(x).split(":")+[i] for i,x in enumerate(tx.transaction.tx_outs)]
                      )
        self.close_conn()
        
        #start new thread to check if the transaction goes through in the blockchain or not.
        #Maybe move this to the front end class to pop a warning when it doesn't go through
        mythread = threading.Thread(target=self.confirm_tx_sent,args=(tx_id,))
        mythread.start()
        
        return tx,push
        