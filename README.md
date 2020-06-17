# blockchain

This project is still in development. 

### Description:

The blockchain project is mostly an educational-purpose project which aims to develope robust wallets from scratch (no external libraries except for python built-in libraries) for some well known cryptocurrencies, and having in mind real world applications like companies or small businesses. 

### Status:

Currently only supporting Testnet Bitcoin.

### Achievments:

-Eliptic Curve Criptography (secp256k1)

-Transactions

-Bip32

-Bip39

-Accounts

-Segwit Compliant

-Multi signature

Some of the code here comes from the book Programming Bitcoin, so a big share of the credit goes to Jimmy Song (the author of the book).

### General Description of Current Version

The current version of the wallet is a wallet for the testnet network. It is intended for individual use, however a company version is on its way. The general features will will be discussed next:

#### Security:

 - This Wallet is not a cloud-based wallet since this is considered a major security hazard.

 - All keys are stored locally in the device in an sqlite database. 

 - Recovery function (comming soon) will be available following BIP44, BIP32 standard for addresses creation, and BIP39 mnemonic phrase.

 #### Privacy:

 - No address will be used more than once (BIP32/BIP44 standard).

 #### Technology:

- Multisignature technology is available, although not fully exploited yet. Only used for making SegWit addresses backward compatible (P2SH_P2WPKH). Fully multisignature wallets will come in next versions.

- Segregated Witness technology is supported with the exception of multisignature SegWit addresses (P2WSH, P2SH_P2WSH). This will be available in the comming versions.


### How to use:

This library uses Kivy for its front-end development. A release with executables for different platforms is on its way. But for right now, to use this app follow the following steps (I suggest you to do this in a brand new virtual environment):

1. Clone this repository.
2. Install dependencies:
    - kivy
    - blockcypher
    - pyperclip
    - qrcode
3. Run:

     ```$ cd blockchain```

    ```$ python3 bitcoin/basics/final/main.py ```



Once there, you will have your wallet running on the wallet-selection screen:


![Initialization](bitcoin/basics/final/images/screenshots/01.png)


Press the "+" button to create a Wallet. A popup window will prompt to name your new wallet:

![Name your new wallet](bitcoin/basics/final/images/screenshots/02.png)

Once you have named your wallet, you will be able to see it in your wallets list. 

![Main Screen](bitcoin/basics/final/images/screenshots/03.png)

Click the wallet to access to it. You will go to the "Main" screen of your selected Wallet. Here, you can see your balance, and choose to send or receive testnet bitcoins:

![Main Screen](bitcoin/basics/final/images/screenshots/04.png)

Let's receive some Bitcoin! press the "RECEIVE" button:

![Receive Screen](bitcoin/basics/final/images/screenshots/05.png)

You can choose to use an unused address. Press the spinner under the label "From an unused address". You can choose between P2PKH, P2WPKH and P2SH (multi signature) address. P2PKH is the default:

![Choose Address Type](bitcoin/basics/final/images/screenshots/06.png)

But, of course, we have no unused addresses yet.

![No Unused Addresses Available](bitcoin/basics/final/images/screenshots/07.png)

 So let's create a new one. Select any type of address under the label "From a new address":

 ![Create a New Address](bitcoin/basics/final/images/screenshots/08.png)

 Now, let's see the address and its QR code. Simply press the "Show QR code" button:

 ![QRcode Popup](bitcoin/basics/final/images/screenshots/09.png)

 You can simply tab on the address to get it copied to the clipboard. Press "OK" to go back.

 Now let's try to send some Testnet Bitcoins. Press the "GO BACK" button to go to the main screen. Now, press "SEND":

 ![Send Screen](bitcoin/basics/final/images/screenshots/10.png)

 You can paste an address in the text-input field by double-tapping on it, or you can scan a QR code. Let's do the latter. Press the QR code button. A camera popup will prompt. Place the QR code of the address to which you wish to send Testnet Bitcoins to:

 ![Scan Address](bitcoin/basics/final/images/screenshots/12.png)

 Once the address is shown below the camera, press "SELECT THIS ADDRESS". This will take you back to the "Send" screen with the address scanned in the text-input field:

 ![Introduce Amount](bitcoin/basics/final/images/screenshots/13.png)

 You can now introduce the amount you wish to send to that address. You can select Bitcoins or Satoshis by pressing the spinner under "Units":

 ![Select Units](bitcoin/basics/final/images/screenshots/14.png)

 Bitcoins is the default unit. Let's send 10.000 Satoshis (or 0.0001 BTC): 

 ![Send BTC to Address](bitcoin/basics/final/images/screenshots/15.png)

 A confirmation window will pop up. If this information is correct, press "YES":

 ![Confirmation Popup](bitcoin/basics/final/images/screenshots/16.png)

 Wait a second! we still don't have money:

 ![Not Enough Funds](bitcoin/basics/final/images/screenshots/17.png)

 Let's receive some testnet money throuhg a Bitcoin Faucet through the address we created previously. Then let's manually update our balance by clicking the update-balance icon <img src="bitcoin/basics/final/images/Reload-icon.png "  width="15" height="15" /> located in the top-right corner of the "Main" screen of the wallet.

 ![Updating Balance](bitcoin/basics/final/images/screenshots/18.png)

 The wallet will prompt some mesages while retreiving the information from the blockchain and writting it into the local database. Then your balance will be displayed:

 ![Balance Up to Date](bitcoin/basics/final/images/screenshots/19.png)

 To select, create or delete a wallet, simply hit the  <img src="bitcoin/basics/final/images/backwards.png "  width="20" height="20" /> button to go back to the "Wallet-Selection" screen. 