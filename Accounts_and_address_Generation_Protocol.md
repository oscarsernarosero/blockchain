# Wallet Protocol for Account and Address Generation

This wallet aims to offer solutions for the cryptocurrency-acceptance needs from the retailer industry in general, but specially for restaurant and chain stores. 

With this approach, it is important to create different kinds of accounts that will work together to ensure privacy, portability, accountability, and security for the users. These concepts will have a very specific meaning within the frame of this wallet which will be described next:

**Privacy:** The ability to hide identity of the participants of transactions conducted in the blockchain. 

**Security:** Recilience to cyber attacks that might jeopardize the funds of the legitimate holder of the wallet. Privacy is a big help for this subject.

**Portability:** The ability to access the same wallet from different devices. This might be affected or limitted in order to improve security.

**Accountability:** The degree of efficiency in which the wallet facilitates the process of money accounting for specific periods of time, funds transfering, etc.


This wallet relies heavily in the use of the Herarchical Deterministic Derivation algorythm defined in BIP32, and in the Mnemonic-Phrase generation defined in BIP39. Therefore, the protocol that this wallet will use for these deterministic derivation addresses will be defined in this document. But first, let's define our accounts.

## Accounts

### Corporate Super-Account:

These accounts will be the most important accounts for the company wallet. For this same reason, it relies heavily in the multi-signature technology to avoid a single point of failure. This wallet stablishes a minimum of three Corporate Super-Account (CSA) per company wallet to ensure the security of the funds.

The holders of these accounts must be in the highest rank of the company, such as CEOs, owners, Accounting Managers, etc. since they will be able to transfer the funds of the entire company.

Only one of the three CSA will be the main CSA account while the other two will be CSA co-signer accounts. The main CSA will be the one responsible for the different store accounts generation and some safe accounts generation. Therefore, setting up the main CSA will be the first step to setup the company wallet.

### Store Account:

This type of account works mostly as a payment point for a store. Therefore, this account is not assigned to any person, but to a store. This account will be responsible for generating the receiving addresses in the daily basis for the particular store or location.

### Manager Account:

These accounts will be given to any kind of manager or employee that does not possess a CSA. These accounts will be responsible for the transfering of funds from Store Accounts to safe addresses that will store the money of the company. These accounts will also have access to the funds kept in the store safe addresses to ensure a certain degree of autonomy for the locations.

Now that we have talked about safe addresses, it is important to define them.

## Addresses:

### Safe Addresses:

These are not a type of account, but mostly a type of addresses where multiple accounts are necessary to have access to the funds. So, in order for this wallet to ensure the safety and the accountability of the funds, the wallet will store the funds collected throughout the day and throughout the week in these safe addresses. These addresses are multisignature addresses that require at least 2 co-signer accounts to transfer the funds to ensure its safety. The possible configuration of cosigners will differ depending of the aomunt of money that the address will store. There are three types of safe addresses:

**Daily Safe:** These addresses will store the total of the payments received at a certain location in a single day. These will be a 2-of-6 multi-signature address, and this is considered a low risk safe address since the amount of money it holds is the least out of the three kinds of safe addresses.

**Weekly Safe:** These addresses will store the funds remaining in the daily safes from a certain location at the end of the week. These will be a 2-of-5 multi-signature address, and it is cosidered a medium risk address since it stores a considerable amount of funds for the company.

**Corporate safe:** These addresses will store funds securly for corporate. These addresses can be generated arbitrarily any time corporate considers it necessary to ensure the security of the funds or to ensure the accountability of them. These addresses will be 2-of-3 multi-signature addresses, and only CSA can sign its transactions to ensure maximum security of its funds.

### Receiving Addresses

These addresses will be generated exclusively by Store Accounts. They are not multi-signature addresses and their funds can be transfered with only the Store Account signature.


## Account and Address Generation:

In general, this wallet makes use of a combination of deterministic and randomic generation of accounts and addresses to ensure portability and security at the same time. This means that even though many accounts are created randomely to ensure security, the wallet will create some accounts and addresses with a certain degree of predictability to ensure that switching devices will be possible with only the recovery prahse, and without the need of a cloud service which would be a major hazard for the security of the company funds. The full disclosure of the account and address generation will follow.

### CSA Generation

These accounts are the most important accounts for the company regarding many aspects including security. Therefore, the generation of these accounts are totally randomic.

### Manager Account Generation

Same as CSA generation, the generation of these accounts are totally randomic.

### Store Account Generation

This accounts will be direct descendants from the main CSA, and therefore, the generation of these accounts is entirely deterministic. The index and depth in the deterministic tree assigned to each store is totally left to the company's freedom. However, a simple and existing-index reuse is suggested. 

### Daily Payment Account Genereation

The Store Account, however, is responsible for the generation of the **Daily Payment Accounts**. As its name suggests, these accounts are generated daily to ensure security and accountability of the funds. The generation for these accounts will be entirely deterministic. The path of creation for these accounts will make use of the date in a specific format (YYMMDD).

Let's make an example to ilustrate these last two account generations:

Let's imagine that the CEO of company XYZ has 50 stores under his watch. In his company, every store has already a code which refers to a state and an internal index. So the store in Galleria Mall in Houston, Tx. has the code of 0105. Therefore, he asigned this path under his account to generate the store account: m'\3'\105.

