# Wallet Protocol for Account and Address Generation

Since this wallet aims to offer solutions for the cryptocurrency-acceptance needs from the retailer industry in general, but specially for restaurant and chain stores, it is important to create different kinds of accounts that will work together to ensure privacy, portability, accountancy, and security for the users. These concepts will have a very specific meaning within the frame of this wallet which will be described next:

**Privacy:** The ability to hide identity of the participants of transactions conducted in the blockchain. 

**Security:** Resilience to cyber attacks that might jeopardize the funds of the legitimate holder of the wallet. Privacy is a big help for this subject.

**Portability:** The ability to access the same wallet from different devices. This might be affected or limited in order to improve security.

**accountancy:** The degree of efficiency in which the wallet facilitates the process of money accounting for specific periods of time, funds transferring, etc.


This wallet relies heavily in the use of the Herarchical Deterministic Derivation algorithm defined in BIP32, and in the Mnemonic-Phrase generation defined in BIP39. Therefore, the protocol that this wallet will use for these deterministic derivation addresses will be defined in this document. But first, let's define our accounts.

## Wallets

### Corporate Super-Wallet:

These wallets will be the most important wallets for the company wallet. For this same reason, it relies heavily in the multi-signature technology to avoid a single point of failure. This wallet establishes a minimum of three Corporate Super-wallet (CSW) per company wallet to ensure the security of the funds.

The holders of these wallets must be in the highest rank of the company, such as CEOs, owners, Accounting Managers, etc. since they will be able to transfer the funds of the entire company.

Only one of the three CSW will be the main CSW wallet while the other two will be CSW co-signer wallets. The main CSW will be the one responsible for the different store wallets generation and some safe wallets generation. Therefore, setting up the main CSW will be the first step to setup the company wallet.

### Store Wallet:

This type of wallet works mostly as a payment point for a store. Therefore, this wallet is not assigned to any person, but to a store. This wallet will be responsible for generating the Deposit addresses in the daily basis for the particular store or location.

### Manager Wallet:

These wallets will be given to any kind of manager or employee that does not possess a CSA. These wallets will be responsible for the transferring of funds from Store wallets to safe addresses that will store the money of the company. These wallets will also have access to the funds kept in the store safe addresses to ensure a certain degree of autonomy for the locations.

Now that we have talked about safe addresses, it is important to define them.

## Addresses:

### Safe Addresses:

In order for this wallet to ensure the safety and the accountancy of the funds, the wallet will store the funds collected throughout the day and throughout the week in these safe addresses. These addresses are multisignature addresses that require at least 2 co-signer wallets to transfer the funds to ensure its safety. The possible configuration of cosigners will differ depending of the amount of money that the address will store. There are three types of safe addresses:

**Daily Safe:** These addresses will store the total of the payments received at a certain location in a single day. These will be a 2-of-6 multi-signature address, and this is considered a low risk safe address since the amount of money it holds is the least out of the three kinds of safe addresses.

**Weekly Safe:** These addresses will store the funds remaining in the daily safes from a certain location at the end of the week. These will be a 2-of-5 multi-signature address, and it is considered a medium risk address since it stores a considerable amount of funds for the company.

**Corporate safe:** These addresses will store funds securely for corporate. These addresses can be generated arbitrarily any time corporate considers it necessary to ensure the security of the funds or to ensure the accountancy of them. These addresses will be 2-of-3 multi-signature addresses, and only CSA can sign its transactions to ensure maximum security of its funds.

### Deposit Addresses

These addresses will be generated exclusively by Store wallets. They are not multi-signature addresses and their funds can be transferred with only the Store wallet signature.


## Wallet and Account-Address Generation:

This wallet relies on deterministic algorithms for  the account and address generation to ensure portability. This means that the wallet will have a high degree of predictability at the address-account generation to ensure that switching devices will be possible and fast with the need of only the recovery phrase, and without the need of a cloud service which would be a major hazard for the security of the company funds. The full disclosure of the account and address generation will follow.

