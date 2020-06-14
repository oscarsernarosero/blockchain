import kivy
kivy.require('1.11.1') # replace with your current kivy version !
from wallet import Wallet
from wallet_database_sqlite3 import Sqlite3Wallet
import qrcode
from urllib.request import Request, urlopen
import json
import os
from dotenv import load_dotenv
import pyperclip
import time, threading

from kivy.core.clipboard import Clipboard 
from kivy.clock import Clock
from kivy.base import EventLoop
from  kivy.uix.camera import Camera
from kivy_garden.zbarcam import ZBarCam

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.config import Config
from kivy.uix.image import AsyncImage
from kivy.properties import StringProperty,BooleanProperty, ObjectProperty, NumericProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen
import kivy.input.motionevent 
Config.set('graphics','width',300)
Config.set('graphics','height',600)

        
class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''


class SelectableLabel(RecycleDataViewBehavior, Label):
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(SelectableLabel, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(SelectableLabel, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        if is_selected:
            
            print("selection changed to {0}".format(rv.data[index]))
            app = App.get_running_app()
            sm = app.sm
            
            sm.add_widget(MainScreen(name="Main"))
            
            words = app.db.get_words_from_wallet(rv.data[index]["text"])
            #the result of the query will come in the form [(result,)]. Therefore, we  
            #will select the datum in result[0][0].
            print(f"words from db: {words[0][0]}")
            _wallet = Wallet.recover_from_words(mnemonic_list=words[0][0],testnet = True)
            
            app.wallets.append({f"{rv.data[index]['text']}": _wallet})
            app.current_wallet = rv.data[index]['text']
            print(f"app.wallets: {app.wallets}, current: {app.current_wallet}")
            
            Clock.schedule_once(self.go_to_main, 0.7)                    
            #sm.switch_to(Screen(name="Main"), direction='right')
                                
        else:
            print("selection removed for {0}".format(rv.data[index]))
                                
    def go_to_main(self,obj):
        app = App.get_running_app()
        sm = app.sm
        #sm.switch_to(Screen(name="Main"), direction='right')
        sm.current = "Main"


class WalletScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__()
        app = App.get_running_app()
        my_wallet_names = app.my_wallet_names
        no_wallet_msg ="You don't have any wallet yet.\nLet's start by creating one.\n\nPress the '+' button." 
        if len(my_wallet_names)>0:
            self.ids.rv.data = [{'text': str(x[1])} for x in my_wallet_names]
        else:
            self.ids.rv.data = [{'text': no_wallet_msg}]

    def new_wallet(self):
        self.new_wallet_popup = NewWalletPopup()
        self.newWalletWindow = Popup(title="New Wallet", content=self.new_wallet_popup, size_hint=(None,None), size=(500,700), 
                                 pos_hint={"center_x":0.5, "center_y":0.6}
                           )
        self.newWalletWindow.open()
        self.new_wallet_popup.ids.button.bind(on_release=self.create_wallet)
        
    def create_wallet(self,button):
        app = App.get_running_app()
        my_wallet_names = app.my_wallet_names
        name = self.new_wallet_popup.ids.wallet_name.text
        my_wallet = Wallet.generate_random(testnet=True)
        app.db.new_wallet(my_wallet.xtended_key, str(my_wallet.words)[1:], name)
        my_wallet_names.append((my_wallet.xtended_key, name, str(my_wallet.words)[1:]))
        self.ids.rv.data = [{'text': x[1]} for x in my_wallet_names]
        self.newWalletWindow.dismiss()
        
    
        
class MainScreen(Screen):
    btc_balance = NumericProperty()
    usd_balance = 0.0
    
    def on_pre_enter(self):
        app = App.get_running_app()
        if app.current_wallet is not None:
            self.update_balance()
        
    btc_balance_text = StringProperty(str(btc_balance) + " BTC")
    usd_balance_text = StringProperty("{:10.2f}".format(usd_balance) + " USD")
    
    font_size = "20sp"
   
    def update_real_balance(self):
        self.loading = LoadingPopup("Now consulting the blockchain..\n\nUpdating the database...\n\nThis might take a few\nmore seconds...\nPlease wait.")
        self.loadingDB = Popup(title="Loading... ", content=self.loading,size_hint=(None,None),
                                   auto_dismiss=False, size=(500, 500), pos_hint={"center_x":0.5, "center_y":0.5})
        self.loadingDB.open()
        mythread = threading.Thread(target=self.update_real_balance_process)
        mythread.start()
    
    
    def update_real_balance_process(self):
        app = App.get_running_app() 
        #my_wallet = app.my_wallet
        print(f"update_balance_process:\napp.wallets {app.wallets}, current wallet: {app.current_wallet}")
        index=None
        for i,w in enumerate(app.wallets):
            if list(w.keys())[0] == app.current_wallet: 
                index=i
                break
        my_wallet = app.wallets[index][app.current_wallet]
        my_wallet.start_conn()
                                
        try:                        
            my_wallet.update_balance()  
            print("Database up to date. Updating information on display...")
            self.loadingDB.dismiss()

            self.update_balance()
        except Exception as e:
            if str(e).startswith("('Status Code 429'"):
                #TRIGGER THE "WRONG INPUT POPUP"
                self.exception_popup = GenericOkPopup("Too many requests in the\npast hour.\nTry again later.")
                self.notEnoughFundsWindow = Popup(title="Server Error", content=self.exception_popup, 
                                                  size_hint=(None,None),size=(500,500), 
                                                  pos_hint={"center_x":0.5, "center_y":0.5}
                                   )
                self.notEnoughFundsWindow.open()
                self.exception_popup.OK.bind(on_release=self.notEnoughFundsWindow.dismiss)                
                                
                #closing popups
                self.loadingDB.dismiss()

                self.update_balance()                  
        
        
    
    def update_balance(self):
        #Creating the loading screen
        self.loading = LoadingPopup("Consulting the\ndatabase\nand Bitcoin's price...\n\nAlmost done.\nPlease wait.")
        self.loadingBalance = Popup(title="Loading... ", content=self.loading,size_hint=(None,None),
                                   auto_dismiss=False, size=(500, 500), pos_hint={"center_x":0.5, "center_y":0.5})
        self.loadingBalance.open()
        mythread = threading.Thread(target=self.update_balance_process)
        mythread.start()
        
    def update_balance_process(self):
        load_dotenv()
        api_key = os.getenv("CC_API")
        url = f"https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD"
        raw_data = self.read_json(url)
        btc_price = raw_data["USD"]
        app = App.get_running_app() 
        #my_wallet = app.my_wallet
        print(f"update_balance_process:\napp.wallets {app.wallets}, current wallet: {app.current_wallet}")
        index=None
        for i,w in enumerate(app.wallets):
            print(f"w.keys(): {w.keys()}")
            if list(w.keys())[0] == app.current_wallet: 
                index=i
                break
        my_wallet = app.wallets[index][app.current_wallet]
        my_wallet.start_conn()
        self.btc_balance = my_wallet.get_balance()/100000000
        print(f"balance: {self.btc_balance}")
        #self.btc_balance = app.btc_balance/100000000
        self.usd_balance = self.btc_balance * btc_price
        self.btc_balance_text =  str(self.btc_balance) + " BTC"
        self.usd_balance_text = "{:10.2f}".format(self.usd_balance) + " USD"
        
        print("closing loading window")
        self.loadingBalance.dismiss()
        my_wallet.close_conn()
        
    def read_json(self,url):
        request = Request(url)
        response = urlopen(request)
        data = response.read()
        url2 = json.loads(data)
        return url2
        

        
class SendScreen(Screen):
 
    def paste(self):
        text_to_paste = pyperclip.paste()
        self.ids.address.text = text_to_paste
  
    def confirm_popup(self):
        #reading the inputs and 
        denomination = self.ids.denomination.text
        amount = None
        try: 
            amount = float(self.ids.amount.text)
            address = self.ids.address.text
            if denomination == "Bitcoins": amount = int(amount*100000000)
            else: amount = int(amount)

            self.show = ConfirmSendPopup(amount,address,denomination)
            self.popupWindow = Popup(title="Confirm Transaction", content=self.show, size_hint=(None,None), size=(500,500), 
                                     pos_hint={"center_x":0.5, "center_y":0.5}
                                #auto_dismiss=False
                               )
            self.popupWindow.open()
            self.show.YES.bind(on_release=self.go_back)
            self.show.CANCEL.bind(on_release=self.popupWindow.dismiss)
        except: 
            #TRIGGER THE "WRONG INPUT POPUP"
            self.wrong_input = WrongInputPopup()
            self.wrongInputWindow = Popup(title="Not a valid amount", content=self.wrong_input, size_hint=(None,None), 
                                          size=(500,500), pos_hint={"center_x":0.5, "center_y":0.5}
                               )
            self.wrongInputWindow.open()
            self.wrong_input.OK.bind(on_release=self.wrongInputWindow.dismiss)                    

                                
    def send_tx(self,screen, amount, address):
        "the button is the Button object"
        print(screen.show.YES.text)
        print(f"amount: {amount}, address: {address}")
        print("SENDING TX")
        app = App.get_running_app() 
        #my_wallet = app.my_wallet
        index=None
        for i,w in enumerate(app.wallets):
            print(f"w.keys(): {w.keys()}")
            if list(w.keys())[0] == app.current_wallet: 
                index=i
                break
        my_wallet = app.wallets[index][app.current_wallet]
        my_wallet.start_conn()
        transaction = my_wallet.send([(address,amount)])
        print(f"SENT SUCCESSFULLY. TX ID: {transaction[0].transaction.id()}")
        
        
    def go_back(self,button):
        """
        Sends transaction, pops up a loading scree, cleans the inputs, and updates balances.
        """
        #disabling the button to avoid unintentional double action.
        self.show.YES.disabled = True
        
        #Creating the loading screen
        self.loading = LoadingPopup("Broadcasting your\ntransaction...")
        self.loadingWindow = Popup(title="Loading... ", content=self.loading,size_hint=(None,None),
                                   auto_dismiss=False, size=(500, 500), pos_hint={"center_x":0.5, "center_y":0.5})
        self.loadingWindow.open()
        mythread = threading.Thread(target=self.send_tx_process)
        mythread.start()
        
    def send_tx_process(self):
        #reading the inputs and 
        denomination = self.ids.denomination.text
        amount = float(self.ids.amount.text)                        
        address = self.ids.address.text
        address = address.replace("\n","")
        address = address.strip(" ")
        address = address.strip("'")
        starts = address.rfind("'")
        address = address[starts+1:]                        
        
        if denomination == "Bitcoins": amount = int(amount*100000000)
        else: amount = int(amount)
            
        #broadcasting transaction
        try: 
            self.send_tx(self, amount, address)
                                
            #cleanning the inputs
            self.ids.amount.text = ""
            self.ids.address.text = ""
                                
            #closing popups
            self.loadingWindow.dismiss()
                                
            #updating balance
            main = MainScreen()
            main.update_real_balance()

            self.popupWindow.dismiss()
                                
        except Exception as e:
                                
            if str(e).startswith("Not enough funds"):
                self.exception_popup = GenericOkPopup("You don't have enough\nfunds for this transaction.\n\nSorry :/")
                self.notEnoughFundsWindow = Popup(title="Not a valid amount", content=self.exception_popup, 
                                                  size_hint=(None,None),size=(500,500), 
                                                  pos_hint={"center_x":0.5, "center_y":0.5}
                                   )
                self.notEnoughFundsWindow.open()
                self.exception_popup.OK.bind(on_release=self.notEnoughFundsWindow.dismiss)                
                                
                #closing popups
                self.loadingWindow.dismiss()
                self.popupWindow.dismiss()
                                
            elif str(e).startswith("('Status Code 429'"):
                self.exception_popup = GenericOkPopup("Too many requests in the\npast hour.\nTry again later.")
                self.notEnoughFundsWindow = Popup(title="Server Error", content=self.exception_popup, 
                                                  size_hint=(None,None),size=(500,500), 
                                                  pos_hint={"center_x":0.5, "center_y":0.5}
                                   )
                self.notEnoughFundsWindow.open()
                self.exception_popup.OK.bind(on_release=self.notEnoughFundsWindow.dismiss)                
                                
                #closing popups
                self.loadingWindow.dismiss()
                self.popupWindow.dismiss()
                                 
            elif (str(e)[str(e).find(" ")+1:]).startswith("not a valid"):
                                
                msg1 = "You entered an invalid address.\nWe prevented the transaction from\nlosing your funds. "
                msg2 = "Please\nenter a valid address and try\nagain."
                self.exception_popup = GenericOkPopup(msg)
                self.notEnoughFundsWindow = Popup(title="Bad Address", content=self.exception_popup, 
                                                  size_hint=(None,None),size=(500,500), 
                                                  pos_hint={"center_x":0.5, "center_y":0.5}
                                   )
                self.notEnoughFundsWindow.open()
                self.exception_popup.OK.bind(on_release=self.notEnoughFundsWindow.dismiss)                
                                
                #closing popups
                self.loadingWindow.dismiss()
                self.popupWindow.dismiss()
                                
            else:
                #TRIGGER THE "OOPS! POPUP"
                self.exception_popup = GenericOkPopup("Oops! Something went wrong.\nPlease try again later.")
                self.notEnoughFundsWindow = Popup(title="Unknown Exception", content=self.exception_popup, 
                                                  size_hint=(None,None),size=(500,500), 
                                                  pos_hint={"center_x":0.5, "center_y":0.5}
                                   )
                self.notEnoughFundsWindow.open()
                self.exception_popup.OK.bind(on_release=self.notEnoughFundsWindow.dismiss)                
                                
                #closing popups
                self.loadingWindow.dismiss()
                self.popupWindow.dismiss()
                
        
        
        
        
        
    def scan_qr(self):
        self.qrscanner = CameraPopup()
        self.QRScannerWindow = Popup(title="Scan Qr Code", content=self.qrscanner, size_hint=(None,None), size=(500,700), 
                                 pos_hint={"center_x":0.5, "center_y":0.6}
                            #auto_dismiss=False
                           )
        self.QRScannerWindow.open()
        self.qrscanner.ids.select.bind(on_release=self.scanqr)
    
    
    def scanqr(self,button_object):
        self.ids.address.text = self.qrscanner.ids.address.text
        self.QRScannerWindow.dismiss()
        
class CameraPopup(FloatLayout):
    pass

class NewWalletPopup(FloatLayout):
    pass

class GenericOkPopup(FloatLayout):
    def __init__(self,msg_txt):
        super().__init__()
                                
        message = Label(text= msg_txt,
                       halign="center",size_hint= (0.6,0.3), 
                        pos_hint={"center_x":0.5, "center_y":0.65}, font_size="14sp"
                       )

        self.OK = Button(text="Ok. Got it!",
                     pos_hint= {"center_x":0.5, "center_y":0.18}, 
                     size_hint= (1,0.17),
                          background_color=[0.5,1,0.75,1]
                      )
        self.add_widget(message)
        self.add_widget(self.OK)                                
                                
class WrongInputPopup(FloatLayout):
    def __init__(self):
        super().__init__()
        #self.orientation="vertical")
        msg_txt1 = "Only decimal numbers are allowed\nin the 'Amount' field.\nPlease enter a valid amount of"
        msg_txt2 = " currency.\nMake sure you are\nselecting the right 'Units'(Bitcoins/Satoshis)."
        msg_txt3 = "\nFor example:\n0.0234 Bitcoins;  or:  2340000 Satoshis."
        msg_txt = msg_txt1 + msg_txt2 + msg_txt3
        message = Label(text= msg_txt,
                       halign="center",size_hint= (0.6,0.3), 
                        pos_hint={"center_x":0.5, "center_y":0.65}, font_size="12sp"
                       )

        self.OK = Button(text="Ok. Got it!",
                     pos_hint= {"center_x":0.5, "center_y":0.18}, 
                     size_hint= (1,0.17),
                          background_color=[0.5,1,0.75,1]
                      )
        self.add_widget(message)
        self.add_widget(self.OK)
            
        
class LoadingPopup(FloatLayout):
     def __init__(self,msg):
        super().__init__()
        
        self.message = Label(text=msg,
                            halign="center", size_hint=(1,1), pos_hint={"center_x":0.5, "center_y":0.5},
                            
                            )
        self.add_widget(self.message)
        
class ConfirmSendPopup(FloatLayout):
    def __init__(self,amount,address,denomination):
        super().__init__()
        #self.orientation="vertical")
            
        message = Label(text=f"Are you sure you want to send\n {amount/100000000} BTC to the adress\n{address}\n?",
                       halign="center",size_hint= (0.6,0.3), 
                        pos_hint={"center_x":0.5, "center_y":0.8}, font_size="11sp"
                       )

        self.YES = Button(text="YES",
                     pos_hint= {"center_x":0.5, "center_y":0.43}, 
                     size_hint= (1,0.17),
                          background_color=[0.5,1,0.75,1]
                      )
        self.CANCEL = Button(text="CANCEL",
                     pos_hint= {"center_x":0.5, "center_y":0.15}, 
                     size_hint= (1,0.3),
                             background_color=[1,0.3,0.3,1]
                      )
        self.add_widget(message)
        self.add_widget(self.YES)
        self.add_widget(self.CANCEL)
              
            
            
class TouchLabel(Label):       
    def on_touch_down(self, touch):
        Clock.schedule_once(lambda dt: pyperclip.copy(self.text))
        Label.on_touch_down(self, touch)
        


#class LabelButton
    
class QRcodePopup(FloatLayout):
    def __init__(self, address):
        super().__init__()
        #self.orientation="vertical")
        self.address = address
        
        
        if self.address:
            qrcode.make(self.address).save("images/QR.png")
        
            qrcode_image = AsyncImage(source='images/QR.png',
                                size_hint= (0.8, 0.8),size=(210,210),
                                pos_hint= {'center_x':.5, 'center_y': 0.65} )
        
            address = TouchLabel(text=self.address,
                           halign="center",size_hint= (0.6,0.25), 
                            pos_hint={"center_x":0.5, "center_y":0.23},
                            font_name= "Arial",
                            font_size="12sp",
                            
                           )
            self.add_widget(qrcode_image)
            self.add_widget(address)
        else:
            address = Label(text="NO UNUSED ADDRESSES\nAVAILABLE. \n\nPLEASE CREATE A\nNEW ADDRESS.",
                           halign="center",size_hint= (0.6,0.25), 
                            pos_hint={"center_x":0.5, "center_y":0.6},
                            font_name= "Arial",
                            font_size="15sp"
                           )
            self.add_widget(address)
            
        
        self.OK = Button(text="OK",
                     pos_hint= {"x":0, "y":0.01}, 
                     size_hint= (1,0.15),
                             background_color=[0.6,0.9,1,1]
                      )
        
        self.add_widget(self.OK)
        
            
        
        

        
class SelectOnePopup(FloatLayout):
    def __init__(self):
        super().__init__()
        #self.orientation="vertical")
        
        address = Label(text="YOU MUST SELECT ONE\nOPTION FOR THE ADDRESS\n\n(NEW ADDRESS)\nOR\nEXISTING UNUSED\nADDRESS)",
                        halign="center",size_hint= (0.6,0.25), 
                        pos_hint={"center_x":0.5, "center_y":0.7},
                        font_name= "Arial",
                        font_size="18sp"
                        )
        self.OK = Button(text="OK",
                     pos_hint= {"x":0, "y":0.01}, 
                     size_hint= (1,0.15),
                             background_color=[0.6,0.9,1,1]
                      )
        
        self.add_widget(self.OK)
        self.add_widget(address)

        
class ReceiveScreen(Screen):
    label_font_size = "15sp"
    address = None
    
    #def from_unused():
        

    def qr_popup(self):
        app = App.get_running_app() 
        index=None
        for i,w in enumerate(app.wallets):
            print(f"w.keys(): {w.keys()}")
            if list(w.keys())[0] == app.current_wallet: 
                index=i
                break
        my_wallet = app.wallets[index][app.current_wallet]
        my_wallet.start_conn()
        
        if self.ids.existing_addr.state == "down":
        
            addresses = my_wallet.get_unused_addresses_list()
            print(addresses)
            addr_type = self.ids.existing_addr.text
            
            if addr_type == "P2PKH (default)": 
                addresses_filtered = [x for x in addresses if x[0][0] in "1mn"]
                
            elif addr_type == "P2WPKH": 
                addresses_filtered = [x for x in addresses if x[0][:3] in ["tb1","bc1"]]
                
            else:
                addresses_filtered = [x for x in addresses if x[0][0] in "23"]

                
            if len(addresses_filtered)==0:
                self.show = QRcodePopup(None)
            else:
                self.show = QRcodePopup(addresses_filtered[0][0])
                
        elif self.ids.new_addr.state == "down":
            #app = App.get_running_app() 
            #my_wallet = app.my_wallet
            addr_type = self.ids.new_addr.text
            
            if addr_type == "P2PKH (default)": 
                addr_type = "P2PKH"
                
            account = my_wallet.create_receiving_address(addr_type)
            self.show = QRcodePopup(account.address)
        
        else: 
            self.show = SelectOnePopup()
    
        self.popupWindow = Popup(title="Address and QR Code", content=self.show, size_hint=(None,None), size=(550,700),
                                pos_hint={"center_x":0.5, "center_y":0.5})
        self.popupWindow.open()
        #self.show.YES.bind(on_press=self.send_tx)
        self.show.OK.bind(on_release=self.popupWindow.dismiss)
    
    def activate_spinner(self):
        new_addr = True
    
    
        
        
#class WindowManager(ScreenManager):
    #pass



class walletguiApp(App):
    
    title = "Wallet"
    #self.my_variable = StringProperty("THIS IS MY FLAG")
    """
    words = "engine over neglect science fatigue dawn axis parent mind man escape era goose border invest slab relax bind desert hurry useless lonely frozen morning"
    
    my_wallet = ObjectProperty()
    btc_balance = NumericProperty()
    
    my_wallet = Wallet.recover_from_words(words, 256, "RobertPauslon",True)
    btc_balance = my_wallet.get_balance()
    """
    my_wallet_names = ListProperty()
    wallets = ListProperty()
    current_wallet = StringProperty()
    db = ObjectProperty()
    sm = ObjectProperty()
    
    
    current_wallet = None
    db = Sqlite3Wallet()
    res =  db.does_table_exist("Wallets")
    print(res)
    
    if len(res)>0:
        
        #res = db.conn.cursor().execute("SELECT * FROM Wallets")
        #wallets = res.fetchall()
        res = db.get_all_wallets()
        print(f"the table exists, {res}")
        my_wallet_names = res
        
    else:
        my_wallet_names = []
        
    def build(self):
        #return Builder.load_file("walletgui.kv")
        #return WalletScreen()
        self.sm = ScreenManager()
        self.sm.add_widget(WalletScreen())
        self.sm.add_widget(MainScreen())
        self.sm.add_widget(ReceiveScreen())
        self.sm.add_widget(SendScreen())                       
        return self.sm

    def on_stop(self):
        self.db.close_database()

if __name__ == '__main__':
    walletguiApp().run()
    
    