Here, it is important to note three aspects. First, the ( ' ) symbol that follows the first 2 characters. This symbol indicates hardened paths which ensures security of the master account *m*. Second, the number *3* in the middle, represents a child account that follows inmidietely the master account in hierarchy, and that has the index of 3 in this level. This means that the CEO -for a reason unknown to us- decided that all the Store Accounts will descend from his child account with index 3. At this point, we can start thinking of Store Accounts as grand child accounts of the CEO's main account, which are also children of his child account 3'. Finally, the 105 represents the code that the location already had in the files of the company (0105), and therefore, the CEO decided to reuse to generate the Store Account. 

The same principle that applies for the generation of the Store Account applies for the Daily Payment Accounts. So the Store Account will generate automatically a different account daily with an index which will be entirely determined by the date. Therefore, these accounts are generated deterministically. As aforementioned, the date will have the format YYMMDD. So, if -for example- today were December the 31st of 2020, the account that the Store Account would generate will be the one with the index of 201231. Seen from the Store Account perspective, this account will be m'/201231. From the CEO perspective, however, it will be m'/3'/105'/201231.

### Receiving Address Generation

Now that we know how the CEO generated the Store Account, and how the Store account generates the Daily Payment Account, let's see how the Daily Payment Accounts generates the receiving addresses.

For privacy and accountability reasons, every single payment must be conducted through an address specifically and exclusively created for such transaction. An address must not be reused for any reason. 

The creation of the receiving address is totally random within two boundaries: it must be created inside a daily payment account, and its index inside such account should be within the set of possible addresses defined by the range of daily payments expected. 

The generation of these addresses will be then defined by these 2 variables:

**Leap:** this sets the value that will multiply the random index selected for a receiving address. The purpose of this leap is to make it harder to crack the daily-payment-account master key that generates the addresses. The default value for this variable is 7, and modifying it should be avoided always since this might result in lost of funds in a future recovery process if this change is not recorded.

**Range:** This is the maximum amount of addresses that can be created by the daily payment account. The original range for addresses that Bitcoin offers is 2 billion addresses. However, this presents a chanllenge of portability since it would be necessary to scan all 2 billion addresses for each day in order to recover transactions made in a store (if accessing from a different device was desired). For this reason, selecting the right *Range* is key for portability speed, but also to ensure that the store will not run out of addresses during a day of opperations. As a guideline, we sugest to set this amount to twice whatever amount of payments received has been the highest in the past.

The formula on which an address will be created will be:

new_address = random_integer(0 - Range)*Leap.
is new_address new?
No: recalculate.
Yes: new_address is valid.

Following the former example of company XYZ, let's pretend that the highest volume of crypto-payments this company has had in a single day  at this location has been 400 payments. Therefore, the company setups a limit of 800 possible addresses per day (Range = 800). This means that the daily payment account will select any of the 800 possible addresses every time it needs to receive a payment (receiving address).

### Daily Safe Address Genration

These addresses are multisignature addresses as pointed out previously. For each store, it will be always the same co-signers:

- Store General Manager.
- Store Assistant Manager.
- Regional Manager.
- CEO Main account.
- CEO co-signing account 1
- CEO co-signing account 2/ Accounting

The required signatures to conduct a fund transfer will be 2 out of 6.

However, due to the way that multi-signature addresses are generated in Bitcoin, this address would always be the same if we don't modify at least one of the accounts every time we generat it. For this reason, the CEO main account will not be the master key as it is the case with the other accounts. It will be a deterministic grandchild account that will use the same principle used previously by the Daily Payment Account.

These grandchild accounts will be direct descendant of a single child account from the the CEO main account: m'/1'/1000'. The indices that these grandchild accounts will have will obvey to the date for which it will be created following the format YYMMDD. Therefore, if today were December the 31st of 2020, the accont that would be able to sign the Daily Safe Address of that day will be the account m'/1'/1000'/201231 from the CEO's main account.

For this to actually be possible, public key exchange will be necessary. This will be discuss later. However, the account responsible for the generation of these safe addresses will be the CEO main account.


### Weekly Safe Address Genration

These addresses are also multisignature addresses. For each store, it will be always the same co-signers:

- Store General Manager.
- Regional Manager.
- CEO Main account.
- CEO co-signing account 1
- CEO co-signing account 2/ Accounting

The required signatures to conduct a fund transfer will be 2 out of 5.

Similar to the Daily Safe Accounts, these Weekly Safe Accounts are grandchild accounts descending directly from a single child account from the the CEO main account: m'/1'/2020'. The indices that these grandchild accounts will have will obvey to the number of the week in the year for which it will be created. Therefore, if today were December the 31st of 2020, the accont that would be able to sign the Weekly Safe Address of that week will be the account m'/1'/2020'/53 from the CEO's main account.

### Safe Corporate Addresses

Corporate will have to its disposal a whole wallet which is built upon the three Corporate Super Accounts. This wallet will be a 2-of-3 multi signature wallet at the least. By default, every address generated to receive payments directly to corporate level will be handled under Safe Corporate Addresses. These addresses are similiar to the receiving addresses for stores in the way that these are created randomly under 2 boundaries which are, again, the account and the range.

Every receiving payment at corporate level will ocure in a **yearly account**. These accounts will have the index of the year in the format YYYY, and they will be under the account m'/2'. So, for example, the payments received from corporate in 2020 will be under the account m'/2'/2020. 

The range will be a default amount of 2000, with no leap.

## Change Addresses








