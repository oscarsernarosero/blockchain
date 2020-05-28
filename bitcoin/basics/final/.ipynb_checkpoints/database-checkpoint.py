from neo4j import GraphDatabase

class WalletDB(object):

    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)#REVISE LATER FOR ENCRYPTION!!!

    def close(self):
        self._driver.close()
        
        
    @staticmethod
    def _new_address(tx, address,i,change_addr,wallet_xprv):
        """
        Creates new address in the database.
        tx: internal database driver transaction.
        address: the base58 representation of the address.
        i: Int, the index in the bip32 account.
        change_addr: Boolean, if it is a change adress the True. Otherwise False.
        wallet_xprv: The wallet extended private key the the generated the address.
        """
        if change_addr: addr_type = "change"
        else: addr_type = "recipient"
        result = tx.run("MATCH (w:wallet {xprv:$xprv})"
                        "CREATE a = (:address {address:$address, acc_index:$index, type:$kind, created:timestamp()}) "
                        "<- [:OWNS]-(w)"
                        "RETURN a ", address=address, index = i, kind = addr_type, xprv=wallet_xprv)
        return result.single()
    
    
    @staticmethod
    def _new_utxo(tx, address,tx_id,out_index, amount,confirmed):
        """
        Creates new utxo in the database.
        tx: internal database driver transaction.
        address: the base58 representation of the address that holds the utxo.
        tx_id: String, the tx id or hash of the transaction the generated the utxo.
        out_index: Int, the index of the output in the transaction that generated the utxo.
        amount: Int, the amount of SATOSHIS that the utxo holds.
        confirmed: Boolean, if the transaction has less than 6 confirmations then False.
        """
        local_index = tx.run( "MATCH (u:utxo) RETURN COUNT (u) ").single()[0] 
        result = tx.run("MATCH (n:address {address : $address}) "
                        "CREATE p = (:utxo {address:$address, transaction_id:$tx_id, out_index:$out_index, local_index:$local_index, spent:false, amount:$amount, confirmed:$confirmed})-[:BELONGS]->(n) "
                        "RETURN p ", address=address, tx_id = tx_id, out_index = out_index, 
                        local_index=local_index,amount=amount,confirmed=confirmed)
        return result.single()
    
    
    @staticmethod
    def _new_tx(tx,tx_id,inputs, outputs):
        """
        Creates new transaction in the database.
        tx: internal database driver transaction.
        tx_id: String, the id or hash of the transaction being created.
        inputs: List, the list of inputs of the transaction.
        outputs: List, the list of outputs of the transaction.
        """
        result = tx.run("CREATE (n:TxOut {id:$tx_id, inputs:$inputs , outputs:$outputs, confirmations:0, created:timestamp()}) "
                        "WITH n "
                        "UNWIND n.inputs AS ins "
                        "MATCH coins = (:utxo {local_index:ins}) "
                        "FOREACH ( coin IN nodes(coins) | CREATE (coin)<-[:SPENT]-(n) ) ",
                        tx_id=tx_id, inputs = inputs, outputs = outputs)
        return result.single()
    
    
    @staticmethod
    def _update_confirmations(tx,tx_id,n_confirmations):
        """
        Updates the number of confirmations for a transaction to later confirm the transaction was broadcasted.
        tx: internal database driver transaction.
        tx_id: String, the id or hash of the transaction being broadcasted.
        n_confirmations: Int, the number of confirmations.
        """
        result = tx.run("MATCH (n:TxOut {id:$tx_id}) "
                        "SET n.confirmations=$n_confirmations "
                        "RETURN n ", tx_id=tx_id, n_confirmations = n_confirmations)
        return result.single()
    
    
    @staticmethod
    def _update_utxo(tx,tx_id):
        """
        Updates the state of an exisiting utxo to "spent=True" once the transaction was broadcasted successfully and confirmed.
        tx: internal database driver transaction.
        tx_id: String, the id or hash of the transaction that spent the utxo.
        """
        result = tx.run("MATCH p = (u)<-[:SPENT]-(:TxOut {id:$tx_id}) "
                        "SET u.spent=true "
                        "RETURN p ", tx_id=tx_id)
        return result.data()
    
    
    @staticmethod
    def _clean_addresses(tx):
        """
        Deletes addresses in the database that had were innactive for more than one month.
        """
        result = tx.run("MATCH (a: address) "
                        "WHERE NOT (:wallet)--(a)--() AND (timestamp() - a.created )>2592000000 "
                        "DELETE a ")
        return result.single()

    
    @staticmethod
    def _look_for_coins(tx,xprv):
        """
        Searches the database for utxos that haven't been spent for the specific wallet.
        tx: internal database driver transaction.
        xprv: String, The wallet extended private key.
        """
        result = tx.run("MATCH (coin:utxo {spent:false})--(address)--(w:wallet {xprv:$xprv}) "
                        "RETURN coin.transaction_id, coin.out_index, coin.address, coin.amount, coin.local_index, address.acc_index, address.type ",xprv=xprv)
        return result.data()
    
    @staticmethod
    def _get_unused_addresses(tx,xprv, days_range=None, max_days=None):
        """
        Searches the database for addresses that haven't been used in the specific wallet.
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
            result = tx.run("MATCH (unused_address:address) "
                            "WHERE NOT (:wallet)--(unused_address)--() "
                            "RETURN  unused_address.address, unused_address.acc_index, unused_address.type ")
            
        elif (days_range is None or max_days is None) and (days_range != max_days):
            raise Exception("Arguments days_range and max_days must be either both specified or neither one specified.")
            
        else:
            MILSEC_PER_DAY = 86400000
            finish_day = max_days * MILSEC_PER_DAY
            start_day = finish_day - days_range*MILSEC_PER_DAY
            result = tx.run("MATCH (unused_address:address) "
                            "WHERE NOT (:wallet)--(unused_address)--() AND (timestamp() - unused_address.created )>finish_day AND (timestamp() - unused_address.created )<start_day"
                            "RETURN  unused_address.address, unused_address.acc_index, unused_address.type ")
            
            
        return result.data()
    
    @staticmethod
    def _get_all_addresses(tx,xprv):
        """
        Returns all the addresses in the database for the specific wallet.
        tx: internal database driver transaction.
        xprv: String, The wallet extended private key.
        """
        result = tx.run("MATCH (addr:address)<-[:OWNS]-(:wallet {xprv:$xprv}) "
                        "RETURN  addr.address, addr.acc_index, addr.type ",xprv=xprv)
        return result.data()
    
    @staticmethod
    def _exist_utxo(tx, tx_id, out_index, confirmed):
        """
        Returns True if the utxo already exists in the database. False if it doesn't. It also updates
        the "confirmed" property of the utxo if necessary.
        tx: internal database driver transaction.
        tx_id: String, the tx id or hash of the transaction the generated the utxo.
        out_index: Int, the index of the output in the transaction that generated the utxo.
        confirmed: Boolean, the current state of confirmation of the transaction in the actual blockchain.
        """
        result = tx.run("MATCH (coin:utxo {transaction_id:$tx_id, out_index:$out_index}) "
                        "RETURN  coin.amount, coin.confirmed ",tx_id=tx_id, out_index=out_index)
        data = result.data()
        if len(data)>0:
            _confirmed = data[0]["coin.confirmed"]
            if _confirmed != confirmed:
                tx.run("MATCH (coin:utxo {transaction_id:$tx_id, out_index:$out_index}) "
                       "SET coin.confirmed = $confirmed "
                        "RETURN  coin.amount, coin.confirmed ",tx_id=tx_id, out_index=out_index, confirmed=confirmed)
            return True
        else: return False
        
    @staticmethod
    def _new_wallet(tx,xprv):
        """
        Creates a new wallet node in the database. 
        tx: internal database driver transaction.
        xprv: String, The extended private key if the wallet being created.
        """
        result = tx.run("CREATE (w:wallet {xprv: $xprv}) "
                        "RETURN  w ",xprv = xprv )
        return result.single()
    
    @staticmethod
    def _exist_wallet(tx, xprv):
        """
        Returns True if the wallet exists in the database. False if it doesn't. 
        tx: internal database driver transaction.
        xprv: String, The extended private key if the wallet being created.
        """
        result = tx.run("MATCH (wallet:wallet {xprv:$xprv}) "
                        "RETURN  COUNT (wallet) ",xprv = xprv )
        data = result.data()
        #print(f"data: {data}")
        if data[0]["COUNT (wallet)"]>0: return True
        else: return False
            



    
    def new_address(self, address,i,change_addr,wallet_xprv):
        """
        Creates new address in the database.
        address: the base58 representation of the address.
        i: Int, the index in the bip32 account.
        change_addr: Boolean, if it is a change adress the True. Otherwise False.
        wallet_xprv: The wallet extended private key the the generated the address.
        """
        with self._driver.session() as session:
            result = session.write_transaction(self._new_address, address,i,change_addr,wallet_xprv)
            print(result)
            
    def new_utxo(self, address,tx_id,out_index,amount,confirmed):
        """
        Creates new utxo in the database.
        address: the base58 representation of the address that holds the utxo.
        tx_id: String, the tx id or hash of the transaction the generated the utxo.
        out_index: Int, the index of the output in the transaction that generated the utxo.
        amount: Int, the amount of SATOSHIS that the utxo holds.
        confirmed: Boolean, if the transaction has less than 6 confirmations then False.
        """
        with self._driver.session() as session:
            result = session.write_transaction(self._new_utxo, address,tx_id,out_index,amount,confirmed)
            print(result)
            
    def new_tx(self, tx_id,utxo_local_index_list, outputs):
        """
        Creates new transaction in the database.
        tx_id: String, the id or hash of the transaction being created.
        inputs: List, the list of inputs of the transaction.
        outputs: List, the list of outputs of the transaction.
        """
        with self._driver.session() as session:
            result = session.write_transaction(self._new_tx, tx_id,utxo_local_index_list, outputs)
            print(result)
            
    def update_confirmations(self, tx_id,n_confirmations):
        """
        Updates the number of confirmations for a transaction to later confirm the transaction was broadcasted.
        tx_id: String, the id or hash of the transaction being broadcasted.
        n_confirmations: Int, the number of confirmations.
        """
        with self._driver.session() as session:
            result = session.write_transaction(self._update_confirmations, tx_id,n_confirmations)
            print(result)
            
    def update_utxo(self, tx_id):
        """
        Updates the state of an exisiting utxo to "spent=True" once the transaction was broadcasted successfully and confirmed.
        tx_id: String, the id or hash of the transaction that spent the utxo.
        """
        with self._driver.session() as session:
            result = session.write_transaction(self._update_utxo, tx_id)
            print(result)
        
    def clean_addresses(self):
        """
        Deletes addresses in the database that had were innactive for more than one month.
        """
        with self._driver.session() as session:
            result = session.write_transaction(self._clean_addresses)
            print(result)
            
    def look_for_coins(self,xprv):
        """
        Searches the database for utxos that haven't been spent for the specific wallet.
        xprv: String, The wallet extended private key.
        """
        with self._driver.session() as session:
            result = session.write_transaction(self._look_for_coins,xprv)
            return result
        
    def get_unused_addresses(self,xprv, days_range=None, max_days=None):
        """
        Searches the database for addresses that haven't been used in the specific wallet.
        xprv: String, The wallet extended private key.
        """
        with self._driver.session() as session:
            result = session.write_transaction(self._get_unused_addresses,xprv, days_range, max_days)
            return result
        
    def get_all_addresses(self,xprv):
        """
        Returns all the addresses in the database for the specific wallet.
        xprv: String, The wallet extended private key.
        """
        with self._driver.session() as session:
            result = session.write_transaction(self._get_all_addresses,xprv)
            return result
            
    def exist_utxo(self, tx_id, out_index, confirmed):
        """
        Returns True if the utxo already exists in the database. False if it doesn't. It also updates
        the "confirmed" property of the utxo if necessary.
        tx_id: String, the tx id or hash of the transaction the generated the utxo.
        out_index: Int, the index of the output in the transaction that generated the utxo.
        confirmed: Boolean, the current state of confirmation of the transaction in the actual blockchain.
        """
        with self._driver.session() as session:
            result = session.write_transaction(self._exist_utxo, tx_id, out_index, confirmed)
            return result
        
    def new_wallet(self, xprv):
        """
        Creates a new wallet node in the database. 
        xprv: String, The extended private key if the wallet being created.
        """
        with self._driver.session() as session:
            result = session.write_transaction(self._new_wallet, xprv )
            print(result)
            return result
        
    def exist_wallet(self, xprv):
        """
        Returns True if the wallet exists in the database. False if it doesn't. 
        xprv: String, The extended private key if the wallet being created.
        """
        with self._driver.session() as session:
            result = session.write_transaction(self._exist_wallet, xprv )
            return result