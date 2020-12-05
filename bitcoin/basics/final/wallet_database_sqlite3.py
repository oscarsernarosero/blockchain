import sqlite3
from sqlite3 import Error
import time
import ast

class Sqlite3Wallet:
    
    def __init__(self):
        self.conn = self.create_connection(r"database/wallet_db.db")
        print("connection with database made.")
        
    def create_connection(self,db_file):
        """ create a database self.connection to a SQLite database """
        conn = None
        try:
            conn = sqlite3.connect(db_file)
            return conn

        except Error as e:
            print(e)

    def close_database(self):
        if self.conn:
            self.conn.close()
        
    def execute_w_res(self, query):
        try:
            c = self.conn.cursor()
            result = c.execute(query)
            return result.fetchall()
        except Error as e:
            print(e)
            return None
        
    def execute(self, query):
        try:
            c = self.conn.cursor()
            c.execute(query)
            self.conn.commit()
            return True
        except Error as e:
            print(e)
            return None
        
    def create_wallet_table(self):
        query1 =  f"CREATE TABLE IF NOT EXISTS Wallets ( xprv text NOT NULL PRIMARY KEY,\n "
        query2 = f"name text, words text NOT NULL, passphrase text, child INT) WITHOUT ROWID;"
        query = query1+query2
        #print(query)
        return self.execute(query)
    
    def create_SHDSafeWallet_table(self):
        """
        name is the primary key
        """
        query1 = "CREATE TABLE IF NOT EXISTS SHDSafeWallet (name text NOT NULL PRIMARY KEY,\n "
        query2 = " public_key_list text NOT NULL, m INT NOT NULL, n INT NOT NULL, privkey text, xpriv text, \n "
        query3 = " xpub text NOT NULL, addr_type text NOT NULL, testnet INT NOT NULL, segwit INT NOT NULL,\n "
        query4 = " parent_name text, safe_index INT, level1pubkeys text\n) WITHOUT ROWID;"
        query = query1+query2+query3+query4
        #print(query)
        return self.execute(query)
    
    def create_HDMWallet_table(self):
        """
        name is the primary key
        """
        query1 = "CREATE TABLE IF NOT EXISTS HDMWallet (name text NOT NULL PRIMARY KEY,\n "
        query2 = " master_pubkey_list text NOT NULL, m INT NOT NULL, n INT NOT NULL, xpriv text NOT NULL, \n "
        query3 = " addr_type text NOT NULL, testnet INT NOT NULL, segwit INT NOT NULL,\n "
        query4 = " parent_name text, safe_index INT\n) WITHOUT ROWID;"
        query = query1+query2+query3+query4
        #print(query)
        return self.execute(query)

    def create_CorporateAccount_table(self):
        """
        name is the primary key
        """
        query = "CREATE TABLE IF NOT EXISTS CorporateAccount ( acc_index INT NOT NULL, account_name text NOT NULL, \n\
        wallet_name text NOT NULL,\nPRIMARY KEY (acc_index, wallet_name) ) WITHOUT ROWID;"
        
        print(query)
        return self.execute(query)

    
    def create_address_table(self):
        query1 =f"CREATE TABLE IF NOT EXISTS Addresses ( address text NOT NULL PRIMARY KEY,\nacc_index INT NOT NULL,"
        query2 = "\npath text NOT NULL,\nchange_addr INT NOT NULL,\ncreated INT NOT NULL,\nwallet text NOT NULL,\n"
        query3 = "type INT NOT NULL,\nsafe_index INT,\nFOREIGN KEY (wallet) \nREFERENCES Wallets(xprv) ) WITHOUT ROWID ;"
        query = query1 + query2 + query3
        #print(query)
        return self.execute(query)

    def create_utxo_table(self):
        query1 =f"CREATE TABLE IF NOT EXISTS Utxos ( address text NOT NULL,\namount INT NOT NULL,\ntx_id text NOT NULL,"
        query2 = "\nout_index INT NOT NULL,\ncreated INT NOT NULL,\nspent INT NOT NULL,\nconfirmed INT NOT NULL, "
        query3 = "\nPRIMARY KEY (tx_id, out_index)\nFOREIGN KEY (address)\nREFERENCES Addresses(address) );"
        query = query1 + query2 + query3
        #print(query)
        return self.execute(query)

    def create_transaction_table(self):
        query1 =f"CREATE TABLE IF NOT EXISTS Transactions ( tx_id text NOT NULL PRIMARY KEY,\nlock_time INT,\nversion INT,\n"
        query2 = "\nn_confirmations INT NOT NULL,\ncreated INT NOT NULL)  WITHOUT ROWID ;"
        query = query1 + query2
        #print(query)
        return self.execute( query)
    
    def create_partial_transaction_table(self):
        query =f"CREATE TABLE IF NOT EXISTS PartialTransactions ( tx_id text NOT NULL PRIMARY KEY, lock_time INT, version \
        INT,\nn_confirmations INT NOT NULL, created INT NOT NULL, cosigners_reply text NOT NULL, tx_hex text NOT NULL) \
        \nWITHOUT ROWID;"
        return self.execute(query)

    def create_tx_in_table(self):
        query1 =f"CREATE TABLE IF NOT EXISTS Tx_Ins ( tx_id text NOT NULL, out_index INT NOT NULL,\nspent_by text NOT NULL,\n"
        query2 = "PRIMARY KEY (tx_id,out_index,spent_by)\n "
        query3 = "FOREIGN KEY (tx_id,out_index)\nREFERENCES Utxo(tx_id,out_index) \n "
        query4 = "FOREIGN KEY (spent_by)\nREFERENCES Transactions(tx_id) )  WITHOUT ROWID ;"
        query = query1 + query2 + query3 + query4
        #print(query)
        return self.execute(query)
    
    def create_partial_tx_in_table(self):
        query = f"CREATE TABLE IF NOT EXISTS Partial_Tx_Ins ( tx_id text NOT NULL, out_index INT NOT NULL,\
        \nspent_by text NOT NULL,\nPRIMARY KEY (tx_id,out_index,spent_by)\nFOREIGN KEY (tx_id,out_index)\nREFERENCES \
        Utxo(tx_id,out_index) \nFOREIGN KEY (spent_by)\nREFERENCES PartialTransactions(tx_id) ) WITHOUT ROWID ;"
        return self.execute(query)

    def create_tx_out_table(self):
        query1 = "CREATE TABLE IF NOT EXISTS Tx_Outs ( out_index INT NOT NULL,\n amount INT NOT NULL,\ncreated_by text NOT NULL,\n"
        query2 = "script_pubkey text NOT NULL, \n PRIMARY KEY (created_by, out_index)\n"
        query3 = "FOREIGN KEY (created_by)\nREFERENCES Transactions(tx_id) )  WITHOUT ROWID ;"
        query = query1 + query2 + query3
        #print(query)
        return self.execute(query)
    
    def create_partial_tx_out_table(self):
        query = "CREATE TABLE IF NOT EXISTS Partial_Tx_Outs ( out_index INT NOT NULL,\n amount INT NOT NULL,\n\
                created_by text NOT NULL,\nscript_pubkey text NOT NULL, \n PRIMARY KEY (created_by, out_index)\n\
                FOREIGN KEY (created_by)\nREFERENCES PartialTransactions(tx_id) )  WITHOUT ROWID ;"
        return self.execute(query)
    
    def create_contact_table(self):
        query1 = "CREATE TABLE IF NOT EXISTS Contacts ( first_name text NOT NULL, last_name text NOT NULL,\n "
        query2 = "position text NOT NULL, xpub text NOT NULL PRIMARY KEY, phone text, safe_pubkey text) "
        query3 = " WITHOUT ROWID;"
        query = query1+query2+query3
        #print(query)
        return self.execute(query)

    def create_tables(self):
        self.create_wallet_table()
        self.create_address_table()
        self.create_utxo_table()
        self.create_transaction_table()
        self.create_tx_in_table()
        self.create_tx_out_table()
        self.create_contact_table()
        return True

    def new_wallet(self, xprv, words, name = None, child = 0 ):
        """
        Creates a new wallet in the database.
        self.conn: self.conn: internal database driver transaction.
        xprv: String; extended private key of the wallet.
        words: String; The mnemonic phrase of the wallet.
        name: String Optional. This is an alias for the wallet if user prefers it.
        """
        query1 = "INSERT INTO Wallets (xprv, words, name, child)\n "
        query2 = f"VALUES('{xprv}', {words}, '{name}', {child}) ;"
        query = query1+query2
        #print(query)
        return self.execute(query)
    
    def new_SHDSafeWallet(self,name,public_key_list,m,n,privkey,xpriv,xpub,addr_type,testnet,segwit,parent_name,safe_index,level1):
        """
        Creates a new SHD multi signature Wallet in the database.
        to do...
        """
        query1 = "INSERT OR IGNORE INTO SHDSafeWallet \
        (name,public_key_list,m,n,privkey,xpriv,xpub,addr_type,testnet,segwit,parent_name "
        query2 = f',safe_index, level1pubkeys) \nVALUES("{name}","{public_key_list}",{m},{n},"{privkey}","{xpriv}","{xpub}",'
        query3 = f"'{addr_type}',{testnet},{segwit},'{parent_name}',{safe_index}, '{level1}' ) ;"
        query = query1 + query2 + query3
        print(query)
        return self.execute(query)
    
    def new_HDMWallet(self,name,master_pubkey_list,m,n,xpriv,addr_type,testnet,segwit,parent_name,safe_index):
        """
        Creates a new fully HD multi signature Wallet in the database.
        to do...
        """
        query1 = "INSERT OR IGNORE INTO HDMWallet (name,master_pubkey_list,m,n,xpriv,addr_type,testnet,segwit,parent_name "
        query2 = f',safe_index) \nVALUES("{name}","{master_pubkey_list}",{m},{n},"{xpriv}","{addr_type}",'
        query3 = f"{testnet},{segwit},'{parent_name}',{safe_index}) ;"
        query = query1 + query2 + query3
        print(query)
        return self.execute(query)

    def new_address(self, address, path, acc_index, change_addr, _type, wallet, safe_index = 0):
        """
        Creates a new address in the database.
        self.conn: internal database driver transaction.
        address: String; the address to create.
        path: String; the path in wich the address is created until the account level. i.e. "m/44'/0'/0'/"
        as a standard, it must start with m and end with /
        acc_index: int; account index. This would be the last part of the path.
        change_addr: int, 0=False, 1=True; if the address is a "change adrress" then 1 (True). Otherwise 0 (False).
        _type: INTEGER; the codes are: P2PKH = 2, P2SH = 3, P2WPKH = 4, P2WSH = 5, P2SH_P2WPKH = 6, P2SH_P2WSH = 7
        wallet: String; the xtended private key of the wallet
        """
        created = int(time.time())
        query1 = "INSERT OR IGNORE INTO Addresses (address, path, acc_index, change_addr, created, type, wallet, safe_index)\n "
        query2 = f'VALUES("{address}", "{path}", {acc_index}, {change_addr}, {created}, {_type}, "{wallet}", {safe_index}) ;'
        query = query1+query2
        print(query)
        return self.execute(query)

    def new_utxo(self, address, amount, tx_id, out_index, spent=0, confirmed=0):
        """
        Creates new utxo in the database.
        self.conn: internal database driver transaction.
        address: the base58 representation of the address that holds the utxo.
        tx_id: String, the tx id or hash of the transaction the generated the utxo.
        out_index: Int, the index of the output in the transaction that generated the utxo.
        amount: Int, the amount of SATOSHIS that the utxo holds.
        spent: Int, 0=False, 1=True; if the utxo has been spent by a transaction then 1 (True).
        confirmed: Int, 0=False, 1=True; if the transaction has less than 6 confirmations then 0 (False).
        """
        created = int(time.time())
        query1 = "INSERT INTO Utxos (address, amount, tx_id, out_index, created, spent, confirmed)\n "
        query2 = f"VALUES('{address}', {amount}, '{tx_id}', {out_index}, {created}, {spent}, {confirmed});"
        query = query1+query2
        #print(query)
        return self.execute(query)

    def new_tx(self, tx_id, tx_ins, tx_outs, n_confirmations = 0, lock_time=0, version=1 ):
        """
        tx_id: String. transaction id.
        tx_ins: List of touples: [ (prev_tx_id, index), ... ]
        tx_outs: List of touples: [ (amount, script_pubkey), ... ]
        n_confirmations: int; number of confirmations in the blockchain.
        lock_time: Int: transaction locktime.
        version: Int: version.
        """
        created = int(time.time())
        query1 = "INSERT INTO Transactions ( tx_id, created, n_confirmations, lock_time, version)\n "
        query2 = f"VALUES('{tx_id}', {created}, {n_confirmations}, {lock_time}, {version});"
        query = query1+query2
        self.execute(query)

        for tx_in in tx_ins:
            query3 = "INSERT INTO Tx_Ins ( tx_id, out_index, spent_by)\n "
            query4 = f"VALUES( '{tx_in[0]}', {tx_in[1]}, '{tx_id}');"
            query = query3+query4
            self.execute(query)
            #CHANGE THIS LATER FOR A CONFIRMATION IN THE BLOCKCHAIN UTXO
            query = f"UPDATE Utxos SET spent = 1 WHERE tx_id = '{tx_in[0]}' AND out_index = {tx_in[1]}"
            self.execute(query)

        for tx_out in tx_outs:
            query5 = "INSERT INTO Tx_Outs ( amount, script_pubkey, out_index, created_by)\n "
            query6 = f"VALUES( {tx_out[0]}, '{tx_out[1]}',{tx_out[2]}, '{tx_id}');"
            query = query5+query6
            self.execute(query)
            
        return True
    
    
    def new_partial_tx(self, tx_id, tx_ins, tx_outs, consigners_reply, tx_hex, n_confirmations = 0, lock_time=0, version=1 ):
        """
        tx_id: String. transaction id.
        tx_ins: List of touples: [ (prev_tx_id, index), ... ]
        tx_outs: List of touples: [ (amount, script_pubkey), ... ]
        consigners_reply: Dictionary. A dictionary with the reply from the cosigners with the structure:  
        {"<cosigner1_pubkey>":reply(Boolean/None), {"<cosigner2_pubkey>":reply(Boolean/None), ... }
        This dict will be parsed to text for storing convinience. To convert back to dict: import ast, and \
        use: consigners_reply_dict = ast.literal_eval(consigners_reply_string) 
        tx_hex: str. The hexadecimal representation of the transaction.
        n_confirmations: int; number of confirmations in the blockchain.
        lock_time: Int: transaction locktime.
        version: Int: version.
        """
        created = int(time.time())
        query1 = "INSERT INTO PartialTransactions (tx_id,created,n_confirmations,lock_time,version,cosigners_reply,tx_hex)\n "
        query2 = f'VALUES("{tx_id}",{created},{n_confirmations},{lock_time},{version},"{consigners_reply}","{tx_hex}");'
        query = query1+query2
        print(query)
        self.execute(query)

        for tx_in in tx_ins:
            query3 = "INSERT INTO Partial_Tx_Ins ( tx_id, out_index, spent_by)\n "
            query4 = f"VALUES( '{tx_in[0]}', {tx_in[1]}, '{tx_id}');"
            query = query3+query4
            self.execute(query)
            print(query)
            #CHANGE THIS LATER FOR A CONFIRMATION IN THE BLOCKCHAIN UTXO
            query = f"UPDATE Utxos SET spent = 1 WHERE tx_id = '{tx_in[0]}' AND out_index = {tx_in[1]}"
            print(query)
            self.execute(query)

        for tx_out in tx_outs:
            query5 = "INSERT INTO Partial_Tx_Outs ( amount, script_pubkey, out_index, created_by)\n "
            query6 = f"VALUES( {tx_out[0]}, '{tx_out[1]}',{tx_out[2]}, '{tx_id}');"
            query = query5+query6
            print(query)
            self.execute(query)
            
        return True
    
    def get_tx_ins(self, tx_id):
        #First, let's get all the tx_ins
        query = f"SELECT tx_id,out_index FROM Tx_Ins\nWHERE spent_by ='{tx_id}' ;"
        tx_ins = self.execute_w_res(query)
        print(f"tx_ins: {tx_ins}")
        return tx_ins
        
    def set_utxos_spendable(self, tx_ins):
        """
        tx_ins: List of tuples: [(prev_tx1,index1),(prev_tx2,index2)...]
        """
        for tx_in in tx_ins:
            query1 = f"UPDATE Utxos SET spent = 0  WHERE tx_id ="
            query2 = f" '{tx_in[0]}' AND out_index = '{tx_in[1]}' "
            query = query1 + query2
            self.execute(query)
        return True
    
    def check_utxos_are_spendable(self,utxos):
        """
        Checks that all the utxos are still spendable in the database. That is 'spent' = 0.
        It will return True if all of the utxos are spendable, or False if at least one of\
         them is not. It would also print in the terminal which ones are not spendable.
        utxos: List of tuples: [(prev_tx1,index1),(prev_tx2,index2)...]
        """
        all_spendable = True
        for utxo in utxos:
            query = f"SELECT spent FROM Utxos WHERE tx_id = '{utxo[0]}' AND out_index = '{utxo[1]}' "
            res = self.execute_w_res(query)
            try:
                all_spendable = all_spendable and not bool(res[0][0])
                if res[0][0] != 0: print(f"utxo {utxo} is NOT spendable.")
            except:
                print("No such utxo")
        return all_spendable
              
    def recover_utxo(self, tx_id):
        #Set the utxos consumed by the transaction to NOT spent (spent=0)
        tx_ins = self.get_tx_ins(tx_id)
        #Now let's set the Utxo to NOT spent.
        self.set_utxos_spendable(tx_ins)
        #Check Utxos
        job_done = self.check_utxos_are_spendable(tx_ins)
        return job_done
    
    def delete_tx(self, tx_id):
        """
        If for any reason a transaction didn't go through in the blockchain, this method
        will delete the transaction from the database as well as its inputs and outputs.
        tx_id: String. transaction id.
        """
        #Set the utxos consumed by the transaction to NOT spent (spent=0)
        #First, let's get all the tx_ins
        try: self.recover_utxo(tx_id)
        except: print("following with the deleting process. Please fix manually the recovering of the utxos.")
            
        #delete the inputs
        query1 = f"DELETE FROM Tx_Ins\n"
        query2 = f"WHERE spent_by ='{tx_id}' ;"
        query = query1+query2
        self.execute(query)
        
        #delete the outputs
        query1 = f"DELETE FROM Tx_Outs\n"
        query2 = f"WHERE created_by ='{tx_id}' ;"
        query = query1+query2
        self.execute(query)
        
        #delete the transaction
        query1 = f"DELETE FROM Transactions\n"
        query2 = f"WHERE tx_id ='{tx_id}' ;"
        query = query1+query2
        self.execute(query)
        
        return True
    
    def delete_partial_tx(self, tx_id):
        """
        This is an internal-use method only. To delete a partial transaction, see delete_failed_partial_tx.
        If for any reason a multi-signature transaction didn't go through in the blockchain, this method
        will delete the transaction from the partial-transaction database as well as its inputs and outputs.
        tx_id: String. transaction id.
        """
        #delete the inputs
        query1 = f"DELETE FROM Partial_Tx_Ins\n"
        query2 = f"WHERE spent_by ='{tx_id}' ;"
        query = query1+query2
        self.execute(query)
        
        #delete the outputs
        query1 = f"DELETE FROM Partial_Tx_Outs\n"
        query2 = f"WHERE created_by ='{tx_id}' ;"
        query = query1+query2
        self.execute(query)
        
        #delete the transaction
        query1 = f"DELETE FROM PartialTransactions\n"
        query2 = f"WHERE tx_id ='{tx_id}' ;"
        query = query1+query2
        self.execute(query)
        
        return True
    
    def delete_failed_partial_tx(self, tx_id):
        #Check if the failed partial tx is actually a failed tx or just a successfull transaction that
        #didn't get properly erased from the partial-tx database:
        query = f"SELECT created FROM Transactions WHERE tx_id = {tx_id}"
        res = self.execute_w_res(query)
        if len(res) == 0:
            #Set the utxos consumed by the transaction to NOT spent (spent=0)
            try: self.recover_utxo(tx_id)
            except: print("following with the deleting process. Please fix manually the recovering of the utxos.")

        return self.delete_partial_tx(tx_id)
        
    def clean_expire_partial_tx(self):
        """
        This method cleans automatically the partial-transaction database from already expired partial-txs.
        """
        query = f"SELECT tx_id, created FROM PartialTransactions"
        all_partial_txs = self.execute_w_res(query)
        print(f"all_partial_txs: {all_partial_txs}")
        
        if len(all_partial_txs) > 0:
            for partial_tx in all_partial_txs:
                if partial_tx[1] > 60*60*24: 
                    print(f"deleting expired partial tx {partial_tx[0]} from database")
                    self.delete_failed_partial_tx(partial_tx[0])
        else: print("No expired partial txs")  
            
        return    
    
    def new_broadcasted_partial_tx(self, tx_id):
        """
        DEPRECATED!
        This method will delete the multi-signature transaction from the partial-tx database, and write it \
        into the actual transaction database. This will not modify the status of the UTXOs spent \
        in the partial tx since it was successfully broadcasted.
        tx_id: String. transaction id.
        """
        #get the inputs
        query1 = f"SELECT * FROM Partial_Tx_Ins\n"
        query2 = f"WHERE spent_by ='{tx_id}' ;"
        query = query1+query2
        raw_tx_ins = self.execute_w_res(query)
        print(raw_tx_ins)
        print(raw_tx_ins)
        tx_ins = [(x[0],x[1]) for x in raw_tx_ins]
        print(tx_ins)
        
        #get the outputs
        query1 = f"SELECT * FROM Partial_Tx_Outs\n"
        query2 = f"WHERE created_by ='{tx_id}' ;"
        query = query1+query2
        raw_tx_outs = self.execute_w_res(query)
        tx_outs = [(x[1],x[3]) for x in raw_tx_outs]
        
        #get the transaction
        query1 = f"SELECT * FROM PartialTransactions\n"
        query2 = f"WHERE tx_id ='{tx_id}' ;"
        query = query1+query2
        tx = self.execute_w_res(query)
        
        #self.new_tx(self, tx_id, tx_ins, tx_outs, n_confirmations = 0, lock_time= tx[0][1], version=tx[0][2] )
        
        return self.delete_partial_tx(tx_id)
        

    def update_cosigners_reply(self, tx_id, pubkey, reply,m,n):
        """
        updates the cosigners_reply dictionary with the reply of the participant.
        tx_id: string. The tx id to update.
        pubkey: the public key of the participant. Must be in the public_key_list or be the master_pubkey.
        reply: Boolean. The reply will be True if the participant agreed to sign the tx, or False if \
        the participant oppossed the transaction.
        """
        if not isinstance(reply,bool): raise Exception(f"reply must be of type bool, not {type(reply)}")
            
        #get the transaction
        query1 = f"SELECT * FROM PartialTransactions\n"
        query2 = f"WHERE tx_id ='{tx_id}' ;"
        query = query1+query2
        tx = self.execute_w_res(query)
        
        print(f"from database: tx: {tx}")
        consigners_reply = ast.literal_eval(tx[0][5])#original was tx[3]
        consigners_reply[f"{pubkey}"] = reply
        print(f"consigners_reply updated: {consigners_reply}")
        #Let's make sure that the tx still has room to be approved. If not, we'll delete the transaction.
        declined = False
        declines = 0
        for cosigner in consigners_reply:
            reply = consigners_reply[cosigner]
            if not reply and isinstance(reply,bool):
                declines+=1
                if declines > n - m:
                    declined =  True
                    print("Transaction has been rejected by cosigners")
                    return self.delete_failed_partial_tx(tx_id)
            
        #if it hasn't been declined, then we proceed to update the reply in the database
        query = f"UPDATE PartialTransactions \nSET consigners_reply = '{str(consigners_reply)}' WHERE tx_id = '{tx_id}'"
        print(f"query from update_cosigners_reply\n{query}")
        return self.execute(query)
    
    def update_partial_tx(self, tx_id, new_tx_hex):
        """
        Updates the version of the hexadecimal representation of the transaction stored in the database.
        tx_id: string. The tx id to update.
        new_tx_hex: str. the new hexadecimal of the transaction.
        """
        
        query = f"UPDATE PartialTransactions \nSET tx_hex = '{new_tx_hex}' WHERE tx_id = '{tx_id}'"
        return self.execute(query)
        
    def update_confirmations(self, tx_id, n_confirmations):
        """
        Updates the number of confirmations for a transaction to later confirm the transaction was broadcasted.
        self.conn: internal database driver transaction.
        tx_id: String, the id or hash of the transaction being broadcasted.
        n_confirmations: Int, the number of confirmations.
        """
        query = f"UPDATE Transactions \nSET n_confirmations = {n_confirmations} WHERE tx_id = '{tx_id}'"
        return self.execute(query)

    def spend_utxo(self, tx_id, out_index):
        query = f"UPDATE Utxos \nSET spent = 1 \nWHERE tx_id = '{tx_id}' AND out_index = {out_index} "
        return self.execute(query)

    def spend_utxo(self, tx_id, out_index):
        """
        Updates the state of an exisiting utxo to "spent=True" once the transaction was broadcasted successfully and confirmed.
        self.conn: internal database driver transaction.
        tx_id: String, the id or hash of the transaction that created the utxo (previous transaction).
        out_index: index of the utxo in the previous transaction.
        """
        query = f"UPDATE Utxos \nSET spent = 1 \nWHERE tx_id = '{tx_id}' AND out_index = {out_index} "
        return self.execute(query)

    def clean_addresses(self):
        """
        Not necessary in this implementation.
        """
        pass

    def look_for_coins(self, wallet):
        """
        Searches the database for utxos that haven't been spent for the specific wallet.
        self.conn: internal database driver transaction.
        wallet: String, The wallet extended private key.
        Returns: List of touples [(tx_id, out_index, amount)]
        """
        query1 = f"SELECT Utxos.tx_id, Utxos.out_index, Utxos.amount, Addresses.path, Addresses.acc_index, Addresses.address,\n "
        query2 = f"Addresses.type \nFROM Utxos INNER JOIN Addresses \nON Utxos.address = Addresses.address\n"
        query3 = f"WHERE Utxos.spent = 0 AND Addresses.wallet = '{wallet}';"
        query = query1 + query2 + query3
        #print(query)
        return self.execute_w_res(query)
    
    def get_utxo_info(self, tx_id, out_index):
        """
        Searches the database for a specific utxo and retreives its info.
        self.conn: internal database driver transaction.
        wallet: String, The wallet extended private key.
        tx_id: transaction id of the utxo.
        out_index: index of the output.
        Returns: List of touples [(tx_id, out_index, amount)]
        """
        query1 = f"SELECT Utxos.tx_id, Utxos.out_index, Utxos.amount, Addresses.path, Addresses.acc_index, Addresses.address,\n "
        query2 = f"Addresses.type \nFROM Utxos INNER JOIN Addresses \nON Utxos.address = Addresses.address\n"
        query3 = f"WHERE Utxos.tx_id = '{tx_id}' AND Utxos.out_index = {out_index};"
        query = query1 + query2 + query3
        print(query)
        return self.execute_w_res(query)

    def get_unused_addresses(self,wallet, days_range=None, max_days=None):
        """
        Searches the database for addresses that haven't been used in the specific wallet.
        Returns a list of touples: (address, change_addr, path, acc_index).
        tx: internal database driver transaction.
        xprv: String, The wallet extended private key.
        max_days: how far away should the app look for the unused address in the pass. The limit is 30 since the app deletes 
        unused addresses after a month of creation.
        days_range: number of days for the range in which to look for the address. The range will start
        in day_range days before the max_days day (starting_day = (max_days - days_range)).

        days_range and max_days should be either both specified or neither specified. If they are not, both values will be
        automatically set to 30 making the search to happen from now to the last 30 days. If only one of them is specified, 
        the function will throw an exception.
        """
        if days_range is None and max_days is None:
            query1 = f"SELECT address, change_addr, path, acc_index  \nFROM Addresses WHERE\nNOT EXISTS(\nSELECT 1 \n FROM Utxos"
            query2 = f"\nWHERE Utxos.address = Addresses.address) \nAND\n Addresses.wallet = '{wallet}';"
            query = query1 + query2
            #print(query)
            return self.execute_w_res(query)

        elif (days_range is None or max_days is None) and (days_range != max_days):
            raise Exception("Arguments days_range and max_days must be either both specified or neither one specified.")

        else:
            SEC_PER_DAY = 86400
            finish_day = max_days * SEC_PER_DAY
            start_day = finish_day - days_range * SEC_PER_DAY
            now = int(time.time())
            query1 = f"SELECT address \nFROM Addresses WHERE\nNOT EXISTS(\nSELECT 1 \n FROM Utxos"
            query2 = f"\nWHERE Utxos.address = Addresses.address) \nAND\n Addresses.wallet = '{wallet}'"
            query3 = f"\nAND\n ({now} - Addresses.created) > {start_day} AND ({now} - Addresses.created) < {finish_day} ;"
            query = query1 + query2 + query3
            #print(query)
            return self.execute_w_res(query)

    #CHECK IF THIS IS NECESSARY. IF NOT JUST DELETE THIS METHOD
    def get_unused_safe_addresses(self, name):
        query1 = f"SELECT address, change_addr, path, acc_index  \nFROM Addresses WHERE\nNOT EXISTS(\nSELECT 1 \n FROM Utxos"
        query2 = f"\nWHERE Utxos.address = Addresses.address) \nAND\n Addresses.wallet = '{name}';"
        query = query1 + query2
        print(query)
        return self.execute_w_res(query)

    
    def get_day_deposit_addresses(self, name):
        query = f"SELECT address FROM Addresses \nWHERE wallet = '{name}' AND change_addr = 0 AND acc_index = 0"
        print(query)
        return self.execute_w_res(query)
    
    def get_all_addresses(self,wallet):
        """
        Returns all the addresses in the database for the specific wallet.
        self.conn: internal database driver transaction.
        wallet: String, The wallet extended private key.
        """
        query = f"SELECT address \nFROM Addresses WHERE wallet = '{wallet}'; "
        return self.execute_w_res(query)

    def exist_utxo(self, tx_id, out_index, confirmed):
        """
        Returns True if the utxo already exists in the database. False if it doesn't. It also updates
        the "confirmed" property of the utxo if necessary.
        tx: internal database driver transaction.
        tx_id: String, the tx id or hash of the transaction the generated the utxo.
        out_index: Int, the index of the output in the transaction that generated the utxo.
        confirmed: Int/Boolean 0=False, 1=True; the current state of confirmation of the transaction in the actual blockchain.
        """
        query = f"SELECT * FROM Utxos WHERE  tx_id = '{tx_id}' AND out_index = {out_index}"
        print(query)
        result = self.execute_w_res(query)
        print(f"result of looking_for coins: {result}")
        if len(result)>0:
            if result[0][6] != confirmed:
                query = f"UPDATE Utxos \nSET confirmed = {confirmed} WHERE tx_id = '{tx_id}' AND out_index = {out_index} "
                print(f"changed confirmations on utxo {tx_id}:{out_index}")
                result = self.execute_w_res(query)

            return True
        else: return False

    def does_table_exist(self, table):
        query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';"
        return self.execute_w_res(query)
    
    def get_words_from_wallet(self, name):
        """
        Returns the Mnemonic phrase of the wallet.
        name: the name of the wallet provided.
        """
        query = f"SELECT words FROM Wallets WHERE name='{name}';"
        #print(query)
        return self.execute_w_res(query)
    
    def get_all_wallets(self):
        query = f"SELECT * FROM Wallets;"
        return self.execute_w_res(query)
    
    def get_all_store_wallets(self):
        query = f"SELECT * FROM SHDSafeWallet;"
        return self.execute_w_res(query)
    
    def get_daily_safe_wallets(self,parent_wallet):
        query = f"SELECT * FROM SHDSafeWallet WHERE parent_name = '{parent_wallet}' and safe_index > 201001;"
        return self.execute_w_res(query)
    
    def get_weekly_safe_wallets(self,parent_wallet):
        query = f"SELECT * FROM SHDSafeWallet WHERE parent_name = '{parent_wallet}' and safe_index < 9999;"
        return self.execute_w_res(query)
    
    def get_all_m_s_corporate_wallets(self):
        query = f"SELECT * FROM HDMWallet;"
        return self.execute_w_res(query)
    
    def get_year_wallets(self,parent_wallet):
        query = f"SELECT * FROM HDMWallet WHERE parent_name = '{parent_wallet}' and safe_index >= 2019;"
        return self.execute_w_res(query)
    
    def recover_SHDSafeWallet(self,name):
        query = f"SELECT * FROM SHDSafeWallet WHERE name='{name}'"
        return self.execute_w_res(query)
    
    def recover_HDMWallet(self,name):
        query = f"SELECT * FROM HDMWallet WHERE name='{name}'"
        return self.execute_w_res(query)
    
    def get_child_corporate_wallets(self,parent_name):
        query = f"SELECT * FROM HDMWallet WHERE parent_name='{parent_name}'"
        return self.execute_w_res(query)
    
    
    def get_partial_tx_hex(self, tx_id):
        query = f"SELECT tx_hex FROM PartialTransactions WHERE tx_id='{tx_id}'"
        return self.execute_w_res(query)
        
    def get_partial_tx_ins(self, tx_id):
        query = f"SELECT * FROM Partial_Tx_Ins WHERE spent_by ='{tx_id}'"
        return self.execute_w_res(query)
    
    def get_max_index(self, account, wallet):
        """
        Returns an INTEGER representing the highest index of the address in 
        the specified account belonging to the specified wallet. If there is
        NO addresses under specified account, it will return None.
        account: String (Path); i.e: m/44H/0H/
        wallet: String; extended private key.
        """
        query = f"SELECT MAX(acc_index) FROM Addresses WHERE wallet='{wallet}' AND path='{account}';"
        return self.execute_w_res(query)[0][0]
    
    def get_max_child_wallet_index(self, name):
        """
        Returns an INTEGER representing the highest index of the child-wallet for \
        the specified HDMWallet. If there is NO addresses under specified account, it \
        will return None.
        name: String; name of the HDMWallet
        """
        query = f"SELECT MAX(safe_index) FROM HDMWallet WHERE parent_name='{name}';"
        return self.execute_w_res(query)[0][0]
    
    def get_max_corporate_account_index(self, name):
        """
        Returns an INTEGER representing the highest index of the child-wallet for \
        the specified HDMWallet. If there is NO addresses under specified account, it \
        will return None.
        name: String; name of the HDMWallet
        """
        query = f"SELECT MAX(acc_index) FROM CorporateAccount WHERE wallet_name='{name}';"
        return self.execute_w_res(query)
    
    def get_all_corporate_accounts(self, name):
        """
        Returns an INTEGER representing the highest index of the child-wallet for \
        the specified HDMWallet. If there is NO addresses under specified account, it \
        will return None.
        name: String; name of the HDMWallet
        """
        query = f"SELECT * FROM CorporateAccount WHERE wallet_name='{name}';"
        return self.execute_w_res(query)
    
    def get_corporate_account_by_name(self, name, wallet_name):
        """
        Returns an INTEGER representing the highest index of the child-wallet for \
        the specified HDMWallet. If there is NO addresses under specified account, it \
        will return None.
        name: String; name of the HDMWallet
        """
        query = f"SELECT * FROM CorporateAccount WHERE wallet_name='{wallet_name}' AND account_name = '{name}';"
        return self.execute_w_res(query)
    
    def new_corportate_account(self, account_name,index,wallet_name):
        """
        account_name: String; name or alias of the account being created
        wallet_name: String; name of the corportate wallet in the HDMWallet database
        index: int. The index of the account being created. Must be greater than 1 since \
        accounts with index 0 and 1 are reserved for depossit and change address generation.
        """
        query = f"INSERT OR IGNORE INTO CorporateAccount (acc_index, account_name, wallet_name) \
        VALUES({index}, '{account_name}', '{wallet_name}');"
        print(query)
        return self.execute(query)
    
    def erase_database(self):
        query = "DROP TABLE Tx_Ins"
        self.execute(query)
        query = "DROP TABLE Tx_Outs"
        self.execute(query)
        query = "DROP TABLE Transactions"
        self.execute(query)
        query = "DROP TABLE Utxos"
        self.execute(query)
        query = "DROP TABLE Addresses"
        self.execute(query)
        query = "DROP TABLE Wallets"
        self.execute(query)
        
        self.create_tables()
        return True
    
    def get_contact(self, xpub):
        query1 = f"SELECT first_name, last_name, phone, position, xpub, safe_pubkey FROM Contacts\n"
        query2 = f"WHERE xpub ='{xpub}' ;"
        query = query1+query2
        print(query)
        return self.execute_w_res(query)
    
    def get_contact_by_name(self, first_name,last_name):
        query1 = f"SELECT first_name, last_name, phone, position, xpub, safe_pubkey FROM Contacts\n"
        query2 = f"WHERE first_name ='{first_name}' AND last_name='{last_name}';"
        query = query1+query2
        print(query)
        return self.execute_w_res(query)
    
    def get_contact_by_store_safe_pubkey(self, store_safe_pubkey):
        query1 = f"SELECT first_name, last_name, phone, position, xpub, safe_pubkey FROM Contacts\n"
        query2 = f"WHERE safe_pubkey ='{store_safe_pubkey}';"
        query = query1+query2
        print(query)
        return self.execute_w_res(query)
        
    def get_all_contacts(self):
        query = f"SELECT first_name, last_name, phone, position, xpub, safe_pubkey FROM Contacts\n"
        #print(query)
        return self.execute_w_res(query)
    
    def new_contact(self, first_name, last_name, phone_number, position, xpub, safe_pubkey):
        query1 = f"INSERT INTO Contacts (first_name, last_name, phone, position, xpub, safe_pubkey)\n"
        query2 = f"VALUES('{first_name}','{last_name}', '{phone_number}', '{position}', '{xpub}', '{safe_pubkey}') ;"
        query = query1+query2
        print(query)
        return self.execute(query)
        
    def update_contact(self,original_xpub, first_name, last_name, phone_number, position, xpub, safe_pubkey):
        query1 = f"UPDATE Contacts SET first_name = '{first_name}', last_name = '{last_name}', "
        query2 = f"phone = '{phone_number}', position = '{position}', xpub = '{xpub}'\n, safe_pubkey = '{safe_pubkey}'"
        query3 = f"WHERE xpub ='{original_xpub}' ;"
        query = query1+query2+query3
        print(query)
        return self.execute(query)
    
    def delete_contact(self, xpub):
        query1 = f"DELETE FROM Contacts\n"
        query2 = f"WHERE xpub ='{xpub}' ;"
        query = query1+query2
        print(query)
        return self.execute(query)
    
    
    