### CSW Generation

These wallets are the most important wallets for the company regarding many aspects including security. Therefore, the generation of these wallets are totally random. These wallets, however, are responsible for the generation of all the other wallets, and therefore, the use of some paths is already defined and restricted.

The path generation for account and addresses in this wallet complies with standard BIP44 with some exceptions for security reasons. The Only difference with BIP44 is that this wallet still use hardened keys even in the account and address level. The only exception is deposit addresses for Stores under the Daily Deposit accounts, and the addresses for daily and weekly safes, although these last ones are multi-signature addresses.

#### Restricted paths for CSW accounts

| Account Path | Purpose |
| --- | -- |
| m/44'/0'/0' | Store-Wallet Parent Account |
| m/44'/0'/1' | Daily-Safe-Address Parent Account |
| m/44'/0'/2' | Weekly-Safe-Address Parent Account |
| m/44'/0'/3' | Annual-Corporate Parent Account |

### Manager Wallet Generation

Same as CSW generation, the generation of these wallets are totally random.

### Store wallet Generation

This wallets will be direct descendants from the main CSW, and therefore, the generation of these wallets is entirely deterministic. The index in the deterministic tree assigned to each store is totally left to the company's freedom. However, a simple and existing-index reuse is suggested. 

### Daily Payment Account Generation

The Store wallet, however, is responsible for the generation of the **Daily Payment Accounts**. As its name suggests, these accounts are generated daily to ensure security and accountancy of the funds. The generation for these accounts will be entirely deterministic. The path of creation for these accounts will make use of the date in a specific format (YYMMDD).

#### An example:

Let's make an example to illustrate these last account generation:

Let's imagine that the CEO of company XYZ has 50 stores under his watch. In his company, every store has already a code which refers to a state and an internal index. So the store in Galleria Mall in Houston, Tx. has the code 0105. Therefore, he assigned this path under his *Store-Wallet Parent Account* which is the *m/44'/0'/0'* account. Therefore, the wallet assigned for the store is the one derived from the master private key generated from the path: m/44'/0'/0'/**105'**.

