import kivy
kivy.require('1.11.1') # replace with your current kivy version !
from wallet import Wallet
import qrcode
from urllib.request import Request, urlopen
import json
import os

from kivy.core.clipboard import Clipboard 

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.config import Config
from kivy.uix.image import AsyncImage
from kivy.properties import StringProperty,BooleanProperty, ObjectProperty, NumericProperty
from kivy.uix.screenmanager import ScreenManager, Screen
Config.set('graphics','width',300)
Config.set('graphics','height',600)



class MainScreen(Screen):
    btc_balance = NumericProperty()
    usd_balance = 0.0
    
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        # Initialize Target Container
        self.update_balance()
    
    
    btc_balance_text = StringProperty(str(btc_balance) + " BTC")
    usd_balance_text = StringProperty("{:10.2f}".format(usd_balance) + " USD")
    
    font_size = "20sp"
    
    def update_real_balance(self):
        self.ids.reload_button.disabled = True
        app = App.get_running_app() 
        my_wallet = app.my_wallet
        my_wallet.update_balance()  
        self.update_balance()
        self.ids.reload_button.disabled = False
    
    def update_balance(self):
        api_key = os.getenv("CC_API")
        url = f"https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD"
        raw_data = self.read_json(url)
        btc_price = raw_data["USD"]
        app = App.get_running_app() 
        my_wallet = app.my_wallet
        self.btc_balance = my_wallet.get_balance()/100000000
        print(f"balance: {self.btc_balance}")
        #self.btc_balance = app.btc_balance/100000000
        self.usd_balance = self.btc_balance * btc_price
        self.btc_balance_text =  str(self.btc_balance) + " BTC"
        self.usd_balance_text = "{:10.2f}".format(self.usd_balance) + " USD"
        
    def read_json(self,url):
        request = Request(url)
        response = urlopen(request)
        data = response.read()
        url2 = json.loads(data)
        return url2
        

        
class SendScreen(Screen):
    
    """
    def function():
        app = App.get_running_app() 
        print(app.root.manager.MainScreen.my_variable)
        
    function()
    """
    def paste(self):
        self.ids.address.text = Clipboard.paste()
  
    def confirm_popup(self):
        self.show = ConfirmSendPopup()
        self.popupWindow = Popup(title="Confirm Transaction", content=self.show, size_hint=(None,None), size=(280,280), 
                            #auto_dismiss=False
                           )
        self.popupWindow.open()
        self.show.YES.bind(on_release=self.go_back)
        self.show.CANCEL.bind(on_release=self.popupWindow.dismiss)
        
    
    def send_tx(self,screen, amount, address):
        "the button is the Button object"
        print(screen.show.YES.text)
        print(f"amount: {amount}, address: {address}")
        print("SENDING TX")
        app = App.get_running_app() 
        my_wallet = app.my_wallet
        transaction = my_wallet.send([(address,amount)])
        print(f"SENT SUCCESSFULLY. TX ID: {transaction[0].transaction.id()}")
        
        
    def go_back(self,button):
        main = MainScreen()
        self.show.YES.disabled = True
        denomination = self.ids.denomination.text
        amount = float(self.ids.amount.text)
        address = self.ids.address.text
        if denomination == "Bitcoins": amount = int(amount*100000000)
        else: amount = int(amount)
        self.send_tx(self, amount, address)
        print(self.ids)
        self.ids.amount.text = ""
        self.ids.address.text = ""
        self.popupWindow.dismiss()
        app = App.get_running_app() 
        my_wallet = app.my_wallet
        my_wallet.get_balance()
        main.update_real_balance()
        
        
        
class ConfirmSendPopup(FloatLayout):
    def __init__(self):
        super().__init__()
        #self.orientation="vertical")
        message = Label(text="Are you sure you want \nto send xx.xxx BTC to adress\n abc666lkp1233?",
                       halign="center",size_hint= (0.6,0.3), 
                        pos_hint={"x":0.2, "top":1}
                       )

        self.YES = Button(text="YES",
                     pos_hint= {"x":0, "y":0.35}, 
                     size_hint= (1,0.17),
                          background_color=[0.5,1,0.75,1]
                      )
        self.CANCEL = Button(text="CANCEL",
                     pos_hint= {"x":0, "y":-0.01}, 
                     size_hint= (1,0.3),
                             background_color=[1,0.3,0.3,1]
                      )
        self.add_widget(message)
        self.add_widget(self.YES)
        self.add_widget(self.CANCEL)
        

        
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
        
            address = Label(text=self.address,
                           halign="center",size_hint= (0.6,0.25), 
                            pos_hint={"center_x":0.5, "center_y":0.23},
                            font_name= "Arial",
                            font_size="12sp"
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
        my_wallet = app.my_wallet
        
        if self.ids.existing_addr.state == "down":
        
            addresses = my_wallet.get_unused_addresses_list()
            addr_type = self.ids.existing_addr.text
            
            if addr_type == "P2PKH (default)": 
                addresses_filtered = [x for x in addresses if x["unused_address.address"][0] in "1mn"]
                
            elif addr_type == "P2WPKH": 
                addresses_filtered = [x for x in addresses if x["unused_address.address"][:3] in ["tb1","bc1"]]
                
            else:
                addresses_filtered = [x for x in addresses if x["unused_address.address"][0] in "23"]

                
            if len(addresses_filtered)==0:
                self.show = QRcodePopup(None)
            else:
                self.show = QRcodePopup(addresses_filtered[0]["unused_address.address"])
                
        elif self.ids.new_addr.state == "down":
            app = App.get_running_app() 
            my_wallet = app.my_wallet
            addr_type = self.ids.new_addr.text
            
            if addr_type == "P2PKH (default)": 
                addr_type = "P2PKH"
                
            account = my_wallet.create_receiving_address(addr_type)
            self.show = QRcodePopup(account.address)
        
        else: 
            self.show = SelectOnePopup()
    
        self.popupWindow = Popup(title="Address and QR Code", content=self.show, size_hint=(None,None), size=(280,380))
        self.popupWindow.open()
        #self.show.YES.bind(on_press=self.send_tx)
        self.show.OK.bind(on_release=self.popupWindow.dismiss)
    
    def activate_spinner(self):
        new_addr = True
    
    
        
        
class WindowManager(ScreenManager):
    pass


class walletguiApp(App):
    
    title = "Wallet"
    #self.my_variable = StringProperty("THIS IS MY FLAG")
    
    words = "engine over neglect science fatigue dawn axis parent mind man escape era goose border invest slab relax bind desert hurry useless lonely frozen morning"
    
    my_wallet = ObjectProperty()
    btc_balance = NumericProperty()
    
    my_wallet = Wallet.recover_from_words(words, 256, "RobertPauslon",True)
    btc_balance = my_wallet.get_balance()
    
    def build(self):
        return Builder.load_file("walletgui.kv")


if __name__ == '__main__':
    walletguiApp().run()
    
    