class Sqlite3Environment:
    
    def __init__(self):
        self.conn = self.create_connection(r"database/env.db")
        print("connection with database made.")
        
    def create_connection(self,db_file):
        """ create a database self.connection to a SQLite database """
        conn = None
        try:
            conn = sqlite3.connect(db_file)
            return conn

        except Error as e:
            print(e)

    def close_database(self):
        if self.conn:
            self.conn.close()
        
    def execute_w_res(self, query):
        try:
            c = self.conn.cursor()
            result = c.execute(query)
            return result.fetchall()
        except Error as e:
            print(e)
            return None
        
    def execute(self, query):
        try:
            c = self.conn.cursor()
            c.execute(query)
            self.conn.commit()
            return True
        except Error as e:
            print(e)
            return None
        
    def create_table(self):
        query1 =  f"CREATE TABLE IF NOT EXISTS Keys ( name text NOT NULL PRIMARY KEY,\n "
        query2 = f"key text NOT NULL UNIQUE) WITHOUT ROWID;"
        query = query1+query2
        print(query)
        return self.execute(query)
    
    def new_key(self,name, key):
        query1 = "INSERT INTO Keys (name, key)\n"
        query2 = f"VALUES('{name}', '{key}') ;"
        query = query1+query2
        print(query)
        return self.execute(query)
    
    def update_key(self,name, key):
        query1 = f"UPDATE Keys SET key = '{key}'\n"
        query2 = f"WHERE name ='{name}' ;"
        query = query1+query2
        print(query)
        return self.execute(query)
    
    def delete_key(self,name):
        query1 = f"DELETE FROM Keys\n"
        query2 = f"WHERE name ='{name}' ;"
        query = query1+query2
        print(query)
        return self.execute(query)
    
    def get_key(self, name):
        query1 = f"SELECT key FROM Keys\n"
        query2 = f"WHERE name ='{name}' ;"
        query = query1+query2
        print(query)
        return self.execute_w_res(query)
        
    
        
        