Here, it is important to note two things. First, the ( ' ) symbol that follows every level of the path. This symbol indicates hardened paths which ensures security of the accounts all the way until the store level. This is an extra layer of security that ensures that the funds of the wallet won't be compromised even if one of the private keys is leaked. And the second one, the number 105' represents the code that the location already had in the files of the company (0105), and therefore, the CEO decided to reuse to generate the Store Wallets. 

The same principle applies for the Daily Payment Accounts. So the Store Wallet will generate automatically a different account every day with an index which will be entirely determined by the date. Therefore, these accounts are generated deterministically. As aforementioned, the date will have the format YYMMDD. So, if -for example- today were December the 31st of 2020, the account that the Store Account would generate will be the one with the index of 201231'. Seen from the Store Wallet perspective, this account will be m/201231'. From the CEO perspective, however, it will be m/44'/0'/0'/105'/201231'. Don't forget that all the path generation will be hardened keys and therefore the ( ' )  symbol will proceed them.

### Deposit Address Generation

Now that we know how the CEO generated the Store Wallet, and how the Store Wallet generates the Daily Payment Account, let's see how the Daily Payment Accounts generates the Deposit addresses.

For privacy and accountancy reasons, every single payment must be conducted through an address specifically and exclusively created for such transaction. An address must not be reused for any reason. 

The creation of the Deposit address is totally deterministic in the way that the index of the address created will increase by one. This means that the first payment will have the index 0, the second one will have the index 1, and the hundredth the index 99. This is done this way to ensure portability for future wallet scanning.

Following the former example of company XYZ, let's pretend that, at the end of the day, the store located in Galleria Mall in Houston is ready to receive the last payment from a customer. This payment will be the 456th payment of the day. The path for this address then will be m/201231'/456. From the CEO perspective, however, it will be m/44'/0'/0'/105'/201231'/456. Note that the address doesn't have the ( ' ) symbol since these are some of the few addresses that are non-hardened keys in the whole wallet. The reason for this is to be able to monitor the daily balance of a store through a watch only wallet.

The following table summarizes the path generation for deposit addresses at store level:
| Path | Purpose |
| --- | -- |
| m/44'/0'/0' | Store-Wallets Parent Account |
| m/44'/0'/0'/XXXX' | Store Wallets |
| m/44'/0'/0'/XXXX'/YYMMDD' | Store's Daily-Payment Account |
| m/44'/0'/0'/XXXX'/YYMMDD'/i* | Store's Daily-Payment Addresses* |

XXXX: code for the store.<br>
YYMMDD: date.<br>
i: number or index of payment.


*Even though we haven't talked about change and deposit accounts yet, this is a best practice on which this wallet relies. However, in this case, there is no need to create two separate accounts for deposits and change since this account is already meant to exclusively be a deposit account.

### Daily Safe Wallet Generation

These addresses are multisignature addresses as pointed out previously. For each store, it will be always the same co-signers:

- Store General Manager.
- Store Assistant Manager.
- Regional Manager.
- CEO Main Wallet.
- CEO co-signing Wallet 1
- CEO co-signing Wallet 2/ Accounting

The required signatures to conduct a fund transfer will be 2 out of 6.

However, due to the way that multi-signature addresses are generated in Bitcoin, these addresses would always be the same one if we don't modify at least one of the private-public keys every time we generate it. For this reason, the CEO main wallet will not use a single static private-public key as it is the case with the other Wallets. It will be a deterministic grandchild private-public key that will use the same principle used previously by the Daily Payment Account.

These grandchild accounts will be direct descendants from a single child account from the the CEO main wallet: m/44'/0'/1'. The indices that these grandchild accounts will obey to the date for which it will be created following the format YYMMDD used before. Therefore, if today were December the 31st of 2020, the account that would be able to sign the Daily Safe Address of that day will be the account m/44'/0'/1'/201231' from the CEO's main wallet.

For this to actually be possible, some public-key exchange will be necessary. This will be discussed later. However, the wallet responsible for the generation of these safe addresses will be the CEO main wallet.

The following table summarizes the path generation for daily dafe accounts:

| Path | Purpose |
| --- | -- |
| m/44'/0'/1' | Daily-Safe-Wallet Parent Account |
| m/44'/0'/1'/YYMMDD' | Daily-Safe-Wallet Accounts|
| m/44'/0'/1'/YYMMDD'/0 | Daily-Safe Deposit Account |
| m/44'/0'/1'/YYMMDD'/0/0 | Daily Safe Deposit Address |
| m/44'/0'/1'/YYMMDD'/1 | Daily-Safe Change Account |
| m/44'/0'/1'/YYMMDD'/1/n | Daily Safe Change Addresses |

The reason for change and deposit accounts not to be hardened accounts is to be able to give the stores the autonomy to generate change addresses. The possibility to generate deposit addresses also exists. However this kind of addresses are not meant to receive but just once. 

The creation of the safe-daily deposit and change addresses is totally deterministic in the way that the index of the address created will increase by one. This means that the daily safe address will always have the index 0, and the change addresses will start at index 0 and increase by one making the second address to have the index 1, and the hundredth the index 99. This is done this way to ensure portability for future wallet scanning.

### Weekly Safe Address Generation

These addresses are also multisignature addresses. For each store, it will be always the same co-signers:

- Store General Manager.
- Regional Manager.
- CEO Main account.
- CEO co-signing account 1
- CEO co-signing account 2/ Accounting

The required signatures to conduct a fund transfer will be 2 out of 5.

Similar to the Daily Safe Accounts, these Weekly Safe Accounts are grandchild accounts descending directly from a single child account from the the CEO main account: m/44'/0'/2'. The indices that these grandchild accounts will have will obey to the number of the week in the year for which it will be created. Therefore, if today were December the 31st of 2020, the account that would be able to sign the Weekly Safe Address of that week will be the account m/44'/0'/2'/2053' from the CEO's main account.

| Path | Purpose |
| --- | -- |
| m/44'/0'/2' | Weekly-Safe-Address Parent Account |
| m/44'/0'/2'/YYN' | Weekly-Safe-Address Parent Account |
| m/44'/0'/2'/YYN'/0 | Weekly-Safe Deposit Account |
| m/44'/0'/2'/YYN'/0/0 | Weekly Safe Deposit Address |
| m/44'/0'/2'/YYN'/1 | Weekly-Safe Change Account |
| m/44'/0'/2'/YYN'/n | Weekly-Safe Change Addresses |

Same as for the daily safe accounts, the reason for change and deposit accounts not to be hardened accounts is to be able to give the stores the autonomy to generate change addresses.

### Safe Corporate Addresses

Corporate will have to its disposal a whole wallet which is built upon all the Corporate Super Accounts (three at the minimum). This wallet will be a 2-of-3 multi signature wallet at the least. By default, every address generated to receive payments directly to corporate level will be handled under Safe Corporate Addresses.

Corportate can handle creation of accounts for certain clients, if desired. However, all transactions and accounts are going to happen under the annual accounts.

Every deposit or payment at corporate level will occur in an **annual account**. These accounts will have the index of the year in the format YYYY, and they will be under the account m/44'/0'/3'. So, for example, the payments received from corporate in 2020 will be under the account m/44'/0'/3'/2020'. 

The deposit account will be 0, and the change account will be 1. The creation of custom accounts will be left to the company's freedom as long as they don't use 0 or 1.

| Path | Purpose |
| --- | -- |
| m/44'/0'/3' | Annual-Corporate Parent accounts |
| m/44'/0'/3'/YYYY' | Annual Corporate Account |
| m/44'/0'/3'/YYYY'/0' | Annual Corporate Deposit Accounts |
| m/44'/0'/3'/YYYY'/1' | Annual Corporate Change Accounts |


## Multi-Signature Wallet Creation Protocol

### Daily/Weekly Safe Wallet Creation:

1. Main CSW requests or pull up the public keys of managers, and the other 2 CSWs for the daily/weekly safe wallets.

2. Main CSW creates the Daily/Weekly Safe Super Wallet ( SHDSafeWallet ).

3. Main CSW shares the Daily/Weekly Safe Super Wallet with every body ( \<SHDSafeWallet\>.share() ).

4. Participants accept the invitation for the Daily/Weekly Safe Super Wallet ( \<ManagerWalet\>.accept_invite() ).

5. Participants have access now to the daily/weekly safe wallets for their daily/weekly operations ( \<MultiSignature\>.get_daily_safe_wallet() ).


## Transacting from Daily/Weekly Safe Wallets:

1. Initiate the transaction by specifing the recipient and the amount list ( response = \<get_daily_safe_wallet\>.send() )

2. Share the response with the other cosigners (response)

3. Cosigners will sign transaction ( \<cosigner_wallet\>.sign_received_tx(response[0]) ) until it is broadcasted.


### Corporate Safe Wallet Creation:

1. Main CSW requests or pull up the public keys of the other CSWs for the corporate safe wallet.

2. Main CSW creates the Corporate Safe Super Wallet (HDMWallet).

3. Main CSW shares the Corportate Safe Super Wallet with every body ( HDMWallet.share() ).

4. Participants accept the invitation for the Corporate Safe Super Wallet ( \<CSW\>.accept_corporate_safe_invite() ).

5. Participants have access now to the corporate safe wallets for their operations ( \<MultiSignature\>.get_year_wallet() ).


## Transacting from Corporate Safe Wallets:

1. Initiate the transaction by specifing the recipient and the amount list ( response = \<get_year_wallet\>.send() )

2. Share the response with the other cosigners (response)

3. Cosigners will sign transaction ( \<cosigner_wallet\>.sign_received_tx(response[0]) ) until it is broadcasted.



