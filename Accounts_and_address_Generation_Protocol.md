# Wallet Protocol for Account and Address Generation

This wallet aims to offer solutions for the cryptocurrency-acceptance needs from the retailer industry in general, but specially for restaurant and chain stores. 

With this approach, it is important to create different kinds of accounts that will work together to ensure privacy, portability, accountability, and security for the users. These concepts will have a very specific meaning within the frame of this wallet which will be described next:

**Privacy:** The ability to hide identity of the participants of transactions conducted in the blockchain. 

**Security:** Recilience to cyber attacks that might jeopardize the funds of the legitimate holder of the wallet. Privacy is a big help for this subject.

**Portability:** The ability to access the same wallet from different sources. This might be affected or limitted in order to improve security.

**Accountability:** The degree of efficiency in which the wallet facilitates the process of money accounting for specific periods of time, funds transfering, etc.


This wallet relies heavily in the use of the Herarchical Deterministic Derivation algorythm defined in BIP32, and in the Mnemonic-Phrase generation defined in BIP39. Therefore, the protocol that this wallet will use for these deterministic derivation addresses will be defined in this document. But first, let's define our accounts.

## Accounts

### Corporate Super-Account:

These accounts will be the most important accounts for the company wallet. For this same reason, it relies heavily in the multi-signature technology to avoid a single point of failure. This wallet stablishes a total of three Corporate Super-Account (CSA) per company wallet to ensure the security of the funds.

The holders of these accounts must be in the highest rank of the company, such as CEOs, owners, Accounting Managers, etc. since they will be able to transfer the funds of the entire company.

Only one of the three CSA will be the main CSA account while the other two will be CSA co-signer account. The main CSA will be the one responsible for the different store accounts generation and some safe accounts generation. Therefore, setting up the main CSA will be the first step to setup the company wallet.

### Store Account:

This type of account works mostly as a payment point for a store. Therefore, this account is not assigned to any person, but to a store. This account will be responsible for generating the receiving addresses in the daily basis for the particular store or location.

### Manager Account:

These accounts will be given to any kind of manager or employee that does not possess a CSA. These accounts will be responsible for the transfering of funds from Store Accounts to safe addresses that will store the money of the company. These accounts will also have access to the funds stored in the store safe addresses to ensure a certain degree of autonomy for the stores.

Now that we have talked about safe addresses, it is important to define them.

## Safe Addresses:

These are not a type of account, but mostly a type of addresses where multiple accounts are necessary to have access to the funds. So, in order for this wallet to ensure the safety and the accountability of the funds, the wallet will store the funds collected throughout the day and throughout the week in these safe addresses. These addresses are multisignature addresses that require at least 2 co-signer accounts to transfer the funds to ensure its safety. The possible configuration of cosigners will differ depending of the aomunt of money that the address will store. There are three types of safe addresses:

**Daily Safe:** These addresses will store the total of the payments received at a certain location in a single day. These will be a 2-of-6 multi-signature address, and this is considered a low risk safe address since the amount of money it holds is the least out of the three kinds of safe addresses.

**Weekly Safe:** These addresses will store the funds remaining in the daily safes from a certain location at the end of the week. These will be a 2-of-5 multi-signature address, and it is cosidered a medium risk address since it stores a considerable amount of funds for the company.

**Corporate safe:** These addresses will store funds securly for corporate. These addresses can be generated arbitrarily any time corporate consider it necessary to ensure the security of the funds or to ensure the accountability of them. These addresses will be 2-of-3 multi-signature address, and only CSA can sign its transactions to ensure maximum security of its funds.










